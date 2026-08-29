from datetime import date

from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label

import supabase_client as supabase
from session_manager import load_session

RING_LABELS = {"bronze": "💍 خاتم برونزي", "silver": "💍 خاتم فضي", "gold": "💍 خاتم ذهبي"}


class CoupleScreen(Screen):
    couple_id = None

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
        try:
            data, _, status = supabase.select(
                "couples", token,
                select_cols="id,user_a,user_b,status,intimacy,love_level,ring_tier",
                filters=f"or=(user_a.eq.{uid},user_b.eq.{uid})&order=created_at.desc",
                limit=1,
            )
            couple = (data or [None])[0]
        except Exception as e:
            print(f"Couple lookup error: {e}")
            couple = None

        if self.ids.get("active_bar"):
            self.ids.active_bar.opacity = 0
            self.ids.active_bar.disabled = True

        if not couple or couple.get("status") == "ended":
            self.couple_id = None
            self.ids.status_label.text = "ما عندكش شريك ديجا"
            if "task_label" in self.ids:
                self.ids.task_label.text = ""
            return

        self.couple_id = couple.get("id")
        status = couple.get("status")
        intimacy = int(couple.get("intimacy", 0))
        love_level = couple.get("love_level", 1)
        ring = RING_LABELS.get(couple.get("ring_tier", "bronze"), "")

        if status == "pending":
            self.ids.status_label.text = "طلب ارتباط فـ الانتظار… (اطلب من شريكك يقبل)"
            return

        self.ids.status_label.text = f"💞 ارتباط نشط  •  Lv.{love_level}  •  ألفة: {intimacy:,}  {ring}"
        if self.ids.get("active_bar"):
            self.ids.active_bar.opacity = 1
            self.ids.active_bar.disabled = False
        self.load_daily_task()

    def load_daily_task(self):
        token = self.get_access_token()
        if not self.couple_id or not token or "task_label" not in self.ids:
            return
        try:
            today = date.today().isoformat()
            data, _, status = supabase.select(
                "couple_daily_tasks", token,
                select_cols="gift_amount,goal,completed,reward_claimed",
                filters=f"couple_id=eq.{self.couple_id}&task_date=eq.{today}",
                single=True,
            )
        except Exception:
            data = None

        if not data:
            self.ids.task_label.text = "📋 مهمة اليوم: ابعثو هدايا لبعضكم باش تبداو"
            return

        amount = int(data.get("gift_amount", 0))
        goal = int(data.get("goal", 50000))
        if data.get("reward_claimed"):
            self.ids.task_label.text = f"✅ مهمة اليوم كاملة والمكافأة متاخذة ({amount:,}/{goal:,})"
        elif data.get("completed"):
            self.ids.task_label.text = f"🎉 مهمة اليوم كاملة! ({amount:,}/{goal:,}) — يمكن تاخذو المكافأة"
        else:
            self.ids.task_label.text = f"📋 مهمة اليوم: {amount:,}/{goal:,}"

    def claim_daily_reward(self):
        token = self.get_access_token()
        try:
            supabase.rpc("claim_couple_daily_reward", token, {})
            self.show("✅ تم أخذ مكافأة المهمة اليومية")
            self.refresh()
        except Exception as e:
            self.show(f"تعذر أخذ المكافأة: {e}")

    def claim_anniversary(self):
        token = self.get_access_token()
        try:
            supabase.rpc("claim_couple_anniversary", token, {})
            self.show("🎉 مبروك الذكرى! تم إضافة المكافأة")
            self.refresh()
        except Exception as e:
            self.show(f"تعذر أخذ جائزة الذكرى: {e}")

    def open_propose_popup(self):
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        id_input = TextInput(hint_text="User ID ديال الشريك/ة", multiline=False, size_hint_y=None, height=45)
        confirm_btn = Button(text="إرسال طلب الارتباط", size_hint_y=None, height=45)
        layout.add_widget(id_input)
        layout.add_widget(confirm_btn)
        popup = Popup(title="طلب ارتباط", content=layout, size_hint=(0.85, 0.4))

        def on_confirm(_):
            partner_id = id_input.text.strip()
            if not partner_id:
                return
            token = self.get_access_token()
            try:
                supabase.rpc("propose_couple", token, {"p_partner_id": partner_id})
                popup.dismiss()
                self.refresh()
            except Exception as e:
                self.show(f"تعذر الإرسال: {e}")

        confirm_btn.bind(on_release=on_confirm)
        popup.open()

    def accept_pending(self, couple_id):
        token = self.get_access_token()
        try:
            supabase.rpc("accept_couple", token, {"p_couple_id": couple_id})
            self.refresh()
        except Exception as e:
            self.show(f"تعذر القبول: {e}")

    def break_up(self):
        if not self.couple_id:
            return
        token = self.get_access_token()
        try:
            supabase.rpc("end_couple", token, {"p_couple_id": self.couple_id})
            self.show("💔 تم فك الارتباط")
            self.refresh()
        except Exception as e:
            self.show(f"تعذر فك الارتباط: {e}")

    def show(self, text):
        Popup(title="الزوجين", content=Label(text=text), size_hint=(0.9, 0.4)).open()
