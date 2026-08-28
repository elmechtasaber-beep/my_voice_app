from kivy.app import App
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


if __name__ == "__main__":
    SARVOCApp().run()
