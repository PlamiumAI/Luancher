import flet as ft
import threading
import subprocess
import requests
import feedparser
import shutil
import os
import sys
import random
from pathlib import Path
from html.parser import HTMLParser
from io import StringIO

# =====================================================
# PATHS - UPDATED FOR BUNDLING
# =====================================================

# Detect if we are running as a compiled binary
IS_BUNDLE = getattr(sys, 'frozen', False)

if IS_BUNDLE:
    # Use a hidden folder in the User's Home for data/builds
    # This prevents data loss when the app updates or moves
    ROOT = Path.home() / ".luancher"
    # Assets (like default themes) are bundled inside the app directory
    ASSETS_DIR = Path(__file__).parent / "assets"
else:
    # Use the local folder when running 'python luancher.py'
    ROOT = Path(__file__).parent.resolve()
    ASSETS_DIR = ROOT / "assets"

RUNTIME = ROOT / "runtime"
SRC = RUNTIME / "src" / "luanti"
BUILDS = ROOT / "runtime" / "builds"
DATA = ROOT / "data"
CACHE = ROOT / "cache"
LOGS = ROOT / "logs"
THEMES_DIR = DATA / "themes"

GITHUB_API = "https://api.github.com/repos/luanti-org/luanti/releases/latest"
RSS_FEED = "https://blog.luanti.org/feed.rss"

# =====================================================
# CONSTANTS
# =====================================================

MIGRATE_PATHS = [
    "games",
    "mods",
    "worlds",
    "textures",
    "cache",
    "minetest.conf",
    "client/serverlist/favoriteservers.json",
]

QUOTES = [
    "Creation starts here.",
    "To build is to believe in tomorrow.",
    "Purposeful play creates mastery.",
    "The expert was once a beginner.",
]

# =====================================================
# UTILS
# =====================================================

class HTMLToText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = StringIO()
        self.in_strong = False
        
    def handle_data(self, data):
        if data.strip():
            self.text.write(data)
        
    def handle_starttag(self, tag, attrs):
        if tag in ['p', 'div']:
            self.text.write('\n\n')
        elif tag == 'br':
            self.text.write('\n')
        elif tag == 'li':
            self.text.write('\n  • ')
        elif tag in ['h2', 'h3']:
            self.text.write('\n\n')
        elif tag == 'tr':
            self.text.write('\n')
        elif tag == 'td':
            self.text.write('  ')
        elif tag == 'strong':
            self.in_strong = True
            
    def handle_endtag(self, tag):
        if tag in ['h2', 'h3']:
            self.text.write('\n')
        elif tag == 'strong':
            self.in_strong = False
        elif tag == 'ul':
            self.text.write('\n')
            
    def get_text(self):
        return self.text.getvalue().strip()

def html_to_text(html):
    parser = HTMLToText()
    parser.feed(html)
    return parser.get_text()

def log(msg):
    LOGS.mkdir(exist_ok=True, parents=True)
    with open(LOGS / "launcher.log", "a") as f:
        f.write(msg + "\n")

def run(cmd, cwd=None, cancel_event=None):
    log(" ".join(cmd))
    proc = subprocess.Popen(cmd, cwd=cwd)
    
    while proc.poll() is None:
        if cancel_event and cancel_event.is_set():
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise InterruptedError("Build cancelled by user")
    
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

def ensure_dirs():
    # Create all required app directories in the ROOT (Home folder)
    for p in [RUNTIME, SRC.parent, BUILDS, DATA, CACHE, LOGS, THEMES_DIR]:
        p.mkdir(parents=True, exist_ok=True)
    
    active_themes = ["Vanilla", "Windows XP", "Cyberpunk", "Deep Forest", "Retro Terminal"]
    for t in active_themes:
        (THEMES_DIR / t).mkdir(exist_ok=True)

# =====================================================
# THEME SYSTEM
# =====================================================

def find_texture_dirs():
    found = []
    if not RUNTIME.exists(): return []
    for root, dirs, files in os.walk(str(RUNTIME)):
        p = Path(root)
        if p.parts[-3:] == ("textures", "base", "pack"):
            found.append(p)
    return found

def apply_theme(theme_name):
    targets = find_texture_dirs()
    if not targets:
        return "Error: Luanti textures not found."

    bg_file = "menu_background.png"
    if theme_name == "Vanilla":
        for target_dir in targets:
            file_path = target_dir / bg_file
            if file_path.exists():
                os.remove(file_path)
        return "Restored Vanilla."

    source_path = THEMES_DIR / theme_name
    theme_img = source_path / bg_file
    if not theme_img.exists():
        return f"Error: {bg_file} missing in {theme_name}."

    for target_dir in targets:
        shutil.copy2(theme_img, target_dir / bg_file)
    return f"Applied {theme_name}!"

# =====================================================
# VERSION HANDLING
# =====================================================

