

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

    # ------------------------------
    # USER INTERFACE
    # ------------------------------

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

        heading = self.make_label("IDEA2APK", 32, 90)
        heading.bold = True

        layout.add_widget(heading)

        layout.add_widget(
            self.make_label(
                "Turn your ideas into Android apps",
                17,
                60
            )
        )

        layout.add_widget(
            self.make_button(
                "START NEW APP",
                self.start_new_project
            )
        )

        layout.add_widget(
            self.make_button(
                "MY PROJECTS",
                self.show_projects
            )
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
            self.make_label("SMART APP PLANNER", 24, 50)
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

        layout.add_widget(self.name_input)
        layout.add_widget(self.description_input)

        self.result_label = Label(
            text="Your smart app plan will appear here.",
            size_hint_y=None,
            font_size=sp(14),
            halign="left",
            valign="top"
        )

        self.result_label.bind(
            width=lambda instance, value:
            setattr(instance, "text_size", (value, None))
        )

        self.result_label.bind(
            texture_size=lambda instance, value:
            setattr(instance, "height", value[1] + dp(30))
        )

        result_scroll = ScrollView(
            size_hint_y=0.45
        )

        result_scroll.add_widget(self.result_label)
        layout.add_widget(result_scroll)

        layout.add_widget(
            self.make_button(
                "CREATE SMART APP PLAN & SAVE",
                self.generate
            )
        )

        layout.add_widget(
            self.make_button(
                "MY PROJECTS",
                self.show_projects,
                45
            )
        )

        layout.add_widget(
            self.make_button(
                "BACK HOME",
                self.go_home,
                45
            )
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
            self.make_label("MY PROJECTS", 26, 55)
        )

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
            self.make_button(
                "START NEW APP",
                self.start_new_project
            )
        )

        layout.add_widget(
            self.make_button(
                "BACK HOME",
                self.go_home,
                45
            )
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

        detail_scroll = ScrollView()
        detail_scroll.add_widget(self.detail_label)
        layout.add_widget(detail_scroll)

        layout.add_widget(
            self.make_button(
                "EDIT PROJECT",
                self.edit_project
            )
        )

        layout.add_widget(
            self.make_button(
                "DELETE PROJECT",
                self.confirm_delete
            )
        )

        layout.add_widget(
            self.make_button(
                "BACK TO PROJECTS",
                self.show_projects,
                45
            )
        )

        screen.add_widget(layout)
        self.root.add_widget(screen)

    # ------------------------------
    # PROJECT STORAGE
    # ------------------------------

    def get_storage_path(self):
        return os.path.join(
            self.user_data_dir,
            "projects.json"
        )

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
                json.dump(
                    self.projects,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            return True

        except OSError:
            return False

    # ------------------------------
    # SMART APP PLANNER
    # ------------------------------

    def build_smart_plan(self, name, description):

        idea = description.lower()

        features = [
            "User registration and login",
            "Main dashboard",
            "User profile management",
            "Settings and preferences",
            "Error handling and validation"
        ]

        screens = [
            "Welcome screen",
            "Home dashboard",
            "Profile screen",
            "Settings screen"
        ]

        database = [
            "Users: user details and account information",
            "Settings: user preferences"
        ]

        # Finance applications

        if any(word in idea for word in [
            "finance", "money", "expense", "income",
            "budget", "saving", "bank", "payment"
        ]):
            features.extend([
                "Record income and expenses",
                "Monthly budget management",
                "Savings goals",
                "Financial reports",
                "Transaction history"
            ])

            screens.extend([
                "Income and expense screen",
                "Budget screen",
                "Savings screen",
                "Financial reports screen"
            ])

            database.extend([
                "Transactions: income and expenses",
                "Budgets: monthly spending limits",
                "Savings: savings targets"
            ])

        # Shopping applications

        if any(word in idea for word in [
            "shop", "shopping", "store", "product",
            "market", "ecommerce", "order"
        ]):
            features.extend([
                "Product catalogue",
                "Shopping cart",
                "Order management",
                "Product search",
                "Customer checkout"
            ])

            screens.extend([
                "Products screen",
                "Product details screen",
                "Shopping cart screen",
                "Orders screen"
            ])

            database.extend([
                "Products: product information",
                "Orders: customer orders",
                "Cart: selected products"
            ])

        # Education applications

        if any(word in idea for word in [
            "school", "student", "education",
            "learn", "teacher", "course", "lesson"
        ]):
            features.extend([
                "Learning materials",
                "Student progress tracking",
                "Quizzes and assessments",
                "Course management"
            ])

            screens.extend([
                "Courses screen",
                "Lessons screen",
                "Quiz screen",
                "Student progress screen"
            ])

            database.extend([
                "Courses: course information",
                "Lessons: learning content",
                "Results: student assessment results"
            ])

        # Social applications

        if any(word in idea for word in [
            "social", "chat", "message", "friend",
            "community", "network"
        ]):
            features.extend([
                "Create and manage posts",
                "Messaging system",
                "Friend connections",
                "Notifications",
                "Community interactions"
            ])

            screens.extend([
                "News feed",
                "Messages screen",
                "Friends screen",
                "Notifications screen"
            ])

            database.extend([
                "Posts: user publications",
                "Messages: conversations",
                "Connections: user relationships"
            ])

        # Transport applications

        if any(word in idea for word in [
            "taxi", "transport", "delivery",
            "driver", "ride", "vehicle"
        ]):
            features.extend([
                "Booking system",
                "Driver information",
                "Trip tracking",
                "Booking history"
            ])

            screens.extend([
                "Booking screen",
                "Driver screen",
                "Trip details screen"
            ])

            database.extend([
                "Bookings: customer bookings",
                "Drivers: driver information",
                "Trips: journey records"
            ])

        # Health applications

        if any(word in idea for word in [
            "health", "hospital", "doctor",
            "medicine", "fitness", "medical"
        ]):
            features.extend([
                "Health information records",
                "Appointment management",
                "Health reminders",
                "Activity tracking"
            ])

            screens.extend([
                "Health dashboard",
                "Appointments screen",
                "Reminders screen"
            ])

            database.extend([
                "Appointments: appointment details",
                "Health records: user-entered records",
                "Reminders: scheduled reminders"
            ])

        # Music and entertainment applications

        if any(word in idea for word in [
            "music", "song", "radio", "audio",
            "video", "movie", "entertainment"
        ]):
            features.extend([
                "Media library",
                "Audio or video player",
                "Search and discovery",
                "Favourite content"
            ])

            screens.extend([
                "Media library screen",
                "Player screen",
                "Search screen",
                "Favourites screen"
            ])

            database.extend([
                "Media: content information",
                "Favourites: saved content"
            ])

        # Agriculture applications

        if any(word in idea for word in [
            "farm", "agriculture", "crop",
            "livestock", "animal", "farming"
        ]):
            features.extend([
                "Farm records",
                "Crop management",
                "Livestock records",
                "Production tracking"
            ])

            screens.extend([
                "Farm dashboard",
                "Crop records screen",
                "Livestock screen",
                "Production reports"
            ])

            database.extend([
                "Crops: crop information",
                "Livestock: animal records",
                "Farm records: farm activities"
            ])

        # Remove duplicate suggestions

        features = list(dict.fromkeys(features))
        screens = list(dict.fromkeys(screens))
        database = list(dict.fromkeys(database))

        # Generate navigation plan

        navigation = [
            "Welcome -> Home dashboard",
            "Home dashboard -> Main features",
            "Main features -> Details and actions",
            "Profile -> Account settings"
        ]

        # Generate development roadmap

        roadmap = [
            "Step 1: Confirm app requirements",
            "Step 2: Design the user interface",
            "Step 3: Develop the app screens",
            "Step 4: Implement application features",
            "Step 5: Create and connect the database",
            "Step 6: Test the application",
            "Step 7: Build the Android APK",
            "Step 8: Release the application"
        ]

        sections = []

        sections.append("IDEA2APK SMART APP PLAN")
        sections.append("=" * 30)

        sections.append("\nAPP NAME")
        sections.append(name)

        sections.append("\nAPP PURPOSE")
        sections.append(description)

        sections.append("\n1. SUGGESTED FEATURES")
        for number, feature in enumerate(features, 1):
            sections.append(str(number) + ". " + feature)

        sections.append("\n2. PLANNED APP SCREENS")
        for number, item in enumerate(screens, 1):
            sections.append(str(number) + ". " + item)

        sections.append("\n3. USER NAVIGATION")
        for item in navigation:
            sections.append("- " + item)

        sections.append("\n4. DATABASE STRUCTURE")
        for item in database:
            sections.append("- " + item)

        sections.append("\n5. DEVELOPMENT ROADMAP")
        for item in roadmap:
            sections.append(item)

        sections.append("\n6. TECHNICAL RECOMMENDATION")
        sections.append(
            "Recommended framework: Python and Kivy."
        )
        sections.append(
            "Target platform: Android."
        )
        sections.append(
            "Initial approach: Build a simple working version "
            "before adding advanced features."
        )

        sections.append("\n7. IMPORTANT NOTE")
        sections.append(
            "This plan is generated using offline keyword rules. "
            "It is a starting design, not finished application code."
        )

        return "\n".join(sections)

    # ------------------------------
    # CREATE AND SAVE PROJECTS
    # ------------------------------

    def start_new_project(self):
        self.editing_index = None

        self.name_input.text = ""
        self.description_input.text = ""

        self.result_label.text = (
            "Describe your app to create a smart development plan."
        )

        self.root.current = "idea"

    def generate(self):
        name = self.name_input.text.strip()
        description = self.description_input.text.strip()

        if not name or not description:
            self.result_label.text = (
                "Please enter your app name and description."
            )
            return

        plan = self.build_smart_plan(name, description)

        project = {
            "name": name,
            "description": description,
            "blueprint": plan,
            "created_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            )
        }

        if self.editing_index is None:
            self.projects.append(project)
            self.editing_index = len(self.projects) - 1
        else:
            old_project = self.projects[self.editing_index]

            project["created_at"] = old_project.get(
                "created_at",
                project["created_at"]
            )

            self.projects[self.editing_index] = project

        if self.save_projects():
            self.result_label.text = (
                "SMART APP PLAN CREATED AND SAVED!\n\n" + plan
            )
        else:
            self.result_label.text = (
                "ERROR: Your project could not be saved."
            )

    # ------------------------------
    # VIEW PROJECTS
    # ------------------------------

    def show_projects(self):
        self.load_projects()
        self.project_list.clear_widgets()

        if not self.projects:
            self.project_list.add_widget(
                self.make_label(
                    "No saved projects yet.",
                    17,
                    100
                )
            )
        else:
            for index, project in enumerate(self.projects):

                button = Button(
                    text=project.get(
                        "name",
                        "Untitled Project"
                    ),
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
            + project.get("name", "")
            + "\n\nDESCRIPTION\n\n"
            + project.get("description", "")
            + "\n\nSMART APP PLAN\n\n"
            + project.get("blueprint", "")
        )

        self.root.current = "detail"

    # ------------------------------
    # EDIT PROJECTS
    # ------------------------------

    def edit_project(self):
        if self.selected_index is None:
            return

        self.editing_index = self.selected_index

        project = self.projects[self.editing_index]

        self.name_input.text = project.get("name", "")
        self.description_input.text = project.get(
            "description",
            ""
        )

        self.result_label.text = (
            "Edit your project and create an updated smart plan."
        )

        self.root.current = "idea"

    # ------------------------------
    # DELETE PROJECTS
    # ------------------------------

    def confirm_delete(self):
        if self.selected_index is None:
            return

        content = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(10)
        )

        content.add_widget(
            Label(
                text="Are you sure you want to delete this project?"
            )
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

        cancel.bind(
            on_release=lambda instance: popup.dismiss()
        )

        delete.bind(
            on_release=lambda instance: self.delete_project(popup)
        )

        buttons.add_widget(cancel)
        buttons.add_widget(delete)

        content.add_widget(buttons)

        popup.open()

    def delete_project(self, popup):
        if popup:
            popup.dismiss()

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
