

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


class IDEA2APK(App):

    def build(self):
        self.title = "IDEA2APK"

        self.manager = ScreenManager()

        self.create_home_screen()
        self.create_idea_screen()
        self.create_projects_screen()

        self.manager.current = "home"

        return self.manager

    def make_label(self, text, size=18):
        return Label(
            text=text,
            font_size=sp(size),
            halign="center",
            valign="middle"
        )

    def make_button(self, text, callback):
        button = Button(
            text=text,
            font_size=sp(17),
            size_hint_y=None,
            height=dp(60)
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

        heading = self.make_label("IDEA2APK", 32)
        heading.bold = True

        layout.add_widget(heading)

        layout.add_widget(
            self.make_label(
                "Turn your ideas into Android apps",
                17
            )
        )

        layout.add_widget(
            self.make_button(
                "START NEW APP",
                self.open_idea
            )
        )

        layout.add_widget(
            self.make_button(
                "MY PROJECTS",
                self.open_projects
            )
        )

        layout.add_widget(
            self.make_label(
                "NEXGEN TECHNOLOGY",
                13
            )
        )

        screen.add_widget(layout)
        self.manager.add_widget(screen)

    def create_idea_screen(self):
        screen = Screen(name="idea")

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(20)
        )

        layout.add_widget(
            self.make_label("CREATE NEW APP", 25)
        )

        layout.add_widget(
            self.make_label(
                "Stage 1 is working!\n\n"
                "The Smart App Planner will be added "
                "in the next development stage.",
                17
            )
        )

        layout.add_widget(
            self.make_button(
                "BACK HOME",
                self.go_home
            )
        )

        screen.add_widget(layout)
        self.manager.add_widget(screen)

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
                "Your project library will be "
                "activated in the next stage.",
                17
            )
        )

        layout.add_widget(
            self.make_button(
                "BACK HOME",
                self.go_home
            )
        )

        screen.add_widget(layout)
        self.manager.add_widget(screen)

    def open_idea(self, instance):
        self.manager.current = "idea"

    def open_projects(self, instance):
        self.manager.current = "projects"

    def go_home(self, instance):
        self.manager.current = "home"


if __name__ == "__main__":
    IDEA2APK().run()
