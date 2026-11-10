
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
        self.manager = ScreenManager()

        self.create_home_screen()
        self.create_idea_screen()
        self.create_projects_screen()

        self.manager.current = "home"
        return self.manager

    def make_label(self, text, size=18, height=None):
        label = Label(
            text=text,
            font_size=sp(size),
            halign="center",
            valign="middle"
        )
        if height is not None:
            label.size_hint_y = None
            label.height = dp(height)
        return label

    def make_button(self, text, callback):
        button = Button(
            text=text,
            font_size=sp(16),
            size_hint_y=None,
            height=dp(55)
        )
        button.bind(on_release=callback)
        return button

    def create_home_screen(self):
        screen = Screen(name="home")
        layout = BoxLayout(
            orientation="vertical",
            padding=dp(25),
            spacing=dp(18)
        )

        heading = self.make_label("IDEA2APK", 32, 80)
        heading.bold = True
        layout.add_widget(heading)

        layout.add_widget(
            self.make_label(
                "Turn your ideas into Android apps",
                17, 60
            )
        )

        layout.add_widget(
            self.make_button(
                "START NEW APP", self.open_idea
            )
        )

        layout.add_widget(
            self.make_button(
                "MY PROJECTS", self.open_projects
            )
        )

        layout.add_widget(
            self.make_label("NEXGEN TECHNOLOGY", 13, 40)
        )

        screen.add_widget(layout)
        self.manager.add_widget(screen)

    def create_idea_screen(self):
        screen = Screen(name="idea")
        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        layout.add_widget(
            self.make_label("SMART APP PLANNER", 23, 50)
        )

        self.name_input = TextInput(
            hint_text="Enter your app name",
            multiline=False,
            size_hint_y=None,
            height=dp(50),
            font_size=sp(17)
        )
        layout.add_widget(self.name_input)

        self.description_input = TextInput(
            hint_text="Describe what your app should do...",
            multiline=True,
            font_size=sp(16),
            size_hint_y=None,
            height=dp(115)
        )
        layout.add_widget(self.description_input)

        layout.add_widget(
            self.make_button(
                "GENERATE SMART APP PLAN",
                self.generate_plan
            )
        )

        scroll = ScrollView(size_hint=(1, 1))

        self.result_label = Label(
            text="Your generated plan will appear here.",
            font_size=sp(14),
            halign="left",
            valign="top",
            size_hint_y=None
        )

        self.result_label.bind(
            width=self.update_result_width
        )
        self.result_label.bind(
            texture_size=self.update_result_height
        )

        scroll.add_widget(self.result_label)
        layout.add_widget(scroll)

        layout.add_widget(
            self.make_button("BACK HOME", self.go_home)
        )

        screen.add_widget(layout)
        self.manager.add_widget(screen)

    def update_result_width(self, instance, width):
        instance.text_size = (width, None)

    def update_result_height(self, instance, size):
        instance.height = size[1] + dp(25)

    def create_projects_screen(self):
        screen = Screen(name="projects")
        layout = BoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(20)
        )

        layout.add_widget(
            self.make_label("MY PROJECTS", 25)
        )

        layout.add_widget(
            self.make_label(
                "Project saving will be added in Stage 3.",
                17
            )
        )

        layout.add_widget(
            self.make_button("BACK HOME", self.go_home)
        )

        screen.add_widget(layout)
        self.manager.add_widget(screen)

    def open_idea(self, instance):
        self.name_input.text = ""
        self.description_input.text = ""
        self.result_label.text = (
            "Enter your idea and generate your plan."
        )
        self.manager.current = "idea"

    def open_projects(self, instance):
        self.manager.current = "projects"

    def go_home(self, instance):
        self.manager.current = "home"

    def generate_plan(self, instance):
        name = self.name_input.text.strip()
        description = self.description_input.text.strip()

        if not name or not description:
            self.result_label.text = (
                "Please enter both the app name "
                "and its description."
            )
            return

        idea = description.lower()

        features = [
            "User registration and login",
            "Home dashboard",
            "User profile",
            "Settings"
        ]

        screens = [
            "Welcome screen",
            "Home screen",
            "Profile screen",
            "Settings screen"
        ]

        categories = {
            "Finance": [
                "money", "finance", "budget", "expense",
                "income", "saving", "payment"
            ],
            "Shopping": [
                "shop", "shopping", "store", "product",
                "market", "order"
            ],
            "Education": [
                "school", "student", "education",
                "learn", "teacher", "course"
            ],
            "Social": [
                "social", "chat", "message",
                "friend", "community"
            ],
            "Transport": [
                "taxi", "transport", "delivery",
                "driver", "ride"
            ],
            "Health": [
                "health", "hospital", "doctor",
                "medicine", "fitness"
            ],
            "Entertainment": [
                "music", "song", "radio", "audio",
                "video", "movie"
            ],
            "Agriculture": [
                "farm", "agriculture", "crop",
                "livestock", "animal"
            ]
        }

        extra_features = {
            "Finance": [
                "Record income and expenses",
                "Manage monthly budgets",
                "Track savings",
                "View financial reports"
            ],
            "Shopping": [
                "Product catalogue",
                "Shopping cart",
                "Order management",
                "Product search"
            ],
            "Education": [
                "Learning materials",
                "Student progress",
                "Quizzes and assessments",
                "Course management"
            ],
            "Social": [
                "Create posts",
                "Messaging",
                "Friend connections",
                "Notifications"
            ],
            "Transport": [
                "Booking system",
                "Driver information",
                "Trip tracking",
                "Booking history"
            ],
            "Health": [
                "Health records",
                "Appointment management",
                "Health reminders",
                "Activity tracking"
            ],
            "Entertainment": [
                "Media library",
                "Audio or video player",
                "Search content",
                "Favourite content"
            ],
            "Agriculture": [
                "Farm records",
                "Crop management",
                "Livestock records",
                "Production tracking"
            ]
        }

        extra_screens = {
            "Finance": [
                "Transactions", "Budget", "Savings", "Reports"
            ],
            "Shopping": [
                "Products", "Product details", "Cart", "Orders"
            ],
            "Education": [
                "Courses", "Lessons", "Quizzes", "Progress"
            ],
            "Social": [
                "News feed", "Messages", "Friends", "Notifications"
            ],
            "Transport": [
                "Bookings", "Drivers", "Trip details"
            ],
            "Health": [
                "Health dashboard", "Appointments", "Reminders"
            ],
            "Entertainment": [
                "Media library", "Player", "Search", "Favourites"
            ],
            "Agriculture": [
                "Farm dashboard", "Crops", "Livestock", "Reports"
            ]
        }

        detected = []

        for category, keywords in categories.items():
            if any(word in idea for word in keywords):
                detected.append(category)
                features.extend(extra_features[category])
                screens.extend(extra_screens[category])

        if not detected:
            detected.append("General application")

        features = list(dict.fromkeys(features))
        screens = list(dict.fromkeys(screens))

        lines = [
            "IDEA2APK SMART APP PLAN",
            "==============================",
            "",
            "APP NAME",
            name,
            "",
            "APP PURPOSE",
            description,
            "",
            "APP CATEGORY",
            ", ".join(detected),
            "",
            "SUGGESTED FEATURES"
        ]

        for number, feature in enumerate(features, 1):
            lines.append(str(number) + ". " + feature)

        lines.extend([
            "",
            "PLANNED APP SCREENS"
        ])

        for number, item in enumerate(screens, 1):
            lines.append(str(number) + ". " + item)

        lines.extend([
            "",
            "DEVELOPMENT ROADMAP",
            "1. Confirm requirements",
            "2. Design the interface",
            "3. Develop the screens",
            "4. Add the app features",
            "5. Connect the database",
            "6. Test the application",
            "7. Build the Android APK",
            "",
            "TECHNICAL RECOMMENDATION",
            "Framework: Python and Kivy",
            "Platform: Android",
            "",
            "NOTE",
            "This is an offline generated plan, "
            "not finished application code."
        ])

        self.result_label.text = "\n".join(lines)


if __name__ == "__main__":
    IDEA2APK().run()

