
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

from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
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

        self.manager = ScreenManager()

        self.home_screen = Screen(name="home")
        self.planner_screen = Screen(name="planner")
        self.projects_screen = Screen(name="projects")
        self.result_screen = Screen(name="result")

        self.manager.add_widget(self.home_screen)
        self.manager.add_widget(self.planner_screen)
        self.manager.add_widget(self.projects_screen)
        self.manager.add_widget(self.result_screen)

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
            self.make_button("REFRESH PROJECTS", self.refresh_projects)
        )

        root.add_widget(
            self.make_button("BACK HOME", self.go_home)
        )

        self.projects_screen.add_widget(root)

    def create_result_screen(self):
        root = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        root.add_widget(
            self.make_label("GENERATED APP CODE", 45, 20)
        )

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
                "PREPARE APK BUILD",
                self.prepare_apk_build
            )
        )

        root.add_widget(
            self.make_button("BACK TO PLANNER", self.open_planner)
        )

        self.result_screen.add_widget(root)

    def get_project_data(self):
        name = self.name_input.text.strip()
        description = self.description_input.text.strip()

        if not name:
            self.message("Please enter an app name.")
            return None

        return {
            "id": (
                self.current_project["id"]
                if self.current_project else str(uuid.uuid4())
            ),
            "name": name,
            "description": description,
            "target": self.target_input.text.strip(),
            "app_type": self.type_input.text.strip(),
            "features": self.features_input.text.strip()
        }

    def generate_blueprint(self, *args):
        data = self.get_project_data()
        if not data:
            return

        blueprint = (
            "IDEA2APK APP BLUEPRINT\n\n"
            "APP NAME: " + data["name"] + "\n\n"
            "DESCRIPTION: " + data["description"] + "\n\n"
            "TARGET USERS: " + data["target"] + "\n\n"
            "APP TYPE: " + data["app_type"] + "\n\n"
            "FEATURES:\n" + data["features"] + "\n\n"
            "NEXT STEP: Generate the application code."
        )

        self.generated_code = blueprint
        self.result_text.text = blueprint
        self.manager.current = "result"

    def generate_app_code(self, *args):
        data = self.get_project_data()
        if not data:
            return

        app_name = re.sub(
            r"[^A-Za-z0-9_]",
            "",
            data["name"].replace(" ", "_")
        )

        if not app_name:
            app_name = "MyBusiness"

        description = data["description"]
        features = [
            item.strip()
            for item in data["features"].split(",")
            if item.strip()
        ]

        feature_lines = "\n".join(
            "            self.add_feature(" + repr(item) + ")"
            for item in features
        )

        code = '''from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp, sp


class GeneratedApp(App):

    def build(self):
        self.title = APP_NAME

        root = BoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(12)
        )

        title = Label(
            text=APP_NAME,
            font_size=sp(25),
            size_hint_y=None,
            height=dp(65)
        )
        root.add_widget(title)

        description = Label(
            text=APP_DESCRIPTION,
            font_size=sp(16)
        )
        root.add_widget(description)

        self.feature_box = BoxLayout(
            orientation="vertical",
            spacing=dp(8)
        )
        root.add_widget(self.feature_box)

        self.add_feature("Welcome to your new app")

        return root

    def add_feature(self, feature):
        button = Button(
            text=feature,
            size_hint_y=None,
            height=dp(50)
        )
        self.feature_box.add_widget(button)


if __name__ == "__main__":
    GeneratedApp().run()
'''

        code = code.replace("APP_NAME", repr(app_name))
        code = code.replace(
            "APP_DESCRIPTION",
            repr(description)
        )

        self.generated_code = code
        self.current_project = data
        self.result_text.text = code
        self.manager.current = "result"

    def load_projects(self):
        try:
            if os.path.exists(PROJECTS_FILE):
                with open(PROJECTS_FILE, "r", encoding="utf-8") as file:
                    return json.load(file)
        except Exception:
            pass
        return []

    def save_projects(self):
        try:
            with open(PROJECTS_FILE, "w", encoding="utf-8") as file:
                json.dump(self.projects, file, indent=4)
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

            row.add_widget(self.make_label(name, 35, 17))

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

        self.manager.current = "planner"

    def delete_project(self, project):
        self.projects = [
            item for item in self.projects
            if item.get("id") != project.get("id")
        ]

        self.save_projects()
        self.refresh_projects()
        self.message("Project deleted.")

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
                    "README.txt",
                    "IDEA2APK GENERATED PROJECT\n"
                    "Build this project using Buildozer.\n"
                )

                archive.writestr(
                    "buildozer.spec",
                    self.create_buildozer_spec(data)
                )

            self.message(
                "ZIP exported successfully:\n" + zip_path
            )

        except Exception as error:
            self.message("ZIP export failed: " + str(error))

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
source.include_exts = py,kv,png,jpg,jpeg,atlas
version = 0.1
requirements = python3,kivy==2.3.0
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
""".format(
            title=data["name"],
            package=package_name
        )

    def copy_generated_code(self, *args):
        if not self.generated_code:
            self.message("Generate app code first.")
            return

        try:
            Clipboard.copy(self.generated_code)
            self.message("Code copied to clipboard.")
        except Exception as error:
            self.message("Copy failed: " + str(error))

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
                file.write(self.create_buildozer_spec(data))

            with open(
                os.path.join(folder, "README.txt"),
                "w",
                encoding="utf-8"
            ) as file:
                file.write(
                    "IDEA2APK BUILD PACKAGE\n\n"
                    "Upload this folder's contents to your "
                    "GitHub project and build using Buildozer.\n"
                )

            self.message(
                "APK build files prepared:\n" + folder
            )

        except Exception as error:
            self.message("Preparation failed: " + str(error))

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
