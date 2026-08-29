from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label

import supabase_client as supabase
from session_manager import load_session

_ASSET_DIR = "assets/sar_voc_library/drawable-xhdpi-v4"

# Fixed prices — NOT random loot boxes, to stay clear of Google Play's
# real-money-gambling policy. Perks per tier are enforced server-side in
# become_guard() (supabase_schema_v2_family_guard_couple_pk.sql); the
# numbers below are only for display and must be kept in sync with it.
TIERS = [
    ("bronze", 500000, "خصم 3% على الهدايا", f"{_ASSET_DIR}/sar_voc_guard_treasure_tab_left_unselected.webp"),
    ("silver", 2000000, "خصم 6% + حماية من الطرد + مقعد أولوية", f"{_ASSET_DIR}/sar_voc_guard_treasure_tab_right_unselected.webp"),
    ("gold", 8000000, "خصم 10% + حماية من الطرد + مقعد أولوية", f"{_ASSET_DIR}/sar_voc_guard_treasure_tab_selected.webp"),
]


class GuardScreen(Screen):
    host_id = None
    host_name = ""

    def set_host(self, host_id, host_name):
        self.host_id = host_id
        self.host_name = host_name
        self.ids.host_label.text = f"حراسة: {host_name}"
        self.refresh()

    def get_access_token(self):
        saved = load_session()
        return saved["access_token"] if saved else None

    def refresh(self):
        token = self.get_access_token()
        if not token or not self.host_id:
            self.ids.guards_rv.data = []
            return
        try:
            data, _, status = supabase.select(
                "guards", token,
                select_cols="guardian_id,tier,expires_at,gift_discount_percent,kick_protected,priority_seat",
                filters=f"host_id=eq.{self.host_id}&order=expires_at.desc",
                limit=20,
            )
            self.ids.guards_rv.data = [
                {
                    "guard_tier": g.get("tier", ""),
                    "guard_expires": (g.get("expires_at") or "")[:10],
                    "guard_perks": self._perk_summary(g),
                }
                for g in (data or [])
            ]
        except Exception as e:
            print(f"Guards list error: {e}")

        self.load_my_discount()

    def _perk_summary(self, g):
        parts = [f"خصم {int(g.get('gift_discount_percent', 0))}%"]
        if g.get("kick_protected"):
            parts.append("🛡️ محمي")
        if g.get("priority_seat"):
            parts.append("⭐ مقعد أولوية")
        return " • ".join(parts)

    def load_my_discount(self):
        """My own active discount when sending gifts to this host — read
        by wallet_screen before it prices a gift (does not touch send_gift)."""
        token = self.get_access_token()
        if not token or not self.host_id:
            return
        try:
            discount = supabase.rpc("get_gift_discount", token, {"p_host_id": self.host_id})
            discount = int(discount or 0)
        except Exception as e:
            print(f"get_gift_discount: {e}")
            discount = 0
        if "my_discount_label" in self.ids:
            self.ids.my_discount_label.text = (
                f"🎁 عندك خصم {discount}% على الهدايا لهاد الهوست" if discount else ""
            )

    def buy_tier(self, tier, cost):
        token = self.get_access_token()
        if not token or not self.host_id:
            return
        try:
            supabase.rpc("become_guard", token, {
                "p_host_id": self.host_id, "p_tier": tier, "p_coin_cost": cost,
            })
            self.show(f"✅ مبروك، ولّيت حارس {tier} لمدة 30 يوم")
            self.refresh()
        except Exception as e:
            self.show(f"تعذر الشراء: {e}")

    def show(self, text):
        Popup(title="الحراسة", content=Label(text=text), size_hint=(0.9, 0.4)).open()
