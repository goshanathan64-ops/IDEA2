

import os
import json
from datetime import datetime

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.label import Label


KV = """
ScreenManager:
    Home:
    Idea:
    Projects:
    Detail:

<Home>:
    name: "home"

    BoxLayout:
        orientation: "vertical"
        padding: 25
        spacing: 15

        Label:
            text: "[b]IDEA2APK[/b]"
            markup: True
            font_size: 32

        Label:
            text: "Turn your ideas into Android apps"

        Button:
            text: "START NEW APP"
            on_release: app.start_new_project()

        Button:
            text: "MY PROJECTS"
            on_release: app.show_projects()


<Idea>:
    name: "idea"

    BoxLayout:
        orientation: "vertical"
        padding: 15
        spacing: 10

        Label:
            text: "DESCRIBE YOUR APP"
            font_size: 24
            size_hint_y: None
            height: 45

        TextInput:
            id: appname
            hint_text: "Enter app name"
            multiline: False
            size_hint_y: None
            height: 50

        TextInput:
            id: description
            hint_text: "Describe what your app should do..."

        Label:
            id: result
            text: ""
            size_hint_y: 0.3

        Button:
            text: "GENERATE BLUEPRINT & SAVE"
            size_hint_y: None
            height: 55
            on_release: app.generate(appname.text, description.text)

        Button:
            text: "MY PROJECTS"
            size_hint_y: None
            height: 45
            on_release: app.show_projects()

        Button:
            text: "BACK HOME"
            size_hint_y: None
            height: 45
            on_release: root.manager.current = "home"


<Projects>:
    name: "projects"

    BoxLayout:
        orientation: "vertical"
        padding: 15
        spacing: 10

        Label:
            text: "[b]MY PROJECTS[/b]"
            markup: True
            font_size: 26
            size_hint_y: None
            height: 50

        ScrollView:
            BoxLayout:
                id: project_list
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: 10

        Button:
            text: "START NEW APP"
            size_hint_y: None
            height: 50
            on_release: app.start_new_project()

        Button:
            text: "BACK HOME"
            size_hint_y: None
            height: 45
            on_release: root.manager.current = "home"


<Detail>:
    name: "detail"

    BoxLayout:
        orientation: "vertical"
        padding: 15
        spacing: 10

        Label:
            text: "[b]PROJECT DETAILS[/b]"
            markup: True
            font_size: 24
            size_hint_y: None
            height: 45

        ScrollView:
            Label:
                id: detail_text
                text: ""
                size_hint_y: None
                height: self.texture_size[1] + 30
                text_size: self.width, None
                halign: "left"
                valign: "top"

        Button:
            text: "EDIT PROJECT"
            size_hint_y: None
            height: 50
            on_release: app.edit_project()

        Button:
            text: "DELETE PROJECT"
            size_hint_y: None
            height: 50
            on_release: app.delete_project()

        Button:
            text: "BACK TO PROJECTS"
            size_hint_y: None
            height: 45
            on_release: app.show_projects()


class Home(Screen):
    pass


class Idea(Screen):
    pass


class Projects(Screen):
    pass


class Detail(Screen):
    pass


class Idea2APK(App):

    def build(self):
        self.title = "IDEA2APK"
        self.projects = []
        self.editing_index = None
        self.selected_index = None

        self.root = Builder.load_string(KV)
        self.load_projects()

        return self.root

    def get_storage_path(self):
        return os.path.join(self.user_data_dir, "projects.json")

    def load_projects(self):
        path = self.get_storage_path()

        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    self.projects = json.load(file)

                if not isinstance(self.projects, list):
                    self.projects = []

        except (OSError, ValueError):
            self.projects = []

    def save_projects(self):
        path = self.get_storage_path()

        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(self.projects, file, indent=4)

            return True

        except OSError:
            return False

    def start_new_project(self):
        self.editing_index = None

        screen = self.root.get_screen("idea")
        screen.ids.appname.text = ""
        screen.ids.description.text = ""
        screen.ids.result.text = ""

        self.root.current = "idea"

    def generate(self, name, description):
        name = name.strip()
        description = description.strip()

        screen = self.root.get_screen("idea")

        if not name or not description:
            screen.ids.result.text = "Enter your app name and description."
            return

        blueprint = (
            "APP BLUEPRINT\\n\\n"
            "Name: " + name + "\\n\\n"
            "Description: " + description + "\\n\\n"
            "NEXT STEPS:\\n"
            "1. Design the interface\\n"
            "2. Generate app code\\n"
            "3. Test the application\\n"
            "4. Build Android APK"
        )

        project = {
            "name": name,
            "description": description,
            "blueprint": blueprint,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        if self.editing_index is None:
            self.projects.append(project)
            self.editing_index = len(self.projects) - 1
        else:
            old_project = self.projects[self.editing_index]
            project["created_at"] = old_project.get(
                "created_at", project["created_at"]
            )
            self.projects[self.editing_index] = project

        if self.save_projects():
            screen.ids.result.text = (
                "SUCCESS!\\n\\n"
                "Your project has been saved.\\n\\n"
                + blueprint
            )
        else:
            screen.ids.result.text = (
                "Could not save the project. Please try again."
            )

    def show_projects(self):
        self.load_projects()

        screen = self.root.get_screen("projects")
        project_list = screen.ids.project_list
        project_list.clear_widgets()

        if not self.projects:
            project_list.add_widget(
                Label(
                    text="No saved projects yet.\\nStart a new app!",
                    size_hint_y=None,
                    height=100
                )
            )
        else:
            for index, project in enumerate(self.projects):
                button = Button(
                    text=project.get("name", "Untitled Project"),
                    size_hint_y=None,
                    height=60
                )
                button.bind(
                    on_release=lambda instance, i=index:
                    self.open_project(i)
                )
                project_list.add_widget(button)

        self.root.current = "projects"

    def open_project(self, index):
        if index < 0 or index >= len(self.projects):
            return

        self.selected_index = index
        project = self.projects[index]

        screen = self.root.get_screen("detail")

        screen.ids.detail_text.text = (
            "APP NAME\\n"
            + project.get("name", "") + "\\n\\n"
            "DESCRIPTION\\n"
            + project.get("description", "") + "\\n\\n"
            "BLUEPRINT\\n"
            + project.get("blueprint", "")
        )

        self.root.current = "detail"

    def edit_project(self):
        if self.selected_index is None:
            return

        self.editing_index = self.selected_index
        project = self.projects[self.editing_index]

        screen = self.root.get_screen("idea")
        screen.ids.appname.text = project.get("name", "")
        screen.ids.description.text = project.get("description", "")
        screen.ids.result.text = "Edit your project and save changes."

        self.root.current = "idea"

    def delete_project(self):
        if self.selected_index is None:
            return

        self.projects.pop(self.selected_index)
        self.selected_index = None
        self.editing_index = None

        self.save_projects()
        self.show_projects()


if __name__ == "__main__":
    Idea2APK().run()
