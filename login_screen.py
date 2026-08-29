from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.clock import Clock

import supabase_client as supabase
from session_manager import save_session, load_session, clear_session


class LoginScreen(Screen):
    def on_enter(self):
        self.try_auto_login()

    def try_auto_login(self):
        saved = load_session()
        if not saved:
            return

        try:
            response = supabase.set_session(
                saved["access_token"], saved["refresh_token"]
            )
            if response.user:
                save_session(
                    response.session.access_token,
                    response.session.refresh_token,
                )
                self.go_to_rooms()
        except Exception as e:
            print(f"فشلت محاولة الدخول التلقائي: {e}")
            clear_session()

    def login(self, email, password):
        email = email.strip()
        password = password.strip()

        if not email or not password:
            self.show_error("خاصك تعمر الإيميل و كلمة السر")
            return

        try:
            response = supabase.sign_in_with_password(email, password)
            if response.user and response.session:
                save_session(
                    response.session.access_token,
                    response.session.refresh_token,
                )
                self.go_to_rooms()
            else:
                self.show_error("الإيميل أو كلمة السر غالطة")
        except Exception as e:
            self.show_error(f"خطأ فـ تسجيل الدخول: {e}")

    def sign_up(self, email, password):
        email = email.strip()
        password = password.strip()

        if not email or not password:
            self.show_error("خاصك تعمر الإيميل و كلمة السر")
            return

        if len(password) < 6:
            self.show_error("كلمة السر خاصها تكون 6 حروف أو أكثر")
            return

        try:
            response = supabase.sign_up(email, password)
            if response.user:
                if response.session:
                    save_session(
                        response.session.access_token,
                        response.session.refresh_token,
                    )
                    self.go_to_rooms()
                else:
                    self.show_error("تأكد من الإيميل ديالك باش تفعل الحساب")
            else:
                self.show_error("ماقدرناش نخلقو الحساب")
        except Exception as e:
            self.show_error(f"خطأ فـ إنشاء الحساب: {e}")

    def logout(self):
        try:
            saved = load_session()
            if saved:
                supabase.sign_out(saved["access_token"])
        except Exception as e:
            print(f"خطأ فـ تسجيل الخروج: {e}")
        finally:
            clear_session()
            self.manager.current = "login"

    def go_to_rooms(self):
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", "rooms"))

    def show_error(self, message):
        popup = Popup(
            title="خطأ",
            content=Label(text=message),
            size_hint=(0.8, 0.3),
        )
        popup.open()
