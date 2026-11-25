"""Conservative self-repair for IDEA2APK Android builds.

Only applies deterministic Android SDK repairs that are safe to repeat.
It never rewrites generated application source code.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


MAX_ATTEMPTS = 3
SDK_PACKAGES = (
    "platform-tools",
    "platforms;android-34",
    "build-tools;34.0.0",
)


def classify_failure(log_text):
    text = (log_text or "").lower()
    if "aidl not found" in text or "aidl: not found" in text:
        return "missing_aidl"
    if "license is not accepted" in text or "licenses not accepted" in text:
        return "sdk_license"
    if "sdkmanager: command not found" in text or "sdkmanager not found" in text:
        return "missing_sdkmanager"
    if "no module named" in text or "modulenotfounderror" in text:
        return "missing_python_dependency"
    if "syntaxerror" in text or "indentationerror" in text:
        return "python_source_error"
    return "unknown"


def locate_sdk_root():
    candidates = [
        os.environ.get("ANDROID_SDK_ROOT"),
        os.environ.get("ANDROID_HOME"),
        str(Path.home() / ".buildozer/android/platform/android-sdk"),
        str(Path.home() / "Android/Sdk"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    return None


def locate_sdkmanager(sdk_root):
    if sdk_root:
        matches = list(sdk_root.glob("cmdline-tools/*/bin/sdkmanager"))
        if matches:
            return matches[-1]
        legacy = sdk_root / "tools/bin/sdkmanager"
        if legacy.exists():
            return legacy
    found = shutil.which("sdkmanager")
    return Path(found) if found else None


def repair_android_sdk(kind, log_text=""):
    if kind not in ("missing_aidl", "sdk_license"):
        return False, "No safe automatic Android SDK repair applies to this error."

    sdk_root = locate_sdk_root()
    sdkmanager = locate_sdkmanager(sdk_root)
    if not sdkmanager:
        return False, (
            "Could not locate Android sdkmanager. The build environment needs "
            "manual SDK setup; application source was not changed."
        )

    if sdk_root is None:
        sdk_root = sdkmanager.parents[3]
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(sdk_root)
    env["ANDROID_SDK_ROOT"] = str(sdk_root)

    license_result = subprocess.run(
        [str(sdkmanager), "--sdk_root=" + str(sdk_root), "--licenses"],
        input=("y\n" * 100),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=False,
    )
    install_result = subprocess.run(
        [str(sdkmanager), "--sdk_root=" + str(sdk_root), *SDK_PACKAGES],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=False,
    )

    build_tools = sdk_root / "build-tools/34.0.0"
    aidl = build_tools / "aidl"
    if install_result.returncode == 0 and aidl.exists():
        env_path = str(build_tools) + os.pathsep + env.get("PATH", "")
        os.environ["PATH"] = env_path
        os.environ["ANDROID_HOME"] = str(sdk_root)
        os.environ["ANDROID_SDK_ROOT"] = str(sdk_root)
        return True, "Installed/verified Android Build Tools 34.0.0 and AIDL."
    detail = (license_result.stdout + "\n" + install_result.stdout)[-1800:]
    return False, "Android SDK repair did not complete:\n" + detail



def repair_python_source(source_path):
    """Apply only provably safe cleanup, then verify Python syntax."""
    path = Path(source_path)
    if not path.is_file():
        return False, "Generated Python file was not found."

    original = path.read_text(encoding="utf-8-sig")
    repaired = original.replace("\r\n", "\n").replace("\r", "\n")
    lines = repaired.splitlines()
    fence = chr(96) * 3
    if len(lines) >= 2 and lines[0].strip().startswith(fence) and lines[-1].strip() == fence:
        repaired = "\n".join(lines[1:-1]) + "\n"

    if repaired == original:
        return False, "No safe source-code cleanup rule matched."

    try:
        compile(repaired, str(path), "exec")
    except SyntaxError as error:
        return False, "Safe cleanup did not resolve the syntax error: " + str(error)

    backup = path.with_suffix(path.suffix + ".autofix.bak")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
    temporary = path.with_suffix(path.suffix + ".autofix.tmp")
    temporary.write_text(repaired, encoding="utf-8")
    temporary.replace(path)
    return True, "Removed an accidental Markdown wrapper/BOM or normalized line endings. Original saved as " + backup.name + "."



def run_build(max_attempts=MAX_ATTEMPTS):
    attempts = max(1, min(int(max_attempts), MAX_ATTEMPTS))
    log_path = Path("idea2apk-build.log")

    for attempt in range(1, attempts + 1):
        print("IDEA2APK build attempt {}/{}".format(attempt, attempts), flush=True)
        with log_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                ["buildozer", "-v", "android", "debug"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ.copy(),
            )
            captured = []
            for line in process.stdout:
                print(line, end="", flush=True)
                log_file.write(line)
                captured.append(line)
            return_code = process.wait()

        if return_code == 0:
            print("IDEA2APK_BUILD_RESULT=SUCCESS", flush=True)
            return 0

        log_text = "".join(captured)
        kind = classify_failure(log_text)
        print("IDEA2APK_ERROR_CLASS=" + kind, flush=True)

        if attempt >= attempts:
            break
        if kind == "python_source_error":
            repaired, message = repair_python_source("main.py")
        else:
            repaired, message = repair_android_sdk(kind, log_text)
        print("IDEA2APK_AUTO_FIX: " + message, flush=True)
        if not repaired:
            break
        print("Retrying the build after the safe repair...", flush=True)

    print(
        "IDEA2APK_BUILD_RESULT=FAILED. See idea2apk-build.log. "
        "No generated app source was overwritten.",
        flush=True,
    )
    return 1


def main():
    parser = argparse.ArgumentParser(description="IDEA2APK safe Android build repair")
    parser.add_argument("--build", action="store_true", help="Build APK with safe repair retries")
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    args = parser.parse_args()

    if not args.build:
        parser.error("Use --build to run the APK build and repair loop.")

    source = Path("main.py")
    if not source.exists():
        print("ERROR: generated main.py was not found.", file=sys.stderr)
        return 2
    try:
        compile(source.read_text(encoding="utf-8-sig"), str(source), "exec")
    except (SyntaxError, UnicodeError) as error:
        repaired, message = repair_python_source(source)
        print("IDEA2APK_SOURCE_AUTO_FIX: " + message, flush=True)
        if not repaired:
            print(
                "AUTO-FIX STOPPED: this source error needs an AI/code review; "
                "the original file was preserved. " + str(error),
                file=sys.stderr,
            )
            return 2

    return run_build(args.max_attempts)


if __name__ == "__main__":
    sys.exit(main())
