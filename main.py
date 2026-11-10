

import os
import re
import json
import uuid

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView


class IDEA2APK(App):

    def build(self):
        self.title = "IDEA2APK"
        self.projects = []
        self.editing_id = None

        self.storage_file = os.path.join(
            self.user_data_dir, "projects.json"
        )

        self.load_projects()

        self.manager = ScreenManager()

        self.create_home()
        self.create_planner()
        self.create_projects()

        return self.manager

    def load_projects(self):
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, "r") as file:
                    data = json.load(file)
                if isinstance(data, list):
                    self.projects = data
        except (OSError, ValueError, TypeError):
            self.projects = []

    def save_projects(self):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            temp = self.storage_file + ".tmp"

            with open(temp, "w") as file:
                json.dump(self.projects, file, indent=4)

            os.replace(temp, self.storage_file)
            return True
        except (OSError, TypeError, ValueError):
            return False

    def make_button(self, text, callback):
        btn = Button(
            text=text,
            size_hint_y=None,
            height=dp(55),
            font_size=sp(15),
            background_normal="",
            background_color=(0.1, 0.55, 0.8, 1)
        )
        btn.bind(on_release=callback)
        return btn

    def create_home(self):
        screen = Screen(name="home")

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(15)
        )

        layout.add_widget(Label(
            text="[b]IDEA2APK[/b]",
            markup=True,
            font_size=sp(32),
            size_hint_y=None,
            height=dp(80)
        ))

        layout.add_widget(Label(
            text="TURN YOUR IDEAS INTO ANDROID APPS",
            font_size=sp(15),
            size_hint_y=None,
            height=dp(55)
        ))

        layout.add_widget(self.make_button(
            "START NEW APP",
            lambda x: self.open_planner()
        ))

        layout.add_widget(self.make_button(
            "MY PROJECTS",
            lambda x: self.open_projects()
        ))

        layout.add_widget(Label(
            text="NEXGEN TECHNOLOGIES",
            size_hint_y=None,
            height=dp(50)
        ))

        screen.add_widget(layout)
        self.manager.add_widget(screen)

    def create_planner(self):
        screen = Screen(name="planner")

        root = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        root.add_widget(Label(
            text="[b]SMART APP PLANNER[/b]",
            markup=True,
            font_size=sp(23),
            size_hint_y=None,
            height=dp(55)
        ))

        scroll = ScrollView()

        form = BoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_y=None
        )
        form.bind(minimum_height=form.setter("height"))

        self.app_name = TextInput(
            hint_text="Enter your app name",
            multiline=False,
            size_hint_y=None,
            height=dp(55)
        )

        self.description = TextInput(
            hint_text="Describe what your app should do",
            size_hint_y=None,
            height=dp(110)
        )

        self.target = TextInput(
            hint_text="Who will use this app?",
            multiline=False,
            size_hint_y=None,
            height=dp(55)
        )

        self.features = TextInput(
            hint_text="List features separated by commas",
            size_hint_y=None,
            height=dp(100)
        )

        form.add_widget(self.app_name)
        form.add_widget(self.description)
        form.add_widget(self.target)
        form.add_widget(self.features)

        form.add_widget(self.make_button(
            "GENERATE BLUEPRINT",
            self.generate_blueprint
        ))

        form.add_widget(self.make_button(
            "GENERATE APP CODE",
            self.generate_app_code
        ))

        self.result = Label(
            text="Your results will appear here.",
            size_hint_y=None,
            halign="left",
            valign="top",
            font_size=sp(14)
        )

        self.result.bind(
            texture_size=lambda instance, value:
            setattr(instance, "height", value[1] + dp(30))
        )
        self.result.text_size = (None, None)
        form.add_widget(self.result)

        self.code_preview = TextInput(
            hint_text="Generated Python code appears here",
            readonly=True,
            multiline=True,
            size_hint_y=None,
            height=dp(300),
            font_size=sp(11)
        )
        form.add_widget(self.code_preview)

        scroll.add_widget(form)
        root.add_widget(scroll)

        root.add_widget(self.make_button(
            "BACK TO HOME",
            lambda x: self.go_home()
        ))

        screen.add_widget(root)
        self.manager.add_widget(screen)

    def get_project(self):
        name = self.app_name.text.strip()
        description = self.description.text.strip()
        target = self.target.text.strip()
        features = self.features.text.strip()

        if not name or not description:
            return None

        return {
            "id": self.editing_id or uuid.uuid4().hex,
            "name": name,
            "description": description,
            "target": target,
            "features": features
        }

    def generate_blueprint(self, instance):
        project = self.get_project()

        if not project:
            self.result.text = "Enter an app name and description."
            return

        blueprint = (
            f"APP BLUEPRINT: {project['name']}\n\n"
            f"DESCRIPTION:\n{project['description']}\n\n"
            f"TARGET USERS:\n{project['target']}\n\n"
            f"FEATURES:\n{project['features']}\n\n"
            "DEVELOPMENT PLAN:\n"
            "1. Design the interface.\n"
            "2. Create app screens.\n"
            "3. Generate source code.\n"
            "4. Test the app.\n"
            "5. Build Android APK.\n"
            "6. Prepare for release."
        )

        self.store_project(project, blueprint=blueprint)
        self.result.text = blueprint

    def generate_app_code(self, instance):
        project = self.get_project()

        if not project:
            self.result.text = "Enter an app name and description."
            return

        features = [
            item.strip()
            for item in re.split(
                r"[,;\n]", project["features"]
            )
            if item.strip()
        ]

        source = "\n".join([
            "from kivy.app import App",
            "from kivy.uix.boxlayout import BoxLayout",
            "from kivy.uix.label import Label",
            "from kivy.uix.button import Button",
            "from kivy.metrics import dp, sp",
            "",
            f"APP_NAME = {project['name']!r}",
            f"DESCRIPTION = {project['description']!r}",
            f"FEATURES = {features!r}",
            "",
            "class GeneratedApp(App):",
            "    def build(self):",
            "        self.title = APP_NAME",
            "        layout = BoxLayout(",
            "            orientation='vertical',",
            "            padding=dp(20),",
            "            spacing=dp(12)",
            "        )",
            "",
            "        layout.add_widget(Label(",
            "            text=APP_NAME,",
            "            font_size=sp(28),",
            "            size_hint_y=None,",
            "            height=dp(65)",
            "        ))",
            "",
            "        layout.add_widget(Label(",
            "            text=DESCRIPTION,",
            "            size_hint_y=None,",
            "            height=dp(90)",
            "        ))",
            "",
            "        for feature in FEATURES:",
            "            layout.add_widget(Button(",
            "                text=feature,",
            "                size_hint_y=None,",
            "                height=dp(50)",
            "            ))",
            "",
            "        return layout",
            "",
            "if __name__ == '__main__':",
            "    GeneratedApp().run()",
            ""
        ])

        project["generated_code"] = source
        self.store_project(project)

        safe_name = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            project["name"]
        ).strip("_") or "GeneratedApp"

        code_folder = os.path.join(
            self.user_data_dir, "generated_apps"
        )

        try:
            os.makedirs(code_folder, exist_ok=True)

            code_file = os.path.join(
                code_folder, safe_name + "_main.py"
            )

            with open(code_file, "w") as file:
                file.write(source)

            self.code_preview.text = source

            self.result.text = (
                "APP CODE GENERATED SUCCESSFULLY!\n\n"
                "Python/Kivy starter code saved.\n"
                "Location: " + code_file
            )

        except OSError as error:
            self.result.text = (
                "Code generated but file saving failed: "
                + str(error)
            )

    def store_project(self, project, blueprint=None):
        if blueprint is not None:
            project["blueprint"] = blueprint

        found = False

        for i, old in enumerate(self.projects):
            if old["id"] == project["id"]:
                self.projects[i].update(project)
                found = True
                break

        if not found:
            self.projects.append(project)

        self.editing_id = project["id"]

        if not self.save_projects():
            self.result.text = "Could not save project."

    def create_projects(self):
        screen = Screen(name="projects")

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        layout.add_widget(Label(
            text="[b]MY SAVED PROJECTS[/b]",
            markup=True,
            font_size=sp(24),
            size_hint_y=None,
            height=dp(55)
        ))

        scroll = ScrollView()

        self.project_list = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None
        )
        self.project_list.bind(
            minimum_height=self.project_list.setter("height")
        )

        scroll.add_widget(self.project_list)
        layout.add_widget(scroll)

        layout.add_widget(self.make_button(
            "BACK TO HOME",
            lambda x: self.go_home()
        ))

        screen.add_widget(layout)
        self.manager.add_widget(screen)

    def update_projects(self):
        self.project_list.clear_widgets()

        if not self.projects:
            self.project_list.add_widget(Label(
                text="No saved projects yet.",
                size_hint_y=None,
                height=dp(60)
            ))
            return

        for project in self.projects:
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(55),
                spacing=dp(5)
            )

            row.add_widget(Label(
                text=project.get("name", "Unnamed"),
                font_size=sp(13)
            ))

            open_btn = Button(
                text="OPEN",
                size_hint_x=0.35
            )
            open_btn.bind(
                on_release=lambda btn, p=project:
                self.edit_project(p)
            )

            delete_btn = Button(
                text="DELETE",
                size_hint_x=0.35
            )
            delete_btn.bind(
                on_release=lambda btn, p=project:
                self.delete_project(p)
            )

            row.add_widget(open_btn)
            row.add_widget(delete_btn)
            self.project_list.add_widget(row)

    def edit_project(self, project):
        self.editing_id = project["id"]

        self.app_name.text = project.get("name", "")
        self.description.text = project.get("description", "")
        self.target.text = project.get("target", "")
        self.features.text = project.get("features", "")

        self.result.text = project.get(
            "blueprint", "Project opened."
        )

        self.code_preview.text = project.get(
            "generated_code", ""
        )

        self.manager.current = "planner"

    def delete_project(self, project):
        self.projects = [
            p for p in self.projects
            if p["id"] != project["id"]
        ]

        self.save_projects()
        self.update_projects()

    def open_planner(self):
        self.editing_id = None

        self.app_name.text = ""
        self.description.text = ""
        self.target.text = ""
        self.features.text = ""

        self.result.text = "Your results will appear here."
        self.code_preview.text = ""

        self.manager.current = "planner"

    def open_projects(self):
        self.update_projects()
        self.manager.current = "projects"

    def go_home(self):
        self.manager.current = "home"


if __name__ == "__main__":
    IDEA2APK().run()
