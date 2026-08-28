from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout

from supabase_client import supabase
from realtime_helper import subscribe_postgres, unsubscribe_channel

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
        self.round_channel = None
        self.bet_channel = None
        self.winner_channel = None
        self.selected_bet = BET_AMOUNTS[0]
        self.round_no = None
        self.timer_event = None
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
        if n >= 1000000:
            return f"{n // 1000000}M"
        return f"{n // 1000}K"

    def select_bet(self, amount):
        self.selected_bet = amount

    def set_room(self, room_id):
        self.cleanup()
        self.room_id = room_id
        self.show()
        self.load_current_round()

    def hide(self):
        self.opacity = 0
        self.disabled = True

    def show(self):
        self.opacity = 1
        self.disabled = False

    def load_current_round(self):
        if not self.room_id:
            return
        try:
            r = (supabase.table("fruit_rounds").select("*")
                 .eq("room_id", self.room_id).eq("status", "open")
                 .order("round_no", desc=True).limit(1).execute())
            rows = r.data or []
            if rows:
                self.apply_round(rows[0])
                self.start_realtime()
            else:
                self.timer_label.text = "بانتظار السيرفر لفتح الجولة…"
        except Exception as e:
            self.timer_label.text = "تعذر الاتصال بسيرفر اللعبة"
            print(f"Fruit round load error: {e}")

    def apply_round(self, row):
        self.round_id = row.get("id")
        self.round_no = row.get("round_no")
        self.timer_label.text = f"الجولة {self.round_no} • 30 ثانية"
        self.load_history()
        self.start_timer(row.get("ends_at"))

    def start_timer(self, ends_at):
        if self.timer_event:
            self.timer_event.cancel()
        # Server timestamp parsing is kept simple; realtime round update will also close it.
        self.timer_label.text = "الجولة مفتوحة • 30 ثانية"
        self.timer_event = Clock.schedule_once(lambda *_: self.load_current_round(), 30)

    def place_bet(self, fruit):
        if not self.round_id or self.disabled:
            return
        try:
            result = supabase.rpc("place_fruit_bet", {
                "p_room_id": self.room_id,
                "p_round_id": self.round_id,
                "p_fruit": fruit,
                "p_coin_amount": self.selected_bet,
            }).execute()
            if result.data:
                self.load_history()
        except Exception as e:
            self.timer_label.text = "الرصيد غير كافٍ أو انتهت الجولة"
            print(f"Fruit bet error: {e}")

    def load_history(self):
        try:
            r = (supabase.table("fruit_bets").select("fruit,coin_amount,created_at")
                 .eq("round_id", self.round_id).order("created_at", desc=True).limit(8).execute())
            labels = [f"{x.get('fruit')} {self.format_amount(int(x.get('coin_amount', 0)))}" for x in (r.data or [])]
            self.history.text = "  •  ".join(labels) if labels else "-  -  -  -"
        except Exception as e:
            print(f"Fruit history error: {e}")

    def start_realtime(self):
        self.stop_realtime()
        try:
            self.round_channel = supabase.channel(f"fruit-round-{self.room_id}")
            subscribe_postgres(self.round_channel, "*", "public", "fruit_rounds",
                               lambda payload: Clock.schedule_once(lambda *_: self.load_current_round(), 0),
                               filter_value=f"room_id=eq.{self.room_id}")
            self.bet_channel = supabase.channel(f"fruit-bets-{self.room_id}")
            subscribe_postgres(self.bet_channel, "*", "public", "fruit_bets",
                               lambda payload: Clock.schedule_once(lambda *_: self.load_history(), 0),
                               filter_value=f"room_id=eq.{self.room_id}")
            self.winner_channel = supabase.channel(f"fruit-winners-{self.room_id}")
            subscribe_postgres(self.winner_channel, "*", "public", "fruit_round_winners",
                               lambda payload: Clock.schedule_once(lambda *_: self.load_winners(), 0),
                               filter_value=f"room_id=eq.{self.room_id}")
        except Exception as e:
            print(f"Fruit realtime error: {e}")

    def load_winners(self):
        if not self.round_id:
            return
        try:
            r = (supabase.table("fruit_round_winners").select("rank,user_id,bet_amount,payout,balance_after")
                 .eq("round_id", self.round_id).order("rank").execute())
            rows = r.data or []
            self.winners.text = "\n".join(
                f"#{x['rank']}  {str(x['user_id'])[:8]}…  رهان {self.format_amount(x['bet_amount'])}  +{self.format_amount(x['payout'])}"
                for x in rows
            )
        except Exception as e:
            print(f"Fruit winners error: {e}")

    def stop_realtime(self):
        for ch in (self.round_channel, self.bet_channel, self.winner_channel):
            if ch:
                unsubscribe_channel(ch)
        self.round_channel = self.bet_channel = self.winner_channel = None

    def cleanup(self):
        self.stop_realtime()
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        self.round_id = None
        self.round_no = None
        self.history.text = "-  -  -  -"
        self.winners.text = ""
