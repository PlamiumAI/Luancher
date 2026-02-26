import os
import sys
import base64
import threading
import subprocess
import requests
import feedparser
import shutil
import random
import json
import datetime
from pathlib import Path
from html.parser import HTMLParser
from io import StringIO
import flet as ft
from PIL import Image

# =====================================================
# SECURITY HANDSHAKE
# =====================================================
if os.environ.get("LUANCHER_BOOTED") != "TRUE":
    print("\n" + "─"*60)
    print(" LUANCHER: INITIALIZATION PREVENTED")
    print(" " + "─"*58)
    print(" Status: Direct launch of 'main.py' is restricted.")
    print(" Reason: Environment handshake missing.")
    print("\n How to fix:")
    print(" 1. Close this terminal.")
    print(" 2. Run 'python3 updater.py' to launch the application.")
    print(" 3. The updater will manage dependencies and launch safely.")
    print("─"*60 + "\n")
    sys.exit(0)

# =====================================================
# THEME DATA
# =====================================================
INTERNAL_THEMES = {
    "Deep Charcoal": "#121212",
    "Midnight Blue": "#000b1e",
    "Forest Green":  "#0b1a0b",
    "Crimson Red":   "#1a0505",
    "OLED Black":    "#000000",
}

# =====================================================
# PATHS
# =====================================================
IS_BUNDLE = getattr(sys, 'frozen', False)
ROOT = Path.home() / ".luancher" if IS_BUNDLE else Path(__file__).parent.resolve()

RUNTIME         = ROOT / "runtime"
SRC             = RUNTIME / "src" / "luanti"
BUILDS          = RUNTIME / "builds"
DATA            = ROOT / "data"
CACHE           = ROOT / "cache"
LOGS            = ROOT / "logs"
THEMES_DIR      = DATA / "themes"
MY_THEMES_FILE  = DATA / "my_themes.json"
SETTINGS_FILE   = ROOT / "luancher_settings.json"

GITHUB_API = "https://api.github.com/repos/luanti-org/luanti/releases/latest"
RSS_FEED   = "https://blog.luanti.org/feed.rss"

MIGRATE_PATHS = [
    "games", "mods", "worlds", "textures", "cache",
    "minetest.conf", "client/serverlist/favoriteservers.json",
]

QUOTES = [
    "Creation starts here.",
    "To build is to believe in tomorrow.",
    "Purposeful play creates mastery.",
    "The expert was once a beginner.",
    "Every world begins with a single block.",
    "Build what you can't find.",
    "The best mods are the ones you write yourself.",
    "A server of one is still a world worth exploring.",
    "Dig deep. Build higher.",
    "Open source, open world.",
]

LAUNCH_MILESTONES = {
    1:   "First launch! Welcome to Luancher.",
    5:   "5 launches already. You're getting the hang of it!",
    10:  "10 launches. A seasoned explorer.",
    25:  "25 launches. Practically a Luanti veteran.",
    50:  "50 launches. Are you okay? (affectionately)",
    100: "100 launches. We should add a trophy for this.",
}

ACCENT_PRESETS = {
    "Blue":   {"primary": "#a8c7fa", "primary_cont": "#1c3a5e",
               "l_primary": "#4a65a8", "l_primary_cont": "#d8e3ff"},
    "Purple": {"primary": "#c8b8ff", "primary_cont": "#2d1f5e",
               "l_primary": "#6b4fa0", "l_primary_cont": "#e8deff"},
    "Green":  {"primary": "#7fd9a0", "primary_cont": "#0f3320",
               "l_primary": "#2d7a51", "l_primary_cont": "#d0f0dc"},
    "Amber":  {"primary": "#ffd080", "primary_cont": "#3d2800",
               "l_primary": "#a06010", "l_primary_cont": "#fff0cc"},
    "Rose":   {"primary": "#ffb3b3", "primary_cont": "#4a0a0a",
               "l_primary": "#c0392b", "l_primary_cont": "#ffe0e0"},
    "Teal":   {"primary": "#80d8e0", "primary_cont": "#0a3040",
               "l_primary": "#1a7a8a", "l_primary_cont": "#ccf0f5"},
}

# =====================================================
# SETTINGS
# =====================================================
DEFAULT_SETTINGS = {
    "theme":          "Vanilla",
    "light_mode":     False,
    "accent":         "Blue",
    "nickname":       "",
    "launch_count":   0,
    "quote_index":    0,
    "quote_date":     "",
    "total_sessions": 0,
    "first_seen":     "",
}

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    s = dict(DEFAULT_SETTINGS)
    s["first_seen"] = datetime.date.today().isoformat()
    return s

def save_settings(s: dict):
    ROOT.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)

def get_daily_quote(s: dict) -> str:
    today = datetime.date.today().isoformat()
    if s.get("quote_date") != today:
        s["quote_index"] = random.randint(0, len(QUOTES) - 1)
        s["quote_date"] = today
        save_settings(s)
    return QUOTES[s["quote_index"]]

# =====================================================
# DESIGN TOKENS
# =====================================================
DARK_BASE = {
    "bg":           "#0d0d11",
    "surface":      "#16161e",
    "surface2":     "#1e1e28",
    "surface3":     "#26263200",   # transparent for gradient effect
    "rail":         "#111118",
    "outline":      "#2e2e3e",
    "on_surface":   "#e8e6f4",
    "on_surface2":  "#8e8aa8",
    "on_surface3":  "#5a566e",
    "accent":       "#7fd9a0",
    "error":        "#ff8a80",
    "news_title":   "#c8b8ff",
    "news_date":    "#6a6680",
    "topbar":       "#13131a",
}

