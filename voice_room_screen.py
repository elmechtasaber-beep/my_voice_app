from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

import supabase_client as supabase
from session_manager import load_session

AGORA_APP_ID = "0df15e97a5b7423bbb0090bf560c9177"


class VoiceRoomScreen(Screen):
    channel_name = None
    room_id = None
    is_muted = False
    rtc_engine = None
    joined = False
    participants_event = None

    def get_access_token(self):
        saved = load_session()
        return saved["access_token"] if saved else None

    def join_channel(self, channel_name, room_id):
        self.cleanup_room(remove_participant=False)
        self.channel_name = channel_name
        self.room_id = room_id
        self.is_muted = False

        self.ids.room_status_label.text = f"داخل الغرفة: {channel_name}"

        if not self.add_current_user():
            self.ids.room_status_label.text = "تعذر تسجيل دخولك للغرفة"
            return

        self.joined = True
        self.ids.fruit_game.set_room(room_id)
        self.request_microphone_permission()
        self.load_participants()
        self.start_participants_polling()
        self.init_agora_engine()

    def request_microphone_permission(self):
        try:
            from android.permissions import Permission, request_permissions
            request_permissions([Permission.RECORD_AUDIO])
        except Exception:
            pass

    def get_current_user(self):
        token = self.get_access_token()
        if not token:
            return None
        try:
            return supabase.get_user(token)
        except Exception:
            return None

    def get_current_user_id(self):
        user = self.get_current_user()
        return user.id if user else None

    def get_display_name(self):
        user = self.get_current_user()
        if not user:
            return "مستخدم"
        metadata = user.user_metadata or {}
        return metadata.get("display_name") or metadata.get("name") or user.email or "مستخدم"

    def add_current_user(self):
        user_id = self.get_current_user_id()
        token = self.get_access_token()
        if not user_id or not self.room_id or not token:
            return False
        try:
            supabase.upsert(
                "room_participants", token,
                {"room_id": self.room_id, "user_id": user_id},
                on_conflict="room_id,user_id",
            )
            return True
        except Exception as e:
            print(f"خطأ فـ دخول المشارك: {e}")
            return False

    def init_agora_engine(self):
        try:
            from jnius import autoclass
            RtcEngineConfig = autoclass("io.agora.rtc2.RtcEngineConfig")
            RtcEngine = autoclass("io.agora.rtc2.RtcEngine")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            config = RtcEngineConfig()
            config.mAppId = AGORA_APP_ID
            config.mContext = PythonActivity.mActivity.getApplicationContext()
            self.rtc_engine = RtcEngine.create(config)
            self.rtc_engine.enableAudio()
            self.rtc_engine.joinChannel(None, self.channel_name, "", 0)
        except Exception as e:
            print(f"Agora غير جاهزة في الـAPK الحالي: {e}")
            self.rtc_engine = None

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.rtc_engine:
            try:
                self.rtc_engine.muteLocalAudioStream(self.is_muted)
            except Exception as e:
                print(f"خطأ فـ mute: {e}")
        self.ids.mute_button.text = "🔇 مكتوم" if self.is_muted else "🎤 مفعّل"

    def on_leave(self):
        self.cleanup_room(remove_participant=True)

    def leave_channel(self):
        self.cleanup_room(remove_participant=True)
        self.manager.current = "rooms"

    def cleanup_room(self, remove_participant=True):
        self.stop_participants_polling()

        if self.rtc_engine:
            try:
                self.rtc_engine.leaveChannel()
                self.rtc_engine.destroy()
            except Exception as e:
                print(f"خطأ فـ إغلاق Agora: {e}")
            self.rtc_engine = None

        if remove_participant and self.joined:
            self.remove_current_user()

        self.joined = False
        self.channel_name = None
        self.room_id = None
        if "fruit_game" in self.ids:
            self.ids.fruit_game.cleanup()

    def remove_current_user(self):
        user_id = self.get_current_user_id()
        token = self.get_access_token()
        if not user_id or not self.room_id or not token:
            return
        try:
            supabase.delete(
                "room_participants", token,
                filters=f"room_id=eq.{self.room_id}&user_id=eq.{user_id}",
            )
        except Exception as e:
            print(f"خطأ فـ الخروج من الغرفة: {e}")

    def load_participants(self):
        token = self.get_access_token()
        if not self.room_id or not token:
            return
        try:
            data, _, status = supabase.select(
                "room_participants", token,
                select_cols="id,user_id,joined_at",
                filters=f"room_id=eq.{self.room_id}",
                order="joined_at.asc",
            )
            self.populate_participants_ui(data or [])
        except Exception as e:
            print(f"خطأ فـ جلب المشاركين: {e}")

    def populate_participants_ui(self, participants):
        names = {}
        token = self.get_access_token()
        try:
            ids = [p.get("user_id") for p in participants if p.get("user_id")]
            if ids and token:
                id_list = ",".join(ids)
                profiles, _, status = supabase.select(
                    "profiles", token,
                    select_cols="id,username",
                    filters=f"id=in.({id_list})",
                )
                names = {x.get("id"): (x.get("username") or "مستخدم") for x in (profiles or [])}
        except Exception:
            pass
        self.ids.participants_rv.data = [
            {"participant_name": names.get(p.get("user_id"), "مستخدم")}
            for p in participants
        ]

    def start_participants_polling(self):
        self.stop_participants_polling()
        self.participants_event = Clock.schedule_interval(lambda dt: self.load_participants(), 3)

    def stop_participants_polling(self):
        if self.participants_event:
            self.participants_event.cancel()
            self.participants_event = None
