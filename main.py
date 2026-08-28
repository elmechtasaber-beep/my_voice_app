import traceback

from kivy.app import App
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label


def _run_real_app():
    from kivy.lang import Builder
    from kivy.uix.screenmanager import ScreenManager, FadeTransition

    from login_screen import LoginScreen
    from rooms_screen import RoomsScreen
    from voice_room_screen import VoiceRoomScreen
    from wallet_screen import WalletScreen

    Builder.load_file("login_screen.kv")
    Builder.load_file("rooms_screen.kv")
    Builder.load_file("voice_room_screen.kv")
    Builder.load_file("wallet_screen.kv")

    class SARVOCApp(App):
        def build(self):
            sm = ScreenManager(transition=FadeTransition())
            sm.add_widget(LoginScreen(name="login"))
            sm.add_widget(RoomsScreen(name="rooms"))
            sm.add_widget(VoiceRoomScreen(name="voice_room"))
            sm.add_widget(WalletScreen(name="wallet"))
            sm.current = "login"
            return sm

    SARVOCApp().run()


class CrashDisplayApp(App):
    def __init__(self, error_text, **kwargs):
        super().__init__(**kwargs)
        self.error_text = error_text

    def build(self):
        scroll = ScrollView()
        label = Label(
            text=self.error_text,
            size_hint_y=None,
            text_size=(700, None),
            halign="left",
            valign="top",
        )
        label.bind(texture_size=lambda inst, val: setattr(label, "height", val[1]))
        scroll.add_widget(label)
        return scroll


if __name__ == "__main__":
    try:
        _run_real_app()
    except Exception:
        error_text = traceback.format_exc()
        CrashDisplayApp(error_text).run()