LIGHT_BASE = {
    "bg":           "#f0edf8",
    "surface":      "#ffffff",
    "surface2":     "#e8e3f5",
    "surface3":     "#ddd8f0",
    "rail":         "#fafaff",
    "outline":      "#d0cce0",
    "on_surface":   "#1a1828",
    "on_surface2":  "#5a5670",
    "on_surface3":  "#9090a8",
    "accent":       "#2d7a51",
    "error":        "#c0392b",
    "news_title":   "#5a3f9a",
    "news_date":    "#a0a0b8",
    "topbar":       "#f8f5ff",
}

def build_tokens(light: bool, accent_name: str) -> dict:
    base = dict(LIGHT_BASE if light else DARK_BASE)
    preset = ACCENT_PRESETS.get(accent_name, ACCENT_PRESETS["Blue"])
    if light:
        base["primary"]      = preset["l_primary"]
        base["primary_cont"] = preset["l_primary_cont"]
    else:
        base["primary"]      = preset["primary"]
        base["primary_cont"] = preset["primary_cont"]
    return base

# =====================================================
# FLET 0.80 LAYOUT HELPERS
# =====================================================
def _border_all(width, color):
    s = ft.BorderSide(width, color)
    return ft.Border(left=s, right=s, top=s, bottom=s)

def _border_right(width, color):
    return ft.Border(right=ft.BorderSide(width, color))

def _border_left(width, color):
    return ft.Border(left=ft.BorderSide(width, color))

def _border_bottom(width, color):
    return ft.Border(bottom=ft.BorderSide(width, color))

def _border_side_left(width, color):
    return ft.Border(left=ft.BorderSide(width, color))

def _pad(vertical=0, horizontal=0):
    return ft.Padding(left=horizontal, right=horizontal,
                      top=vertical,    bottom=vertical)

def _pad4(left=0, top=0, right=0, bottom=0):
    return ft.Padding(left=left, top=top, right=right, bottom=bottom)

def _margin_b(bottom):
    return ft.Margin(left=0, right=0, top=0, bottom=bottom)

def _br_top(radius):
    return ft.BorderRadius(top_left=radius, top_right=radius,
                           bottom_left=0,   bottom_right=0)

def _br_all(r):
    return ft.BorderRadius(top_left=r, top_right=r,
                           bottom_left=r, bottom_right=r)

# =====================================================
# UTILS
# =====================================================
class HTMLToText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = StringIO()

    def handle_data(self, data):
        if data.strip():
            self.text.write(data)

    def handle_starttag(self, tag, attrs):
        if tag in ['p', 'div']:   self.text.write('\n\n')
        elif tag == 'br':         self.text.write('\n')
        elif tag == 'li':         self.text.write('\n  • ')
        elif tag in ['h2', 'h3']: self.text.write('\n\n')
        elif tag == 'tr':         self.text.write('\n')
        elif tag == 'td':         self.text.write('  ')

    def handle_endtag(self, tag):
        if tag in ['h2', 'h3']: self.text.write('\n')
        elif tag == 'ul':        self.text.write('\n')

    def get_text(self):
        return self.text.getvalue().strip()

def html_to_text(html):
    p = HTMLToText()
    p.feed(html)
    return p.get_text()

def log(msg):
    LOGS.mkdir(exist_ok=True, parents=True)
    with open(LOGS / "launcher.log", "a") as f:
        f.write(msg + "\n")

def run_cmd(cmd, cwd=None, cancel_event=None):
    log(" ".join(cmd))
    proc = subprocess.Popen(cmd, cwd=cwd)
    while proc.poll() is None:
        if cancel_event and cancel_event.is_set():
            proc.terminate()
            try:    proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill()
            raise InterruptedError("Build cancelled by user")
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

def ensure_dirs():
    for p in [RUNTIME, SRC.parent, BUILDS, DATA, CACHE, LOGS, THEMES_DIR]:
        p.mkdir(parents=True, exist_ok=True)

def load_my_themes():
    if MY_THEMES_FILE.exists():
        try:
            with open(MY_THEMES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_my_themes(d):
    MY_THEMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MY_THEMES_FILE, "w") as f:
        json.dump(d, f, indent=2)

# =====================================================
# THEME SYSTEM
# =====================================================
def find_texture_dirs():
    if not RUNTIME.exists(): return []
    found = []
    for root, dirs, files in os.walk(str(RUNTIME)):
        p = Path(root)
        if len(p.parts) >= 3 and tuple(p.parts[-3:]) == ("textures", "base", "pack"):
            found.append(p)
    return found

def apply_theme(theme_name, custom_themes=None):
    targets = find_texture_dirs()
    if not targets:
        return "Error: Luanti textures not found."
    bg_file = "menu_background.png"
    if theme_name == "Vanilla":
        for td in targets:
            fp = td / bg_file
            if fp.exists(): fp.unlink()
        return "Restored Vanilla."
    theme_data = INTERNAL_THEMES.get(theme_name)
    if theme_data is None and custom_themes:
        theme_data = custom_themes.get(theme_name)
    if not theme_data:
        return f"Error: No data for '{theme_name}'"
    try:
        if theme_data.startswith("#"):
            img = Image.new("RGB", (16, 16), theme_data)
            for td in targets: img.save(td / bg_file)
        else:
            _, encoded = theme_data.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            for td in targets:
                with open(td / bg_file, "wb") as f:
                    f.write(image_bytes)
        return f"Applied '{theme_name}'!"
    except Exception as e:
        return f"Injection error: {e}"

