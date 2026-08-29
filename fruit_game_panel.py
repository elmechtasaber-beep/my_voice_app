from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout

import supabase_client as supabase
from session_manager import load_session

FRUITS = [
    ("🍓", "strawberry", "45×"), ("🥭", "mango", "25×"),
    ("🍉", "watermelon", "15×"), ("🍎", "apple", "10×"),
    ("🍒", "cherry", "5×"), ("🍇", "grape", "5×"),
    ("🍊", "orange", "5×"), ("🍋", "lemon", "5×"),
    ("💎", "diamond", "60×"),
]
BET_AMOUNTS = [1000, 10000, 1000000, 10000000]


class FruitGamePanel(BoxLayout):
    """Small room-embedded fruit game. Wallet changes happen only through RPC."""
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=4, padding=5, size_hint_y=None,
                         height=330, **kwargs)
        self.room_id = None
        self.round_id = None
        self.selected_bet = BET_AMOUNTS[0]
        self.round_no = None
        self.timer_event = None
        self.poll_event = None
        self.timer_label = Label(text="بانتظار الجولة…", size_hint_y=None, height=28)
        self.add_widget(self.timer_label)

        header = BoxLayout(size_hint_y=None, height=32)
        header.add_widget(Label(text="# السجل", halign="right"))
        self.remove_btn = Button(text="× نزع اللعبة", size_hint_x=None, width=105)
        self.remove_btn.bind(on_release=lambda *_: self.hide())
        header.add_widget(self.remove_btn)
        self.add_widget(header)

        self.history = Label(text="-  -  -  -", size_hint_y=None, height=35)
        self.add_widget(self.history)

        fruits = GridLayout(cols=3, spacing=3, size_hint_y=None, height=125)
        self.fruit_buttons = {}
        for emoji, key, mult in FRUITS:
            b = Button(text=f"{emoji}\n{mult}")
            b.bind(on_release=lambda btn, fruit=key: self.place_bet(fruit))
            fruits.add_widget(b)
            self.fruit_buttons[key] = b
        self.add_widget(fruits)

        bets = GridLayout(cols=4, spacing=3, size_hint_y=None, height=45)
        for amount in BET_AMOUNTS:
            b = Button(text=self.format_amount(amount))
            b.bind(on_release=lambda btn, a=amount: self.select_bet(a))
            bets.add_widget(b)
        self.add_widget(bets)

        self.winners = Label(text="", size_hint_y=None, height=55, halign="right", valign="middle")
        self.winners.bind(size=lambda *_: setattr(self.winners, "text_size", self.winners.size))
        self.add_widget(self.winners)

    @staticmethod
    def format_amount(n):
        n = int(n)
        if n >= 1000000:
            return f"{n // 1000000}M"
        return f"{n // 1000}K"

    def get_access_token(self):
        saved = load_session()
        return saved["access_token"] if saved else None

    def select_bet(self, amount):
        self.selected_bet = amount

    def set_room(self, room_id):
        self.cleanup()
        self.room_id = room_id
        self.show()
        self.load_current_round()
        self.start_polling()

    def hide(self):
        self.opacity = 0
        self.disabled = True

    def show(self):
        self.opacity = 1
        self.disabled = False

    def load_current_round(self):
        if not self.room_id:
            return
        token = self.get_access_token()
        if not token:
            return
        try:
            data, _, status = supabase.select(
                "fruit_rounds", token,
                select_cols="*",
                filters=f"room_id=eq.{self.room_id}&status=eq.open",
                order="round_no.desc",
                limit=1,
            )
            rows = data or []
            if rows:
                self.apply_round(rows[0])
            else:
                self.timer_label.text = "بانتظار السيرفر لفتح الجولة…"
        except Exception as e:
            self.timer_label.text = "تعذر الاتصال بسيرفر اللعبة"
            print(f"Fruit round load error: {e}")

    def apply_round(self, row):
        new_round_id = row.get("id")
        round_changed = new_round_id != self.round_id
        self.round_id = new_round_id
        self.round_no = row.get("round_no")
        self.timer_label.text = f"الجولة {self.round_no} • 30 ثانية"
        self.load_history()
        self.load_winners()
        if round_changed:
            self.start_timer()

    def start_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
        self.timer_label.text = "الجولة مفتوحة • 30 ثانية"
        self.timer_event = Clock.schedule_once(lambda *_: self.load_current_round(), 30)

    def place_bet(self, fruit):
        if not self.round_id or self.disabled:
            return
        token = self.get_access_token()
        if not token:
            return
        try:
            result = supabase.rpc("place_fruit_bet", token, {
                "p_room_id": self.room_id,
                "p_round_id": self.round_id,
                "p_fruit": fruit,
                "p_coin_amount": self.selected_bet,
            })
            if result:
                self.load_history()
        except Exception as e:
            self.timer_label.text = "الرصيد غير كافٍ أو انتهت الجولة"
            print(f"Fruit bet error: {e}")

    def load_history(self):
        token = self.get_access_token()
        if not self.round_id or not token:
            return
        try:
            data, _, status = supabase.select(
                "fruit_bets", token,
                select_cols="fruit,coin_amount,created_at",
                filters=f"round_id=eq.{self.round_id}",
                order="created_at.desc",
                limit=8,
            )
            labels = [f"{x.get('fruit')} {self.format_amount(x.get('coin_amount', 0))}" for x in (data or [])]
            self.history.text = "  •  ".join(labels) if labels else "-  -  -  -"
        except Exception as e:
            print(f"Fruit history error: {e}")

    def load_winners(self):
        token = self.get_access_token()
        if not self.round_id or not token:
            return
        try:
            data, _, status = supabase.select(
                "fruit_round_winners", token,
                select_cols="rank,user_id,bet_amount,payout,balance_after",
                filters=f"round_id=eq.{self.round_id}",
                order="rank.asc",
            )
            rows = data or []
            self.winners.text = "\n".join(
                f"#{x['rank']}  {str(x['user_id'])[:8]}…  رهان {self.format_amount(x['bet_amount'])}  +{self.format_amount(x['payout'])}"
                for x in rows
            )
        except Exception as e:
            print(f"Fruit winners error: {e}")

    def start_polling(self):
        self.stop_polling()
        self.poll_event = Clock.schedule_interval(lambda dt: self.load_current_round(), 3)

    def stop_polling(self):
        if self.poll_event:
            self.poll_event.cancel()
            self.poll_event = None

    def cleanup(self):
        self.stop_polling()
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        self.round_id = None
        self.round_no = None
        self.history.text = "-  -  -  -"
        self.winners.text = ""
