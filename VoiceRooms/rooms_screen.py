from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock

from supabase_client import supabase
from realtime_helper import subscribe_postgres, unsubscribe_channel


class RoomsScreen(Screen):
    rooms_channel = None
    refresh_event = None

    def on_enter(self):
        self.load_rooms()
        self.start_realtime()

    def on_leave(self):
        self.stop_realtime()

    def get_current_user(self):
        try:
            session = supabase.auth.get_session()
            return session.user if session and session.user else None
        except Exception:
            return None

    def load_rooms(self):
        try:
            response = (
                supabase.table("rooms")
                .select("id,room_name,host_id,created_at")
                .order("created_at", desc=True)
                .execute()
            )
            self.populate_ui(response.data or [])
        except Exception as e:
            print(f"خطأ فـ جلب الغرف: {e}")

    def get_participant_count(self, room_id):
        if not room_id:
            return 0
        try:
            response = supabase.table("room_participants").select("id", count="exact").eq("room_id", room_id).execute()
            return int(getattr(response, "count", 0) or 0)
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

    def start_realtime(self):
        self.stop_realtime()
        try:
            self.rooms_channel = supabase.channel("rooms-list")
            subscribe_postgres(
                self.rooms_channel,
                "*",
                "public",
                "rooms",
                lambda payload: Clock.schedule_once(lambda dt: self.load_rooms(), 0),
            )
        except Exception as e:
            print(f"تعذر تشغيل Realtime للغرف: {e}")
            # Fallback: keep the list fresh even if Realtime is unavailable.
            self.refresh_event = Clock.schedule_interval(lambda dt: self.load_rooms(), 3)

    def stop_realtime(self):
        if self.refresh_event:
            self.refresh_event.cancel()
            self.refresh_event = None
        if self.rooms_channel:
            unsubscribe_channel(self.rooms_channel)
            self.rooms_channel = None

    def join_room(self, room_data):
        if not room_data:
            return
        voice_screen = self.manager.get_screen("voice_room")
        room_id = room_data["id"]
        channel_name = f"room_{str(room_id).replace("-", "")}"
        voice_screen.join_channel(channel_name=channel_name, room_id=room_id)
        self.manager.current = "voice_room"

    def create_room(self, room_name):
        user = self.get_current_user()
        if not user:
            print("خطأ: المستخدم ماشي مسجل دخول")
            return None

        room_name = room_name.strip()
        if not room_name:
            return None

        try:
            response = (
                supabase.table("rooms")
                .insert({
                    "room_name": room_name,
                    "host_id": user.id,
                })
                .execute()
            )
            self.load_rooms()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"خطأ فـ إنشاء الغرفة: {e}")
            return None

    def open_create_room_popup(self):
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        text_input = TextInput(
            hint_text="اسم الغرفة",
            multiline=False,
            size_hint_y=None,
            height=45,
        )
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
        self.stop_realtime()
        login_screen = self.manager.get_screen("login")
        login_screen.logout()
