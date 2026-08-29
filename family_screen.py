from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label

import supabase_client as supabase
from session_manager import load_session

_ASSET_DIR = "assets/sar_voc_library/drawable-xhdpi-v4"
RANK_BADGES = {
    1: f"{_ASSET_DIR}/sar_voc_family_contribution_rank_1_ic.webp",
    2: f"{_ASSET_DIR}/sar_voc_family_contribution_rank_2_ic.webp",
    3: f"{_ASSET_DIR}/sar_voc_family_contribution_rank_3_ic.webp",
}
ROLE_LABELS = {"owner": "👑 مالك", "manager": "🛡️ مدير", "member": "عضو"}


class FamilyScreen(Screen):
    my_family_id = None
    my_role = None
    my_user_id = None

    def on_enter(self):
        self.refresh()

    def get_access_token(self):
        saved = load_session()
        return saved["access_token"] if saved else None

    def get_user_id(self):
        token = self.get_access_token()
        if not token:
            return None
        try:
            return supabase.get_user(token).id
        except Exception:
            return None

    def refresh(self):
        uid = self.get_user_id()
        token = self.get_access_token()
        if not uid or not token:
            return
        self.my_user_id = uid
        try:
            membership, _, status = supabase.select(
                "family_members", token,
                select_cols="family_id,role,contribution",
                filters=f"user_id=eq.{uid}", single=True,
            )
        except Exception as e:
            print(f"Family membership lookup: {e}")
            membership = None

        if not membership:
            self.my_family_id = None
            self.my_role = None
            self.show_no_family_state()
            return

        self.my_family_id = membership.get("family_id")
        self.my_role = membership.get("role")
        self.load_family_details()

    def show_no_family_state(self):
        self.ids.family_name_label.text = "أنت ما زلت ما فيك عائلة"
        self.ids.members_rv.data = []
        if "manage_bar" in self.ids:
            self.ids.manage_bar.opacity = 0
            self.ids.manage_bar.disabled = True

    def load_family_details(self):
        token = self.get_access_token()
        try:
            fam, _, status = supabase.select(
                "families", token, select_cols="name,score,weekly_score",
                filters=f"id=eq.{self.my_family_id}", single=True,
            )
            members, _, status2 = supabase.select(
                "family_members", token,
                select_cols="user_id,role,contribution",
                filters=f"family_id=eq.{self.my_family_id}",
                order="contribution.desc",
            )
        except Exception as e:
            print(f"Family details error: {e}")
            return

        if fam:
            score = int(fam.get("score", 0))
            weekly = int(fam.get("weekly_score", 0))
            fam_level = self.family_level_estimate(score)
            self.ids.family_name_label.text = (
                f"{fam.get('name')}  •  Lv.{fam_level}  •  نقاط: {score:,}  •  هاد الأسبوع: {weekly:,}"
            )

        is_manager = self.my_role in ("owner", "manager")
        if "manage_bar" in self.ids:
            self.ids.manage_bar.opacity = 1 if is_manager else 0
            self.ids.manage_bar.disabled = not is_manager

        self.ids.members_rv.data = [
            {
                "member_role": ROLE_LABELS.get(m.get("role", "member"), "عضو"),
                "contribution": f"{int(m.get('contribution', 0)):,}",
                "rank_badge": RANK_BADGES.get(i + 1, ""),
                "member_user_id": m.get("user_id", ""),
                "is_currently_manager": m.get("role") == "manager",
                "can_manage": is_manager and m.get("user_id") != self.my_user_id and m.get("role") != "owner",
            }
            for i, m in enumerate(members or [])
        ]

    def family_level_estimate(self, score):
        """Client-side mirror of the family_level() SQL function — for
        instant display without an extra round trip. Keep the formula
        (score // 50000 + 1, capped at 100) in sync with the DB function."""
        return min(100, max(1, (int(score) // 50000) + 1))

    # ---------- إدارة الأعضاء ----------

    def kick_member(self, user_id):
        if not user_id:
            return
        token = self.get_access_token()
        try:
            supabase.rpc("kick_family_member", token, {"p_user_id": user_id})
            self.show("✅ تم طرد العضو")
            self.refresh()
        except Exception as e:
            self.show(f"تعذر الطرد: {e}")

    def toggle_manager(self, user_id, is_currently_manager):
        token = self.get_access_token()
        new_role = "member" if is_currently_manager else "manager"
        try:
            supabase.rpc("set_family_member_role", token, {"p_user_id": user_id, "p_role": new_role})
            self.show("✅ رجع عضو عادي" if new_role == "member" else "✅ ولّى مدير")
            self.refresh()
        except Exception as e:
            self.show(f"تعذر تبديل الرتبة: {e}")

    def open_transfer_popup(self):
        if self.my_role != "owner":
            self.show("غير المالك يقدر يحوّل الملكية")
            return
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        id_input = TextInput(hint_text="User ID ديال العضو الجديد كمالك", multiline=False, size_hint_y=None, height=45)
        confirm_btn = Button(text="تحويل الملكية", size_hint_y=None, height=45)
        layout.add_widget(id_input)
        layout.add_widget(confirm_btn)
        popup = Popup(title="⚠️ تحويل ملكية العائلة", content=layout, size_hint=(0.85, 0.4))

        def on_confirm(_):
            new_owner = id_input.text.strip()
            if not new_owner:
                return
            token = self.get_access_token()
            try:
                supabase.rpc("transfer_family_ownership", token, {"p_new_owner_id": new_owner})
                popup.dismiss()
                self.refresh()
            except Exception as e:
                self.show(f"تعذر التحويل: {e}")

        confirm_btn.bind(on_release=on_confirm)
        popup.open()

    def open_weekly_leaderboard(self):
        token = self.get_access_token()
        try:
            data, _, status = supabase.select(
                "family_weekly_rankings", token,
                select_cols="family_name,score,rank,week_start",
                order="week_start.desc,rank.asc",
                limit=30,
            )
        except Exception as e:
            self.show(f"تعذر جلب الترتيب: {e}")
            return

        if not data:
            self.show("ما كاين حتى ترتيب أسبوعي متسجل بعد (كيتسجل مع نهاية كل أسبوع)")
            return

        lines = [f"#{r.get('rank')}  {r.get('family_name')}  —  {int(r.get('score', 0)):,}" for r in data]
        self.show("🏆 الترتيب الأسبوعي\n\n" + "\n".join(lines))

    # ---------- إنشاء / انضمام / خروج ----------

    def open_create_popup(self):
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        name_input = TextInput(hint_text="اسم العائلة", multiline=False, size_hint_y=None, height=45)
        confirm_btn = Button(text="إنشاء", size_hint_y=None, height=45)
        layout.add_widget(name_input)
        layout.add_widget(confirm_btn)
        popup = Popup(title="عائلة جديدة", content=layout, size_hint=(0.85, 0.4))

        def on_confirm(_):
            name = name_input.text.strip()
            if not name:
                return
            token = self.get_access_token()
            try:
                supabase.rpc("create_family", token, {"p_name": name})
                popup.dismiss()
                self.refresh()
            except Exception as e:
                self.show(f"تعذر إنشاء العائلة: {e}")

        confirm_btn.bind(on_release=on_confirm)
        popup.open()

    def open_join_popup(self):
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        id_input = TextInput(hint_text="رقم العائلة (Family ID)", multiline=False, size_hint_y=None, height=45)
        confirm_btn = Button(text="انضمام", size_hint_y=None, height=45)
        layout.add_widget(id_input)
        layout.add_widget(confirm_btn)
        popup = Popup(title="الانضمام لعائلة", content=layout, size_hint=(0.85, 0.4))

        def on_confirm(_):
            fam_id = id_input.text.strip()
            if not fam_id:
                return
            token = self.get_access_token()
            try:
                supabase.rpc("join_family", token, {"p_family_id": fam_id})
                popup.dismiss()
                self.refresh()
            except Exception as e:
                self.show(f"تعذر الانضمام: {e}")

        confirm_btn.bind(on_release=on_confirm)
        popup.open()

    def leave_family(self):
        token = self.get_access_token()
        try:
            supabase.rpc("leave_family", token, {})
            self.refresh()
        except Exception as e:
            self.show(f"تعذر الخروج: {e}")

    def show(self, text):
        Popup(title="المعلومات", content=Label(text=text), size_hint=(0.9, 0.5)).open()
