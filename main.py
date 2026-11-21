
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

from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup


APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(APP_DIR, "idea2apk_projects.json")
EXPORT_DIR = os.path.join(APP_DIR, "exports")


class IDEA2APK(App):

    def build(self):
        self.title = "IDEA2APK"
        self.projects = self.load_projects()
        self.current_project = None
        self.generated_code = ""
        self.generated_is_app_code = False

        self.manager = ScreenManager()

        self.home_screen = Screen(name="home")
        self.planner_screen = Screen(name="planner")
        self.projects_screen = Screen(name="projects")
        self.result_screen = Screen(name="result")

        for screen in [
            self.home_screen,
            self.planner_screen,
            self.projects_screen,
            self.result_screen
        ]:
            self.manager.add_widget(screen)

        self.create_home_screen()
        self.create_planner_screen()
        self.create_projects_screen()
        self.create_result_screen()

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

        self.features_input = self.make_input(
            "Enter features separated by commas",
            100,
            True
        )
        form.add_widget(self.features_input)

        # Optional details that complete the 16-section app blueprint.
        self.extra_inputs = {}
        extra_fields = [
            ("logo_version", "Logo idea and app version", "Example: Blue and white logo; version 1.0"),
            ("user_accounts", "User accounts and permissions", "Example: Owner login, staff accounts, customer accounts"),
            ("screens", "Screens and navigation", "Example: Dashboard, products, sales, settings"),
            ("database", "Database and data to store", "Example: Products, prices, stock, customers, sales"),
            ("business_logic", "Business rules and workflows", "Example: Reduce stock automatically after each sale"),
            ("design", "Design and branding", "Example: Green theme, large buttons, simple layout"),
            ("notifications", "Notifications and reminders", "Example: Low-stock alerts and payment reminders"),
            ("reports", "Reports and analytics", "Example: Daily sales, monthly profit, stock reports"),
            ("connectivity", "Internet and offline requirements", "Example: Works offline; syncs when internet is available"),
            ("security", "Security and data protection", "Example: PIN login, role permissions, backups"),
            ("monetization", "Monetization and payments", "Example: Free app, subscriptions, mobile money"),
            ("platforms", "Target platforms", "Example: Android phone and tablet"),
            ("testing", "Testing and release requirements", "Example: Test adding products, sales, stock and reports")
        ]

        for key, heading, hint in extra_fields:
            form.add_widget(self.make_label(heading, 35, 15))
            field = self.make_input(hint, 72, True)
            self.extra_inputs[key] = field
            form.add_widget(field)

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

        self.result_text = TextInput(
            readonly=False,
            multiline=True,
            font_size=sp(12),
            size_hint_y=1
        )

        root.add_widget(self.result_text)
        self.result_text.bind(text=self.on_result_text_change)

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
                "BUILD APK (CREATE BUILD PACKAGE)",
                self.build_apk
            )
        )

        root.add_widget(
            self.make_button(
                "BACK TO PLANNER",
                self.open_planner
            )
        )

        self.result_screen.add_widget(root)

    def on_result_text_change(self, instance, value):
        # Keep the editable result window as the single source of truth.
        self.generated_code = value

    # PROJECT DATA

    def get_project_data(self):
        name = self.name_input.text.strip()
        description = self.description_input.text.strip()

        if not name:
            self.message("Please enter an app name.")
            return None

        return {
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
            **{
                key: field.text.strip()
                for key, field in self.extra_inputs.items()
            }
        }

    # BLUEPRINT GENERATION

    def generate_blueprint(self, *args):
        data = self.get_project_data()

        if not data:
            return

        def value(key):
            return data.get(key, "").strip() or "Not specified"

        sections = [
            ("1. APP IDENTITY", "Name: " + value("name") + "\nDescription: " + value("description") + "\nLogo and version: " + value("logo_version")),
            ("2. TARGET USERS", value("target")),
            ("3. APP CATEGORY", value("app_type")),
            ("4. CORE FEATURES", value("features")),
            ("5. USER ACCOUNTS AND PERMISSIONS", value("user_accounts")),
            ("6. SCREENS AND NAVIGATION", value("screens")),
            ("7. DATABASE AND DATA STORAGE", value("database")),
            ("8. BUSINESS LOGIC AND WORKFLOWS", value("business_logic")),
            ("9. DESIGN AND BRANDING", value("design")),
            ("10. NOTIFICATIONS AND REMINDERS", value("notifications")),
            ("11. REPORTS AND ANALYTICS", value("reports")),
            ("12. INTERNET AND OFFLINE REQUIREMENTS", value("connectivity")),
            ("13. SECURITY AND DATA PROTECTION", value("security")),
            ("14. MONETIZATION AND PAYMENTS", value("monetization")),
            ("15. TARGET PLATFORMS", value("platforms")),
            ("16. TESTING AND RELEASE REQUIREMENTS", value("testing"))
        ]

        blueprint = "IDEA2APK COMPLETE APP BLUEPRINT\n"
        blueprint += "================================\n\n"
        for heading, details in sections:
            blueprint += heading + "\n" + details + "\n\n"
        blueprint += "NEXT STEP: Review this blueprint, then generate the application code."

        self.generated_code = blueprint
        self.generated_is_app_code = False
        self.current_project = data
        self.result_text.text = blueprint
        self.manager.current = "result"

    # APP CODE GENERATION

    def generate_app_code(self, *args):
        data = self.get_project_data()
        if not data:
            return

        # Generate a reusable local-data app shell from the user's own feature list.
        feature_names = [
            item.strip() for item in data.get("features", "").split(",")
            if item.strip()
        ]
        if not feature_names:
            feature_names = ["General Records", "Tasks", "Customers"]

        # Keep the generated navigation manageable on a phone.
        feature_names = feature_names[:12]
        app_title = data["name"].strip()
        description = data.get("description", "").strip()

        code = r'''# Generated by IDEA2APK — blueprint-driven starter app
import os
import json
from datetime import datetime

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

APP_TITLE = __APP_TITLE__
APP_DESCRIPTION = __APP_DESCRIPTION__
FEATURES = __FEATURES__


class GeneratedApp(App):
    def build(self):
        self.title = APP_TITLE
        self.data_file = os.path.join(self.user_data_dir, "app_records.json")
        self.records = self.load_records()
        self.active_feature = None

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        heading = Label(text=APP_TITLE, size_hint_y=None, height=dp(48),
                        font_size=sp(22), bold=True)
        root.add_widget(heading)
        self.status = Label(text=APP_DESCRIPTION or "Your app workspace",
                            size_hint_y=None, height=dp(42), font_size=sp(12))
        root.add_widget(self.status)

        scroll = ScrollView()
        self.content = BoxLayout(orientation="vertical", spacing=dp(7),
                                 size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll.add_widget(self.content)
        root.add_widget(scroll)
        self.show_home()
        return root

    def load_records(self):
        try:
            with open(self.data_file, "r", encoding="utf-8") as handle:
                saved = json.load(handle)
            if isinstance(saved, dict):
                return saved
        except (OSError, ValueError, TypeError):
            pass
        return {feature: [] for feature in FEATURES}

    def save_records(self):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as handle:
                json.dump(self.records, handle, indent=2, ensure_ascii=False)
            self.status.text = "Saved on this device"
            return True
        except Exception as error:
            self.status.text = "Save error: " + str(error)
            return False

    def clear_content(self):
        self.content.clear_widgets()

    def add_label(self, text, height=38, size=15):
        label = Label(text=str(text), size_hint_y=None, height=dp(height),
                      font_size=sp(size), halign="left", valign="middle")
        label.bind(size=lambda obj, value: setattr(obj, "text_size", (value[0], None)))
        self.content.add_widget(label)

    def add_button(self, text, callback):
        button = Button(text=text, size_hint_y=None, height=dp(46),
                        font_size=sp(14))
        button.bind(on_release=lambda instance: callback())
        self.content.add_widget(button)

    def show_home(self):
        self.clear_content()
        self.add_label("APP WORKSPACE", 42, 19)
        self.add_label("Choose a feature to manage its records.", 40, 13)
        for feature in FEATURES:
            self.add_button(feature, lambda selected=feature: self.show_feature(selected))
        self.add_label("Your records are stored locally on this device.", 44, 12)

    def show_feature(self, feature):
        self.active_feature = feature
        self.clear_content()
        self.add_label(feature.upper(), 42, 19)
        self.add_button("ADD NEW RECORD", self.add_record)
        entries = self.records.setdefault(feature, [])
        if not entries:
            self.add_label("No records yet. Tap ADD NEW RECORD to begin.", 48, 13)
        for index, entry in enumerate(entries):
            title = entry.get("title", "Untitled")
            details = entry.get("details", "")
            self.add_label(str(index + 1) + ". " + title, 34, 15)
            if details:
                self.add_label(details, 48, 12)
            self.add_label("Created: " + entry.get("created", ""), 28, 11)
            self.add_button("DELETE RECORD " + str(index + 1),
                            lambda position=index: self.delete_record(position))
        self.add_button("BACK TO HOME", self.show_home)

    def add_record(self):
        panel = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        title_field = TextInput(hint_text="Record title", multiline=False,
                                size_hint_y=None, height=dp(44))
        details_field = TextInput(hint_text="Details (optional)", multiline=True,
                                  size_hint_y=None, height=dp(100))
        panel.add_widget(title_field)
        panel.add_widget(details_field)
        controls = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        popup = Popup(title="Add " + str(self.active_feature), content=panel,
                      size_hint=(0.9, None), height=dp(300))
        save_button = Button(text="SAVE")
        cancel_button = Button(text="CANCEL")
        controls.add_widget(save_button)
        controls.add_widget(cancel_button)
        panel.add_widget(controls)

        def submit(instance):
            title = title_field.text.strip()
            if not title:
                self.status.text = "Enter a title before saving."
                return
            self.records.setdefault(self.active_feature, []).append({
                "title": title,
                "details": details_field.text.strip(),
                "created": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            popup.dismiss()
            if self.save_records():
                self.show_feature(self.active_feature)

        save_button.bind(on_release=submit)
        cancel_button.bind(on_release=lambda instance: popup.dismiss())
        popup.open()

    def delete_record(self, index):
        entries = self.records.setdefault(self.active_feature, [])
        if 0 <= index < len(entries):
            entries.pop(index)
            self.save_records()
            self.show_feature(self.active_feature)


if __name__ == "__main__":
    GeneratedApp().run()
'''
        code = code.replace("__APP_TITLE__", repr(app_title))
        code = code.replace("__APP_DESCRIPTION__", repr(description))
        code = code.replace("__FEATURES__", repr(feature_names))

        self.generated_code = code
        self.generated_is_app_code = True
        self.current_project = data
        self.result_text.text = code
        self.manager.current = "result"

    # SAVE AND LOAD PROJECTS

    def load_projects(self):
        try:
            if os.path.exists(PROJECTS_FILE):
                with open(
                    PROJECTS_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:
                    return json.load(file)
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

        # Persist the generated blueprint/code together with the planner fields.
        data["generated_code"] = self.generated_code
        data["generated_is_app_code"] = bool(self.generated_is_app_code)

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
        self.current_project = project

        self.name_input.text = project.get("name", "")
        self.description_input.text = project.get("description", "")
        self.target_input.text = project.get("target", "")
        self.type_input.text = project.get("app_type", "")
        self.features_input.text = project.get("features", "")
        for key, field in self.extra_inputs.items():
            field.text = project.get(key, "")

        self.generated_code = project.get("generated_code", "")
        self.generated_is_app_code = bool(project.get("generated_is_app_code", False))
        self.result_text.text = self.generated_code

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
        safe_title = re.sub(
            r"[\r\n]+",
            " ",
            data.get("name", "MyBusiness")
        ).strip()[:50] or "MyBusiness"

        package_name = re.sub(
            r"[^a-z0-9]",
            "",
            safe_title.lower()
        )

        if not package_name:
            package_name = "mybusiness"
        if not package_name[0].isalpha():
            package_name = "app" + package_name
        package_name = package_name[:50]

        return """[app]
title = {title}
package.name = {package}
package.domain = com.nexgen

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,txt

version = 0.1

requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 21
android.ndk = 28c
p4a.commit = 0382d27de2f7315ed98e74884bafb30365decdee
android.build_tools_version = 34.0.0
android.accept_sdk_license = True

android.archs = arm64-v8a, armeabi-v7a

# Use Android's system file picker; no broad storage permission is needed.
android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 1
""".format(
            title=safe_title,
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
        if not self.generated_code or not self.generated_is_app_code:
            self.message("Generate APP CODE first. A blueprint cannot be exported as an APK build package.")
            return

        try:
            compile(self.generated_code, "main.py", "exec")
        except SyntaxError as error:
            self.message("The edited code has a syntax error on line {}: {}".format(error.lineno, error.msg))
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
                    + "This ZIP is a build package, not the APK itself.\n\n"
                    + "1. Create a GitHub repository.\n"
                    + "2. Extract this ZIP and upload all files, including the hidden .github folder.\n"
                    + "3. Commit the files to the main branch.\n"
                    + "4. Open the repository Actions tab.\n"
                    + "5. Select Build Android APK, then choose Run workflow.\n"
                    + "6. Wait for the build to finish successfully.\n"
                    + "7. Open the completed run and download Generated-Android-APK.\n"
                    + "8. Extract the downloaded artifact and install the APK on Android.\n\n"
                    + "Security: do not put passwords, API keys or private information in this project.\n"
                    + "On a public repository, uploaded source code is visible to everyone.\n"
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
                "BUILD PACKAGE SAVED\n\n"
                "This ZIP is not the APK yet. GitHub Actions must build it.\n\n"
                "Next steps:\n"
                "1. Extract the ZIP.\n"
                "2. Upload all files, including the hidden .github folder, to a GitHub repository.\n"
                "3. Commit the files to the main branch.\n"
                "4. Open Actions > Build Android APK > Run workflow.\n"
                "5. When the run succeeds, download Generated-Android-APK.\n"
                "6. Extract the artifact and install the APK.\n\n"
                "Saved as: "
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

    # BUILD APK PACKAGE

    def build_apk(self, *args):
        """Create a complete GitHub Actions build package for the generated app.

        This prepares the project for a remote APK build. It does not compile
        the APK on the phone; GitHub Actions performs that build after upload.
        """
        if not self.generated_code or not self.generated_is_app_code:
            self.message("Generate APP CODE first. A blueprint cannot be built as an APK.")
            return

        data = self.current_project or {}
        if not data.get("name", "").strip():
            self.message("Please enter and generate an app name first.")
            return

        # Reuse the existing ZIP export and Android system save picker.
        self.export_project_zip(*args)

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
