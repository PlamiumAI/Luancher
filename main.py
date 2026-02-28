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
import queue
import webbrowser
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

GITHUB_API      = "https://api.github.com/repos/luanti-org/luanti/releases/latest"
GITHUB_RELEASES = "https://api.github.com/repos/luanti-org/luanti/releases?per_page=30"
RSS_FEED        = "https://blog.luanti.org/feed.rss"

MIGRATE_PATHS = [
    "games", "mods", "worlds", "textures", "cache",
    "minetest.conf", "client/serverlist/favoriteservers.json",
]

QUOTES = [
    ("Play is the highest form of research.", "Albert Einstein"),
    ("Imagination is more important than knowledge.", "Albert Einstein"),
    ("Creativity is intelligence having fun.", "Albert Einstein"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Logic will get you from A to B. Imagination will take you everywhere.", "Albert Einstein"),
    ("In the middle of every difficulty lies opportunity.", "Albert Einstein"),
    ("The expert in anything was once a beginner.", "Helen Hayes"),
    ("Whether you think you can or you think you can't, you're right.", "Henry Ford"),
]

LAUNCH_MILESTONES = {
    1:   "First launch! Welcome to Luancher.",
    5:   "5 launches already. You're getting the hang of it!",
    10:  "10 launches. A seasoned explorer.",
    25:  "25 launches. Practically a Luanti veteran.",
    50:  "50 launches. Are you okay?",
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
    "theme":            "Vanilla",
    "light_mode":       False,
    "accent":           "Blue",
    "nickname":         "",
    "launch_count":     0,
    "quote_index":      0,
    "quote_date":       "",
    "total_sessions":   0,
    "first_seen":       "",
    "selected_version": "latest",
    "known_latest":     "",
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
    q, author = QUOTES[s["quote_index"]]
    return f'"{q}"  — {author}'

# =====================================================
# DESIGN TOKENS
# =====================================================
DARK_BASE = {
    "bg":           "#0d0d11",
    "surface":      "#16161e",
    "surface2":     "#1e1e28",
    "surface3":     "#262632",
    "rail":         "#111118",
    "outline":      "#2e2e3e",
    "on_surface":   "#e8e6f4",
    "on_surface2":  "#8e8aa8",
    "on_surface3":  "#5a566e",
    "accent":       "#7fd9a0",
    "error":        "#ff8a80",
    "news_title":   "#c8b8ff",
    "news_date":    "#6a6680",
    "console_bg":   "#090910",
    "console_text": "#b0f0b0",
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
    "console_bg":   "#1a1a22",
    "console_text": "#90ee90",
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
# LAYOUT HELPERS
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

def _border_top(width, color):
    return ft.Border(top=ft.BorderSide(width, color))

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
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    with open(LOGS / "launcher.log", "a") as f:
        f.write(f"[{ts}] {msg}\n")

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
# VERSION HELPERS
# =====================================================
def _parse_ver(tag: str):
    try:
        return tuple(int(x) for x in tag.lstrip("v").split(".")[:3])
    except Exception:
        return (0, 0, 0)

def version_is_legacy(tag: str) -> bool:
    return _parse_ver(tag) < (5, 13, 0)

def fetch_all_releases() -> list:
    try:
        r = requests.get(GITHUB_RELEASES,
                         headers={"User-Agent": "Luancher-Client"},
                         timeout=15)
        r.raise_for_status()
        out = []
        for rel in r.json():
            out.append({
                "tag":        rel["tag_name"].lstrip("v"),
                "name":       rel.get("name") or rel["tag_name"],
                "date":       rel.get("published_at", "")[:10],
                "prerelease": rel.get("prerelease", False),
            })
        return out
    except Exception:
        return []

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
# BUILD / LAUNCH
# =====================================================
def run_cmd_stream(cmd, cwd=None, cancel_event=None, out_q=None):
    log("RUN: " + " ".join(str(c) for c in cmd))
    proc = subprocess.Popen(
        cmd, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    if out_q is not None:
        def _reader():
            for line in proc.stdout:
                out_q.put(("line", line.rstrip()))
            out_q.put(("done", None))
        threading.Thread(target=_reader, daemon=True).start()
    while proc.poll() is None:
        if cancel_event and cancel_event.is_set():
            proc.terminate()
            try:    proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill()
            raise InterruptedError("Cancelled by user")
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

def latest_version() -> str:
    r = requests.get(GITHUB_API,
                     headers={"User-Agent": "Luancher-Client"},
                     timeout=15)
    r.raise_for_status()
    return r.json()["tag_name"].lstrip("v")

def current_version():
    link = BUILDS / "current"
    if link.exists() and link.is_symlink():
        try: return link.resolve().name
        except Exception: pass
    return None

def installed_versions() -> list:
    if not BUILDS.exists(): return []
    return sorted(
        [d.name for d in BUILDS.iterdir()
         if d.is_dir() and d.name != "current"],
        key=_parse_ver, reverse=True,
    )

def _get_source_tarball_url(version: str) -> str:
    """Return the source tarball URL from GitHub for this version."""
    for tag in [version, f"v{version}"]:
        url = f"https://api.github.com/repos/luanti-org/luanti/releases/tags/{tag}"
        try:
            r = requests.get(url, headers={"User-Agent": "Luancher-Client"}, timeout=15)
            if r.status_code == 200:
                return r.json()["tarball_url"]
        except Exception:
            continue
    raise RuntimeError(f"Could not find release for version {version} on GitHub.")

def build_version(version, cancel_event=None, out_q=None):
    """Download source tarball from GitHub release and build with cmake."""
    target = BUILDS / version
    if target.exists(): return

    def _emit(msg):
        log(msg)
        if out_q: out_q.put(("line", msg))

    def _check_cancel():
        if cancel_event and cancel_event.is_set():
            raise InterruptedError("Cancelled by user")

    CACHE.mkdir(parents=True, exist_ok=True)
    archive_path = CACHE / f"luanti-{version}.tar.gz"

    _emit(f"Fetching release info for v{version}...")
    dl_url = _get_source_tarball_url(version)

    _emit(f"Downloading source for v{version}...")
    with requests.get(dl_url, stream=True, timeout=120,
                      headers={"User-Agent": "Luancher-Client"}) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        done  = 0
        with open(archive_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                _check_cancel()
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    _emit(f"Downloading... {pct}%  ({done // 1024 // 1024} / {total // 1024 // 1024} MB)")

    _emit("Extracting source...")
    _check_cancel()
    import tarfile
    tmp = CACHE / f"_src_{version}"
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as tf:
        tf.extractall(tmp)

    # GitHub tarballs have a single top-level dir
    entries = list(tmp.iterdir())
    src_dir = entries[0] if len(entries) == 1 and entries[0].is_dir() else tmp

    _emit("Running cmake...")
    _check_cancel()
    target.mkdir(parents=True, exist_ok=True)
    run_cmd_stream(
        ["cmake", str(src_dir),
         f"-DCMAKE_INSTALL_PREFIX={target}",
         "-DRUN_IN_PLACE=FALSE",
         "-DENABLE_GETTEXT=TRUE"],
        cwd=target, cancel_event=cancel_event, out_q=out_q,
    )

    _emit(f"Compiling with {os.cpu_count() or 2} cores (this takes a while)...")
    run_cmd_stream(
        ["make", "-j", str(os.cpu_count() or 2), "install"],
        cwd=target, cancel_event=cancel_event, out_q=out_q,
    )

    # Cleanup
    try: archive_path.unlink()
    except Exception: pass
    try: shutil.rmtree(tmp)
    except Exception: pass

    _emit(f"v{version} built and installed.")
    if out_q: out_q.put(("done", None))

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

def find_binary(version: str):
    if version is None: return None
    base = BUILDS / version
    if not base.exists(): return None
    # Search common locations, then fall back to recursive search
    for name in ["luanti", "minetest"]:
        for candidate in [
            base / "bin" / name,
            base / name,
            base / "luanti" / "bin" / name,
            base / "minetest" / "bin" / name,
        ]:
            if candidate.exists(): return candidate
    # Recursive fallback
    for name in ["luanti", "minetest"]:
        for p in base.rglob(name):
            if p.is_file() and os.access(p, os.X_OK):
                return p
    return None

def launch(version: str):
    binary = find_binary(version)
    if not binary:
        raise FileNotFoundError(f"No binary for v{version}. Is it built?")
    os.chmod(binary, 0o755)
    subprocess.Popen([str(binary)])

# =====================================================
# NEWS — cached, non-blocking
# =====================================================
_news_cache = None
_news_lock  = threading.Lock()

def fetch_news():
    global _news_cache
    with _news_lock:
        if _news_cache is not None:
            return _news_cache
    try:
        feed = feedparser.parse(RSS_FEED)
        if not feed.entries: return None
        out = []
        for e in feed.entries[:6]:
            words = e.get("summary", "").split()
            short = " ".join(words[:8]) + ("..." if len(words) > 8 else "")
            out.append({
                "title": e.title,
                "date":  e.get("published", ""),
                "desc":  short,
                "full":  e.get("summary", ""),
                "link":  e.get("link", ""),
            })
        with _news_lock:
            _news_cache = out
        return out
    except Exception:
        return None

# =====================================================
# UI — LAUNCHER
# =====================================================
class Launcher(ft.Container):
    def __init__(self, settings: dict):
        super().__init__()
        self.expand    = True
        self.is_busy   = False
        self.cancel_event = None
        self._settings = settings
        self._is_light = settings.get("light_mode", False)
        self._accent   = settings.get("accent", "Blue")
        self._tokens   = build_tokens(self._is_light, self._accent)
        self._latest_ver = ""
        self._out_q: queue.Queue = queue.Queue()

        t = self._tokens

        # ── Status chip ──
        self.status_chip = ft.Container(
            visible=False, border_radius=20,
            bgcolor=t["surface2"], border=_border_all(1, t["outline"]),
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

        self.quote_text = ft.Text(
            value=get_daily_quote(settings),
            size=13, italic=True, color=t["on_surface2"],
            text_align=ft.TextAlign.CENTER,
        )
        self.news_col = ft.Column(
            spacing=6, scroll=ft.ScrollMode.ADAPTIVE, expand=True
        )
        self.progress_bar = ft.ProgressBar(
            color=t["primary"], bgcolor=t["outline"],
            visible=False, border_radius=2, height=3,
        )

        # ── START BUTTON ──
        self._play_icon = ft.Icon(
            ft.Icons.PLAY_ARROW_ROUNDED, size=20, color=t["primary"]
        )
        self._start_text = ft.Text(
            value="START GAME", size=14,
            weight=ft.FontWeight.W_700, color=t["on_surface"],
            style=ft.TextStyle(letter_spacing=1.5),
        )
        self.start_btn = ft.Container(
            width=230, height=56,
            border_radius=14,
            bgcolor=t["primary_cont"],
            border=_border_all(2, t["primary"]),
            ink=True, on_click=self._on_start,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
                controls=[self._play_icon, self._start_text],
            ),
        )
        self.cancel_btn = ft.TextButton(
            content="Cancel",
            icon=ft.Icons.CLOSE_ROUNDED,
            on_click=self._on_cancel,
            visible=False,
            style=ft.ButtonStyle(color=t["error"]),
        )
        self.version_badge = ft.Container(
            border_radius=12, bgcolor=t["surface2"],
            border=_border_all(1, t["outline"]),
            padding=_pad(vertical=4, horizontal=10),
            content=ft.Text(
                value=self._badge_text(),
                size=11, color=t["on_surface2"],
            ),
        )
        self.theme_toggle_btn = ft.IconButton(
            icon=ft.Icons.DARK_MODE_ROUNDED if self._is_light
                 else ft.Icons.LIGHT_MODE_ROUNDED,
            icon_color=t["on_surface2"],
            icon_size=18,
            tooltip="Toggle light/dark mode",
            on_click=self._toggle_theme,
        )
        self.greeting_text = ft.Text(
            value=self._make_greeting(),
            size=11, color=t["on_surface3"], italic=True,
        )

        self._build_lines = []  # internal log buffer

        # ── Version selector card ──
        self._ver_label = ft.Text(
            value=self._ver_selector_text(),
            size=13, color=t["on_surface"],
            weight=ft.FontWeight.W_600,
        )
        self._ver_sub = ft.Text(
            value=self._ver_selector_sub(),
            size=11, color=t["on_surface2"],
        )
        self._version_selector_card = ft.Container(
            width=380, border_radius=12,
            bgcolor=t["surface"],
            border=_border_all(1, t["outline"]),
            padding=_pad(vertical=10, horizontal=16),
            ink=True,
            on_click=self._show_version_manager,
            tooltip="Click to change version",
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    ft.Container(
                        width=36, height=36, border_radius=10,
                        bgcolor=t["primary_cont"],
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(ft.Icons.LAYERS_ROUNDED,
                                        size=18, color=t["primary"]),
                    ),
                    ft.Column(
                        spacing=2, tight=True, expand=True,
                        controls=[self._ver_label, self._ver_sub],
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,
                            size=18, color=t["on_surface3"]),
                ],
            ),
        )

        self._build_layout()
        threading.Thread(target=self._check_update_async, daemon=True).start()

    # ── HELPERS ──────────────────────────────────────
    def _badge_text(self) -> str:
        sel = self._settings.get("selected_version", "latest")
        cv  = current_version()
        if sel == "latest":
            return f"Latest  {cv or '—'}"
        return f"v{sel}  {'✓' if find_binary(sel) else '✗'}"

    def _make_greeting(self) -> str:
        nick  = self._settings.get("nickname", "").strip()
        count = self._settings.get("launch_count", 0)
        hour  = datetime.datetime.now().hour
        tod   = ("Morning" if hour < 12 else
                 "Afternoon" if hour < 18 else "Evening")
        if nick:       return f"{tod}, {nick}"
        if count <= 1: return "Welcome."
        return f"{tod}  ·  #{count}"

    def _ver_selector_text(self) -> str:
        sel = self._settings.get("selected_version", "latest")
        if sel == "latest":
            cv = current_version()
            lv = self._latest_ver
            if lv: return f"Latest  (v{lv})"
            return f"Latest  (v{cv or '—'})"
        return f"Pinned: v{sel}"

    def _ver_selector_sub(self) -> str:
        sel = self._settings.get("selected_version", "latest")
        if sel == "latest":
            return "Auto-updates to newest release · click to change"
        ok = find_binary(sel) is not None
        return "Installed · pinned, no auto-update" if ok else "Not built yet · click to install"

    def _refresh_ver_card(self):
        if not hasattr(self, "_ver_label"): return
        self._ver_label.value = self._ver_selector_text()
        self._ver_sub.value   = self._ver_selector_sub()
        if self.page:
            try: self.page.update()
            except Exception: pass

    def _check_update_async(self):
        try:
            lv = latest_version()
            self._latest_ver = lv
            self._settings["known_latest"] = lv
            save_settings(self._settings)
            if self.page:
                self.version_badge.content.value = self._badge_text()
                self._refresh_ver_card()
                try: self.page.update()
                except Exception: pass
        except Exception:
            pass

    def _ui(self, fn):
        """Run fn() and call page.update() — safe to call from any thread."""
        fn()
        if self.page:
            try: self.page.update()
            except Exception: pass

    def _drain_build_output(self):
        while True:
            try:
                kind, val = self._out_q.get(timeout=0.2)
                if kind == "done": break
                if kind == "line":
                    self._build_lines.append(val)
            except queue.Empty:
                continue

    # ── LAYOUT ───────────────────────────────────────
    def _build_layout(self):
        t = self._tokens

        def rail_btn(icon, tooltip, handler):
            return ft.Container(
                width=48, height=48, border_radius=14,
                ink=True, on_click=handler, tooltip=tooltip,
                content=ft.Icon(icon, size=22, color=t["on_surface2"]),
                alignment=ft.Alignment(0, 0),
            )

        rail = ft.Container(
            width=64, bgcolor=t["rail"],
            border=_border_right(1, t["outline"]),
            padding=_pad(vertical=16, horizontal=8),
            content=ft.Column(
                spacing=4, expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=36, height=36, border_radius=10,
                        bgcolor=t["primary_cont"],
                        content=ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                        size=18, color=t["primary"]),
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Container(height=12),
                    rail_btn(ft.Icons.PALETTE_ROUNDED,     "Themes",     self._show_themes),
                    rail_btn(ft.Icons.TUNE_ROUNDED,        "Settings",   self._show_settings),
                    rail_btn(ft.Icons.LEADERBOARD_ROUNDED, "My Stats",   self._show_stats),
                    rail_btn(ft.Icons.FOLDER_OPEN_ROUNDED, "Mod Folder", self._open_data),
                    rail_btn(ft.Icons.BUG_REPORT_ROUNDED,  "Logs",       self._open_logs),
                    ft.Container(expand=True),
                    self.theme_toggle_btn,
                ],
            ),
        )

        center = ft.Container(
            expand=True, bgcolor=t["bg"],
            content=ft.Column(
                expand=True, spacing=0,
                controls=[
                    # top bar
                    ft.Container(
                        height=48, bgcolor=t["surface"],
                        border=_border_bottom(1, t["outline"]),
                        padding=_pad(vertical=0, horizontal=24),
                        content=ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text("Luancher", size=14,
                                        weight=ft.FontWeight.W_700,
                                        color=t["on_surface"]),
                                ft.Text("  ·  THE LAUNCHER FOR LUANTI",
                                        size=10, color=t["on_surface3"],
                                        style=ft.TextStyle(letter_spacing=1)),
                                ft.Container(expand=True),
                                self.greeting_text,
                                ft.Container(width=8),
                                self.version_badge,
                            ],
                        ),
                    ),
                    self.progress_bar,
                    # hero
                    ft.Container(
                        expand=True,
                        content=ft.Column(
                            expand=True,
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                            controls=[
                                ft.Container(width=380, content=self.quote_text),
                                ft.Container(height=20),
                                # Discord card
                                ft.Container(
                                    width=380,
                                    bgcolor=t["surface"],
                                    border_radius=10,
                                    border=_border_side_left(3, t["primary"]),
                                    padding=_pad(vertical=10, horizontal=16),
                                    content=ft.Row(
                                        spacing=10,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Icon(ft.Icons.FORUM_ROUNDED,
                                                    size=15, color=t["on_surface2"]),
                                            ft.Text("Community & support: ",
                                                    size=12, color=t["on_surface2"]),
                                            ft.GestureDetector(
                                                on_tap=lambda _: webbrowser.open(
                                                    "https://discord.gg/DXhwwCpr3d"),
                                                content=ft.Text(
                                                    "discord.gg/DXhwwCpr3d",
                                                    size=12, color=t["primary"],
                                                    style=ft.TextStyle(
                                                        decoration=ft.TextDecoration.UNDERLINE),
                                                ),
                                            ),
                                        ],
                                    ),
                                ),
                                ft.Container(height=20),
                                # Version selector card
                                self._version_selector_card,
                                ft.Container(height=16),
                                # START button
                                self.start_btn,
                                ft.Container(height=10),
                                self.cancel_btn,
                                ft.Container(height=8),
                                self.status_chip,

                            ],
                        ),
                    ),
                ],
            ),
        )

        news_panel = ft.Container(
            width=300, bgcolor=t["surface"],
            border=_border_left(1, t["outline"]),
            content=ft.Column(
                expand=True, spacing=0,
                controls=[
                    ft.Container(
                        height=48, bgcolor=t["surface"],
                        border=_border_bottom(1, t["outline"]),
                        padding=_pad(vertical=0, horizontal=20),
                        content=ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.NEWSPAPER_ROUNDED,
                                        size=15, color=t["on_surface2"]),
                                ft.Container(width=8),
                                ft.Text("LUANTI NEWS", size=11,
                                        weight=ft.FontWeight.W_700,
                                        color=t["on_surface2"],
                                        style=ft.TextStyle(letter_spacing=1.5)),
                            ],
                        ),
                    ),
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

    # ── SYNC after theme change ───────────────────────
    def _sync_refs(self):
        t = self._tokens
        self.quote_text.color            = t["on_surface2"]
        self.greeting_text.color         = t["on_surface3"]
        self.progress_bar.color          = t["primary"]
        self.progress_bar.bgcolor        = t["outline"]
        self.start_btn.bgcolor           = t["primary_cont"]
        self.start_btn.border            = _border_all(2, t["primary"])
        self._play_icon.color            = t["primary"]
        self._start_text.color           = t["on_surface"]
        self.cancel_btn.style            = ft.ButtonStyle(color=t["error"])
        self.theme_toggle_btn.icon_color  = t["on_surface2"]
        self.status_chip.bgcolor         = t["surface2"]
        self.status_chip.border          = _border_all(1, t["outline"])
        self._status_icon.color          = t["on_surface2"]
        self._status_label.color         = t["on_surface2"]
        self.version_badge.bgcolor       = t["surface2"]
        self.version_badge.border        = _border_all(1, t["outline"])
        self.version_badge.content.color = t["on_surface2"]


    # ── THEME ─────────────────────────────────────────
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
        self.theme_toggle_btn.icon = (
            ft.Icons.DARK_MODE_ROUNDED if self._is_light
            else ft.Icons.LIGHT_MODE_ROUNDED
        )
        self._build_layout()
        self._sync_refs()
        self.load_news()
        if self.page: self.page.update()

    def _force_mode(self, light: bool):
        if self._is_light == light: return
        self._is_light = light
        self._settings["light_mode"] = light
        save_settings(self._settings)
        self._rebuild_theme()

    # ── STATUS ────────────────────────────────────────
    def _set_status(self, msg, icon=ft.Icons.INFO_OUTLINE_ROUNDED, color=None):
        t = self._tokens
        c = color or t["on_surface2"]
        self._status_label.value = msg
        self._status_icon.name   = icon
        self._status_icon.color  = c
        self._status_label.color = c
        self.status_chip.visible = bool(msg)
        if self.page:
            try: self.page.update()
            except Exception: pass

    # ── NEWS ──────────────────────────────────────────
    def load_news(self):
        t = self._tokens
        self.news_col.controls.clear()
        self.news_col.controls.append(
            ft.Container(
                border_radius=10, bgcolor=t["surface2"],
                padding=_pad(vertical=12, horizontal=14),
                content=ft.Row(spacing=10, controls=[
                    ft.ProgressRing(width=14, height=14, stroke_width=2,
                                    color=t["primary"]),
                    ft.Text("Loading news...", size=12, color=t["on_surface2"]),
                ]),
            )
        )
        if self.page:
            try: self.page.update()
            except Exception: pass

        def _fetch():
            items = fetch_news()
            self.news_col.controls.clear()
            if not items:
                self.news_col.controls.append(
                    ft.Container(
                        border_radius=10, bgcolor=t["surface2"],
                        padding=_pad(vertical=12, horizontal=14),
                        content=ft.Row(spacing=10, controls=[
                            ft.Icon(ft.Icons.WIFI_OFF_ROUNDED,
                                    size=14, color=t["on_surface2"]),
                            ft.Text("Offline — cannot load news.",
                                    size=12, color=t["on_surface2"]),
                        ]),
                    )
                )
            else:
                for n in items:
                    def _handler(item):
                        return lambda e: self._show_article(item)
                    card = ft.Container(
                        border_radius=10, ink=True, bgcolor=t["surface2"],
                        border=_border_side_left(3, t["primary"]),
                        padding=_pad4(left=12, top=10, right=12, bottom=10),
                        margin=_margin_b(6),
                        on_click=_handler(n),
                        content=ft.Column(
                            spacing=3, tight=True,
                            controls=[
                                ft.Text(n["date"],  size=10, color=t["news_date"]),
                                ft.Text(n["title"], size=12,
                                        weight=ft.FontWeight.W_600,
                                        color=t["news_title"]),
                                ft.Text(n["desc"],  size=11, color=t["on_surface2"]),
                            ],
                        ),
                    )
                    self.news_col.controls.append(card)
            if self.page:
                try: self.page.update()
                except Exception: pass

        threading.Thread(target=_fetch, daemon=True).start()

    # ── SHEETS ────────────────────────────────────────
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
                height=h, content=col,
            ),
        )

    def _title(self, txt):
        return ft.Text(txt, size=18, weight=ft.FontWeight.W_700,
                       color=self._tokens["on_surface"])

    def _divider(self):
        return ft.Divider(height=20, color=self._tokens["outline"])

    def _sec(self, txt):
        return ft.Text(txt, size=10, color=self._tokens["on_surface2"],
                       weight=ft.FontWeight.W_700,
                       style=ft.TextStyle(letter_spacing=1.5))

    # ── VERSION MANAGER ───────────────────────────────
    def _show_version_manager(self, e=None):
        t    = self._tokens
        sel  = self._settings.get("selected_version", "latest")
        inst = installed_versions()

        sel_label = ft.Text(
            value=self._vm_sel_text(sel, inst),
            size=12, color=t["accent"],
            weight=ft.FontWeight.W_600,
        )

        releases_body = ft.Column(tight=True, spacing=4,
                                  scroll=ft.ScrollMode.ADAPTIVE)
        releases_body.controls.append(ft.Row(spacing=8, controls=[
            ft.ProgressRing(width=14, height=14,
                            stroke_width=2, color=t["primary"]),
            ft.Text("Fetching releases from GitHub...",
                    size=12, color=t["on_surface2"]),
        ]))

        content_col = ft.Column(
            tight=True, spacing=0, scroll=ft.ScrollMode.ADAPTIVE,
            controls=[],
        )
        sheet = self._make_sheet(content_col, height_frac=0.90)

        content_col.controls = [
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self._title("VERSION MANAGER"),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        icon_size=18, icon_color=t["on_surface2"],
                        tooltip="Refresh",
                        on_click=lambda _: threading.Thread(
                            target=self._vm_load_releases,
                            args=(releases_body, sel_label, sheet),
                            daemon=True,
                        ).start(),
                    ),
                ],
            ),
            ft.Container(height=4),
            sel_label,
            ft.Container(height=2),
            ft.Text("Versions coexist independently. "
                    "Pinned versions never auto-update.",
                    size=11, color=t["on_surface2"]),
            self._divider(),
            self._sec("INSTALLED"),
            ft.Container(height=8),
            *self._vm_installed_tiles(inst, sel, sel_label, sheet),
            self._divider(),
            self._sec("AVAILABLE RELEASES"),
            ft.Container(height=8),
            releases_body,
            ft.Container(height=12),
            ft.TextButton(content="Close",
                          on_click=lambda _: self._close_sheet(sheet)),
        ]

        self._open_sheet(sheet)
        threading.Thread(
            target=self._vm_load_releases,
            args=(releases_body, sel_label, sheet),
            daemon=True,
        ).start()

    def _vm_sel_text(self, sel, inst) -> str:
        if sel == "latest":
            cv = current_version()
            lv = self._latest_ver
            if lv and cv and cv != lv:
                return f"Active: Latest  (v{cv} installed, v{lv} available)"
            return f"Active: Latest  (v{cv or '—'})"
        ok = find_binary(sel) is not None
        return f"Active: v{sel}  ({'installed' if ok else 'not built'})"

    def _vm_select(self, tag, sel_label, sheet):
        self._settings["selected_version"] = tag
        save_settings(self._settings)
        inst = installed_versions()
        sel_label.value = self._vm_sel_text(tag, inst)
        self.version_badge.content.value = self._badge_text()
        self._refresh_ver_card()
        if self.page:
            try: self.page.update()
            except Exception: pass

    def _vm_installed_tiles(self, inst, sel, sel_label, sheet):
        t = self._tokens
        tiles = []
        is_sel = (sel == "latest")
        cv  = current_version()
        sub = f"v{cv} installed" if cv else "Not installed yet"
        tiles.append(self._vm_tile(
            tag="latest", label="Latest", sublabel=sub,
            icon=ft.Icons.AUTO_AWESOME_ROUNDED,
            is_selected=is_sel,
            badge_text="AUTO-UPDATE", badge_color=t["primary"],
            badge_bg=t["primary_cont"],
            needs_net=True, warn=False,
            on_select=lambda _: self._vm_select("latest", sel_label, sheet),
        ))
        for v in inst:
            is_sel_v = (sel == v)
            warn     = version_is_legacy(v)
            tiles.append(self._vm_tile(
                tag=v, label=f"v{v}", sublabel="Installed  ·  pinned",
                icon=ft.Icons.LAYERS_ROUNDED,
                is_selected=is_sel_v,
                badge_text=None, badge_color=None, badge_bg=None,
                needs_net=False, warn=warn,
                on_select=lambda _, vv=v: self._vm_select(vv, sel_label, sheet),
            ))
        return tiles

    def _vm_tile(self, tag, label, sublabel, icon,
                 is_selected, badge_text, badge_color, badge_bg,
                 needs_net, warn, on_select):
        t = self._tokens
        chips = []
        if badge_text:
            chips.append(ft.Container(
                border_radius=6, bgcolor=badge_bg or t["surface3"],
                padding=_pad(vertical=2, horizontal=7),
                content=ft.Text(badge_text, size=9, weight=ft.FontWeight.W_700,
                                color=badge_color or t["on_surface2"],
                                style=ft.TextStyle(letter_spacing=0.8)),
            ))
        if needs_net:
            chips.append(ft.Container(
                border_radius=6, bgcolor=t["surface2"],
                padding=_pad(vertical=2, horizontal=7),
                content=ft.Row(tight=True, spacing=3, controls=[
                    ft.Icon(ft.Icons.WIFI_ROUNDED, size=9, color=t["on_surface2"]),
                    ft.Text("Requires internet", size=9, color=t["on_surface2"]),
                ]),
            ))
        if warn:
            chips.append(ft.Container(
                border_radius=6, bgcolor="#2e1500",
                border=_border_all(1, "#cc6600"),
                padding=_pad(vertical=2, horizontal=7),
                content=ft.Row(tight=True, spacing=3, controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=9, color="#ff8800"),
                    ft.Text("Likely build issues (<5.13)", size=9, color="#ff8800"),
                ]),
            ))

        return ft.Container(
            border_radius=12,
            ink=not is_selected,
            bgcolor=t["surface2"] if is_selected else None,
            border=_border_all(2 if is_selected else 1,
                               t["primary"] if is_selected else t["outline"]),
            padding=_pad(vertical=12, horizontal=14),
            margin=_margin_b(6),
            on_click=on_select if not is_selected else None,
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=42, height=42, border_radius=11,
                        bgcolor=t["primary_cont"] if is_selected else t["surface3"],
                        content=ft.Icon(icon, size=20,
                                        color=t["primary"] if is_selected
                                              else t["on_surface2"]),
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Container(width=12),
                    ft.Column(expand=True, spacing=4, tight=True, controls=[
                        ft.Text(label, size=14, weight=ft.FontWeight.W_600,
                                color=t["on_surface"]),
                        ft.Text(sublabel, size=11, color=t["on_surface2"]),
                        ft.Row(spacing=4, wrap=True, controls=chips)
                        if chips else ft.Container(),
                    ]),
                    ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED_ROUNDED
                            if is_selected else
                            ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
                            size=20,
                            color=t["primary"] if is_selected
                                  else t["on_surface2"]),
                ],
            ),
        )

    def _vm_load_releases(self, releases_body, sel_label, sheet):
        t = self._tokens
        releases_body.controls.clear()
        releases_body.controls.append(ft.Row(spacing=8, controls=[
            ft.ProgressRing(width=14, height=14,
                            stroke_width=2, color=t["primary"]),
            ft.Text("Fetching releases...", size=12, color=t["on_surface2"]),
        ]))
        if self.page:
            try: self.page.update()
            except Exception: pass

        releases = fetch_all_releases()
        inst     = installed_versions()
        cur_sel  = self._settings.get("selected_version", "latest")

        releases_body.controls.clear()
        if not releases:
            releases_body.controls.append(
                ft.Text("Could not fetch releases. Check your connection.",
                        size=12, color=t["error"])
            )
            if self.page:
                try: self.page.update()
                except Exception: pass
            return

        for rel in releases:
            tag    = rel["tag"]
            is_i   = tag in inst
            is_sel = (cur_sel == tag)
            warn   = version_is_legacy(tag)
            is_pre = rel.get("prerelease", False)

            def _select_fn(_, v=tag):
                self._vm_select(v, sel_label, sheet)

            def _install_fn(_, v=tag):
                self._close_sheet(sheet)
                self._vm_install(v)

            chips = []
            if is_pre:
                chips.append(ft.Container(
                    border_radius=6, bgcolor="#1e1200",
                    padding=_pad(vertical=2, horizontal=7),
                    content=ft.Text("PRE-RELEASE", size=9, color="#e8a020",
                                    style=ft.TextStyle(letter_spacing=0.8)),
                ))
            if warn:
                chips.append(ft.Container(
                    border_radius=6, bgcolor="#2e1500",
                    border=_border_all(1, "#cc6600"),
                    padding=_pad(vertical=2, horizontal=7),
                    content=ft.Row(tight=True, spacing=3, controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,
                                size=9, color="#ff8800"),
                        ft.Text("May fail to build", size=9, color="#ff8800"),
                    ]),
                ))
            if is_i:
                chips.append(ft.Container(
                    border_radius=6, bgcolor=t["primary_cont"],
                    padding=_pad(vertical=2, horizontal=7),
                    content=ft.Text("INSTALLED", size=9,
                                    weight=ft.FontWeight.W_700,
                                    color=t["primary"],
                                    style=ft.TextStyle(letter_spacing=0.8)),
                ))

            action = (
                ft.FilledButton(content="Play",
                                icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                on_click=_select_fn)
                if is_i else
                ft.OutlinedButton(content="Install",
                                  icon=ft.Icons.DOWNLOAD_ROUNDED,
                                  on_click=_install_fn)
            )

            releases_body.controls.append(ft.Container(
                border_radius=10, ink=not is_sel,
                bgcolor=t["surface2"] if is_sel else None,
                border=_border_all(2 if is_sel else 1,
                                   t["primary"] if is_sel else t["outline"]),
                padding=_pad(vertical=10, horizontal=14),
                margin=_margin_b(4),
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(expand=True, spacing=3, tight=True, controls=[
                            ft.Row(spacing=5, wrap=True, controls=[
                                ft.Text(f"v{tag}", size=13,
                                        weight=ft.FontWeight.W_600,
                                        color=t["on_surface"]),
                                *chips,
                            ]),
                            ft.Text(rel["date"], size=11, color=t["on_surface2"]),
                        ]),
                        action,
                    ],
                ),
            ))

        if self.page:
            try: self.page.update()
            except Exception: pass

    def _vm_install(self, version: str):
        """Install a specific version. Shows build log inline."""
        if version_is_legacy(version):
            self._set_status(
                f"⚠ v{version} is <5.13 — build errors are likely.",
                ft.Icons.WARNING_AMBER_ROUNDED, "#ff8800",
            )
        self._settings["selected_version"] = version
        save_settings(self._settings)
        self.version_badge.content.value = self._badge_text()
        self._set_status(f"Installing v{version}...",
                         ft.Icons.DOWNLOAD_ROUNDED, self._tokens["primary"])
        self.is_busy = True
        self.progress_bar.visible = True
        self.cancel_btn.visible   = True
        self.cancel_btn.content   = "Cancel Install"
        self.start_btn.on_click   = None
        self.cancel_event = threading.Event()
        if self.page:
            try: self.page.update()
            except Exception: pass

        def _run():
            try:
                ensure_dirs()
                while not self._out_q.empty():
                    try: self._out_q.get_nowait()
                    except Exception: pass
                build_version(version,
                              cancel_event=self.cancel_event,
                              out_q=self._out_q)
                self._drain_build_output()
                migrate(version)
                self._set_status(f"v{version} installed! Click START GAME to play.",
                                 ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                                 self._tokens["accent"])
            except InterruptedError:
                self._set_status("Cancelled.", ft.Icons.CANCEL_OUTLINED)
            except Exception as ex:
                log(f"[BUILD ERROR] {ex}")
                import traceback; log(traceback.format_exc())
                self._set_status(f"Build failed: {ex}",
                                 ft.Icons.ERROR_OUTLINE_ROUNDED,
                                 self._tokens["error"])
            finally:
                self.is_busy = False
                self.progress_bar.visible = False
                self.cancel_btn.visible   = False
                self.start_btn.on_click   = self._on_start
                self.cancel_event = None
                self.version_badge.content.value = self._badge_text()
                self._refresh_ver_card()
                if self.page:
                    try: self.page.update()
                    except Exception: pass

        threading.Thread(target=_run, daemon=True).start()

    # ── START / CANCEL ────────────────────────────────
    def _on_start(self, e):
        if self.is_busy: return
        log("[START] clicked")
        self.cancel_event = threading.Event()
        self._set_busy(True)
        self._set_status("Checking...", ft.Icons.MANAGE_SEARCH_ROUNDED)
        threading.Thread(target=self._flow, daemon=True).start()

    def _on_cancel(self, e):
        if self.cancel_event:
            self.cancel_event.set()
            self._set_status("Cancelling...", ft.Icons.HOURGLASS_TOP_ROUNDED)
            self.cancel_btn.disabled = True
            if self.page:
                try: self.page.update()
                except Exception: pass

    def _set_busy(self, busy: bool):
        t = self._tokens
        self.is_busy = busy
        self.start_btn.bgcolor  = t["surface3"]    if busy else t["primary_cont"]
        self._play_icon.color   = t["on_surface2"] if busy else t["primary"]
        self._start_text.color  = t["on_surface2"] if busy else t["on_surface"]
        self.start_btn.border   = _border_all(2, t["outline"] if busy
                                               else t["primary"])
        self.start_btn.on_click = None if busy else self._on_start
        self.progress_bar.visible = busy
        self.cancel_btn.visible   = busy
        self.cancel_btn.disabled  = False
        if not busy:
            self.version_badge.content.value = self._badge_text()
        if self.page:
            try: self.page.update()
            except Exception: pass

    def _flow(self):
        try:
            ensure_dirs()
            sel = self._settings.get("selected_version", "latest")
            log(f"[FLOW] sel={sel}")

            if sel == "latest":
                cv = current_version()
                log(f"[FLOW] current_version={cv!r}")

                if cv is not None and find_binary(cv) is not None:
                    # Already installed — launch right away
                    log(f"[FLOW] launching {cv}")
                    self._set_status("Launching...",
                                     ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                     self._tokens["accent"])
                    launch(cv)
                    self._settings["total_sessions"] = \
                        self._settings.get("total_sessions", 0) + 1
                    save_settings(self._settings)
                else:
                    # Not installed or binary missing — always auto-build
                    self._set_status("Fetching latest version info...",
                                     ft.Icons.MANAGE_SEARCH_ROUNDED)
                    try:
                        lv = latest_version()
                        log(f"[FLOW] latest={lv}")
                    except Exception as ex:
                        log(f"[FLOW] network error: {ex}")
                        self._set_status(
                            "Cannot reach GitHub. Check your connection.",
                            ft.Icons.WIFI_OFF_ROUNDED, self._tokens["error"])
                        return
                    self.cancel_btn.content = "Cancel Install"
                    self._set_status(f"Installing v{lv}...",
                                     ft.Icons.DOWNLOAD_ROUNDED,
                                     self._tokens["primary"])
                    if self.page:
                        try: self.page.update()
                        except Exception: pass
                    while not self._out_q.empty():
                        try: self._out_q.get_nowait()
                        except Exception: pass
                    build_version(lv,
                                  cancel_event=self.cancel_event,
                                  out_q=self._out_q)
                    threading.Thread(target=self._drain_build_output,
                                     daemon=True).start()
                    migrate(lv)
                    switch_current(lv)
                    self._settings["known_latest"] = lv
                    self._set_status("Launching...",
                                     ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                     self._tokens["accent"])
                    launch(lv)
                    self._settings["total_sessions"] = \
                        self._settings.get("total_sessions", 0) + 1
                    save_settings(self._settings)

            else:
                log(f"[FLOW] pinned={sel}")
                if find_binary(sel) is None:
                    # Not built yet — auto-build instead of erroring
                    self._set_status(f"v{sel} not installed. Building now...",
                                     ft.Icons.DOWNLOAD_ROUNDED,
                                     self._tokens["primary"])
                    self.cancel_btn.content = "Cancel Install"
                    if self.page:
                        try: self.page.update()
                        except Exception: pass
                    while not self._out_q.empty():
                        try: self._out_q.get_nowait()
                        except Exception: pass
                    build_version(sel,
                                  cancel_event=self.cancel_event,
                                  out_q=self._out_q)
                    threading.Thread(target=self._drain_build_output,
                                     daemon=True).start()
                    migrate(sel)
                self._set_status("Launching...",
                                 ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                 self._tokens["accent"])
                launch(sel)
                self._settings["total_sessions"] = \
                    self._settings.get("total_sessions", 0) + 1
                save_settings(self._settings)

            count = self._settings.get("launch_count", 0)
            if count in LAUNCH_MILESTONES:
                self._show_milestone(LAUNCH_MILESTONES[count])

        except InterruptedError:
            self._set_status("Cancelled.", ft.Icons.CANCEL_OUTLINED)
        except Exception as ex:
            log(f"[FLOW] ERROR: {ex}")
            import traceback; log(traceback.format_exc())
            self._set_status(f"Error: {ex}",
                             ft.Icons.ERROR_OUTLINE_ROUNDED,
                             self._tokens["error"])
        finally:
            log("[FLOW] done")
            self._set_busy(False)
            self.quote_text.value = get_daily_quote(self._settings)
            self.cancel_event = None
            self._refresh_ver_card()
            if self.page:
                try: self.page.update()
                except Exception: pass

    # ── ARTICLE ───────────────────────────────────────
    def _show_article(self, item):
        t     = self._tokens
        clean = html_to_text(item["full"])
        link  = item.get("link", "")
        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE,
                                expand=True, controls=[])
        sheet = self._make_sheet(content_col, height_frac=0.85)
        rows = [
            ft.Text(item["title"], size=18, weight=ft.FontWeight.W_700,
                    color=t["on_surface"]),
            ft.Text(item["date"], size=11, color=t["news_date"]),
        ]
        if link:
            rows.append(ft.GestureDetector(
                on_tap=lambda _, u=link: webbrowser.open(u),
                content=ft.Text("Read full article →", size=12,
                                color=t["primary"],
                                style=ft.TextStyle(
                                    decoration=ft.TextDecoration.UNDERLINE)),
            ))
        rows += [
            self._divider(),
            ft.Text(clean, size=13, color=t["on_surface2"], selectable=True),
            ft.Container(height=16),
            ft.TextButton(content="Close",
                          on_click=lambda _: self._close_sheet(sheet)),
        ]
        content_col.controls = rows
        self._open_sheet(sheet)

    # ── THEMES ────────────────────────────────────────
    def _show_themes(self, e):
        t      = self._tokens
        custom = load_my_themes()
        active = self._settings.get("theme", "Vanilla")
        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE,
                                controls=[])
        sheet = self._make_sheet(content_col)

        def on_select(name):
            result = apply_theme(name, custom_themes=custom)
            self._settings["theme"] = name
            save_settings(self._settings)
            self._set_status(result, ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                             t["accent"])
            self._close_sheet(sheet)

        def tile(name, icon):
            active_tile = (name == active)
            return ft.Container(
                border_radius=10, ink=True,
                bgcolor=t["surface2"] if active_tile else None,
                padding=_pad(vertical=9, horizontal=12),
                on_click=lambda e, n=name: on_select(n),
                content=ft.Row(spacing=0, controls=[
                    ft.Icon(icon, size=16,
                            color=t["primary"] if active_tile
                                  else t["on_surface2"]),
                    ft.Container(width=12),
                    ft.Text(name, size=13, color=t["on_surface"],
                            weight=ft.FontWeight.W_600 if active_tile
                            else ft.FontWeight.W_400),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.CHECK_ROUNDED, size=14,
                            color=t["primary"]) if active_tile
                    else ft.Container(),
                ]),
            )

        content_col.controls = [
            self._title("THEME GALLERY"),
            ft.Container(height=16),
            self._sec("IMAGE THEMES"),
            ft.Container(height=8),
            *[tile(n, ft.Icons.IMAGE_OUTLINED)
              for n in ["Vanilla"] + list(custom.keys())],
            self._divider(),
            self._sec("SOLID COLORS"),
            ft.Container(height=8),
            *[tile(n, ft.Icons.PALETTE_OUTLINED) for n in INTERNAL_THEMES],
            self._divider(),
            self._sec("CUSTOM THEMES"),
            ft.Container(height=8),
            ft.Text("No uploader yet — paste a Base64 string instead.\n"
                    "Convert any image at base64.guru",
                    size=11, color=t["on_surface2"]),
            ft.Container(height=8),
            ft.FilledButton(
                content="Paste Base64 Image",
                icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED,
                on_click=lambda _: self._show_b64_upload(sheet),
            ),
            ft.Container(height=12),
            ft.TextButton(content="Close",
                          on_click=lambda _: self._close_sheet(sheet)),
        ]
        self._open_sheet(sheet)

    def _show_b64_upload(self, parent_sheet):
        t = self._tokens
        name_f = ft.TextField(
            label="Theme name", border_radius=12, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"],
        )
        b64_f = ft.TextField(
            label="Paste Base64  (data:image/png;base64,...)",
            multiline=True, min_lines=4, max_lines=8,
            border_radius=12, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"],
        )
        fb = ft.Text("", size=12, color=t["on_surface2"])
        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE,
                                controls=[])
        sheet2 = self._make_sheet(content_col)

        def save(_):
            name = (name_f.value or "").strip()
            data = (b64_f.value  or "").strip()
            if not name or not data:
                fb.value = "Fill in both fields."
                if self.page: self.page.update()
                return
            if not data.startswith("data:image"):
                fb.value = "Must start with 'data:image/...'."
                if self.page: self.page.update()
                return
            ex = load_my_themes()
            ex[name] = data
            save_my_themes(ex)
            fb.value = f"Saved '{name}'! Reopen Themes to apply."
            if self.page: self.page.update()

        content_col.controls = [
            self._title("UPLOAD CUSTOM THEME"),
            ft.Container(height=8),
            ft.Text("1. base64.guru/converter/encode/image\n"
                    "2. Upload image → copy output\n3. Paste below.",
                    size=12, color=t["on_surface2"]),
            ft.Container(height=12),
            name_f, ft.Container(height=8),
            b64_f,  ft.Container(height=8),
            fb,     ft.Container(height=12),
            ft.Row(spacing=8, controls=[
                ft.FilledButton(content="Save Theme",
                                icon=ft.Icons.SAVE_ROUNDED, on_click=save),
                ft.TextButton(content="Cancel",
                              on_click=lambda _: self._close_sheet(sheet2)),
            ]),
        ]
        self._open_sheet(sheet2)

    # ── SETTINGS ──────────────────────────────────────
    def _show_settings(self, e):
        t = self._tokens
        nick_f = ft.TextField(
            label="Your nickname (optional)",
            value=self._settings.get("nickname", ""),
            border_radius=12, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"],
        )
        fb = ft.Text("", size=12, color=t["accent"])
        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE,
                                controls=[])
        sheet = self._make_sheet(content_col)

        def save_nick(_):
            nick = (nick_f.value or "").strip()
            self._settings["nickname"] = nick
            save_settings(self._settings)
            self.greeting_text.value = self._make_greeting()
            fb.value = "Saved!" if nick else "Cleared."
            if self.page: self.page.update()

        def swatch(name, preset):
            col    = preset["primary"] if not self._is_light else preset["l_primary"]
            active = (name == self._accent)
            return ft.Container(
                width=36, height=36, border_radius=18, bgcolor=col,
                border=_border_all(3, t["on_surface"] if active
                                   else t["outline"]),
                tooltip=name, ink=True,
                on_click=lambda _, n=name: [
                    self._set_accent(n), self._close_sheet(sheet)],
            )

        content_col.controls = [
            self._title("SETTINGS"),
            ft.Container(height=4),
            ft.Text(f"Member since "
                    f"{self._settings.get('first_seen') or 'today'}",
                    size=11, color=t["on_surface2"]),
            self._divider(),
            self._sec("NICKNAME"),
            ft.Container(height=8),
            nick_f, ft.Container(height=8),
            ft.FilledButton(content="Save",
                            icon=ft.Icons.SAVE_ROUNDED, on_click=save_nick),
            fb,
            self._divider(),
            self._sec("ACCENT COLOR"),
            ft.Container(height=10),
            ft.Row(spacing=10, controls=[
                swatch(n, p) for n, p in ACCENT_PRESETS.items()
            ]),
            self._divider(),
            self._sec("DISPLAY MODE"),
            ft.Container(height=8),
            ft.Row(spacing=8, controls=[
                ft.FilledButton(
                    content="Dark", icon=ft.Icons.DARK_MODE_ROUNDED,
                    on_click=lambda _: [self._force_mode(False),
                                        self._close_sheet(sheet)],
                ),
                ft.FilledButton(
                    content="Light", icon=ft.Icons.LIGHT_MODE_ROUNDED,
                    on_click=lambda _: [self._force_mode(True),
                                        self._close_sheet(sheet)],
                ),
            ]),
            ft.Container(height=16),
            ft.TextButton(content="Close",
                          on_click=lambda _: self._close_sheet(sheet)),
        ]
        self._open_sheet(sheet)

    # ── STATS ─────────────────────────────────────────
    def _show_stats(self, e):
        t = self._tokens
        s = self._settings

        def row(label, value):
            return ft.Container(
                padding=_pad(vertical=10),
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

        launches = s.get("launch_count", 0)
        msg = "Just getting started."
        for thr in sorted(LAUNCH_MILESTONES, reverse=True):
            if launches >= thr:
                msg = LAUNCH_MILESTONES[thr]; break

        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE,
                                controls=[])
        sheet = self._make_sheet(content_col)
        content_col.controls = [
            self._title("MY STATS"),
            ft.Container(height=12),
            ft.Container(
                border_radius=12, bgcolor=t["surface2"],
                padding=_pad(vertical=12, horizontal=14),
                content=ft.Row(spacing=12, controls=[
                    ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED,
                            color=t["primary"], size=22),
                    ft.Text(msg, size=12, color=t["on_surface"], expand=True),
                ]),
            ),
            ft.Container(height=12),
            row("Player",         s.get("nickname") or "Anonymous"),
            row("Luancher opens", launches),
            row("Games launched", s.get("total_sessions", 0)),
            row("Member since",   s.get("first_seen", "unknown")),
            row("Accent",         s.get("accent", "Blue")),
            row("Mode",           "Light" if self._is_light else "Dark"),
            row("Active version", s.get("selected_version", "latest")),
            ft.Container(height=16),
            ft.TextButton(content="Close",
                          on_click=lambda _: self._close_sheet(sheet)),
        ]
        self._open_sheet(sheet)

    # ── MILESTONE ─────────────────────────────────────
    def _show_milestone(self, msg: str):
        t = self._tokens
        content_col = ft.Column(
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[])
        sheet = self._make_sheet(content_col, height_frac=0.45)
        content_col.controls = [
            ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED, size=48, color=t["primary"]),
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
        ]
        self._open_sheet(sheet)

    # ── FOLDERS ───────────────────────────────────────
    def _open_folder(self, path: Path):
        try:
            path.mkdir(parents=True, exist_ok=True)
            if sys.platform == "darwin":  subprocess.Popen(["open",     str(path)])
            elif sys.platform == "win32": subprocess.Popen(["explorer", str(path)])
            else:                         subprocess.Popen(["xdg-open", str(path)])
        except Exception as ex:
            self._set_status(f"Cannot open: {ex}",
                             ft.Icons.ERROR_OUTLINE_ROUNDED,
                             self._tokens["error"])

    def _open_data(self, e): self._open_folder(SRC / "mods")
    def _open_logs(self, e): self._open_folder(LOGS)


# =====================================================
# ENTRY
# =====================================================
def main(page: ft.Page):
    page.title      = "Luancher"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding    = 0
    page.spacing    = 0
    try:
        page.window.width      = 1100
        page.window.height     = 700
        page.window.min_width  = 860
        page.window.min_height = 540
    except AttributeError:
        page.window_width      = 1100
        page.window_height     = 700
        page.window_min_width  = 860
        page.window_min_height = 540

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