def latest_version():
    headers = {'User-Agent': 'Luancher-Client'}
    r = requests.get(GITHUB_API, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()["tag_name"].lstrip("v")

def current_version():
    link = BUILDS / "current"
    if link.exists() and link.is_symlink():
        return link.resolve().name
    return None

# =====================================================
# BUILD SYSTEM
# =====================================================

def ensure_repo(cancel_event=None):
    if not SRC.exists():
        run(["git", "clone", "https://github.com/luanti-org/luanti.git", str(SRC)], cancel_event=cancel_event)

def build(version, cancel_event=None):
    target = BUILDS / version
    if target.exists():
        return

    ensure_repo(cancel_event)
    run(["git", "fetch", "--tags"], cwd=SRC, cancel_event=cancel_event)
    run(["git", "checkout", f"{version}"], cwd=SRC, cancel_event=cancel_event)

    target.mkdir(parents=True, exist_ok=True)
    run(["cmake", str(SRC), "-DRUN_IN_PLACE=FALSE", "-DENABLE_GETTEXT=TRUE"], cwd=target, cancel_event=cancel_event)
    run(["make", "-j", str(os.cpu_count() or 2)], cwd=target, cancel_event=cancel_event)

def switch_current(version):
    link = BUILDS / "current"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(BUILDS / version)

# =====================================================
# DATA MIGRATION
# =====================================================

def migrate(version):
    dest = BUILDS / version
    dest.mkdir(parents=True, exist_ok=True)
    for rel in MIGRATE_PATHS:
        src = DATA / rel
        if not src.exists(): continue
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

# =====================================================
# NEWS
# =====================================================

def fetch_news():
    try:
        feed = feedparser.parse(RSS_FEED)
        if not feed.entries: return None
        news_list = []
        for e in feed.entries[:5]:
            desc_words = e.get("summary", "").split()
            short_desc = " ".join(desc_words[:5]) + ("..." if len(desc_words) > 5 else "")
            news_list.append({"title": e.title, "date": e.get("published", ""), "desc": short_desc, "full": e.get("summary", "")})
        return news_list
    except:
        return None

# =====================================================
# LAUNCH
# =====================================================

def find_binary():
    # Check symlinked current build
    b1 = BUILDS / "current" / "bin" / "luanti"
    if b1.exists(): return b1
    # Check source bin as fallback
    b2 = SRC / "bin" / "luanti"
    if b2.exists(): return b2
    return None

def launch():
    binary = find_binary()
    if not binary: raise FileNotFoundError("No compiled Luanti binary found.")
    # Ensure binary is executable
    os.chmod(binary, 0o755)
    subprocess.Popen([str(binary)])

# =====================================================
# UI
# =====================================================

class Launcher(ft.Container):
    def __init__(self):
        super().__init__()
        self.expand = True
        self.is_busy = False
        self.cancel_event = None
        self.is_update = False 

        self.status = ft.Text("")
        self.quote = ft.Text(random.choice(QUOTES), italic=True)
        self.news = ft.Column(spacing=10)
        
        self.progress = ft.ProgressBar(width=400, color=ft.Colors.GREEN_400, visible=False)

        self.start_btn = ft.IconButton(
            icon=ft.Icons.PLAY_CIRCLE_FILL,
            icon_color=ft.Colors.GREEN_400,
            icon_size=120,
            on_click=self.start_clicked,
            disabled=False
        )
        
        self.cancel_btn = ft.ElevatedButton(
            "Cancel",
            icon=ft.Icons.CANCEL,
            color=ft.Colors.RED_400,
            on_click=self.cancel_clicked,
            visible=False
        )

        self.content = ft.Row([
            ft.Container(
                width=260, padding=20, bgcolor="#1e1e1e",
                content=ft.Column([
                    ft.Text("Luancher", size=30, weight="bold"),
                    ft.Text("THE LAUNCHER FOR LUANTI", size=12, color=ft.Colors.GREY_400),
                    ft.Divider(),
                    ft.TextButton(content=ft.Row([ft.Icon(ft.Icons.PALETTE), ft.Text("THEMES")]), on_click=self.show_themes_popup),
                    ft.Divider(),
                    self.status
                ])
            ),
            ft.Container(
                expand=True,
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self.quote,
                        self.start_btn,
                        ft.Text("START GAME", size=18),
                        ft.Container(height=20),
                        self.progress,
                        self.cancel_btn
                    ]
                )
            ),
            ft.Container(width=300, padding=20, bgcolor="#1e1e1e", content=self.news)
        ])

    def load_news(self):
        items = fetch_news()
        self.news.controls.clear()
        if not items:
            self.news.controls.append(ft.Text("Offline: Cannot load news."))
            return
        self.news.controls.append(ft.Text("NEWS", weight="bold", size=16, color=ft.Colors.AMBER_400))
        for n in items:
            def make_click_handler(news_item):
                def handler(e): self.show_news_popup(news_item)
                return handler
            card = ft.Container(
                padding=10, margin=ft.margin.only(bottom=8), border_radius=5, bgcolor="#2c2c2c", ink=True,
                content=ft.Column([
                    ft.Text(n["date"], size=10, color=ft.Colors.AMBER_200),
                    ft.Text(n["title"], weight="bold", size=12, color=ft.Colors.AMBER_400),
                    ft.Text(n["desc"], size=12, color=ft.Colors.GREY_300),
                ]),
                on_click=make_click_handler(n),
            )
            self.news.controls.append(card)
        self.news.update()

    def show_themes_popup(self, e):
        def on_theme_select(theme_name):
            res = apply_theme(theme_name)
            self.status.value = res
            bottom_sheet.open = False
            self.page.update()
        theme_options = ["Vanilla", "Windows XP", "Cyberpunk", "Deep Forest", "Retro Terminal"]
        bottom_sheet = ft.BottomSheet(
            content=ft.Container(
                padding=30, bgcolor="#1a1a1a", border_radius=ft.border_radius.only(top_left=20, top_right=20),
                content=ft.Column(
                    controls=[
                        ft.Text("SELECT THEME", weight="bold", size=24),
                        ft.Divider(),
                        *[ft.ListTile(title=ft.Text(t), leading=ft.Icon(ft.Icons.COLOR_LENS), on_click=lambda _, name=t: on_theme_select(name)) for t in theme_options],
                        ft.ElevatedButton("Close", on_click=lambda _: setattr(bottom_sheet, 'open', False) or self.page.update()),
                    ], tight=True
                )
            )
        )
        self.page.overlay.append(bottom_sheet)
        bottom_sheet.open = True
        self.page.update()

    def show_news_popup(self, news_item):
        clean_text = html_to_text(news_item["full"])
        bottom_sheet = ft.BottomSheet(
            content=ft.Container(
                padding=30, bgcolor="#1a1a1a", border_radius=ft.border_radius.only(top_left=20, top_right=20),
                content=ft.Column(
                    controls=[
                        ft.Text(news_item["title"], weight="bold", size=24),
                        ft.Divider(height=30),
                        ft.Text(clean_text, size=14, color=ft.Colors.GREY_300, selectable=True),
                        ft.ElevatedButton("Close", on_click=lambda _: setattr(bottom_sheet, 'open', False) or self.page.update()),
                    ], scroll=ft.ScrollMode.ADAPTIVE, expand=True
                ), height=self.page.height * 0.85
            )
        )
        self.page.overlay.append(bottom_sheet)
        bottom_sheet.open = True
        self.page.update()

    def start_clicked(self, e):
        if self.is_busy: return
        self.cancel_event = threading.Event()
        self.toggle_busy(True)
        self.status.value = "Checking Luanti..."
        self.update()
        threading.Thread(target=self.flow, daemon=True).start()

    def cancel_clicked(self, e):
        if self.cancel_event:
            self.cancel_event.set()
            self.status.value = "Cancelling..."
            self.cancel_btn.disabled = True
            self.update()

    def toggle_busy(self, busy: bool):
        self.is_busy = busy
        self.start_btn.disabled = busy
        self.start_btn.icon_color = ft.Colors.GREY_600 if busy else ft.Colors.GREEN_400
        self.progress.visible = busy
        self.cancel_btn.visible = busy
        self.cancel_btn.disabled = False
        self.update()

    def flow(self):
        try:
            ensure_dirs()
            latest = latest_version()
            current = current_version()

            self.is_update = current is not None
            
            if self.is_update:
                self.cancel_btn.text = "Cancel Update"
            else:
                self.cancel_btn.text = "Cancel Installation"
            self.update()

            if current != latest:
                self.status.value = f"{'Updating' if self.is_update else 'Installing'} to {latest}..."
                self.update()
                build(latest, cancel_event=self.cancel_event)
                migrate(latest)
                switch_current(latest)

            self.status.value = "Launching..."
            self.update()
            launch()

        except InterruptedError:
            if self.is_update:
                self.status.value = "Update cancelled. Launching existing..."
                self.update()
                try: launch()
                except: pass
            else:
                self.status.value = "Installation cancelled."
        except Exception as ex:
            self.status.value = f"ERROR: {ex}"
            log(str(ex))
        finally:
            self.toggle_busy(False)
            self.quote.value = random.choice(QUOTES)
            self.cancel_event = None
            self.update()

# =====================================================
# ENTRY
# =====================================================

def main(page: ft.Page):
    page.title = "Luancher"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1100
    page.window_height = 700
    page.padding = 0
    ensure_dirs()
    launcher = Launcher()
    page.add(launcher)
    launcher.load_news()

if __name__ == "__main__":
    ft.run(main)