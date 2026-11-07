
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen

KV = """
ScreenManager:
    Home:
    Idea:

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
            on_release: root.manager.current = "idea"
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
        TextInput:
            id: appname
            hint_text: "Enter app name"
            multiline: False
            size_hint_y: None
            height: 50
        TextInput:
            id: description
            hint_text: "Describe what your app should do..."
        Button:
            text: "GENERATE BLUEPRINT"
            size_hint_y: None
            height: 55
            on_release: app.generate(appname.text, description.text)
        Label:
            id: result
            text: ""
        Button:
            text: "BACK"
            size_hint_y: None
            height: 45
            on_release: root.manager.current = "home"
"""

class Home(Screen):
    pass

class Idea(Screen):
    pass

class Idea2APK(App):

    def build(self):
        self.title = "IDEA2APK"
        return Builder.load_string(KV)

    def generate(self, name, description):
        if not name.strip() or not description.strip():
            self.root.get_screen("idea").ids.result.text = "Enter your app name and idea."
            return

        result = (
            "APP BLUEPRINT\n\n"
            "Name: " + name + "\n\n"
            "Description: " + description + "\n\n"
            "NEXT STEPS:\n"
            "1. Design the interface\n"
            "2. Generate app code\n"
            "3. Test the application\n"
            "4. Build Android APK"
        )

        self.root.get_screen("idea").ids.result.text = result

    def show_projects(self):
        self.root.current = "idea"

if __name__ == "__main__":
    Idea2APK().run()
