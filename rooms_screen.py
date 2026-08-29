from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock

import supabase_client as supabase
from session_manager import load_session


class RoomsScreen(Screen):
    refresh_event = None

    def on_enter(self):
        self.load_rooms()
        self.start_polling()

    def on_leave(self):
        self.stop_polling()

    def get_access_token(self):
        saved = load_session()
        return saved["access_token"] if saved else None

    def get_current_user(self):
        token = self.get_access_token()
        if not token:
            return None
        try:
            return supabase.get_user(token)
        except Exception:
            return None

    def load_rooms(self):
        token = self.get_access_token()
        if not token:
            return
        try:
            data, _, status = supabase.select(
                "rooms", token,
                select_cols="id,room_name,host_id,created_at",
                order="created_at.desc",
            )
            if status < 400:
                self.populate_ui(data or [])
        except Exception as e:
            print(f"خطأ فـ جلب الغرف: {e}")

    def get_participant_count(self, room_id):
        token = self.get_access_token()
        if not room_id or not token:
            return 0
        try:
            _, total_count, status = supabase.select(
                "room_participants", token,
                select_cols="id",
                filters=f"room_id=eq.{room_id}",
                count=True,
            )
            return total_count or 0
        except Exception:
            return 0

    def populate_ui(self, rooms):
        self.ids.rooms_rv.data = [
            {
                "room_name": room.get("room_name", "غرفة"),
                "participant_count": self.get_participant_count(room.get("id")),
                "room_data": room,
            }
            for room in rooms
        ]

    def start_polling(self):
        self.stop_polling()
        self.refresh_event = Clock.schedule_interval(lambda dt: self.load_rooms(), 3)

    def stop_polling(self):
        if self.refresh_event:
            self.refresh_event.cancel()
            self.refresh_event = None

    def join_room(self, room_data):
        if not room_data:
            return
        voice_screen = self.manager.get_screen("voice_room")
        room_id = room_data["id"]
        channel_name = f"room_{str(room_id).replace('-', '')}"
        voice_screen.join_channel(channel_name=channel_name, room_id=room_id)
        self.manager.current = "voice_room"

    def create_room(self, room_name):
        user = self.get_current_user()
        token = self.get_access_token()
        if not user or not token:
            print("خطأ: المستخدم ماشي مسجل دخول")
            return None

        room_name = room_name.strip()
        if not room_name:
            return None

        try:
            data, status = supabase.insert("rooms", token, {
                "room_name": room_name,
                "host_id": user.id,
            })
            self.load_rooms()
            return data[0] if data else None
        except Exception as e:
            print(f"خطأ فـ إنشاء الغرفة: {e}")
            return None

    def open_create_room_popup(self):
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        text_input = TextInput(hint_text="اسم الغرفة", multiline=False, size_hint_y=None, height=45)
        confirm_btn = Button(text="إنشاء", size_hint_y=None, height=45)
        layout.add_widget(text_input)
        layout.add_widget(confirm_btn)
        popup = Popup(title="غرفة جديدة", content=layout, size_hint=(0.8, 0.4))

        def on_confirm(instance):
            if self.create_room(text_input.text):
                popup.dismiss()

        confirm_btn.bind(on_release=on_confirm)
        popup.open()

    def leave_to_login(self):
        self.stop_polling()
        login_screen = self.manager.get_screen("login")
        login_screen.logout()
