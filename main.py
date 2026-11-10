
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

        self.manager = ScreenManager()

        self.create_home()
        self.create_planner()
        self.create_projects()

        return self.manager

    def make_button(self, text, callback):
        btn = Button(
            text=text,
            size_hint_y=None,
            height=dp(55),
            font_size=sp(16),
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
            font_size=sp(24),
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
            height=dp(120)
        )

        self.target = TextInput(
            hint_text="Who will use this app?",
            multiline=False,
            size_hint_y=None,
            height=dp(55)
        )

        self.features = TextInput(
            hint_text="List your app features",
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

        self.result = Label(
            text="Your app blueprint will appear here.",
            size_hint_y=None,
            halign="left",
            valign="top",
            font_size=sp(15)
        )
        self.result.bind(
            texture_size=lambda instance, value:
            setattr(instance, "height", value[1] + dp(30))
        )
        self.result.text_size = (None, None)

        form.add_widget(self.result)

        scroll.add_widget(form)
        root.add_widget(scroll)

        root.add_widget(self.make_button(
            "BACK TO HOME",
            lambda x: self.go_home()
        ))

        screen.add_widget(root)
        self.manager.add_widget(screen)

    def generate_blueprint(self, instance):

        name = self.app_name.text.strip()
        description = self.description.text.strip()
        target = self.target.text.strip()
        features = self.features.text.strip()

        if not name or not description:
            self.result.text = (
                "Please enter an app name and description."
            )
            return

        blueprint = (
            f"APP BLUEPRINT: {name}\n\n"
            f"DESCRIPTION:\n{description}\n\n"
            f"TARGET USERS:\n"
            f"{target or 'Not specified'}\n\n"
            f"MAIN FEATURES:\n"
            f"{features or 'To be decided'}\n\n"
            "DEVELOPMENT PLAN:\n"
            "1. Design the app interface.\n"
            "2. Create the app screens.\n"
            "3. Generate application code.\n"
            "4. Test the application.\n"
            "5. Build the Android APK.\n"
            "6. Prepare the app for release.\n\n"
            "POWERED BY IDEA2APK - NEXGEN"
        )

        self.result.text = blueprint

        self.projects.append({
            "name": name,
            "blueprint": blueprint
        })

    def create_projects(self):
        screen = Screen(name="projects")

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        layout.add_widget(Label(
            text="[b]MY PROJECTS[/b]",
            markup=True,
            font_size=sp(25),
            size_hint_y=None,
            height=dp(60)
        ))

        self.project_list = Label(
            text="No projects generated yet.",
            halign="left",
            valign="top"
        )

        self.project_list.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        scroll = ScrollView()
        scroll.add_widget(self.project_list)
        layout.add_widget(scroll)

        layout.add_widget(self.make_button(
            "BACK TO HOME",
            lambda x: self.go_home()
        ))

        screen.add_widget(layout)
        self.manager.add_widget(screen)

    def open_planner(self):
        self.manager.current = "planner"

    def open_projects(self):
        self.update_projects()
        self.manager.current = "projects"

    def update_projects(self):
        if not self.projects:
            self.project_list.text = "No projects generated yet."
            return

        self.project_list.text = "\n\n".join(
            f"PROJECT {i + 1}: {p['name']}"
            for i, p in enumerate(self.projects)
        )

    def go_home(self):
        self.manager.current = "home"


if __name__ == "__main__":
    IDEA2APK().run()


