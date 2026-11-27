
import os
import re
import json
import uuid
import zipfile
import shutil

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.core.clipboard import Clipboard
from kivy.utils import platform
from kivy.clock import Clock
from threading import Thread

from github_builder import upload_and_dispatch
from project_schema import normalize_project, validate_project
from template_catalog import get_template, list_templates
from blueprint_intelligence import (analyze_blueprint_intelligence, render_blueprint_intelligence_summary,
    recommend_blueprint_improvements, render_blueprint_improvements)

from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup


APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(APP_DIR, "idea2apk_projects.json")
EXPORT_DIR = os.path.join(APP_DIR, "exports")


class IDEA2APK(App):

    def build(self):
        self.title = "IDEA2APK NEXT"
        self.projects = self.load_projects()
        self.current_project = None
        self.selected_template_id = "shop_inventory"
        self.generated_code = ""
        self.pending_blueprint_data = None

        self.manager = ScreenManager()

        self.home_screen = Screen(name="home")
        self.planner_screen = Screen(name="planner")
        self.projects_screen = Screen(name="projects")
        self.result_screen = Screen(name="result")
        self.blueprint_review_screen = Screen(name="blueprint_review")

        for screen in [
            self.home_screen,
            self.planner_screen,
            self.projects_screen,
            self.result_screen,
            self.blueprint_review_screen
        ]:
            self.manager.add_widget(screen)

        self.create_home_screen()
        self.create_planner_screen()
        self.create_projects_screen()
        self.create_result_screen()
        self.create_blueprint_review_screen()

        return self.manager

    def make_button(self, text, callback, height=48):
        btn = Button(
            text=text,
            size_hint_y=None,
            height=dp(height),
            font_size=sp(15)
        )
        btn.bind(on_release=callback)
        return btn

    def make_label(self, text, height=35, size=16):
        return Label(
            text=text,
            size_hint_y=None,
            height=dp(height),
            font_size=sp(size),
            halign="center",
            valign="middle"
        )

    def make_input(self, hint, height=48, multiline=False):
        return TextInput(
            hint_text=hint,
            size_hint_y=None,
            height=dp(height),
            multiline=multiline,
            font_size=sp(15),
            padding=dp(10)
        )

    # HOME SCREEN

    def create_home_screen(self):
        layout = BoxLayout(
            orientation="vertical",
            padding=dp(18),
            spacing=dp(12)
        )

        layout.add_widget(
            self.make_label("IDEA2APK", 65, 28)
        )

        layout.add_widget(
            self.make_label(
                "Turn your ideas into Android apps",
                45,
                16
            )
        )

        layout.add_widget(
            self.make_button(
                "SMART APP PLANNER",
                self.open_planner
            )
        )

        layout.add_widget(
            self.make_button(
                "MY PROJECTS",
                self.open_projects
            )
        )

        layout.add_widget(
            self.make_button(
                "TEMPLATE GALLERY",
                self.show_templates
            )
        )

        layout.add_widget(
            self.make_button(
                "ABOUT IDEA2APK",
                self.show_about
            )
        )

        self.home_screen.add_widget(layout)

    # PLANNER SCREEN

    def create_planner_screen(self):
        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8)
        )

        root.add_widget(
            self.make_label("SMART APP PLANNER", 45, 22)
        )

        self.template_status_label = self.make_label(
            "ACTIVE TEMPLATE: Shop & Inventory — READY",
            42,
            13
        )
        root.add_widget(self.template_status_label)

        scroll = ScrollView()

        form = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None
        )

        form.bind(minimum_height=form.setter("height"))

        form.add_widget(self.make_label("App name"))

        self.name_input = self.make_input(
            "Example: My Business App"
        )
        form.add_widget(self.name_input)

        form.add_widget(self.make_label("App description"))

        self.description_input = self.make_input(
            "Describe what your app does",
            90,
            True
        )
        form.add_widget(self.description_input)

        form.add_widget(self.make_label("Target users"))

        self.target_input = self.make_input(
            "Example: Customers, students, farmers"
        )
        form.add_widget(self.target_input)

        form.add_widget(self.make_label("App type"))

        self.type_input = self.make_input(
            "Example: Business, education, shopping"
        )
        form.add_widget(self.type_input)

        form.add_widget(self.make_label("App features"))

        self.template_guide_label = self.make_label(
            "Choose a template to see its recommended features.",
            72,
            12
        )
        form.add_widget(self.template_guide_label)

        self.features_input = self.make_input(
            "Enter features separated by commas",
            100,
            True
        )
        form.add_widget(self.features_input)

        form.add_widget(
            self.make_button(
                "GENERATE BLUEPRINT",
                self.generate_blueprint
            )
        )

        form.add_widget(
            self.make_button(
                "GENERATE APP CODE",
                self.generate_app_code
            )
        )

        form.add_widget(
            self.make_button(
                "SAVE PROJECT",
                self.save_current_project
            )
        )

        scroll.add_widget(form)
        root.add_widget(scroll)

        root.add_widget(
            self.make_button("BACK HOME", self.go_home)
        )

        self.planner_screen.add_widget(root)

    # PROJECTS SCREEN

    def create_projects_screen(self):
        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8)
        )

        root.add_widget(
            self.make_label("MY PROJECTS", 50, 22)
        )

        self.project_list = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None
        )

        self.project_list.bind(
            minimum_height=self.project_list.setter("height")
        )

        scroll = ScrollView()
        scroll.add_widget(self.project_list)
        root.add_widget(scroll)

        root.add_widget(
            self.make_button(
                "REFRESH PROJECTS",
                self.refresh_projects
            )
        )

        root.add_widget(
            self.make_button(
                "BACK HOME",
                self.go_home
            )
        )

        self.projects_screen.add_widget(root)

    # RESULT SCREEN

    def create_result_screen(self):
        root = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        root.add_widget(
            self.make_label(
                "GENERATED APP CODE",
                45,
                20
            )
        )

        self.generated_quality_label = self.make_label(
            "CODE QUALITY: Waiting for generation audit",
            74, 12
        )
        root.add_widget(self.generated_quality_label)

        self.result_text = TextInput(
            readonly=True,
            multiline=True,
            font_size=sp(12),
            size_hint_y=1
        )

        root.add_widget(self.result_text)

        root.add_widget(
            self.make_button(
                "EXPORT PROJECT ZIP",
                self.export_project_zip
            )
        )

        root.add_widget(
            self.make_button(
                "SHARE GENERATED CODE (COPY)",
                self.copy_generated_code
            )
        )

        root.add_widget(
            self.make_button(
                "BUILD APK (AUTO-FIX ENABLED)",
                self.open_github_build
            )
        )

        root.add_widget(
            self.make_button(
                "PREPARE APK BUILD (MANUAL)",
                self.prepare_apk_build
            )
        )

        root.add_widget(
            self.make_button(
                "BACK TO PLANNER",
                self.open_planner
            )
        )

        self.result_screen.add_widget(root)

    # BLUEPRINT REVIEW

    def create_blueprint_review_screen(self):
        root = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(6)
        )
        root.add_widget(self.make_label("REVIEW & SELECT APP FEATURES", 42, 19))
        self.blueprint_review_text = TextInput(
            readonly=True,
            multiline=True,
            font_size=sp(12),
            size_hint_y=None,
            height=dp(175)
        )
        root.add_widget(self.blueprint_review_text)
        self.blueprint_intelligence_label = self.make_label("BLUEPRINT INTELLIGENCE: Awaiting analysis", 92, 12)
        root.add_widget(self.blueprint_intelligence_label)

        root.add_widget(self.make_label(
            "Tick the features you want included. Untick anything you do not need.",
            42, 12
        ))
        feature_scroll = ScrollView(size_hint_y=1)
        self.review_feature_list = BoxLayout(
            orientation="vertical", spacing=dp(3), size_hint_y=None
        )
        self.review_feature_list.bind(
            minimum_height=self.review_feature_list.setter("height")
        )
        feature_scroll.add_widget(self.review_feature_list)
        root.add_widget(feature_scroll)
        self.dependency_preview_label = self.make_label(
            "AUTOMATIC REQUIREMENTS: None",
            58, 12
        )
        root.add_widget(self.dependency_preview_label)

        add_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(46), spacing=dp(5)
        )
        self.extra_feature_input = TextInput(
            hint_text="Add another feature",
            multiline=False, font_size=sp(13)
        )
        add_row.add_widget(self.extra_feature_input)
        add_row.add_widget(self.make_button("ADD", self.add_review_feature, 42))
        root.add_widget(add_row)

        root.add_widget(self.make_button(
            "APPROVE SELECTED FEATURES & GENERATE",
            self.approve_blueprint
        ))
        root.add_widget(self.make_button(
            "EDIT BLUEPRINT", self.edit_blueprint_from_review
        ))
        root.add_widget(self.make_button(
            "CANCEL REVIEW", self.cancel_blueprint_review
        ))
        self.review_feature_checks = {}
        self.blueprint_review_screen.add_widget(root)

    def refresh_review_feature_list(self, selected_features=None):
        from feature_engine import analyze_blueprint
        self.review_feature_list.clear_widgets()
        data = dict(self.pending_blueprint_data or {})
        analysis = analyze_blueprint(data)
        features = analysis["requested"]
        selected = set(features if selected_features is None else selected_features)
        self.review_feature_checks = {}
        for feature in features:
            status = "SUPPORTED" if feature in analysis["available"] else "NOT READY"
            row = BoxLayout(
                orientation="horizontal", size_hint_y=None, height=dp(42), spacing=dp(6)
            )
            check = CheckBox(
                active=feature in selected,
                size_hint_x=None, width=dp(44)
            )
            self.review_feature_checks[feature] = check
            check.bind(active=lambda *_: self.refresh_dependency_preview())
            label = Label(
                text=feature + "  [" + status + "]",
                font_size=sp(12), halign="left", valign="middle"
            )
            label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
            row.add_widget(check)
            row.add_widget(label)
            self.review_feature_list.add_widget(row)

        summary = (
            "APP: " + str(data.get("name") or "Unnamed app") +
            "\\nDESCRIPTION: " + str(data.get("description") or "Not provided") +
            "\\nTARGET USERS: " + str(data.get("target") or "Not specified") +
            "\\nTEMPLATE: " + analysis.get("template_id", "") +
            "\\nSUPPORTED: " + (", ".join(analysis["available"]) or "None") +
            "\\nNOT READY: " + (", ".join(analysis["unsupported"]) or "None") +
            "\\nAdded items are checked by the same template support rules."
        )
        self.blueprint_review_text.text = summary
        intelligence = analyze_blueprint_intelligence(data, analysis)
        self.blueprint_intelligence_label.text = render_blueprint_intelligence_summary(intelligence)
        self.refresh_dependency_preview()

    def add_blueprint_suggestions(self, *args):
        if not self.pending_blueprint_data:
            self.message("Create a blueprint review first.")
            return
        suggestions = getattr(self, "blueprint_improvement_suggestions", [])
        if not suggestions:
            self.message("There are no additional supported suggestions for this blueprint.")
            return
        selected = [
            name for name, checkbox in self.review_feature_checks.items()
            if checkbox.active
        ]
        for item in suggestions:
            feature = item["feature"]
            if feature not in selected:
                selected.append(feature)
        self.pending_blueprint_data["features"] = ", ".join(selected)
        self.refresh_review_feature_list(selected)
        self.message("Suggested features added to the review. Check the list and remove anything you do not want before generating.")

    def refresh_dependency_preview(self, *args):
        from feature_engine import preview_feature_dependencies
        data = dict(self.pending_blueprint_data or {})
        selected = [
            name for name, checkbox in self.review_feature_checks.items()
            if checkbox.active
        ]
        preview = preview_feature_dependencies(
            data.get("template_id") or "shop_inventory", selected
        )
        automatic = preview["automatic"]
        generated = preview["generated"]
        if hasattr(self, "dependency_preview_label"):
            from feature_engine import analyze_feature_compatibility, render_feature_compatibility
            compatibility = analyze_feature_compatibility(
                data.get("template_id") or "shop_inventory", selected
            )
            self.dependency_preview_label.text = render_feature_compatibility(compatibility)

    def add_review_feature(self, *args):
        if not self.pending_blueprint_data:
            return
        from feature_engine import canonical_feature
        raw = self.extra_feature_input.text.strip()
        if not raw:
            self.message("Enter a feature name first.")
            return
        feature = canonical_feature(raw)
        selected = [
            name for name, checkbox in self.review_feature_checks.items()
            if checkbox.active
        ]
        if feature not in self.review_feature_checks:
            selected.append(feature)
        else:
            selected = list(dict.fromkeys(selected + [feature]))
        self.pending_blueprint_data["features"] = ", ".join(selected)
        self.extra_feature_input.text = ""
        self.refresh_review_feature_list(selected)


    # PROJECT DATA

    def get_project_data(self):
        name = self.name_input.text.strip()
        description = self.description_input.text.strip()

        if not name:
            self.message("Please enter an app name.")
            return None

        data = {
            "id": (
                self.current_project["id"]
                if self.current_project
                else str(uuid.uuid4())
            ),
            "name": name,
            "description": description,
            "target": self.target_input.text.strip(),
            "app_type": self.type_input.text.strip(),
            "features": self.features_input.text.strip(),
            "category": self.type_input.text.strip().lower() or "business",
            "template_id": self.selected_template_id or "shop_inventory"
        }

        data = normalize_project(data)
        errors, _warnings = validate_project(data)
        if errors:
            self.message("\n".join(errors))
            return None
        return data

    # BLUEPRINT GENERATION

    def generate_blueprint(self, *args):
        data = self.get_project_data()
        if not data:
            return

        try:
            from feature_engine import prepare_blueprint_review
            review = prepare_blueprint_review(data)
            self.pending_blueprint_data = review["data"]
            self.current_project = data
            self.blueprint_review_text.text = review["text"]
            self.refresh_review_feature_list(review["analysis"]["requested"])
            self.manager.current = "blueprint_review"
        except Exception as error:
            self.message("Blueprint review failed:\\n" + str(error))

    def approve_blueprint(self, *args):
        if not self.pending_blueprint_data:
            self.message("Create a blueprint review before approving.")
            return
        # Apply the user's checkbox choices; unsupported requests stay visible for diagnostics.
        from feature_engine import apply_blueprint_feature_selection
        selected = [
            feature for feature, checkbox in self.review_feature_checks.items()
            if checkbox.active
        ]
        if not selected:
            self.message("Select at least one feature before generating the app.")
            return
        self.pending_blueprint_data = apply_blueprint_feature_selection(
            self.pending_blueprint_data, selected
        )
        self.current_project = dict(self.pending_blueprint_data)
        self.generate_app_code(use_approved=True)

    def edit_blueprint_from_review(self, *args):
        self.pending_blueprint_data = None
        self.manager.current = "planner"

    def cancel_blueprint_review(self, *args):
        self.pending_blueprint_data = None
        self.manager.current = "planner"

    # APP CODE GENERATION

    def generate_app_code(self, *args, use_approved=False):
        data = (
            dict(self.pending_blueprint_data)
            if use_approved and self.pending_blueprint_data
            else self.get_project_data()
        )

        if not data:
            return

        try:
            from generator_engine import generate_app_code
            from feature_engine import (
                analyze_blueprint, analyze_generated_app_quality,
                validate_generated_source, validate_feature_coverage,
                verify_generated_feature_consistency,
            )

            code = generate_app_code(data)
            template_id = str(data.get("template_id") or "shop_inventory")
            blueprint_analysis = analyze_blueprint(data)
            expected_features = blueprint_analysis["requested"]
            syntax = validate_generated_source(code)
            coverage = validate_feature_coverage(code, expected_features, template_id)
            consistency = verify_generated_feature_consistency(
                code, expected_features, template_id=template_id
            )
            quality = analyze_generated_app_quality(
                code, syntax, coverage, consistency, blueprint=data
            )
            if hasattr(self, "generated_quality_label"):
                self.generated_quality_label.text = (
                    "CODE QUALITY: {}/100 — {}\\n".format(
                        quality["score"], quality["grade"]
                    ) +
                    "Checks passed: {}/{}\\n".format(
                        len(quality["passed"]), len(quality["checks"])
                    ) +
                    ("Warnings: " + "; ".join(quality["warnings"])
                     if quality["warnings"] else "No static quality warnings.") +
                    ("\\nAndroid device testing is still required."
                     if syntax["valid"] else
                     "\\nGeneration stopped: Python syntax is invalid.")
                )
            if not syntax["valid"]:
                self.generated_code = ""
                self.message(
                    "Generated code failed Python syntax validation. "
                    "It cannot be exported or built until repaired: " +
                    "; ".join(syntax["errors"])
                )
                return

            self.generated_code = code
            self.current_project = data
            self.pending_blueprint_data = None
            self.result_text.text = code
            self.manager.current = "result"
            self.selected_template_id = data.get("template_id", "shop_inventory")
            template = get_template(self.selected_template_id)
            template_name = template["name"] if template else self.selected_template_id
            self.refresh_template_status()
            self.message(
                "Generated using the " + template_name + " template. "
                "The source includes a blueprint verification report showing "
                "implemented and unsupported features. Review it before exporting "
                "or building. Android device testing is still required."
            )

        except Exception as error:
            self.message("Code generation failed:\\n" + str(error))

    # SAVE AND LOAD PROJECTS

    def load_projects(self):
        try:
            if os.path.exists(PROJECTS_FILE):
                with open(
                    PROJECTS_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:
                    saved = json.load(file)
                    if not isinstance(saved, list):
                        return []
                    # Upgrade older saved projects in memory while preserving their fields.
                    return [
                        normalize_project(project)
                        for project in saved
                        if isinstance(project, dict)
                    ]
        except Exception:
            pass

        return []

    def save_projects(self):
        try:
            with open(
                PROJECTS_FILE,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    self.projects,
                    file,
                    indent=4
                )

            return True

        except Exception as error:
            self.message("Save failed: " + str(error))
            return False

    def save_current_project(self, *args):
        data = self.get_project_data()

        if not data:
            return

        found = False

        for index, project in enumerate(self.projects):
            if project.get("id") == data["id"]:
                self.projects[index] = data
                found = True
                break

        if not found:
            self.projects.append(data)

        self.current_project = data

        if self.save_projects():
            self.message("Project saved successfully.")

    def open_projects(self, *args):
        self.refresh_projects()
        self.manager.current = "projects"

    def refresh_projects(self, *args):
        self.project_list.clear_widgets()

        if not self.projects:
            self.project_list.add_widget(
                self.make_label("No saved projects yet.", 50)
            )
            return

        for project in self.projects:
            name = project.get("name", "Unnamed project")

            row = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(145),
                spacing=dp(5)
            )

            row.add_widget(
                self.make_label(name, 35, 17)
            )

            row.add_widget(
                self.make_button(
                    "OPEN / EDIT",
                    lambda btn, p=project: self.edit_project(p),
                    38
                )
            )

            row.add_widget(
                self.make_button(
                    "DELETE",
                    lambda btn, p=project: self.delete_project(p),
                    38
                )
            )

            self.project_list.add_widget(row)

    def edit_project(self, project):
        # Normalize old V2 records so their template choice is always explicit.
        project = normalize_project(project)
        self.current_project = project
        self.selected_template_id = project.get("template_id", "shop_inventory")
        self.refresh_template_status()

        self.name_input.text = project.get("name", "")
        self.description_input.text = project.get("description", "")
        self.target_input.text = project.get("target", "")
        self.type_input.text = project.get("app_type", "")
        self.features_input.text = project.get("features", "")
        self.refresh_template_status()

        self.manager.current = "planner"

    def delete_project(self, project):
        self.projects = [
            item for item in self.projects
            if item.get("id") != project.get("id")
        ]

        self.save_projects()
        self.refresh_projects()
        self.message("Project deleted.")

    # BUILD SPEC GENERATOR

    def create_buildozer_spec(self, data):
        package_name = re.sub(
            r"[^a-z0-9]",
            "",
            data["name"].lower().replace(" ", "")
        )

        if not package_name:
            package_name = "mybusiness"

        return """[app]
title = {title}
package.name = {package}
package.domain = com.nexgen

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,txt

version = 0.1

requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 21
android.ndk = 25b
p4a.branch = v2024.01.21
android.build_tools_version = 34.0.0
android.accept_sdk_license = True

android.archs = arm64-v8a, armeabi-v7a

# Use Android's system file picker; no broad storage permission is needed.
android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 1
""".format(
            title=data["name"],
            package=package_name
        )

    # STAGE 5: ZIP EXPORT

    def create_github_workflow(self):
        return """name: Build Android APK

on:
  workflow_dispatch:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-22.04
    steps:
      - name: Checkout repository
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

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip autoconf automake libtool pkg-config zlib1g-dev libncurses5-dev libffi-dev libssl-dev libltdl-dev cmake

      - name: Install Buildozer
        run: |
          python -m pip install --upgrade pip setuptools wheel
          python -m pip install -r requirements.txt

      - name: Build Android APK
        run: buildozer -v android debug

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: Generated-Android-APK
          path: bin/*.apk
          if-no-files-found: error
"""

    def create_requirements_txt(self):
        return (
            "buildozer==1.5.0\n"
            "cython==0.29.33\n"
            "virtualenv\n"
        )

    def export_project_zip(self, *args):
        if not self.generated_code:
            self.message("Generate app code first.")
            return

        try:
            os.makedirs(EXPORT_DIR, exist_ok=True)

            data = self.current_project or {
                "name": "MyBusiness",
                "description": "Generated application"
            }

            folder_name = re.sub(
                r"[^A-Za-z0-9_-]",
                "_",
                data["name"]
            )

            if not folder_name:
                folder_name = "MyBusiness"

            zip_path = os.path.join(
                EXPORT_DIR,
                folder_name + ".zip"
            )

            with zipfile.ZipFile(
                zip_path,
                "w",
                zipfile.ZIP_DEFLATED
            ) as archive:

                archive.writestr(
                    "main.py",
                    self.generated_code
                )

                archive.writestr(
                    "README.md",
                    "# " + data["name"] + "\n\n"
                    + data.get("description", "") + "\n\n"
                    + "## Build the Android APK\n"
                    + "1. Upload all extracted files to a new GitHub repository.\n"
                    + "2. Open the Actions tab.\n"
                    + "3. Run the Build Android APK workflow.\n"
                    + "4. Download the Generated-Android-APK artifact.\n"
                )

                archive.writestr(
                    "buildozer.spec",
                    self.create_buildozer_spec(data)
                )

                archive.writestr(
                    "requirements.txt",
                    self.create_requirements_txt()
                )

                archive.writestr(
                    ".github/workflows/build.yml",
                    self.create_github_workflow()
                )

            if not os.path.exists(zip_path):
                self.message("ZIP file could not be created.")
                return

            self.save_zip_with_picker(zip_path)

        except Exception as error:
            self.message(
                "ZIP export failed:\n" + str(error)
            )

    # ANDROID ZIP EXPORT USING THE SYSTEM FILE PICKER

    def save_zip_with_picker(self, zip_path):
        """Let Android choose where to save the ZIP; no storage permission needed."""
        if platform != "android":
            self.message("ZIP saved at:\\n" + zip_path)
            return

        try:
            from jnius import autoclass
            from android import activity

            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            self._pending_export_path = zip_path
            self._export_request_code = 7301

            intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("application/zip")
            intent.putExtra(
                Intent.EXTRA_TITLE,
                os.path.basename(zip_path)
            )

            # The Android system picker grants access only to the chosen file.
            activity.bind(on_activity_result=self.on_export_activity_result)
            PythonActivity.mActivity.startActivityForResult(
                intent,
                self._export_request_code
            )

        except Exception as error:
            self.message(
                "Could not open Android save window:\\n" + str(error)
            )

    def on_export_activity_result(self, request_code, result_code, intent):
        if request_code != getattr(self, "_export_request_code", None):
            return

        from android import activity
        from jnius import autoclass
        activity.unbind(on_activity_result=self.on_export_activity_result)

        try:
            Activity = autoclass("android.app.Activity")
            if result_code != Activity.RESULT_OK or intent is None:
                self.message("ZIP export cancelled. No file was saved.")
                return

            uri = intent.getData()
            if uri is None:
                self.message("Android did not return a save location.")
                return

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            resolver = PythonActivity.mActivity.getContentResolver()
            output_stream = resolver.openOutputStream(uri)

            if output_stream is None:
                self.message("Android could not open the selected save location.")
                return

            try:
                with open(self._pending_export_path, "rb") as source:
                    while True:
                        chunk = source.read(64 * 1024)
                        if not chunk:
                            break
                        output_stream.write(bytearray(chunk))
                output_stream.flush()
            finally:
                output_stream.close()

            self.message(
                "SUCCESS!\\n\\nProject ZIP saved to the location you selected:\\n"
                + os.path.basename(self._pending_export_path)
            )

        except Exception as error:
            self.message("ZIP save failed:\\n" + str(error))


    # COPY GENERATED CODE

    def copy_generated_code(self, *args):
        if not self.generated_code:
            self.message("Generate app code first.")
            return

        try:
            Clipboard.copy(self.generated_code)
            self.message("Code copied to clipboard.")

        except Exception as error:
            self.message("Copy failed: " + str(error))

    # REAL APK BUILD THROUGH GITHUB ACTIONS

    def open_github_build(self, *args):
        if not self.generated_code:
            self.message("Generate app code first.")
            return

        content = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8)
        )
        content.add_widget(Label(
            text="Enter a GitHub repository you own or can write to.",
            size_hint_y=None,
            height=dp(48)
        ))
        self.github_repo_input = TextInput(
            hint_text="username/repository",
            multiline=False,
            size_hint_y=None,
            height=dp(48)
        )
        content.add_widget(self.github_repo_input)
        content.add_widget(Label(
            text="GitHub Personal Access Token (not saved)",
            size_hint_y=None,
            height=dp(35)
        ))
        self.github_token_input = TextInput(
            hint_text="Paste token with Contents and Actions write access",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(48)
        )
        content.add_widget(self.github_token_input)
        content.add_widget(Label(
            text="The token is used only for this build and is not written to project files.",
            size_hint_y=None,
            height=dp(48)
        ))
        content.add_widget(self.make_button(
            "UPLOAD PROJECT AND START APK BUILD",
            self.start_github_build,
            52
        ))
        content.add_widget(self.make_button(
            "CANCEL",
            lambda *_: self.github_build_popup.dismiss(),
            42
        ))
        self.github_build_popup = Popup(
            title="GitHub APK Builder",
            content=content,
            size_hint=(0.94, 0.72)
        )
        self.github_build_popup.open()

    def start_github_build(self, *args):
        repo = self.github_repo_input.text.strip()
        token = self.github_token_input.text.strip()

        if "/" not in repo or len(repo.split("/")) != 2:
            self.message("Enter the repository as username/repository.")
            return
        if not token:
            self.message("A GitHub token is required to upload and start the build.")
            return

        data = self.current_project or {"name": "MyBusiness"}
        project = {
            "name": data.get("name", "MyBusiness"),
            "description": data.get("description", "")
        }
        code = self.generated_code
        spec = self.create_buildozer_spec(project)
        self.github_token_input.text = ""
        self.github_build_popup.dismiss()
        self.message("Uploading project. The build will check generated Python code, detect supported Android SDK errors, and retry safe repairs up to three times.")

        def worker():
            try:
                result = upload_and_dispatch(token, repo, code, spec)
                message = (
                    "BUILD STARTED WITH AUTO-FIX ENABLED.\n\n"
                    "Open this Actions page to monitor the build:\n"
                    + result["actions_url"]
                    + "\n\nWhen complete, download the Generated-Android-APK artifact."
                )
            except Exception as error:
                message = "GitHub build could not start:\n" + str(error)

            Clock.schedule_once(lambda _dt: self.message(message), 0)

        Thread(target=worker, daemon=True).start()

    # PREPARE APK BUILD

    def prepare_apk_build(self, *args):
        if not self.generated_code:
            self.message("Generate app code first.")
            return

        try:
            data = self.current_project or {
                "name": "MyBusiness"
            }

            folder = os.path.join(
                EXPORT_DIR,
                "apk_build"
            )

            os.makedirs(folder, exist_ok=True)

            with open(
                os.path.join(folder, "main.py"),
                "w",
                encoding="utf-8"
            ) as file:
                file.write(self.generated_code)

            with open(
                os.path.join(folder, "buildozer.spec"),
                "w",
                encoding="utf-8"
            ) as file:
                file.write(
                    self.create_buildozer_spec(data)
                )

            with open(
                os.path.join(folder, "README.txt"),
                "w",
                encoding="utf-8"
            ) as file:
                file.write(
                    "IDEA2APK BUILD PACKAGE\n\n"
                    "Upload these files to your GitHub project "
                    "and build using Buildozer.\n"
                )

            self.message(
                "APK build files prepared:\n" + folder
            )

        except Exception as error:
            self.message(
                "Preparation failed:\n" + str(error)
            )

    # V3 TEMPLATE GALLERY

    def show_templates(self, *args):
        body = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )
        scroll = ScrollView()
        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(8)
        )
        content.bind(minimum_height=content.setter("height"))

        for template in list_templates():
            status = "READY" if template["status"] == "ready" else "COMING SOON"
            card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(140),
                spacing=dp(4)
            )
            card.add_widget(self.make_label(
                template["name"] + " — " + status,
                38,
                16
            ))
            card.add_widget(self.make_label(
                template["description"],
                38,
                12
            ))
            card.add_widget(self.make_button(
                "VIEW / SELECT TEMPLATE",
                lambda _button, item=template: self.show_template_details(item),
                38
            ))
            content.add_widget(card)

        scroll.add_widget(content)
        body.add_widget(scroll)
        popup = Popup(
            title="V3 TEMPLATE GALLERY",
            content=body,
            size_hint=(0.92, 0.82)
        )
        body.add_widget(self.make_button("CLOSE", lambda *_: popup.dismiss()))
        popup.open()

    def show_template_details(self, template, *args):
        ready = template.get("status") == "ready"
        status = "READY TO USE" if ready else "COMING SOON — GENERATOR NOT READY"
        supported = template.get("supported_features", [])
        feature_text = (
            "\\n".join("• " + item.replace("_", " ").title() for item in supported)
            if supported else "No working features have been released for this template yet."
        )

        body = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8)
        )
        body.add_widget(self.make_label(template.get("name", "Template"), 42, 20))
        body.add_widget(self.make_label(status, 36, 14))
        body.add_widget(self.make_label(template.get("description", ""), 64, 13))
        body.add_widget(self.make_label("SUPPORTED FEATURES", 32, 14))
        body.add_widget(self.make_label(feature_text, 120, 12))

        detail_popup = Popup(
            title="TEMPLATE PREVIEW",
            content=body,
            size_hint=(0.92, 0.78)
        )

        if ready:
            body.add_widget(self.make_button(
                "USE THIS TEMPLATE",
                lambda *_: self.apply_template(template, detail_popup),
                48
            ))
        else:
            body.add_widget(self.make_label(
                "This template is visible in the gallery but cannot create projects yet.",
                48,
                12
            ))

        body.add_widget(self.make_button("BACK TO GALLERY", lambda *_: detail_popup.dismiss()))
        detail_popup.open()

    def refresh_template_status(self):
        from template_catalog import get_template, template_planner_guide

        template = get_template(self.selected_template_id or "shop_inventory")
        if hasattr(self, "template_guide_label"):
            self.template_guide_label.text = template_planner_guide(
                self.selected_template_id or "shop_inventory"
            )
        if template is None:
            label = "Unknown template"
        else:
            state = "READY" if template.get("status") == "ready" else "COMING SOON"
            label = template.get("name", "Template") + " — " + state
        if hasattr(self, "template_status_label"):
            self.template_status_label.text = "ACTIVE TEMPLATE: " + label

    def apply_template(self, template, popup=None, *args):
        if template.get("status") != "ready":
            self.message("This template is not ready to use yet.")
            return

        self.selected_template_id = template["id"]
        self.refresh_template_status()
        self.current_project = None
        self.name_input.text = ""
        self.description_input.text = template.get("description", "")
        self.target_input.text = ""
        self.type_input.text = template.get("category", "business").title()
        self.features_input.text = ", ".join(template.get("supported_features", []))

        if popup is not None:
            popup.dismiss()

        self.manager.current = "planner"
        self.message(
            template["name"] + " selected. Enter your app name and target users, "
            "then generate the app code. Your project will use this template."
        )

    # ABOUT AND NAVIGATION

    def show_about(self, *args):
        self.message(
            "IDEA2APK\n\n"
            "A NexGen project for turning app ideas "
            "into Android application projects."
        )

    def message(self, text):
        popup = Popup(
            title="IDEA2APK",
            content=Label(
                text=text,
                halign="center"
            ),
            size_hint=(0.88, 0.4)
        )

        popup.open()

    def open_planner(self, *args):
        self.manager.current = "planner"

    def go_home(self, *args):
        self.manager.current = "home"


if __name__ == "__main__":
    IDEA2APK().run()
