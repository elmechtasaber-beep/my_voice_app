from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout

import supabase_client as supabase
from session_manager import load_session

CHESTS = [
    ("🧰", "common", "2×"), ("🎁", "common", "5×"), ("💎", "rare", "5×"),
    ("👑", "royal", "10×"), ("🔥", "epic", "15×"), ("💰", "legendary", "25×"),
    ("🪙", "common", "5×"), ("🏆", "royal", "10×"), ("💰", "legendary", "45×"),
]
BET_AMOUNTS = [1000, 10000, 100000]


class ChestGamePanel(BoxLayout):
    """Room-embedded chest game. Bets and balance are server-authoritative through RPC."""
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=4, padding=5, size_hint_y=None,
                         height=330, **kwargs)
        self.room_id = None
        self.round_id = None
        self.round_no = None
        self.selected_bet = BET_AMOUNTS[0]
        self.poll_event = None
        self.timer_event = None
        self.seconds = 30

        head = BoxLayout(size_hint_y=None, height=32)
        self.title = Label(text="👑 كنز الحظ", bold=True)
        head.add_widget(self.title)
        self.remove_btn = Button(text="×", size_hint_x=None, width=45)
        self.remove_btn.bind(on_release=lambda *_: self.hide())
        head.add_widget(self.remove_btn)
        self.add_widget(head)

        self.balance_label = Label(text="رصيد الرهان: …", size_hint_y=None, height=28)
        self.add_widget(self.balance_label)
        self.timer_label = Label(text="بانتظار الجولة…", size_hint_y=None, height=28)
        self.add_widget(self.timer_label)

        bets = GridLayout(cols=3, spacing=3, size_hint_y=None, height=42)
        for amount in BET_AMOUNTS:
            b = Button(text=self.format_amount(amount))
            b.bind(on_release=lambda btn, a=amount: self.select_bet(a))
            bets.add_widget(b)
        self.add_widget(bets)

        chests = GridLayout(cols=3, spacing=3, size_hint_y=None, height=145)
        self.chest_buttons = []
        for i, (icon, rarity, mult) in enumerate(CHESTS):
            b = Button(text=f"{icon}\n{mult}\n{rarity}")
            b.bind(on_release=lambda btn, idx=i: self.place_bet(idx))
            chests.add_widget(b)
            self.chest_buttons.append(b)
        self.add_widget(chests)

        self.history = Label(text="سجل اللعبة: -", size_hint_y=None, height=45)
        self.add_widget(self.history)

    @staticmethod
    def format_amount(n):
        if n >= 1000000:
            return f"{n // 1000000}M"
        if n >= 1000:
            return f"{n // 1000}K"
        return str(n)

    def token(self):
        saved = load_session()
        return saved["access_token"] if saved else None

    def set_room(self, room_id):
        self.cleanup()
        self.room_id = room_id
        self.show()
        self.load_round()
        self.poll_event = Clock.schedule_interval(lambda dt: self.load_round(), 3)

    def select_bet(self, amount):
        self.selected_bet = amount

    def hide(self):
        self.opacity = 0
        self.disabled = True

    def show(self):
        self.opacity = 1
        self.disabled = False

    def load_round(self):
        token = self.token()
        if not self.room_id or not token:
            return
        try:
            result = supabase.rpc("get_current_chest_round", token, {"p_room_id": self.room_id})
            row = result[0] if isinstance(result, list) and result else result
            if row:
                self.round_id = row.get("id")
                self.round_no = row.get("round_no")
                self.timer_label.text = f"الجولة {self.round_no} • 30 ثانية"
                self.load_history()
                self.load_balance()
        except Exception as e:
            self.timer_label.text = "تعذر الاتصال بسيرفر اللعبة"
            print(f"Chest round error: {e}")

    def load_balance(self):
        token = self.token()
        try:
            user = supabase.get_user(token)
            data, _, _ = supabase.select("wallets", token, select_cols="balance",
                                         filters=f"user_id=eq.{user.id}", limit=1)
            if data:
                self.balance_label.text = f"رصيد الرهان: {self.format_amount(data[0].get('balance', 0))} 🪙"
        except Exception as e:
            print(f"Chest balance error: {e}")

    def place_bet(self, chest_index):
        token = self.token()
        if not token or not self.room_id or not self.round_id:
            return
        try:
            result = supabase.rpc("place_chest_bet", token, {
                "p_room_id": self.room_id,
                "p_round_id": self.round_id,
                "p_chest_index": chest_index,
                "p_coin_amount": self.selected_bet,
            })
            if result:
                self.load_balance()
                self.load_history()
        except Exception as e:
            self.title.text = "الرصيد غير كافٍ أو انتهت الجولة"
            print(f"Chest bet error: {e}")

    def load_history(self):
        token = self.token()
        if not token or not self.round_id:
            return
        try:
            data, _, _ = supabase.select(
                "chest_bets", token,
                select_cols="chest_index,coin_amount,created_at",
                filters=f"round_id=eq.{self.round_id}",
                order="created_at.desc", limit=6,
            )
            labels = [f"{x.get('created_at','')[-8:]} · صندوق {int(x.get('chest_index',0))+1} · {self.format_amount(x.get('coin_amount',0))}"
                      for x in (data or [])]
            self.history.text = "سجل اللعبة: " + (" • ".join(labels) if labels else "-")
        except Exception as e:
            print(f"Chest history error: {e}")

    def cleanup(self):
        if self.poll_event:
            self.poll_event.cancel()
            self.poll_event = None
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        self.round_id = None
        self.round_no = None