# =====================================================
# VERSION & BUILD
# =====================================================
def latest_version():
    r = requests.get(GITHUB_API,
                     headers={"User-Agent": "Luancher-Client"},
                     timeout=15)
    r.raise_for_status()
    return r.json()["tag_name"].lstrip("v")

def current_version():
    link = BUILDS / "current"
    if link.exists() and link.is_symlink():
        return link.resolve().name
    return None

def ensure_repo(cancel_event=None):
    if not SRC.exists():
        run_cmd(["git", "clone",
                 "https://github.com/luanti-org/luanti.git", str(SRC)],
                cancel_event=cancel_event)

def build(version, cancel_event=None):
    target = BUILDS / version
    if target.exists(): return
    ensure_repo(cancel_event)
    run_cmd(["git", "fetch", "--tags"], cwd=SRC, cancel_event=cancel_event)
    run_cmd(["git", "checkout", version], cwd=SRC, cancel_event=cancel_event)
    target.mkdir(parents=True, exist_ok=True)
    run_cmd(["cmake", str(SRC), "-DRUN_IN_PLACE=FALSE", "-DENABLE_GETTEXT=TRUE"],
            cwd=target, cancel_event=cancel_event)
    run_cmd(["make", "-j", str(os.cpu_count() or 2)],
            cwd=target, cancel_event=cancel_event)

def switch_current(version):
    link = BUILDS / "current"
    if link.exists() or link.is_symlink(): link.unlink()
    link.symlink_to(BUILDS / version)

def migrate(version):
    dest = BUILDS / version
    dest.mkdir(parents=True, exist_ok=True)
    for rel in MIGRATE_PATHS:
        src = DATA / rel
        if not src.exists(): continue
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir(): shutil.copytree(src, dst, dirs_exist_ok=True)
        else:            shutil.copy2(src, dst)

def fetch_news():
    try:
        feed = feedparser.parse(RSS_FEED)
        if not feed.entries: return None
        out = []
        for e in feed.entries[:6]:
            words = e.get("summary", "").split()
            short = " ".join(words[:8]) + ("..." if len(words) > 8 else "")
            out.append({"title": e.title, "date": e.get("published", ""),
                        "desc": short,    "full": e.get("summary", "")})
        return out
    except Exception:
        return None

def find_binary():
    for p in [BUILDS / "current" / "bin" / "luanti",
              SRC / "bin" / "luanti"]:
        if p.exists(): return p
    return None

def launch():
    binary = find_binary()
    if not binary:
        raise FileNotFoundError("No compiled Luanti binary found.")
    os.chmod(binary, 0o755)
    subprocess.Popen([str(binary)])

