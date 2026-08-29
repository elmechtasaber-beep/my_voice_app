"""
Level/XP helpers — mirrors vip_utils.py's pattern.

Reads "levels" from sar_voc_config.json:
    {"min": 1, "max": 100, "level_1_xp": 100, "xp_per_gift": 50, "progression": "balanced"}

ASSUMPTION (please verify against your real backend): XP is stored in the
`user_levels` table (see supabase_schema_new_systems.sql), bumped by the
`log_gift_contribution` RPC every time a gift is sent. If you already track
XP some other way, point `_load_xp` at that instead.
"""

import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sar_voc_config.json")
_ASSET_DIR = "assets/sar_voc_library/drawable-xhdpi-v4"

# Numbered medal icons available in the library (rank 1-10). Beyond rank 10
# we fall back to the generic medal background.
MEDAL_BY_RANK = {i: f"{_ASSET_DIR}/sar_voc_family_medal_rank_{i}_ic.webp" for i in range(1, 11)}
GENERIC_MEDAL = f"{_ASSET_DIR}/sar_voc_bg_all_medal_equip.webp"

TAG_SILVER = "assets/sar_voc_library/drawable-ldrtl-xhdpi-v4/sar_voc_level_tag_bg_9.png"


def _load_config():
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_CONFIG = _load_config()
_LVL_CFG = _CONFIG.get("levels", {}) or {}


def xp_thresholds():
    """List of (level, xp_required), cheapest first. 'balanced' progression:
    each level needs level_1_xp * level XP more than the previous one
    (linear growth of the *increment*, i.e. a mild curve)."""
    base = _LVL_CFG.get("level_1_xp", 100)
    max_level = _LVL_CFG.get("max", 100)
    total = 0
    levels = []
    for lvl in range(1, max_level + 1):
        total += base * lvl
        levels.append((lvl, total))
    return levels


def level_for_xp(total_xp):
    level = _LVL_CFG.get("min", 1)
    for lvl, threshold in xp_thresholds():
        if total_xp >= threshold:
            level = lvl
    return level


def get_xp_for_user(user_id, access_token, supabase_module=None):
    if not user_id or not access_token:
        return 0
    if supabase_module is None:
        import supabase_client as supabase_module
    try:
        data, _, status = supabase_module.select(
            "user_levels", access_token,
            select_cols="xp",
            filters=f"user_id=eq.{user_id}",
            single=True,
        )
        return int(data.get("xp", 0)) if data else 0
    except Exception:
        return 0


def get_levels_for_users(user_ids, access_token, supabase_module=None):
    """Batched level lookup — same pattern as vip_utils.get_vip_levels_for_users."""
    user_ids = [uid for uid in dict.fromkeys(user_ids) if uid]
    if not user_ids or not access_token:
        return {}
    if supabase_module is None:
        import supabase_client as supabase_module
    try:
        id_list = ",".join(user_ids)
        data, _, status = supabase_module.select(
            "user_levels", access_token,
            select_cols="user_id,xp",
            filters=f"user_id=in.({id_list})",
        )
        return {row.get("user_id"): level_for_xp(int(row.get("xp", 0) or 0)) for row in (data or [])}
    except Exception as e:
        print(f"Level batch lookup: {e}")
        return {}


def medal_for_level(level):
    """Every 10 levels earns the next numbered medal (1..10), capped at the
    generic medal art beyond that — tune this mapping to your real reward
    design once it's finalized."""
    rank = min(10, max(1, (level // 10) + 1))
    return MEDAL_BY_RANK.get(rank, GENERIC_MEDAL)
