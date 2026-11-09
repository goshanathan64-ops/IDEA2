

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp, sp


class IDEA2APKTest(App):

    def build(self):
        layout = BoxLayout(
            orientation="vertical",
            padding=dp(25),
            spacing=dp(20)
        )

        heading = Label(
            text="IDEA2APK",
            font_size=sp(30),
            bold=True
        )

        message = Label(
            text="ANDROID STARTUP TEST\n\n"
                 "If you can see this screen,\n"
                 "Kivy has started successfully.",
            font_size=sp(18),
            halign="center"
        )

        button = Button(
            text="TEST SUCCESSFUL",
            font_size=sp(18),
            size_hint_y=None,
            height=dp(60)
        )

        button.bind(
            on_release=lambda instance:
            setattr(message, "text",
                    "SUCCESS!\n\nIDEA2APK can respond to button presses.")
        )

        layout.add_widget(heading)
        layout.add_widget(message)
        layout.add_widget(button)

        return layout


if __name__ == "__main__":
    IDEA2APKTest().run()
