"""
VIP calculation helpers.

Reads pricing straight from sar_voc_config.json (section "vip") so the
levels/prices can be tuned from that one file without touching code:

    "vip": {"vip1_usd": 200, "doubling": true, "max_vip": 13, "svip13_usd": 100000}

Level thresholds are built as: vip1 = vip1_usd, each next level doubles,
except the last level (max_vip) which uses svip13_usd directly (that's
the "SVIP" tier, priced separately from the doubling curve).

ASSUMPTION (please verify against the real backend): "lifetime recharged"
is computed here as the sum of `transactions` rows for the current user
where type == VIP_RECHARGE_TYPE. If the Supabase backend records
confirmed recharges under a different `type` value, change that one
constant below.
"""

import json
import os

VIP_RECHARGE_TYPE = "recharge"  # <-- adjust if the backend uses a different transaction type

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sar_voc_config.json")

_ASSET_DIR = "assets/sar_voc_library/drawable-xhdpi-v4"

# Only vip1..vip6 exist as dedicated numbered badges in the asset library.
BADGE_BY_LEVEL = {
    1: f"{_ASSET_DIR}/sar_voc_vip_label_vip1.png",
    2: f"{_ASSET_DIR}/sar_voc_vip_label_vip2.png",
    3: f"{_ASSET_DIR}/sar_voc_vip_label_vip3.png",
    4: f"{_ASSET_DIR}/sar_voc_vip_label_vip4.png",
    5: f"{_ASSET_DIR}/sar_voc_vip_label_vip5.png",
    6: f"{_ASSET_DIR}/sar_voc_vip_label_vip6.png",
}
GENERIC_VIP_BADGE = f"{_ASSET_DIR}/sar_voc_profile_vip_ic.webp"  # levels 7..max_vip-1
SVIP_BADGE = "assets/sar_voc_library/drawable-hdpi-v4/sar_voc_profile_svip_ic.png"  # top level


def _load_config():
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_CONFIG = _load_config()
_VIP_CFG = _CONFIG.get("vip", {}) or {}
_COINS_CFG = _CONFIG.get("coins", {}) or {}


def usd_to_coins_rate():
    return _COINS_CFG.get("usd_to_coins", 3500000)


def vip_thresholds():
    """List of (level, usd_required) for level 1..max_vip, cheapest first."""
    base = _VIP_CFG.get("vip1_usd", 200)
    max_vip = _VIP_CFG.get("max_vip", 13)
    doubling = _VIP_CFG.get("doubling", True)
    top_usd = _VIP_CFG.get("svip13_usd")

    levels = []
    for lvl in range(1, max_vip + 1):
        if lvl == max_vip and top_usd:
            usd = top_usd
        else:
            usd = base * (2 ** (lvl - 1)) if doubling else base * lvl
        levels.append((lvl, usd))
    return levels


def vip_level_for_usd(total_usd):
    """Given lifetime recharged USD, return the current VIP level (0 = none yet).

    NOTE: with the current sar_voc_config.json numbers, the vip1_usd=200
    doubling curve passes svip13_usd=100000 well before level 13 (level 12
    alone would need $409,600). That means svip13_usd is not actually the
    "hardest to reach" tier under a strict doubling curve — worth
    double-checking those numbers in sar_voc_config.json. This function
    takes the highest level whose threshold is met so it still behaves
    sensibly either way.
    """
    level = 0
    for lvl, threshold in vip_thresholds():
        if total_usd >= threshold:
            level = max(level, lvl)
    return level


def vip_level_for_coins(total_coins):
    rate = usd_to_coins_rate() or 1
    return vip_level_for_usd(total_coins / rate)


def badge_for_level(level):
    if level <= 0:
        return None
    max_vip = _VIP_CFG.get("max_vip", 13)
    if level >= max_vip:
        return SVIP_BADGE
    return BADGE_BY_LEVEL.get(level, GENERIC_VIP_BADGE)


def label_for_level(level):
    if level <= 0:
        return ""
    max_vip = _VIP_CFG.get("max_vip", 13)
    return "SVIP" if level >= max_vip else f"VIP {level}"


def get_vip_levels_for_users(user_ids, access_token, supabase_module=None):
    """Batched VIP-level lookup for a list of user_ids in a single query.

    Used anywhere a list of users is shown at once (room participants, room
    hosts) so we don't fire one transactions query per user. Returns
    {user_id: level}; user_ids with no recharge history simply aren't in
    the returned dict (treat missing as level 0).
    """
    user_ids = [uid for uid in dict.fromkeys(user_ids) if uid]
    if not user_ids or not access_token:
        return {}

    if supabase_module is None:
        import supabase_client as supabase_module

    totals = {}
    try:
        id_list = ",".join(user_ids)
        data, _, status = supabase_module.select(
            "transactions", access_token,
            select_cols="user_id,amount",
            filters=f"user_id=in.({id_list})&type=eq.{VIP_RECHARGE_TYPE}",
            limit=5000,
        )
        for row in (data or []):
            uid = row.get("user_id")
            totals[uid] = totals.get(uid, 0) + int(row.get("amount", 0) or 0)
    except Exception as e:
        print(f"VIP batch lookup: {e}")
        return {}

    return {uid: vip_level_for_coins(coins) for uid, coins in totals.items()}