# =====================================================
# UI
# =====================================================
class Launcher(ft.Container):
    def __init__(self, settings: dict):
        super().__init__()
        self.expand = True
        self.is_busy      = False
        self.cancel_event = None
        self.is_update    = False
        self._settings    = settings
        self._is_light    = settings.get("light_mode", False)
        self._accent      = settings.get("accent", "Blue")
        self._tokens      = build_tokens(self._is_light, self._accent)

        t = self._tokens

        # ── live controls ──────────────────────────────
        self.status_chip = ft.Container(
            visible=False,
            border_radius=20,
            bgcolor=t["surface2"],
            border=_border_all(1, t["outline"]),
            padding=_pad(vertical=6, horizontal=14),
            content=ft.Row(
                spacing=8, tight=True,
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED,
                            size=14, color=t["on_surface2"]),
                    ft.Text(value="", size=12, color=t["on_surface2"]),
                ],
            ),
        )
        self._status_icon  = self.status_chip.content.controls[0]
        self._status_label = self.status_chip.content.controls[1]

        # small inline status below button (errors / sidebar)
        self.status_text = ft.Text(value="", size=11, color=t["on_surface2"])

        self.quote_text = ft.Text(
            value=get_daily_quote(settings),
            size=13, italic=True,
            color=t["on_surface2"],
            text_align=ft.TextAlign.CENTER,
        )
        self.news_col = ft.Column(
            spacing=6, scroll=ft.ScrollMode.ADAPTIVE, expand=True
        )

        # progress bar spans full width of center column
        self.progress_bar = ft.ProgressBar(
            color=t["primary"], bgcolor=t["outline"],
            visible=False, border_radius=2, height=3,
        )

        # play button: outer glow ring + inner circle
        self.start_icon = ft.Icon(
            ft.Icons.PLAY_ARROW_ROUNDED, size=52, color=t["primary"]
        )
        self._ring = ft.Container(
            width=148, height=148, border_radius=74,
            bgcolor="transparent",
            border=_border_all(2, t["primary_cont"]),
        )
        self.start_btn = ft.Container(
            width=120, height=120, border_radius=60,
            bgcolor=t["primary_cont"],
            border=_border_all(2, t["primary"]),
            ink=True, on_click=self._on_start,
            content=self.start_icon,
            animate=150,
        )
        self.start_label = ft.Text(
            value="START GAME", size=12,
            weight=ft.FontWeight.W_700,
            color=t["on_surface2"],
            style=ft.TextStyle(letter_spacing=3),
        )
        self.cancel_btn = ft.TextButton(
            content="Cancel",
            icon=ft.Icons.CLOSE_ROUNDED,
            on_click=self._on_cancel,
            visible=False,
            style=ft.ButtonStyle(color=t["error"]),
        )
        self.version_badge = ft.Container(
            border_radius=12,
            bgcolor=t["surface2"],
            border=_border_all(1, t["outline"]),
            padding=_pad(vertical=4, horizontal=10),
            content=ft.Text(
                value=f"Installed: {current_version() or 'none'}",
                size=11, color=t["on_surface2"],
            ),
        )
        self.theme_toggle_btn = ft.IconButton(
            icon=ft.Icons.DARK_MODE_ROUNDED if self._is_light else ft.Icons.LIGHT_MODE_ROUNDED,
            icon_color=t["on_surface2"],
            icon_size=18,
            tooltip="Toggle light/dark mode",
            on_click=self._toggle_theme,
        )
        self.greeting_text = ft.Text(
            value=self._make_greeting(),
            size=11, color=t["on_surface3"],
            italic=True,
        )

        self._build_layout()

    # ── GREETING ──────────────────────────────────────
    def _make_greeting(self) -> str:
        nick  = self._settings.get("nickname", "").strip()
        count = self._settings.get("launch_count", 0)
        hour  = datetime.datetime.now().hour
        if hour < 12:   tod = "Morning"
        elif hour < 18: tod = "Afternoon"
        else:           tod = "Evening"
        if nick:
            return f"{tod}, {nick}"
        if count <= 1:
            return "Welcome."
        return f"{tod}  ·  #{count}"

    # ── LAYOUT ────────────────────────────────────────
    def _build_layout(self):
        t = self._tokens

        # ── Icon rail (left, 64px) ──────────────────
        def rail_btn(icon, tooltip, handler):
            return ft.Container(
                width=48, height=48,
                border_radius=14,
                ink=True,
                on_click=handler,
                tooltip=tooltip,
                content=ft.Icon(icon, size=22, color=t["on_surface2"]),
                    alignment=ft.Alignment.CENTER,
            )

        rail = ft.Container(
            width=64,
            bgcolor=t["rail"],
            border=_border_right(1, t["outline"]),
            padding=_pad(vertical=16, horizontal=8),
            content=ft.Column(
                spacing=4,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # logo mark at top
                    ft.Container(
                        width=36, height=36,
                        border_radius=10,
                        bgcolor=t["primary_cont"],
                        content=ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                        size=18, color=t["primary"]),
                            alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(height=12),
                    rail_btn(ft.Icons.PALETTE_ROUNDED,    "Themes",     self._show_themes),
                    rail_btn(ft.Icons.TUNE_ROUNDED,       "Settings",   self._show_settings),
                    rail_btn(ft.Icons.LEADERBOARD_ROUNDED,"My Stats",   self._show_stats),
                    rail_btn(ft.Icons.FOLDER_OPEN_ROUNDED,"Mod Folder", self._open_data),
                    rail_btn(ft.Icons.BUG_REPORT_ROUNDED, "Logs",       self._open_logs),
                    ft.Container(expand=True),
                    self.theme_toggle_btn,
                ],
            ),
        )

        # ── Center hero ─────────────────────────────
        center = ft.Container(
            expand=True,
            bgcolor=t["bg"],
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    # top bar strip
                    ft.Container(
                        height=48,
                        bgcolor=t["surface"],
                        border=_border_bottom(1, t["outline"]),
                        padding=_pad(vertical=0, horizontal=24),
                        content=ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text("Luancher",
                                        size=14, weight=ft.FontWeight.W_700,
                                        color=t["on_surface"]),
                                ft.Text(
                                    "  ·  THE LAUNCHER FOR LUANTI",
                                    size=10, color=t["on_surface3"],
                                    style=ft.TextStyle(letter_spacing=1),
                                ),
                                ft.Container(expand=True),
                                self.greeting_text,
                                ft.Container(width=8),
                                self.version_badge,
                            ],
                        ),
                    ),
                    # progress bar flush under top bar
                    self.progress_bar,
                    # hero body
                    ft.Container(
                        expand=True,
                        content=ft.Column(
                            expand=True,
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                            controls=[
                                # quote
                                ft.Container(
                                    width=360,
                                    content=self.quote_text,
                                ),
                                ft.Container(height=40),
                                    # Info section placeholder
                                    ft.Container(
                                        width=360,
                                        bgcolor=t["surface"],
                                        border_radius=8,
                                        padding=_pad(vertical=16, horizontal=20),
                                        content=ft.Text(
                                            "Enjoy playing! For bug reports, support, and connecting with the community, join https://discord.gg/DXhwwCpr3d",
                                            size=12,
                                            color=t["on_surface2"],
                                        ),
                                    ),
                                    ft.Container(height=24),
                                # ring + button stack
                                ft.Stack(
                                    width=148, height=148,
                                    controls=[
                                        self._ring,
                                        ft.Container(
                                            width=148, height=148,
                                            alignment=ft.Alignment.CENTER,
                                            content=self.start_btn,
                                        ),
                                    ],
                                ),
                                ft.Container(height=16),
                                self.start_label,
                                ft.Container(height=12),
                                self.status_chip,
                                self.cancel_btn,
                                ft.Container(height=4),
                                self.status_text,
                            ],
                        ),
                    ),
                ],
            ),
        )

        # ── News panel (right, 300px) ────────────────
        news_panel = ft.Container(
            width=300,
            bgcolor=t["surface"],
            border=_border_left(1, t["outline"]),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    # news header
                    ft.Container(
                        height=48,
                        bgcolor=t["surface"],
                        border=_border_bottom(1, t["outline"]),
                        padding=_pad(vertical=0, horizontal=20),
                        content=ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.NEWSPAPER_ROUNDED,
                                        size=15, color=t["on_surface2"]),
                                ft.Container(width=8),
                                ft.Text(
                                    "LUANTI NEWS", size=11,
                                    weight=ft.FontWeight.W_700,
                                    color=t["on_surface2"],
                                    style=ft.TextStyle(letter_spacing=1.5),
                                ),
                            ],
                        ),
                    ),
                    # news cards
                    ft.Container(
                        expand=True,
                        padding=_pad(vertical=12, horizontal=12),
                        content=self.news_col,
                    ),
                ],
            ),
        )

        self.content = ft.Row(
            expand=True, spacing=0,
            controls=[rail, center, news_panel],
        )

    # ── RAIL helpers (rebuild-safe) ───────────────────
    def _nav_btn_sheet(self, icon, label, handler):
        """Full-width nav row for bottom sheets."""
        t = self._tokens
        return ft.Container(
            border_radius=12, ink=True, on_click=handler,
            padding=_pad(vertical=10, horizontal=12),
            content=ft.Row(
                spacing=0,
                controls=[
                    ft.Icon(icon, size=18, color=t["on_surface2"]),
                    ft.Container(width=12),
                    ft.Text(label, size=13, color=t["on_surface"],
                            weight=ft.FontWeight.W_500),
                ],
            ),
        )

    # ── THEME / ACCENT ────────────────────────────────
    def _toggle_theme(self, e):
        self._is_light = not self._is_light
        self._settings["light_mode"] = self._is_light
        save_settings(self._settings)
        self._rebuild_theme()

    def _set_accent(self, name: str):
        self._accent = name
        self._settings["accent"] = name
        save_settings(self._settings)
        self._rebuild_theme()

    def _rebuild_theme(self):
        self._tokens = build_tokens(self._is_light, self._accent)
        t = self._tokens
        self.theme_toggle_btn.icon = (
            ft.Icons.DARK_MODE_ROUNDED if self._is_light
            else ft.Icons.LIGHT_MODE_ROUNDED
        )
        self._build_layout()
        self._sync_refs()
        self.load_news()
        if self.page: self.page.update()

    def _sync_refs(self):
        t = self._tokens
        self.status_text.color          = t["on_surface2"]
        self.quote_text.color           = t["on_surface2"]
        self.greeting_text.color        = t["on_surface3"]
        self.progress_bar.color         = t["primary"]
        self.progress_bar.bgcolor       = t["outline"]
        self.start_btn.bgcolor          = t["primary_cont"]
        self.start_btn.border           = _border_all(2, t["primary"])
        self._ring.border               = _border_all(2, t["primary_cont"])
        self.start_icon.color           = t["primary"]
        self.start_label.color          = t["on_surface2"]
        self.cancel_btn.style           = ft.ButtonStyle(color=t["error"])
        self.theme_toggle_btn.icon_color = t["on_surface2"]
        self.status_chip.bgcolor        = t["surface2"]
        self.status_chip.border         = _border_all(1, t["outline"])
        self._status_icon.color         = t["on_surface2"]
        self._status_label.color        = t["on_surface2"]
        self.version_badge.bgcolor      = t["surface2"]
        self.version_badge.border       = _border_all(1, t["outline"])
        self.version_badge.content.color = t["on_surface2"]

    # ── STATUS HELPERS ────────────────────────────────
    def _set_status(self, msg: str, icon=ft.Icons.INFO_OUTLINE_ROUNDED,
                    color=None):
        t = self._tokens
        c = color or t["on_surface2"]
        self._status_label.value = msg
        self._status_icon.name   = icon
        self._status_icon.color  = c
        self._status_label.color = c
        self.status_chip.visible = bool(msg)
        if self.page: self.page.update()

    def _clear_status(self):
        self.status_chip.visible = False
        self.status_text.value   = ""
        if self.page: self.page.update()

    # ── NEWS ──────────────────────────────────────────
    def load_news(self):
        t = self._tokens
        self.news_col.controls.clear()
        items = fetch_news()
        if not items:
            self.news_col.controls.append(
                ft.Container(
                    border_radius=10,
                    bgcolor=t["surface2"],
                    padding=_pad(vertical=12, horizontal=14),
                    content=ft.Row(spacing=10, controls=[
                        ft.Icon(ft.Icons.WIFI_OFF_ROUNDED,
                                size=14, color=t["on_surface2"]),
                        ft.Text("Offline — cannot load news.",
                                size=12, color=t["on_surface2"]),
                    ]),
                )
            )
            if self.page: self.news_col.update()
            return

        for n in items:
            def make_handler(item):
                return lambda e: self._show_article(item)

            # accent bar on the left edge of each card
            card = ft.Container(
                border_radius=10,
                ink=True,
                bgcolor=t["surface2"],
                border=_border_side_left(3, t["primary"]),
                padding=_pad4(left=12, top=10, right=12, bottom=10),
                margin=_margin_b(6),
                on_click=make_handler(n),
                content=ft.Column(
                    spacing=3, tight=True,
                    controls=[
                        ft.Text(n["date"],  size=10,
                                color=t["news_date"]),
                        ft.Text(n["title"], size=12,
                                weight=ft.FontWeight.W_600,
                                color=t["news_title"]),
                        ft.Text(n["desc"],  size=11,
                                color=t["on_surface2"]),
                    ],
                ),
            )
            self.news_col.controls.append(card)

        if self.page: self.news_col.update()

    # ── BOTTOM SHEETS ─────────────────────────────────
    def _open_sheet(self, sheet):
        self.page.overlay.append(sheet)
        sheet.open = True
        self.page.update()

    def _close_sheet(self, sheet):
        sheet.open = False
        self.page.update()

    def _make_sheet(self, col, height_frac=0.75):
        t = self._tokens
        h = (self.page.height or 680) * height_frac if self.page else 500
        return ft.BottomSheet(
            content=ft.Container(
                bgcolor=t["surface"],
                border_radius=_br_top(24),
                padding=_pad(vertical=24, horizontal=28),
                height=h,
                content=col,
            ),
        )

    def _sheet_title(self, title: str):
        t = self._tokens
        return ft.Text(title, size=18, weight=ft.FontWeight.W_700,
                       color=t["on_surface"])

    def _sheet_divider(self):
        return ft.Divider(height=20, color=self._tokens["outline"])

    def _sec_label(self, txt: str):
        t = self._tokens
        return ft.Text(txt, size=10, color=t["on_surface2"],
                       weight=ft.FontWeight.W_700,
                       style=ft.TextStyle(letter_spacing=1.5))

    # ── THEMES SHEET ──────────────────────────────────
    def _show_themes(self, e):
        t = self._tokens
        custom      = load_my_themes()
        solid_names = list(INTERNAL_THEMES.keys())
        image_names = ["Vanilla"] + list(custom.keys())
        active      = self._settings.get("theme", "Vanilla")

        def on_select(name):
            result = apply_theme(name, custom_themes=custom)
            self._settings["theme"] = name
            save_settings(self._settings)
            self._set_status(result, ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                             t["accent"])
            self._close_sheet(sheet)

        def tile(name, icon):
            is_active = (name == active)
            return ft.Container(
                border_radius=10, ink=True,
                bgcolor=t["surface2"] if is_active else None,
                padding=_pad(vertical=9, horizontal=12),
                on_click=lambda e, n=name: on_select(n),
                content=ft.Row(
                    spacing=0,
                    controls=[
                        ft.Icon(icon, size=16,
                                color=t["primary"] if is_active else t["on_surface2"]),
                        ft.Container(width=12),
                        ft.Text(name, size=13, color=t["on_surface"],
                                weight=ft.FontWeight.W_600 if is_active
                                else ft.FontWeight.W_400),
                        ft.Container(expand=True),
                        ft.Icon(ft.Icons.CHECK_ROUNDED, size=14,
                                color=t["primary"]) if is_active
                        else ft.Container(),
                    ],
                ),
            )

        sheet = self._make_sheet(ft.Column(
            tight=True, scroll=ft.ScrollMode.ADAPTIVE,
            controls=[
                self._sheet_title("THEME GALLERY"),
                ft.Container(height=16),
                self._sec_label("IMAGE THEMES"),
                ft.Container(height=8),
                *[tile(n, ft.Icons.IMAGE_OUTLINED) for n in image_names],
                self._sheet_divider(),
                self._sec_label("SOLID COLORS"),
                ft.Container(height=8),
                *[tile(n, ft.Icons.PALETTE_OUTLINED) for n in solid_names],
                self._sheet_divider(),
                self._sec_label("CUSTOM THEMES"),
                ft.Container(height=8),
                ft.Text(
                    "No uploader yet — paste a Base64 string instead.\n"
                    "Convert any image in ~2 min at base64.guru",
                    size=11, color=t["on_surface2"],
                ),
                ft.Container(height=8),
                ft.FilledButton(
                    content="Paste Base64 Image",
                    icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED,
                    on_click=lambda _: self._show_b64_upload(sheet),
                ),
                ft.Container(height=12),
                ft.TextButton(content="Close",
                              on_click=lambda _: self._close_sheet(sheet)),
            ],
        ))
        self._open_sheet(sheet)

    def _show_b64_upload(self, parent_sheet):
        t = self._tokens
        name_field = ft.TextField(
            label="Theme name",
            border_radius=12, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"],
        )
        b64_field = ft.TextField(
            label="Paste Base64  (data:image/png;base64,...)",
            multiline=True, min_lines=4, max_lines=8,
            border_radius=12, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"],
        )
        feedback = ft.Text("", size=12, color=t["on_surface2"])

        def save(_):
            name = (name_field.value or "").strip()
            data = (b64_field.value  or "").strip()
            if not name or not data:
                feedback.value = "Fill in both fields."
                if self.page: self.page.update()
                return
            if not data.startswith("data:image"):
                feedback.value = "Must start with 'data:image/...'."
                if self.page: self.page.update()
                return
            existing = load_my_themes()
            existing[name] = data
            save_my_themes(existing)
            feedback.value = f"Saved '{name}'! Reopen Themes to apply."
            if self.page: self.page.update()

        sheet2 = self._make_sheet(ft.Column(
            tight=True, scroll=ft.ScrollMode.ADAPTIVE,
            controls=[
                self._sheet_title("UPLOAD CUSTOM THEME"),
                ft.Container(height=8),
                ft.Text(
                    "1. Go to base64.guru/converter/encode/image\n"
                    "2. Upload your image → copy full output\n"
                    "3. Paste below.",
                    size=12, color=t["on_surface2"],
                ),
                ft.Container(height=12),
                name_field, ft.Container(height=8),
                b64_field,  ft.Container(height=8),
                feedback,   ft.Container(height=12),
                ft.Row(spacing=8, controls=[
                    ft.FilledButton(content="Save Theme",
                                    icon=ft.Icons.SAVE_ROUNDED, on_click=save),
                    ft.TextButton(content="Cancel",
                                  on_click=lambda _: self._close_sheet(sheet2)),
                ]),
            ],
        ))
        self._open_sheet(sheet2)

    # ── SETTINGS SHEET ────────────────────────────────
    def _show_settings(self, e):
        t = self._tokens
        nick_field = ft.TextField(
            label="Your nickname (optional)",
            value=self._settings.get("nickname", ""),
            border_radius=12, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"],
        )
        feedback = ft.Text("", size=12, color=t["accent"])

        def save_nick(_):
            nick = (nick_field.value or "").strip()
            self._settings["nickname"] = nick
            save_settings(self._settings)
            self.greeting_text.value = self._make_greeting()
            feedback.value = "Saved!" if nick else "Nickname cleared."
            if self.page: self.page.update()

        def accent_swatch(name, preset):
            color = preset["primary"] if not self._is_light else preset["l_primary"]
            is_active = (name == self._accent)
            return ft.Container(
                width=36, height=36, border_radius=18, bgcolor=color,
                border=_border_all(3, t["on_surface"] if is_active
                                   else t["outline"]),
                tooltip=name, ink=True,
                on_click=lambda _, n=name: [
                    self._set_accent(n), self._close_sheet(sheet)
                ],
            )

        swatches = ft.Row(
            spacing=10,
            controls=[accent_swatch(n, p)
                      for n, p in ACCENT_PRESETS.items()],
        )

        member_since = self._settings.get("first_seen") or \
                       datetime.date.today().isoformat()

        sheet = self._make_sheet(ft.Column(
            tight=True, scroll=ft.ScrollMode.ADAPTIVE,
            controls=[
                self._sheet_title("SETTINGS"),
                ft.Container(height=4),
                ft.Text(f"Member since {member_since}",
                        size=11, color=t["on_surface2"]),
                self._sheet_divider(),

                self._sec_label("NICKNAME"),
                ft.Container(height=8),
                nick_field, ft.Container(height=8),
                ft.Row(spacing=8, controls=[
                    ft.FilledButton(content="Save",
                                    icon=ft.Icons.SAVE_ROUNDED,
                                    on_click=save_nick),
                ]),
                feedback,

                self._sheet_divider(),
                self._sec_label("ACCENT COLOR"),
                ft.Container(height=10),
                swatches,

                self._sheet_divider(),
                self._sec_label("DISPLAY MODE"),
                ft.Container(height=8),
                ft.Row(spacing=8, controls=[
                    ft.FilledButton(
                        content="Dark",
                        icon=ft.Icons.DARK_MODE_ROUNDED,
                        on_click=lambda _: [
                            self._force_mode(False),
                            self._close_sheet(sheet),
                        ],
                    ),
                    ft.FilledButton(
                        content="Light",
                        icon=ft.Icons.LIGHT_MODE_ROUNDED,
                        on_click=lambda _: [
                            self._force_mode(True),
                            self._close_sheet(sheet),
                        ],
                    ),
                ]),
                ft.Container(height=16),
                ft.TextButton(content="Close",
                              on_click=lambda _: self._close_sheet(sheet)),
            ],
        ))
        self._open_sheet(sheet)

    def _force_mode(self, light: bool):
        if self._is_light == light: return
        self._is_light = light
        self._settings["light_mode"] = light
        save_settings(self._settings)
        self._rebuild_theme()

    # ── STATS SHEET ───────────────────────────────────
    def _show_stats(self, e):
        t = self._tokens
        s = self._settings

        def stat_row(label, value):
            return ft.Container(
                padding=_pad(vertical=10, horizontal=0),
                border=_border_bottom(1, t["outline"]),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(label, size=13, color=t["on_surface2"]),
                        ft.Text(str(value), size=13,
                                weight=ft.FontWeight.W_600,
                                color=t["primary"]),
                    ],
                ),
            )

        launches   = s.get("launch_count",  0)
        sessions   = s.get("total_sessions", 0)
        first_seen = s.get("first_seen", "unknown")
        nick       = s.get("nickname", "") or "Anonymous"
        accent     = s.get("accent",  "Blue")

        # milestone badge
        msg = "Just getting started. Good luck out there."
        for threshold in sorted(LAUNCH_MILESTONES.keys(), reverse=True):
            if launches >= threshold:
                msg = LAUNCH_MILESTONES[threshold]
                break
        badge = ft.Container(
            border_radius=12, bgcolor=t["surface2"],
            padding=_pad(vertical=12, horizontal=14),
            content=ft.Row(spacing=12, controls=[
                ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED,
                        color=t["primary"], size=22),
                ft.Text(msg, size=12, color=t["on_surface"], expand=True),
            ]),
        )

        sheet = self._make_sheet(ft.Column(
            tight=True, scroll=ft.ScrollMode.ADAPTIVE,
            controls=[
                self._sheet_title("MY STATS"),
                ft.Container(height=12),
                badge,
                ft.Container(height=12),
                stat_row("Player",           nick),
                stat_row("Luancher opens",   launches),
                stat_row("Games launched",   sessions),
                stat_row("Member since",     first_seen),
                stat_row("Active accent",    accent),
                stat_row("Display mode",     "Light" if self._is_light else "Dark"),
                ft.Container(height=16),
                ft.TextButton(content="Close",
                              on_click=lambda _: self._close_sheet(sheet)),
            ],
        ))
        self._open_sheet(sheet)

    # ── NEWS ARTICLE ──────────────────────────────────
    def _show_article(self, news_item):
        t = self._tokens
        clean = html_to_text(news_item["full"])
        sheet = self._make_sheet(ft.Column(
            tight=True, scroll=ft.ScrollMode.ADAPTIVE, expand=True,
            controls=[
                ft.Text(news_item["title"], size=18,
                        weight=ft.FontWeight.W_700, color=t["on_surface"]),
                ft.Text(news_item["date"], size=11, color=t["news_date"]),
                self._sheet_divider(),
                ft.Text(clean, size=13, color=t["on_surface2"], selectable=True),
                ft.Container(height=16),
                ft.TextButton(content="Close",
                              on_click=lambda _: self._close_sheet(sheet)),
            ],
        ), height_frac=0.85)
        self._open_sheet(sheet)

    # ── FOLDER SHORTCUTS ──────────────────────────────
    def _open_folder(self, path):
        try:
            if sys.platform == "darwin":  subprocess.Popen(["open",     str(path)])
            elif sys.platform == "win32": subprocess.Popen(["explorer", str(path)])
            else:                         subprocess.Popen(["xdg-open", str(path)])
        except Exception as ex:
            self._set_status(f"Cannot open: {ex}", ft.Icons.ERROR_OUTLINE_ROUNDED,
                             self._tokens["error"])

    def _open_data(self, e): self._open_folder(SRC / "mods")
    def _open_logs(self, e): self._open_folder(LOGS)

    # ── START / CANCEL ────────────────────────────────
    def _on_start(self, e):
        if self.is_busy: return
        self.cancel_event = threading.Event()
        self._set_busy(True)
        self._set_status("Checking Luanti...",
                         ft.Icons.MANAGE_SEARCH_ROUNDED)

    def _on_cancel(self, e):
        if self.cancel_event:
            self.cancel_event.set()
            self._set_status("Cancelling...",
                             ft.Icons.HOURGLASS_TOP_ROUNDED)
            self.cancel_btn.disabled = True
            if self.page: self.page.update()

    def _set_busy(self, busy: bool):
        t = self._tokens
        self.is_busy = busy
        self.start_btn.bgcolor  = t["surface3"] if busy else t["primary_cont"]
        self.start_icon.color   = t["on_surface2"] if busy else t["primary"]
        self.start_btn.border   = _border_all(
            2, t["outline"] if busy else t["primary"]
        )
        self._ring.border = _border_all(
            2, t["outline"] if busy else t["primary_cont"]
        )
        self.start_btn.on_click = None if busy else self._on_start
        self.progress_bar.visible = busy
        self.cancel_btn.visible   = busy
        self.cancel_btn.disabled  = False
        if not busy:
            self.version_badge.content.value = \
                f"Installed: {current_version() or 'none'}"
        if self.page: self.page.update()
        if busy:
            threading.Thread(target=self._flow, daemon=True).start()

    def _flow(self):
        try:
            ensure_dirs()
            latest  = latest_version()
            current = current_version()
            self.is_update = current is not None
            self.cancel_btn.content = (
                "Cancel Update" if self.is_update else "Cancel Install"
            )

            if current != latest:
                verb = "Updating to" if self.is_update else "Installing"
                self._set_status(f"{verb} {latest}...",
                                 ft.Icons.DOWNLOAD_ROUNDED,
                                 self._tokens["primary"])
                build(latest, cancel_event=self.cancel_event)
                migrate(latest)
                switch_current(latest)

            self._settings["total_sessions"] = \
                self._settings.get("total_sessions", 0) + 1
            save_settings(self._settings)

            self._set_status("Launching...",
                             ft.Icons.ROCKET_LAUNCH_ROUNDED,
                             self._tokens["accent"])
            launch()

            count = self._settings.get("launch_count", 0)
            if count in LAUNCH_MILESTONES:
                self._show_milestone(LAUNCH_MILESTONES[count])

        except InterruptedError:
            if self.is_update:
                self._set_status("Update cancelled. Launching...",
                                 ft.Icons.WARNING_AMBER_ROUNDED,
                                 self._tokens["error"])
                try: launch()
                except Exception: pass
            else:
                self._set_status("Installation cancelled.",
                                 ft.Icons.CANCEL_OUTLINED)
        except Exception as ex:
            self._set_status(f"Error: {ex}",
                             ft.Icons.ERROR_OUTLINE_ROUNDED,
                             self._tokens["error"])
            log(str(ex))
        finally:
            self._set_busy(False)
            self.quote_text.value = get_daily_quote(self._settings)
            self.cancel_event = None
            if self.page: self.page.update()

    def _show_milestone(self, msg: str):
        t = self._tokens
        sheet = self._make_sheet(ft.Column(
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED,
                        size=48, color=t["primary"]),
                ft.Container(height=8),
                ft.Text("MILESTONE", size=12, weight=ft.FontWeight.W_700,
                        color=t["on_surface2"],
                        style=ft.TextStyle(letter_spacing=2)),
                ft.Container(height=8),
                ft.Text(msg, size=15, color=t["on_surface"],
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=24),
                ft.TextButton(content="Thanks!",
                              on_click=lambda _: self._close_sheet(sheet)),
            ],
        ), height_frac=0.45)
        self._open_sheet(sheet)

# =====================================================
# ENTRY
# =====================================================
def main(page: ft.Page):
    page.title      = "Luancher"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding    = 0
    page.spacing    = 0
    try:
        page.window.width      = 1080
        page.window.height     = 680
        page.window.min_width  = 860
        page.window.min_height = 520
    except AttributeError:
        page.window_width      = 1080   # type: ignore
        page.window_height     = 680    # type: ignore
        page.window_min_width  = 860    # type: ignore
        page.window_min_height = 520    # type: ignore

    ensure_dirs()
    settings = load_settings()
    settings["launch_count"] = settings.get("launch_count", 0) + 1
    if not settings.get("first_seen"):
        settings["first_seen"] = datetime.date.today().isoformat()
    save_settings(settings)

    launcher = Launcher(settings)

    saved_theme = settings.get("theme", "Vanilla")
    if saved_theme and saved_theme != "Vanilla":
        threading.Thread(
            target=lambda: apply_theme(saved_theme,
                                       custom_themes=load_my_themes()),
            daemon=True,
        ).start()

    page.add(launcher)
    threading.Thread(target=launcher.load_news, daemon=True).start()


if __name__ == "__main__":
    ft.run(main)
