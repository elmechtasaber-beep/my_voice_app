from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label

import supabase_client as supabase
from session_manager import load_session
import vip_utils

# ASSUMPTION (please verify against your real backend): the "profiles"
# table already exists in production (voice_room_screen.py / rooms_screen.py
# already read "id,username" from it). This screen only reads/writes the
# "username" column, which is the one already used elsewhere in the app.
# If "profiles" also has other columns (bio, avatar_url, etc.) that you
# want shown here, tell me and I'll wire them in the same way.


class ProfileScreen(Screen):
    my_user_id = None

    def on_enter(self):
        self.refresh()

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

    def refresh(self):
        user = self.get_current_user()
        token = self.get_access_token()
        if not user or not token:
            self.ids.username_input.text = ""
            self.ids.email_label.text = ""
            return

        self.my_user_id = user.id
        self.ids.email_label.text = user.email or ""

        try:
            data, _, status = supabase.select(
                "profiles", token, select_cols="id,username",
                filters=f"id=eq.{user.id}", single=True,
            )
            self.ids.username_input.text = (data.get("username") if data else "") or ""
        except Exception as e:
            print(f"Profile load error: {e}")
            self.ids.username_input.text = ""

        self.update_vip_badge(token)

    def update_vip_badge(self, token):
        coins = self.get_total_recharged_coins(token)
        level = vip_utils.vip_level_for_coins(coins)
        badge = vip_utils.badge_for_level(level)
        if "vip_badge" in self.ids:
            if badge:
                self.ids.vip_badge.source = badge
                self.ids.vip_badge.opacity = 1
            else:
                self.ids.vip_badge.opacity = 0
        if "vip_label" in self.ids:
            self.ids.vip_label.text = vip_utils.label_for_level(level)

    def get_total_recharged_coins(self, token):
        if not self.my_user_id or not token:
            return 0
        try:
            data, _, status = supabase.select(
                "transactions", token, select_cols="amount",
                filters=f"user_id=eq.{self.my_user_id}&type=eq.{vip_utils.VIP_RECHARGE_TYPE}",
                limit=1000,
            )
            return sum(int(x.get("amount", 0) or 0) for x in (data or []))
        except Exception as e:
            print(f"Profile VIP recharge lookup: {e}")
            return 0

    def save_username(self):
        token = self.get_access_token()
        if not token or not self.my_user_id:
            self.show("سجل الدخول أولاً")
            return

        new_username = self.ids.username_input.text.strip()
        if not new_username:
            self.show("الاسم ما يمكنش يكون فارغ")
            return

        try:
            supabase.upsert(
                "profiles", token,
                {"id": self.my_user_id, "username": new_username},
                on_conflict="id",
            )
            self.show("✅ تم حفظ الاسم")
        except Exception as e:
            self.show(f"تعذر الحفظ: {e}")

    def go_back(self):
        self.manager.current = "rooms"

    def show(self, text):
        Popup(title="البروفايل", content=Label(text=text), size_hint=(0.85, 0.35)).open()
