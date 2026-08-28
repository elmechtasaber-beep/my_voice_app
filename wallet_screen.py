from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.clipboard import Clipboard
from supabase_client import supabase


USDT_ADDRESS = "0xefb1b6f3496c6b2a90d6ad80de88139eeb00769a"
BINANCE_ID = "1241487807"
USDT_NETWORK = "BSC / BEP20"

PACKAGES = [
    (1, 3500000),
    (10, 35000000),
    (43, 150500000),
    (215, 752500000),
    (1000, 3500000000),
]

class WalletScreen(Screen):
    selected_package = None

    def on_enter(self):
        self.refresh()

    def user_id(self):
        try:
            session = supabase.auth.get_session()
            return session.user.id if session and session.user else None
        except Exception:
            return None

    def refresh(self):
        uid = self.user_id()
        if not uid:
            self.ids.balance_label.text = "🪙 0"
            return
        try:
            supabase.table("wallets").upsert({"user_id": uid}, on_conflict="user_id").execute()
            r = supabase.table("wallets").select("balance").eq("user_id", uid).single().execute()
            self.ids.balance_label.text = f"🪙 {int(r.data.get('balance', 0)):,}"
        except Exception as e:
            self.ids.balance_label.text = "تعذر جلب الرصيد"
            print("Wallet refresh:", e)

    def copy_usdt_address(self):
        Clipboard.copy(USDT_ADDRESS)
        self.ids.status_label.text = "✅ تم نسخ عنوان USDT"

    def show_agent_info(self):
        self.show("👤 وكيل الشحن\n\nلشحن الرصيد عن طريق وكيل، تواصل مع الوكيل المعتمد في التطبيق.\n\nالدفع المباشر المتاح: USDT عبر BSC / BEP20")

    def choose_package(self, dollars, coins):
        self.selected_package = (dollars, coins)
        self.ids.package_label.text = f"الباقة المختارة: ${dollars} → {coins:,} كوينز"

    def create_recharge_request(self):
        uid = self.user_id()
        if not uid or not self.selected_package:
            self.show("اختار باقة أولاً")
            return
        dollars, coins = self.selected_package
        content = BoxLayout(orientation="vertical", spacing=8, padding=10)
        info = Label(text=f"${dollars} مقابل {coins:,} كوينز\nأدخل رقم/مرجع عملية الدفع:")
        ref = TextInput(multiline=False, size_hint_y=None, height=45)
        ok = Button(text="إرسال طلب الشحن", size_hint_y=None, height=45)
        content.add_widget(info); content.add_widget(ref); content.add_widget(ok)
        popup = Popup(title="طلب شحن", content=content, size_hint=(0.88, 0.48))

        def submit(_):
            reference = ref.text.strip()
            if not reference:
                self.show("أدخل مرجع العملية")
                return
            try:
                result = supabase.rpc("create_recharge_request", {
                    "p_usd": dollars,
                    "p_metadata": {"payment_reference": reference, "network": USDT_NETWORK, "payment_method": "USDT", "binance_id": BINANCE_ID},
                }).execute()
                if not result.data:
                    raise RuntimeError("لم يرجع السيرفر رقم طلب الشحن")
                popup.dismiss()
                self.ids.status_label.text = "✅ تم إرسال طلب الشحن، في انتظار التحقق."
            except Exception as e:
                self.show(f"تعذر إرسال الطلب: {e}")

        ok.bind(on_release=submit)
        popup.open()

    def send_gift_popup(self):
        uid = self.user_id()
        if not uid:
            self.show("سجل الدخول أولاً")
            return
        content = BoxLayout(orientation="vertical", spacing=8, padding=10)
        receiver = TextInput(hint_text="User ID للمستلم", multiline=False, size_hint_y=None, height=45)
        name = TextInput(hint_text="اسم الهدية", text="🎁 هدية", multiline=False, size_hint_y=None, height=45)
        value = TextInput(hint_text="قيمة الهدية بالكوينز", input_filter="int", multiline=False, size_hint_y=None, height=45)
        ok = Button(text="إرسال", size_hint_y=None, height=45)
        for w in (receiver, name, value, ok): content.add_widget(w)
        popup = Popup(title="🎁 إرسال هدية", content=content, size_hint=(0.88, 0.62))

        def send(_):
            try:
                rid = receiver.text.strip(); gift_name = name.text.strip() or "🎁 هدية"; amount = int(value.text)
                result = supabase.rpc("send_gift", {"p_receiver": rid, "p_gift_name": gift_name, "p_coin_cost": amount}).execute()
                popup.dismiss()
                self.ids.status_label.text = f"✅ تم الإرسال. مكافأة المستلم: {int(result.data.get('receiver_reward', 0)):,} كوينز"
                self.refresh()
            except Exception as e:
                self.show(f"فشل إرسال الهدية: {e}")
        ok.bind(on_release=send)
        popup.open()

    def show_history(self):
        uid = self.user_id()
        if not uid: return
        try:
            r = supabase.table("transactions").select("type,amount,metadata,created_at").eq("user_id", uid).order("created_at", desc=True).limit(30).execute()
            text = "\n".join(f"{x['created_at'][:19]} | {x['type']} | {x['amount']:,}" for x in (r.data or [])) or "لا توجد عمليات"
            self.show(text)
        except Exception as e:
            self.show(f"تعذر جلب السجل: {e}")

    def show(self, text):
        Popup(title="المعلومات", content=Label(text=text), size_hint=(0.9, 0.6)).open()
