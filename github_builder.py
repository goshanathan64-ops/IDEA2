import base64
import json
import re
import urllib.error
import urllib.request


WORKFLOW = """name: Build Generated Android APK

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-22.04
    steps:
      - name: Checkout generated app
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"

      - name: Install Android build dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip openjdk-17-jdk             autoconf automake libtool pkg-config zlib1g-dev             libncurses5-dev libffi-dev libssl-dev libltdl-dev cmake

      - name: Install Buildozer
        run: |
          python -m pip install --upgrade pip setuptools wheel
          python -m pip install buildozer==1.5.0 cython==0.29.33 virtualenv

      - name: Build debug APK
        run: buildozer -v android debug

      - name: Upload installable APK
        uses: actions/upload-artifact@v4
        with:
          name: Generated-Android-APK
          path: bin/*.apk
          if-no-files-found: error
          retention-days: 7
"""


def _request(url, token, method="GET", payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "IDEA2APK"
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            "GitHub API returned HTTP " + str(error.code) + ": " + detail[:700]
        )


def _put_file(api_base, token, branch, path, content, message):
    url = api_base + "/contents/" + path
    existing_sha = None
    try:
        existing = _request(url + "?ref=" + branch, token)
        existing_sha = existing.get("sha")
    except RuntimeError as error:
        if "HTTP 404" not in str(error):
            raise

    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch
    }
    if existing_sha:
        payload["sha"] = existing_sha
    _request(url, token, method="PUT", payload=payload)


def upload_and_dispatch(token, repository, app_code, build_spec):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Repository must be written as owner/name.")

    if repository.lower() == "goshanathan64-ops/idea2":
        raise ValueError(
            "Choose a separate empty repository for the generated app. "
            "Do not use the IDEA2APK source repository."
        )

    api_base = "https://api.github.com/repos/" + repository
    repo_info = _request(api_base, token)
    branch = repo_info.get("default_branch") or "main"

    files = [
        (".github/workflows/build-apk.yml", WORKFLOW),
        ("main.py", app_code),
        ("buildozer.spec", build_spec),
        ("requirements.txt", "buildozer==1.5.0\ncython==0.29.33\nvirtualenv\n"),
        ("README_IDEA2APK_BUILD.md",
         "# IDEA2APK generated project\n\n"
         "The GitHub Actions workflow builds a debug Android APK. "
         "Open the Actions tab and download the Generated-Android-APK artifact.\n")
    ]

    for path, content in files:
        _put_file(
            api_base, token, branch, path, content,
            "IDEA2APK: prepare Android APK build"
        )

    _request(
        api_base + "/actions/workflows/build-apk.yml/dispatches",
        token,
        method="POST",
        payload={"ref": branch}
    )

    return {
        "branch": branch,
        "actions_url": "https://github.com/" + repository + "/actions"
    }
