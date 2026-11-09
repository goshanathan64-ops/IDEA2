
import os
import json
from datetime import datetime

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup


class Idea2APK(App):

    def build(self):
        self.title = "IDEA2APK"
        self.projects = []
        self.editing_index = None
        self.selected_index = None

        self.root = ScreenManager()

        self.create_home_screen()
        self.create_idea_screen()
        self.create_projects_screen()
        self.create_detail_screen()

        self.load_projects()
        self.root.current = "home"

        return self.root

    def make_button(self, text, callback, height=55):
        button = Button(
            text=text,
            size_hint_y=None,
            height=dp(height),
            font_size=sp(16)
        )
        button.bind(on_release=lambda instance: callback())
        return button

    def make_label(self, text, size=18, height=55):
        return Label(
            text=text,
            font_size=sp(size),
            size_hint_y=None,
            height=dp(height),
            halign="center",
            valign="middle"
        )

    def create_home_screen(self):
        screen = Screen(name="home")

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(25),
            spacing=dp(15)
        )

        layout.add_widget(
            self.make_label("[b]IDEA2APK[/b]", 32, 90)
        )

        layout.children[0].markup = True

        layout.add_widget(
            self.make_label("Turn your ideas into Android apps", 17, 60)
        )

        layout.add_widget(
            self.make_button("START NEW APP", self.start_new_project)
        )

        layout.add_widget(
            self.make_button("MY PROJECTS", self.show_projects)
        )

        screen.add_widget(layout)
        self.root.add_widget(screen)

    def create_idea_screen(self):
        screen = Screen(name="idea")

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        layout.add_widget(
            self.make_label("DESCRIBE YOUR APP", 24, 50)
        )

        self.name_input = TextInput(
            hint_text="Enter app name",
            multiline=False,
            size_hint_y=None,
            height=dp(55),
            font_size=sp(17)
        )

        self.description_input = TextInput(
            hint_text="Describe what your app should do...",
            multiline=True,
            font_size=sp(17)
        )

        self.result_label = Label(
            text="",
            size_hint_y=None,
            height=dp(180),
            font_size=sp(14),
            halign="left",
            valign="middle"
        )
        self.result_label.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        layout.add_widget(self.name_input)
        layout.add_widget(self.description_input)

        scroll = ScrollView(size_hint_y=0.35)
        scroll.add_widget(self.result_label)
        layout.add_widget(scroll)

        layout.add_widget(
            self.make_button("GENERATE BLUEPRINT & SAVE", self.generate)
        )

        layout.add_widget(
            self.make_button("MY PROJECTS", self.show_projects, 45)
        )

        layout.add_widget(
            self.make_button("BACK HOME", self.go_home, 45)
        )

        screen.add_widget(layout)
        self.root.add_widget(screen)

    def create_projects_screen(self):
        screen = Screen(name="projects")

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        layout.add_widget(
            self.make_label("[b]MY PROJECTS[/b]", 26, 55)
        )

        layout.children[0].markup = True

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

        layout.add_widget(
            self.make_button("START NEW APP", self.start_new_project)
        )

        layout.add_widget(
            self.make_button("BACK HOME", self.go_home, 45)
        )

        screen.add_widget(layout)
        self.root.add_widget(screen)

    def create_detail_screen(self):
        screen = Screen(name="detail")

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        layout.add_widget(
            self.make_label("PROJECT DETAILS", 24, 50)
        )

        scroll = ScrollView()

        self.detail_label = Label(
            text="",
            size_hint_y=None,
            font_size=sp(15),
            halign="left",
            valign="top"
        )

        self.detail_label.bind(
            width=lambda instance, value:
            setattr(instance, "text_size", (value, None))
        )

        self.detail_label.bind(
            texture_size=lambda instance, value:
            setattr(instance, "height", value[1] + dp(30))
        )

        scroll.add_widget(self.detail_label)
        layout.add_widget(scroll)

        layout.add_widget(
            self.make_button("EDIT PROJECT", self.edit_project)
        )

        layout.add_widget(
            self.make_button("DELETE PROJECT", self.confirm_delete)
        )

        layout.add_widget(
            self.make_button("BACK TO PROJECTS", self.show_projects, 45)
        )

        screen.add_widget(layout)
        self.root.add_widget(screen)

    def get_storage_path(self):
        return os.path.join(self.user_data_dir, "projects.json")

    def load_projects(self):
        path = self.get_storage_path()

        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    data = json.load(file)

                if isinstance(data, list):
                    self.projects = data
                else:
                    self.projects = []
            else:
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

    def go_home(self):
        self.root.current = "home"

    def start_new_project(self):
        self.editing_index = None

        self.name_input.text = ""
        self.description_input.text = ""
        self.result_label.text = ""

        self.root.current = "idea"

    def generate(self):
        name = self.name_input.text.strip()
        description = self.description_input.text.strip()

        if not name or not description:
            self.result_label.text = (
                "Please enter your app name and description."
            )
            return

        blueprint = (
            "APP BLUEPRINT\n\n"
            "Name: " + name + "\n\n"
            "Description: " + description + "\n\n"
            "NEXT STEPS:\n"
            "1. Design the interface\n"
            "2. Generate app code\n"
            "3. Test the application\n"
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
            self.result_label.text = (
                "PROJECT SAVED SUCCESSFULLY!\n\n" + blueprint
            )
        else:
            self.result_label.text = "ERROR: Could not save project."

    def show_projects(self):
        self.load_projects()
        self.project_list.clear_widgets()

        if not self.projects:
            self.project_list.add_widget(
                self.make_label("No saved projects yet.", 17, 100)
            )
        else:
            for index, project in enumerate(self.projects):
                button = Button(
                    text=project.get("name", "Untitled Project"),
                    size_hint_y=None,
                    height=dp(60),
                    font_size=sp(17)
                )

                button.bind(
                    on_release=lambda instance, i=index:
                    self.open_project(i)
                )

                self.project_list.add_widget(button)

        self.root.current = "projects"

    def open_project(self, index):
        if index < 0 or index >= len(self.projects):
            return

        self.selected_index = index
        project = self.projects[index]

        self.detail_label.text = (
            "APP NAME\n\n"
            + project.get("name", "") + "\n\n"
            "DESCRIPTION\n\n"
            + project.get("description", "") + "\n\n"
            "BLUEPRINT\n\n"
            + project.get("blueprint", "")
        )

        self.root.current = "detail"

    def edit_project(self):
        if self.selected_index is None:
            return

        self.editing_index = self.selected_index
        project = self.projects[self.editing_index]

        self.name_input.text = project.get("name", "")
        self.description_input.text = project.get("description", "")
        self.result_label.text = "Edit your project and save changes."

        self.root.current = "idea"

    def confirm_delete(self):
        if self.selected_index is None:
            return

        content = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(10)
        )

        content.add_widget(
            Label(text="Are you sure you want to delete this project?")
        )

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )

        popup = Popup(
            title="Confirm deletion",
            content=content,
            size_hint=(0.85, 0.35)
        )

        cancel = Button(text="CANCEL")
        delete = Button(text="DELETE")

        cancel.bind(on_release=popup.dismiss)

        delete.bind(
            on_release=lambda instance: (
                popup.dismiss(),
                self.delete_project()
            )
        )

        buttons.add_widget(cancel)
        buttons.add_widget(delete)
        content.add_widget(buttons)

        popup.open()

    def delete_project(self):
        if self.selected_index is None:
            return

        self.projects.pop(self.selected_index)

        self.selected_index = None
        self.editing_index = None

        if self.save_projects():
            self.show_projects()
        else:
            self.load_projects()
            self.show_projects()


if __name__ == "__main__":
    Idea2APK().run()

