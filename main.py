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
import zipfile
import datetime
import queue
import webbrowser
from pathlib import Path
from html.parser import HTMLParser
from io import StringIO
import flet as ft
from PIL import Image

# =====================================================
# LAUNCH GUARDRAIL
# =====================================================
if os.environ.get("LUANCHER_BOOTED") != "TRUE":
    print("\n" + "─"*60)
    print(" LUANCHER: Wrong entry point.")
    print(" " + "─"*58)
    print(" Run 'python3 updater.py' instead.")
    print(" The updater will launch and update the app properly.")
    print(" TIP: If you don't want to update, then run 'python3 updater.py --noupdate'")
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
BUILDS          = ROOT / "runtime" / "builds"
DATA            = ROOT / "data"
CACHE           = ROOT / "cache"
LOGS            = ROOT / "logs"
THEMES_DIR      = DATA / "themes"
MY_THEMES_FILE  = DATA / "my_themes.json"
SETTINGS_FILE   = ROOT / "luancher_settings.json"
WORKSPACES_FILE = ROOT / "workspaces.json"
BACKUPS_DIR     = ROOT / "backups"

GITHUB_API      = "https://api.github.com/repos/luanti-org/luanti/releases/latest"
GITHUB_RELEASES = "https://api.github.com/repos/luanti-org/luanti/releases?per_page=30"
RSS_FEED        = "https://blog.luanti.org/feed.rss"

MIGRATE_PATHS = [
    "games", "mods", "worlds", "textures", "cache",
    "minetest.conf", "client/serverlist/favoriteservers.json",
]

PRO_TIPS = [
    "Create separate workspaces for survival, creative, and modded — your worlds won't interfere.",
    "Pin a specific version before a big mod update. Future you will be grateful.",
    "The Mod Folder button opens your active workspace's mods directory directly. No digging required.",
    "Back up to a cloud-synced folder (Dropbox, Google Drive) for offsite protection. Drives fail.",
    "Each workspace has its own worlds and mods — perfect for testing without blowing up your main save.",
    "Backups are plain .zip files. You can crack them open with any archive manager to restore a single world.",
    "Rename workspaces clearly: 'Survival 2024', 'CTF Server', 'Mod Testing' beats 'Workspace 2'.",
    "The version manager shows all GitHub releases. You can install and switch between any of them.",
    "Custom builds go in the Version Manager → Custom Build section. Handy for dev branches.",
    "If a build fails, the error popup has links to the exact docs you need. Read them — they help.",
    "Hold F5 in Luanti to take a screenshot. It saves to your workspace's screenshots folder.",
    "Did you know Luanti was called Minetest until 2024? Old habits die hard. We still love it.",
]

# Milestones: shown as a bottom sheet after hitting the exact launch count.
# Format: (emoji, short title, flavour body)
LAUNCH_MILESTONES = {
    1:   ("⛏️",  "First launch.",     "Your journey begins. The world is yours."),
    5:   ("🌱",  "5 launches.",       "You've punched enough trees to build a house."),
    10:  ("💎",  "10 launches.",      "Diamond tier explorer. Have you found bedrock yet?"),
    25:  ("🏰",  "25 launches.",      "You've basically built a castle at this point."),
    50:  ("🌋",  "50 launches.",      "Fifty times into the void. Still going strong."),
    69:  ("👀",  "69 launches.",      "Heh."),
    100: ("🧱",  "100 launches.",     "Triple digits. We should add a trophy. We did not add a trophy."),
    256: ("📦",  "256 launches.",     "The inventory limit. You have transcended the game."),
    500: ("🚀",  "500 launches.",     "At this point Luanti is basically your job."),
    1000:("🌌",  "1000 launches.",    "Are you okay? Drink some water."),
}

# Shown in the greeting instead of the time-of-day text on milestone counts.
EASTER_EGG_GREETINGS = {
    1:    "First block placed.",
    10:   "10 launches. A seasoned miner.",
    42:   "42 launches. The answer.",
    69:   "69 launches. Heh.",
    100:  "100 launches. Three digits. Respect.",
    256:  "256 launches. You are the inventory.",
    1000: "1000 launches. Are you still here?",
}

ACCENT_PRESETS = {
    "Blue":   {"primary": "#60b4ff", "primary_cont": "#0d3060",
               "l_primary": "#2563eb", "l_primary_cont": "#dbeafe"},
    "Purple": {"primary": "#c480ff", "primary_cont": "#2e1060",
               "l_primary": "#7c3aed", "l_primary_cont": "#ede9fe"},
    "Green":  {"primary": "#3de880", "primary_cont": "#053a20",
               "l_primary": "#16a34a", "l_primary_cont": "#dcfce7"},
    "Amber":  {"primary": "#ffc940", "primary_cont": "#3d2400",
               "l_primary": "#d97706", "l_primary_cont": "#fef3c7"},
    "Rose":   {"primary": "#ff6fa8", "primary_cont": "#450020",
               "l_primary": "#e11d48", "l_primary_cont": "#ffe4e6"},
    "Teal":   {"primary": "#28ddf0", "primary_cont": "#042e38",
               "l_primary": "#0891b2", "l_primary_cont": "#cffafe"},
}

WORKSPACE_ICONS = [
    ft.Icons.FOLDER_ROUNDED,
    ft.Icons.SPORTS_ESPORTS_ROUNDED,
    ft.Icons.CONSTRUCTION_ROUNDED,
    ft.Icons.SCIENCE_ROUNDED,
    ft.Icons.BRUSH_ROUNDED,
    ft.Icons.EXTENSION_ROUNDED,
    ft.Icons.ROCKET_LAUNCH_ROUNDED,
    ft.Icons.TERRAIN_ROUNDED,
    ft.Icons.CASTLE_ROUNDED,
    ft.Icons.FOREST_ROUNDED,
]

WORKSPACE_COLORS = [
    "#a8c7fa", "#c8b8ff", "#7fd9a0", "#ffd080",
    "#ffb3b3", "#80d8e0", "#f4a261", "#e9c46a",
    "#90be6d", "#43aa8b",
]

# =====================================================
# SETTINGS
# =====================================================
DEFAULT_SETTINGS = {
    "theme":              "Vanilla",
    "light_mode":         False,
    "accent":             "Blue",
    "nickname":           "",
    "launch_count":       0,
    "quote_index":        0,
    "quote_date":         "",
    "total_sessions":     0,
    "first_seen":         "",
    "selected_version":   "latest",
    "known_latest":       "",
    "active_workspace":   "Default",
    "backup_path":        "",
    "backup_reminder":    True,
    "last_auto_backup":   "",
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

def get_daily_tip(s: dict) -> str:
    today = datetime.date.today().isoformat()
    if s.get("quote_date") != today:
        s["quote_index"] = random.randint(0, len(PRO_TIPS) - 1)
        s["quote_date"] = today
        save_settings(s)
    return f"Pro Tip:  {PRO_TIPS[s['quote_index']]}"

# =====================================================
# WORKSPACES
# =====================================================
DEFAULT_WORKSPACE = {
    "name":        "Default",
    "description": "The default workspace",
    "icon_index":  0,
    "color":       "#a8c7fa",
    "created":     datetime.date.today().isoformat(),
}

def load_workspaces() -> dict:
    if WORKSPACES_FILE.exists():
        try:
            with open(WORKSPACES_FILE, "r") as f:
                data = json.load(f)
            if "Default" not in data:
                data["Default"] = dict(DEFAULT_WORKSPACE)
            return data
        except Exception:
            pass
    return {"Default": dict(DEFAULT_WORKSPACE)}

def save_workspaces(ws: dict):
    ROOT.mkdir(parents=True, exist_ok=True)
    with open(WORKSPACES_FILE, "w") as f:
        json.dump(ws, f, indent=2)

def workspace_data_dir(ws_name: str) -> Path:
    if ws_name == "Default":
        return DATA
    safe = ws_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    return ROOT / "workspaces" / safe

def ensure_workspace(ws_name: str):
    wd = workspace_data_dir(ws_name)
    for rel in MIGRATE_PATHS:
        p = wd / rel
        if not p.suffix:
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)

# =====================================================
# BACKUP
# =====================================================
def backup_workspaces(dest_dir: Path, workspaces: dict,
                      progress_cb=None, cancel_event=None) -> Path:
    """Zip all workspace data dirs into dest_dir. Returns zip path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = dest_dir / f"luancher_backup_{ts}.zip"

    ws_dirs = []
    for name in workspaces:
        wd = workspace_data_dir(name)
        if wd.exists():
            ws_dirs.append((name, wd))

    # Count files first for progress
    total_files = 0
    for _, wd in ws_dirs:
        for _ in wd.rglob("*"):
            total_files += 1

    done = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED,
                         allowZip64=True) as zf:
        # Also include settings & workspaces.json
        if SETTINGS_FILE.exists():
            zf.write(SETTINGS_FILE, "luancher_settings.json")
        if WORKSPACES_FILE.exists():
            zf.write(WORKSPACES_FILE, "workspaces.json")

        for ws_name, wd in ws_dirs:
            safe = ws_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
            for fpath in wd.rglob("*"):
                if cancel_event and cancel_event.is_set():
                    zip_path.unlink(missing_ok=True)
                    raise InterruptedError("Backup cancelled")
                if fpath.is_file():
                    arcname = f"workspaces/{safe}/{fpath.relative_to(wd)}"
                    try:
                        zf.write(fpath, arcname)
                    except Exception:
                        pass
                    done += 1
                    if progress_cb and total_files:
                        progress_cb(done / total_files, done, total_files)

    return zip_path

def list_backups(dest_dir: Path) -> list:
    if not dest_dir.exists():
        return []
    zips = sorted(dest_dir.glob("luancher_backup_*.zip"), reverse=True)
    out = []
    for z in zips:
        stat = z.stat()
        out.append({
            "path": z,
            "name": z.name,
            "size_mb": round(stat.st_size / 1024 / 1024, 1),
            "mtime": datetime.datetime.fromtimestamp(stat.st_mtime)
                               .strftime("%Y-%m-%d  %H:%M"),
        })
    return out

# =====================================================
# DESIGN TOKENS
# =====================================================
DARK_BASE = {
    "bg":           "#07070e",
    "surface":      "#0e0e1c",
    "surface2":     "#141428",
    "surface3":     "#1c1c34",
    "rail":         "#08080e",
    "outline":      "#2a2a48",
    "on_surface":   "#f2f0ff",
    "on_surface2":  "#a09ec0",
    "on_surface3":  "#606080",
    "accent":       "#34d97b",
    "error":        "#ff6b6b",
    "news_title":   "#bf7fff",
    "news_date":    "#58587a",
    "console_bg":   "#040408",
    "console_text": "#4ade80",
}

LIGHT_BASE = {
    "bg":           "#f5f4ff",
    "surface":      "#ffffff",
    "surface2":     "#f0effe",
    "surface3":     "#e8e6fa",
    "rail":         "#fafaff",
    "outline":      "#00000014",
    "on_surface":   "#0a0818",
    "on_surface2":  "#4a4868",
    "on_surface3":  "#9a98b8",
    "accent":       "#16a34a",
    "error":        "#dc2626",
    "news_title":   "#7c3aed",
    "news_date":    "#a0a0c0",
    "console_bg":   "#0a0a18",
    "console_text": "#4ade80",
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

# Versions below this are known to have build issues on modern toolchains.
LEGACY_VERSION_THRESHOLD = (5, 13, 0)

def version_is_legacy(tag: str) -> bool:
    return _parse_ver(tag) < LEGACY_VERSION_THRESHOLD

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

def migrate(version, workspace_name="Default"):
    dest = BUILDS / version
    dest.mkdir(parents=True, exist_ok=True)
    src_base = workspace_data_dir(workspace_name)
    for rel in MIGRATE_PATHS:
        src = src_base / rel
        if not src.exists(): continue
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir(): shutil.copytree(src, dst, dirs_exist_ok=True)
        else:            shutil.copy2(src, dst)

def find_binary(version: str):
    if version is None: return None
    base = BUILDS / version
    if not base.exists(): return None
    for name in ["luanti", "minetest"]:
        for candidate in [
            base / "bin" / name,
            base / name,
            base / "luanti" / "bin" / name,
            base / "minetest" / "bin" / name,
        ]:
            if candidate.exists(): return candidate
    for name in ["luanti", "minetest"]:
        for p in base.rglob(name):
            if p.is_file() and os.access(p, os.X_OK):
                return p
    return None

def import_custom_version(binary_path: Path, version_name: str) -> Path:
    """
    Import a user-supplied Luanti binary into the builds directory.
    Copies the binary (and its parent directory tree) into BUILDS/<version_name>/bin/.
    Returns the path to the installed binary.
    """
    safe = version_name.strip().replace("/", "_").replace("\\", "_").replace(" ", "_")
    if not safe:
        raise ValueError("Version name cannot be empty.")
    dest_dir = BUILDS / safe
    if dest_dir.exists():
        raise FileExistsError(f"A version named '{safe}' already exists. Choose a different name.")

    src_root = binary_path.parent
    if src_root.name == "bin":
        tree_root = src_root.parent
        shutil.copytree(tree_root, dest_dir)
    else:
        bin_dir = dest_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary_path, bin_dir / binary_path.name)

    result = find_binary(safe)
    if result is None:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise RuntimeError(
            "Imported the files but could not locate an executable Luanti binary inside. "
            "Make sure you selected the actual luanti/minetest binary, not a library."
        )
    os.chmod(result, 0o755)
    return result


def launch(version: str, workspace_name: str = "Default"):
    binary = find_binary(version)
    if not binary:
        raise FileNotFoundError(f"No binary for v{version}. Is it built?")
    os.chmod(binary, 0o755)
    wd = workspace_data_dir(workspace_name)
    ensure_workspace(workspace_name)
    env = os.environ.copy()
    env["MINETEST_USER_PATH"] = str(wd)
    subprocess.Popen([str(binary)], env=env)

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
# EXPANDABLE RAIL BUTTON
# =====================================================
class RailButton(ft.Container):
    def __init__(self, icon, label, handler, tokens):
        super().__init__()
        self._tokens     = tokens
        self._label_text = label
        t = tokens

        self._icon_ctrl = ft.Icon(icon, size=18, color=t["on_surface2"])

        self.content = ft.Container(
            width=18, height=18,
            content=self._icon_ctrl,
            alignment=ft.Alignment(0, 0),
        )
        self.width         = 38
        self.height        = 38
        self.border_radius = 10
        self.ink           = True
        self.on_click      = handler
        self.tooltip       = label
        self.padding       = _pad(vertical=0, horizontal=10)
        self.on_hover      = self._on_hover

    def _on_hover(self, e):
        t = self._tokens
        if e.data == "true":
            self._icon_ctrl.color = t["primary"]
            self.bgcolor = t["surface2"]
        else:
            self._icon_ctrl.color = t["on_surface2"]
            self.bgcolor = None
        if self.page:
            self.page.update()

    def set_tokens(self, tokens):
        self._tokens = tokens
        self._icon_ctrl.color = tokens["on_surface2"]

    def set_expanded(self, expanded: bool):
        pass  # kept for compat

# =====================================================
# UI — LAUNCHER
# =====================================================
class Launcher(ft.Container):
    RAIL_COLLAPSED = 58
    RAIL_EXPANDED  = 190

    def __init__(self, settings: dict, workspaces: dict):
        super().__init__()
        self.expand    = True
        self.is_busy   = False
        self.cancel_event = None
        self._settings   = settings
        self._workspaces = workspaces
        self._is_light   = settings.get("light_mode", False)
        self._accent     = settings.get("accent", "Blue")
        self._tokens     = build_tokens(self._is_light, self._accent)
        self._latest_ver = ""
        self._out_q: queue.Queue = queue.Queue()
        self._rail_buttons: list[RailButton] = []
        self._file_picker = None

        t = self._tokens

        # ── Status chip ──
        self.status_chip = ft.Container(
            visible=False, border_radius=20,
            bgcolor=t["surface2"], border=_border_all(1, t["outline"]),
            padding=_pad(vertical=6, horizontal=14),
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            content=ft.Row(
                spacing=6, tight=True,
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=13, color=t["on_surface2"]),
                    ft.Text(value="", size=11, color=t["on_surface2"]),
                ],
            ),
        )
        self._status_icon  = self.status_chip.content.controls[0]
        self._status_label = self.status_chip.content.controls[1]

        self.quote_text = ft.Text(
            value=get_daily_tip(settings),
            size=12, italic=False, color=t["on_surface2"],
            text_align=ft.TextAlign.CENTER,
        )
        self.news_col = ft.Column(
            spacing=5, scroll=ft.ScrollMode.ADAPTIVE, expand=True
        )
        self.progress_bar = ft.ProgressBar(
            color=t["primary"], bgcolor=t["outline"],
            visible=False, border_radius=4, height=3,
        )

        # ── Hero greeting ──
        self._hero_greeting = ft.Text(
            value=self._make_greeting(),
            size=28, weight=ft.FontWeight.W_800,
            color=t["on_surface"],
            text_align=ft.TextAlign.CENTER,
            style=ft.TextStyle(letter_spacing=-0.5),
        )
        self._hero_greeting_wrap = ft.Container(
            content=self._hero_greeting,
            opacity=0,
            animate_opacity=ft.Animation(900, ft.AnimationCurve.EASE_OUT),
        )

        # ── START BUTTON ──
        self._play_icon = ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, size=20, color=t["primary"])
        self._start_text = ft.Text(
            value="START GAME", size=14,
            weight=ft.FontWeight.W_700, color=t["on_surface"],
            style=ft.TextStyle(letter_spacing=1.6),
        )
        self.start_btn = ft.Container(
            width=230, height=54, border_radius=27,
            bgcolor=t["primary_cont"],
            border=_border_all(2, t["primary"]),
            ink=True, on_click=self._on_start,
            shadow=ft.BoxShadow(
                blur_radius=20, spread_radius=0,
                color="#00000060",
                offset=ft.Offset(0, 6),
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER, spacing=10,
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
            border_radius=20, bgcolor=t["surface2"],
            border=_border_all(1, t["outline"]),
            padding=_pad(vertical=4, horizontal=12),
            content=ft.Text(value=self._badge_text(), size=11, color=t["on_surface2"]),
        )

        # ── Workspace badge in topbar ──
        meta = self._active_ws_meta()
        self._ws_badge_icon = ft.Icon(
            WORKSPACE_ICONS[meta.get("icon_index", 0)],
            size=12, color=meta.get("color", t["primary"]),
        )
        self._ws_badge_label = ft.Text(
            value=self._settings.get("active_workspace", "Default"),
            size=11, color=t["on_surface2"],
        )
        self.ws_badge = ft.Container(
            border_radius=20, bgcolor=t["surface2"],
            border=_border_all(1, t["outline"]),
            padding=_pad(vertical=4, horizontal=12),
            ink=True, tooltip="Switch workspace",
            on_click=self._show_workspaces,
            content=ft.Row(spacing=5, tight=True, controls=[
                self._ws_badge_icon, self._ws_badge_label,
            ]),
        )

        self._build_lines = []

        # ── Version selector card ──
        self._ver_label = ft.Text(
            value=self._ver_selector_text(),
            size=13, color=t["on_surface"], weight=ft.FontWeight.W_600,
        )
        self._ver_sub = ft.Text(value=self._ver_selector_sub(), size=11, color=t["on_surface2"])
        self._ver_icon_cont = ft.Container(
            width=36, height=36, border_radius=12,
            bgcolor=t["primary_cont"], alignment=ft.Alignment(0, 0),
            content=ft.Icon(ft.Icons.LAYERS_ROUNDED, size=18, color=t["primary"]),
        )
        self._ver_icon      = self._ver_icon_cont.content
        self._ver_chevron   = ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, size=16, color=t["on_surface3"])
        self._version_selector_card = ft.Container(
            width=360, border_radius=18,
            bgcolor=t["surface2"],
            border=_border_all(1, t["outline"]),
            padding=_pad(vertical=10, horizontal=16),
            ink=True, on_click=self._show_version_manager,
            tooltip="Click to change version",
            shadow=ft.BoxShadow(blur_radius=20, spread_radius=0,
                                color="#00000030", offset=ft.Offset(0, 4)),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
                controls=[
                    self._ver_icon_cont,
                    ft.Column(spacing=1, tight=True, expand=True,
                              controls=[self._ver_label, self._ver_sub]),
                    self._ver_chevron,
                ],
            ),
        )

        # ── Workspace indicator ──
        ws_meta  = self._active_ws_meta()
        ws_color = ws_meta.get("color", t["primary"])
        ws_icon  = WORKSPACE_ICONS[ws_meta.get("icon_index", 0)]
        self._ws_ind_icon = ft.Icon(ws_icon, size=15, color=ws_color)
        self._ws_ind_name = ft.Text(self._active_ws_name(), size=12,
                                    color=t["on_surface"], weight=ft.FontWeight.W_600)
        self._ws_ind_label = ft.Text("Workspace", size=10, color=t["on_surface2"])
        self._ws_ind_switch = ft.Text("switch →", size=10, color=t["on_surface3"])
        self._ws_ind_container = ft.Container(
            width=36, height=36, border_radius=12,
            bgcolor=ws_color + "22",
            border=_border_all(1, ws_color + "66"),
            alignment=ft.Alignment(0, 0),
            content=self._ws_ind_icon,
        )
        self._ws_indicator = ft.Container(
            width=360, border_radius=18,
            bgcolor=t["surface2"],
            border=_border_all(1, t["outline"]),
            padding=_pad(vertical=10, horizontal=16),
            ink=True, on_click=self._show_workspaces,
            tooltip="Manage workspaces",
            shadow=ft.BoxShadow(blur_radius=20, spread_radius=0,
                                color="#00000030", offset=ft.Offset(0, 4)),
            content=ft.Row(
                spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self._ws_ind_container,
                    ft.Column(spacing=1, tight=True, expand=True, controls=[
                        self._ws_ind_label,
                        self._ws_ind_name,
                    ]),
                    self._ws_ind_switch,
                ],
            ),
        )

        self._build_layout()
        threading.Thread(target=self._check_update_async, daemon=True).start()

    # ── WORKSPACE HELPERS ────────────────────────────
    def _active_ws_name(self) -> str:
        return self._settings.get("active_workspace", "Default")

    def _active_ws_meta(self) -> dict:
        return self._workspaces.get(self._active_ws_name(), DEFAULT_WORKSPACE)

    def _refresh_ws_badge(self):
        """Update ALL workspace-related UI elements at once."""
        meta  = self._active_ws_meta()
        name  = self._active_ws_name()
        color = meta.get("color", self._tokens["primary"])
        icon  = WORKSPACE_ICONS[meta.get("icon_index", 0)]

        self._ws_badge_label.value = name
        self._ws_badge_icon.name   = icon
        self._ws_badge_icon.color  = color

        self._ws_ind_icon.name         = icon
        self._ws_ind_icon.color        = color
        self._ws_ind_name.value        = name
        self._ws_ind_container.bgcolor = color + "22"
        self._ws_ind_container.border  = _border_all(1, color + "66")

        if self.page:
            self.page.update()

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
        tod   = ("Morning" if hour < 12 else "Afternoon" if hour < 18 else "Evening")
        if count in EASTER_EGG_GREETINGS:
            return EASTER_EGG_GREETINGS[count]
        if nick:       return f"{tod}, {nick}"
        if count <= 1: return "First block placed."
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
            self.page.update()

    def _check_update_async(self):
        try:
            lv = latest_version()
            self._latest_ver = lv
            self._settings["known_latest"] = lv
            save_settings(self._settings)
            if self.page:
                self.version_badge.content.value = self._badge_text()
                self._refresh_ver_card()
        except Exception:
            pass

    def _drain_build_output(self, timeout_seconds: float = 300.0):
        """Drain the build output queue until a 'done' sentinel or timeout."""
        deadline = datetime.datetime.now().timestamp() + timeout_seconds
        while datetime.datetime.now().timestamp() < deadline:
            try:
                kind, val = self._out_q.get(timeout=0.5)
                if kind == "done":
                    return
                if kind == "line":
                    self._build_lines.append(val)
            except queue.Empty:
                continue
        log("[DRAIN] timed out waiting for build output sentinel")

    # ── LAYOUT ───────────────────────────────────────
    def _build_layout(self):
        t = self._tokens
        self._rail_buttons.clear()

        def make_rail_btn(icon, label, handler):
            btn = RailButton(icon, label, handler, t)
            self._rail_buttons.append(btn)
            return btn

        rail_btns = [
            make_rail_btn(ft.Icons.DASHBOARD_ROUNDED,   "Workspaces", self._show_workspaces),
            make_rail_btn(ft.Icons.PALETTE_ROUNDED,     "Themes",     self._show_themes),
            make_rail_btn(ft.Icons.TUNE_ROUNDED,        "Settings",   self._show_settings),
            make_rail_btn(ft.Icons.LEADERBOARD_ROUNDED, "My Stats",   self._show_stats),
            make_rail_btn(ft.Icons.BACKUP_ROUNDED,      "Backups",    self._show_backups),
            make_rail_btn(ft.Icons.FOLDER_OPEN_ROUNDED, "Mod Folder", self._open_data),
            make_rail_btn(ft.Icons.BUG_REPORT_ROUNDED,  "Logs",       self._open_logs),
        ]

        self._theme_btn_icon = ft.Icon(
            ft.Icons.DARK_MODE_ROUNDED if self._is_light else ft.Icons.LIGHT_MODE_ROUNDED,
            size=18, color=t["on_surface2"],
        )
        theme_bottom_btn = ft.Container(
            width=38, height=38, border_radius=19,
            ink=True, on_click=self._toggle_theme,
            tooltip="Toggle light/dark mode",
            alignment=ft.Alignment(0, 0),
            content=self._theme_btn_icon,
        )

        rail_inner = ft.Column(
            spacing=6, expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(height=18),
                *rail_btns,
                ft.Container(expand=True),
                theme_bottom_btn,
                ft.Container(height=6),
            ],
        )

        self._rail_container = ft.Container(
            width=self.RAIL_COLLAPSED,
            bgcolor=t["rail"],
            border=_border_right(1, t["outline"]),
            padding=_pad(vertical=10, horizontal=10),
            content=rail_inner,
        )

        topbar = ft.Container(
            height=48,
            bgcolor=t["surface"],
            border=_border_bottom(1, t["outline"]),
            padding=_pad4(left=20, right=16, top=0, bottom=0),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                controls=[
                    ft.Text("Luancher", size=14, weight=ft.FontWeight.W_800,
                            color=t["on_surface"],
                            style=ft.TextStyle(letter_spacing=0.2)),
                    ft.Text("·  THE LAUNCHER FOR LUANTI", size=9,
                            color=t["on_surface3"],
                            style=ft.TextStyle(letter_spacing=1.2)),
                    ft.Container(expand=True),
                    self.ws_badge,
                    self.version_badge,
                ],
            ),
        )

        center = ft.Container(
            expand=True, bgcolor=t["bg"],
            content=ft.Column(
                expand=True, spacing=0,
                controls=[
                    topbar,
                    self.progress_bar,
                    ft.Container(
                        expand=True,
                        content=ft.Column(
                            expand=True,
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                            controls=[
                                self._hero_greeting_wrap,
                                ft.Container(height=4),
                                ft.Container(width=360, content=self.quote_text),
                                ft.Container(height=22),
                                ft.Container(
                                    border_radius=20,
                                    bgcolor=t["surface2"],
                                    border=_border_all(1, t["outline"]),
                                    padding=_pad(vertical=6, horizontal=14),
                                    content=ft.Row(
                                        spacing=8, tight=True,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Icon(ft.Icons.FORUM_ROUNDED, size=12,
                                                    color=t["on_surface2"]),
                                            ft.Text("Community: ", size=11,
                                                    color=t["on_surface2"]),
                                            ft.GestureDetector(
                                                on_tap=lambda _: webbrowser.open(
                                                    "https://discord.gg/DXhwwCpr3d"),
                                                content=ft.Text(
                                                    "discord.gg/DXhwwCpr3d", size=11,
                                                    color=t["primary"],
                                                    style=ft.TextStyle(
                                                        decoration=ft.TextDecoration.UNDERLINE),
                                                ),
                                            ),
                                        ],
                                    ),
                                ),
                                ft.Container(height=18),
                                self._ws_indicator,
                                ft.Container(height=10),
                                self._version_selector_card,
                                ft.Container(height=18),
                                self.start_btn,
                                ft.Container(height=10),
                                self.cancel_btn,
                                ft.Container(height=6),
                                self.status_chip,
                            ],
                        ),
                    ),
                ],
            ),
        )

        news_panel = ft.Container(
            width=255, bgcolor=t["surface"],
            border=_border_left(1, t["outline"]),
            content=ft.Column(
                expand=True, spacing=0,
                controls=[
                    ft.Container(
                        height=48, bgcolor=t["surface"],
                        border=_border_bottom(1, t["outline"]),
                        padding=_pad4(left=16, right=16, top=0, bottom=0),
                        content=ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.NEWSPAPER_ROUNDED, size=13,
                                        color=t["on_surface2"]),
                                ft.Container(width=6),
                                ft.Text("LUANTI NEWS", size=10,
                                        weight=ft.FontWeight.W_700,
                                        color=t["on_surface2"],
                                        style=ft.TextStyle(letter_spacing=1.5)),
                            ],
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        padding=_pad(vertical=10, horizontal=10),
                        content=self.news_col,
                    ),
                ],
            ),
        )

        self.content = ft.Row(
            expand=True, spacing=0,
            controls=[self._rail_container, center, news_panel],
        )

    # ── SYNC after theme change ───────────────────────
    def _sync_refs(self):
        t = self._tokens
        self.quote_text.color            = t["on_surface2"]
        self.progress_bar.color          = t["primary"]
        self.progress_bar.bgcolor        = t["outline"]
        self.start_btn.bgcolor           = t["primary_cont"]
        self.start_btn.border            = _border_all(2, t["primary"])
        self.start_btn.shadow            = ft.BoxShadow(
            blur_radius=20, spread_radius=0,
            color="#00000060", offset=ft.Offset(0, 6),
        )
        self._play_icon.color            = t["primary"]
        self._start_text.color           = t["on_surface"]
        self.cancel_btn.style            = ft.ButtonStyle(color=t["error"])
        self.status_chip.bgcolor         = t["surface2"]
        self.status_chip.border          = _border_all(1, t["outline"])
        self._status_icon.color          = t["on_surface2"]
        self._status_label.color         = t["on_surface2"]
        self.version_badge.bgcolor       = t["surface2"]
        self.version_badge.border        = _border_all(1, t["outline"])
        self.version_badge.content.color = t["on_surface2"]
        self.ws_badge.bgcolor            = t["surface2"]
        self.ws_badge.border             = _border_all(1, t["outline"])
        self._ws_badge_label.color       = t["on_surface2"]
        if hasattr(self, "_hero_greeting"):
            self._hero_greeting.color    = t["on_surface"]
        self._ver_label.color            = t["on_surface"]
        self._ver_sub.color              = t["on_surface2"]
        self._ver_icon_cont.bgcolor      = t["primary_cont"]
        self._ver_icon.color             = t["primary"]
        self._ver_chevron.color          = t["on_surface3"]
        self._version_selector_card.bgcolor = t["surface2"]
        self._version_selector_card.border  = _border_all(1, t["outline"])
        meta  = self._active_ws_meta()
        color = meta.get("color", t["primary"])
        self._ws_ind_icon.color          = color
        self._ws_ind_name.color          = t["on_surface"]
        self._ws_ind_label.color         = t["on_surface2"]
        self._ws_ind_switch.color        = t["on_surface3"]
        self._ws_ind_container.bgcolor   = color + "22"
        self._ws_ind_container.border    = _border_all(1, color + "66")
        self._ws_indicator.bgcolor       = t["surface2"]
        self._ws_indicator.border        = _border_all(1, t["outline"])
        for btn in self._rail_buttons:
            btn.set_tokens(t)
        if hasattr(self, "_theme_btn_icon"):
            self._theme_btn_icon.color   = t["on_surface2"]

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
            self.page.update()

    # ── NEWS ──────────────────────────────────────────
    def load_news(self):
        t = self._tokens
        self.news_col.controls.clear()
        self.news_col.controls.append(
            ft.Container(
                border_radius=12, bgcolor=t["surface2"],
                padding=_pad(vertical=10, horizontal=12),
                content=ft.Row(spacing=8, controls=[
                    ft.ProgressRing(width=12, height=12, stroke_width=2, color=t["primary"]),
                    ft.Text("Fetching blocks from the server...", size=11, color=t["on_surface2"]),
                ]),
            )
        )
        if self.page:
            self.page.update()

        def _fetch():
            items = fetch_news()
            self.news_col.controls.clear()
            if not items:
                self.news_col.controls.append(
                    ft.Container(
                        border_radius=8, bgcolor=t["surface2"],
                        padding=_pad(vertical=10, horizontal=12),
                        content=ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.WIFI_OFF_ROUNDED, size=13, color=t["on_surface2"]),
                            ft.Text("Offline.", size=11, color=t["on_surface2"]),
                        ]),
                    )
                )
            else:
                for n in items:
                    def _handler(item):
                        return lambda e: self._show_article(item)
                    card = ft.Container(
                        border_radius=8, ink=True, bgcolor=t["surface2"],
                        border=_border_side_left(2, t["primary"]),
                        padding=_pad4(left=10, top=8, right=10, bottom=8),
                        margin=_margin_b(5),
                        on_click=_handler(n),
                        content=ft.Column(
                            spacing=2, tight=True,
                            controls=[
                                ft.Text(n["date"],  size=9,  color=t["news_date"]),
                                ft.Text(n["title"], size=11, weight=ft.FontWeight.W_600,
                                        color=t["news_title"]),
                                ft.Text(n["desc"],  size=10, color=t["on_surface2"]),
                            ],
                        ),
                    )
                    self.news_col.controls.append(card)
            if self.page:
                self.page.update()

        threading.Thread(target=_fetch, daemon=True).start()

    # ── SHEETS ────────────────────────────────────────
    def _open_sheet(self, sheet):
        if sheet not in self.page.overlay:
            self.page.overlay.append(sheet)
        sheet.open = True
        self.page.update()

    def _close_sheet(self, sheet):
        sheet.open = False
        if sheet in self.page.overlay:
            self.page.overlay.remove(sheet)
        self.page.update()

    def _make_sheet(self, col, height_frac=0.78):
        t = self._tokens
        h = (self.page.height or 680) * height_frac if self.page else 520
        return ft.BottomSheet(
            content=ft.Container(
                bgcolor=t["surface"],
                border_radius=_br_top(20),
                padding=_pad(vertical=20, horizontal=24),
                height=h, content=col,
            ),
        )

    def _title(self, txt):
        return ft.Text(txt, size=16, weight=ft.FontWeight.W_700,
                       color=self._tokens["on_surface"])

    def _divider(self):
        return ft.Divider(height=16, color=self._tokens["outline"])

    def _sec(self, txt):
        return ft.Text(txt, size=9, color=self._tokens["on_surface2"],
                       weight=ft.FontWeight.W_700,
                       style=ft.TextStyle(letter_spacing=1.5))

    # ── WORKSPACES ────────────────────────────────────
    def _show_workspaces(self, e=None):
        t      = self._tokens
        active = self._active_ws_name()
        content = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE, controls=[])
        sheet   = self._make_sheet(content, height_frac=0.92)

        def refresh():
            nonlocal active
            ws    = self._workspaces
            tiles = []
            for name, meta in ws.items():
                is_active = (name == active)
                color = meta.get("color", t["primary"])
                icon  = WORKSPACE_ICONS[meta.get("icon_index", 0)]
                desc  = meta.get("description", "")
                wd    = workspace_data_dir(name)
                worlds_count = mods_count = 0
                try:
                    wp = wd / "worlds"
                    if wp.exists():
                        worlds_count = len([d for d in wp.iterdir() if d.is_dir()])
                    mp = wd / "mods"
                    if mp.exists():
                        mods_count = len([d for d in mp.iterdir() if d.is_dir()])
                except Exception:
                    pass

                def _select(_, n=name):
                    nonlocal active
                    active = n
                    self._settings["active_workspace"] = n
                    save_settings(self._settings)
                    self._refresh_ws_badge()
                    self._close_sheet(sheet)
                    self._set_status(
                        f"Workspace: {n}",
                        ft.Icons.DASHBOARD_ROUNDED,
                        self._workspaces.get(n, {}).get("color", t["primary"]),
                    )

                def _delete(_, n=name):
                    if n == "Default": return
                    del self._workspaces[n]
                    save_workspaces(self._workspaces)
                    if self._settings.get("active_workspace") == n:
                        self._settings["active_workspace"] = "Default"
                        save_settings(self._settings)
                        self._refresh_ws_badge()
                    refresh()

                stat_chips = ft.Row(spacing=4, wrap=True, controls=[
                    ft.Container(border_radius=5, bgcolor=t["surface3"],
                                 padding=_pad(vertical=2, horizontal=6),
                                 content=ft.Text(f"{worlds_count} worlds", size=9,
                                                 color=t["on_surface2"])),
                    ft.Container(border_radius=5, bgcolor=t["surface3"],
                                 padding=_pad(vertical=2, horizontal=6),
                                 content=ft.Text(f"{mods_count} mods", size=9,
                                                 color=t["on_surface2"])),
                ])
                delete_btn = ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_size=15,
                    icon_color=t["error"], tooltip="Delete workspace",
                    on_click=_delete, visible=(name != "Default"),
                    style=ft.ButtonStyle(padding=ft.Padding(4, 4, 4, 4)),
                )
                folder_btn = ft.IconButton(
                    icon=ft.Icons.FOLDER_OPEN_ROUNDED, icon_size=15,
                    icon_color=t["on_surface2"], tooltip="Open folder",
                    on_click=lambda _, n=name: self._open_folder(workspace_data_dir(n)),
                    style=ft.ButtonStyle(padding=ft.Padding(4, 4, 4, 4)),
                )

                tile = ft.Container(
                    border_radius=12, ink=not is_active,
                    bgcolor=t["surface2"] if is_active else None,
                    border=_border_all(2 if is_active else 1,
                                       color if is_active else t["outline"]),
                    padding=_pad(vertical=10, horizontal=12),
                    margin=_margin_b(6),
                    on_click=_select if not is_active else None,
                    content=ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
                        controls=[
                            ft.Container(
                                width=40, height=40, border_radius=10,
                                bgcolor=color + "33", border=_border_all(2, color),
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(icon, size=18, color=color),
                            ),
                            ft.Container(width=12),
                            ft.Column(expand=True, spacing=3, tight=True, controls=[
                                ft.Row(spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                       controls=[
                                    ft.Text(name, size=13, weight=ft.FontWeight.W_700,
                                            color=t["on_surface"]),
                                    ft.Container(
                                        visible=is_active, border_radius=5,
                                        bgcolor=color + "33",
                                        padding=_pad(vertical=1, horizontal=6),
                                        content=ft.Text("ACTIVE", size=8,
                                                        weight=ft.FontWeight.W_800,
                                                        color=color,
                                                        style=ft.TextStyle(letter_spacing=0.8)),
                                    ),
                                ]),
                                ft.Text(desc, size=10, color=t["on_surface2"]),
                                stat_chips,
                            ]),
                            folder_btn, delete_btn,
                        ],
                    ),
                )
                tiles.append(tile)

            content.controls = [
                ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self._title("WORKSPACES"),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.ADD_ROUNDED, icon_size=18,
                            icon_color=t["primary"], tooltip="New workspace",
                            on_click=lambda _: self._show_create_workspace(sheet, refresh),
                        ),
                    ],
                ),
                ft.Container(height=2),
                ft.Text("Each workspace has its own worlds, mods, and textures — "
                        "but shares the same game engine.",
                        size=11, color=t["on_surface2"]),
                self._divider(),
                *tiles,
                ft.Container(height=8),
                ft.TextButton(content="Close",
                              on_click=lambda _: self._close_sheet(sheet)),
            ]
            if self.page:
                self.page.update()

        refresh()
        self._open_sheet(sheet)

    def _show_create_workspace(self, parent_sheet, on_done):
        t = self._tokens
        name_f = ft.TextField(
            label="Workspace name", border_radius=10, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"], autofocus=True,
        )
        desc_f = ft.TextField(
            label="Short description (optional)", border_radius=10, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"],
        )
        fb = ft.Text("", size=11, color=t["error"])
        chosen_icon  = [0]
        chosen_color = [WORKSPACE_COLORS[0]]
        icon_preview = ft.Icon(WORKSPACE_ICONS[0], size=28, color=WORKSPACE_COLORS[0])

        def _icon_row():
            return ft.Row(spacing=6, wrap=True, controls=[
                ft.Container(
                    width=36, height=36, border_radius=9,
                    bgcolor=(chosen_color[0] + "33"),
                    border=_border_all(2 if i == chosen_icon[0] else 1,
                                       chosen_color[0] if i == chosen_icon[0] else t["outline"]),
                    alignment=ft.Alignment(0, 0), ink=True, tooltip=f"Icon {i+1}",
                    on_click=(lambda _, ii=i: _pick_icon(ii)),
                    content=ft.Icon(WORKSPACE_ICONS[i], size=16,
                                    color=chosen_color[0] if i == chosen_icon[0]
                                          else t["on_surface2"]),
                )
                for i in range(len(WORKSPACE_ICONS))
            ])

        def _color_row():
            return ft.Row(spacing=6, wrap=True, controls=[
                ft.Container(
                    width=26, height=26, border_radius=13, bgcolor=c,
                    border=_border_all(3 if c == chosen_color[0] else 1,
                                       t["on_surface"] if c == chosen_color[0] else t["outline"]),
                    ink=True, tooltip=c,
                    on_click=(lambda _, cc=c: _pick_color(cc)),
                )
                for c in WORKSPACE_COLORS
            ])

        icon_row_ctrl  = ft.Container(content=_icon_row())
        color_row_ctrl = ft.Container(content=_color_row())

        def _pick_icon(i):
            chosen_icon[0] = i
            icon_preview.name  = WORKSPACE_ICONS[i]
            icon_preview.color = chosen_color[0]
            icon_row_ctrl.content = _icon_row()
            if self.page: self.page.update()

        def _pick_color(c):
            chosen_color[0] = c
            icon_preview.color = c
            color_row_ctrl.content = _color_row()
            icon_row_ctrl.content  = _icon_row()
            if self.page: self.page.update()

        def _create(_):
            name = (name_f.value or "").strip()
            if not name:
                fb.value = "Name is required."
                if self.page: self.page.update()
                return
            if name in self._workspaces:
                fb.value = "A workspace with that name already exists."
                if self.page: self.page.update()
                return
            self._workspaces[name] = {
                "name":        name,
                "description": (desc_f.value or "").strip(),
                "icon_index":  chosen_icon[0],
                "color":       chosen_color[0],
                "created":     datetime.date.today().isoformat(),
            }
            save_workspaces(self._workspaces)
            ensure_workspace(name)
            self._close_sheet(sheet2)
            on_done()

        preview_box = ft.Container(
            width=60, height=60, border_radius=15,
            bgcolor=chosen_color[0] + "22",
            border=_border_all(2, chosen_color[0]),
            alignment=ft.Alignment(0, 0), content=icon_preview,
        )

        content = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE, controls=[
            self._title("NEW WORKSPACE"),
            ft.Container(height=10),
            ft.Row(spacing=16, vertical_alignment=ft.CrossAxisAlignment.START,
                   controls=[
                       preview_box,
                       ft.Column(expand=True, spacing=6, tight=True,
                                 controls=[name_f, desc_f]),
                   ]),
            ft.Container(height=10),
            self._sec("ICON"), ft.Container(height=6), icon_row_ctrl,
            ft.Container(height=10),
            self._sec("COLOR"), ft.Container(height=6), color_row_ctrl,
            ft.Container(height=10), fb,
            ft.Row(spacing=8, controls=[
                ft.FilledButton(content="Create Workspace",
                                icon=ft.Icons.ADD_ROUNDED, on_click=_create),
                ft.TextButton(content="Cancel",
                              on_click=lambda _: self._close_sheet(sheet2)),
            ]),
        ])
        sheet2 = self._make_sheet(content, height_frac=0.90)
        self._open_sheet(sheet2)

    # ── VERSION MANAGER ───────────────────────────────
    def _show_build_error_dialog(self, error_str: str, phase: str = "build"):
        t = self._tokens

        if "cmake" in error_str.lower() or "command not found" in error_str.lower():
            hint = ("cmake or make is missing from your system.\n"
                    "Install build tools:\n"
                    "  Ubuntu/Debian:  sudo apt install cmake build-essential\n"
                    "  Fedora:         sudo dnf install cmake gcc-c++ make\n"
                    "  Arch:           sudo pacman -S cmake base-devel")
            resources = [
                ("Luanti Build Deps", "https://github.com/luanti-org/luanti/blob/master/doc/compiling/linux.md"),
            ]
        elif "network" in error_str.lower() or "connection" in error_str.lower() or "timeout" in error_str.lower():
            hint = "Could not reach GitHub. Check your internet connection and try again."
            resources = [
                ("GitHub Releases", "https://github.com/luanti-org/luanti/releases"),
            ]
        else:
            hint = ("The build failed during compilation. This usually means a missing\n"
                    "dependency or an incompatible system library.")
            resources = [
                ("Build Guide (Linux)", "https://github.com/luanti-org/luanti/blob/master/doc/compiling/linux.md"),
                ("Luanti Forums",       "https://forum.luanti.org/"),
                ("Discord / IRC",       "https://discord.gg/DXhwwCpr3d"),
                ("GitHub Issues",       "https://github.com/luanti-org/luanti/issues"),
            ]

        log_path = str(LOGS)

        def _close():
            dialog.open = False
            if self.page: self.page.update()

        resource_rows = []
        for label, url in resources:
            resource_rows.append(
                ft.GestureDetector(
                    on_tap=lambda _, u=url: webbrowser.open(u),
                    content=ft.Text(
                        f"→  {label}", size=11, color=t["primary"],
                        style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE),
                    ),
                )
            )

        dialog = ft.AlertDialog(
            open=True, modal=True,
            title=ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.BUILD_CIRCLE_ROUNDED, color=t["error"], size=22),
                ft.Text(f"{phase.title()} Failed", size=15,
                        weight=ft.FontWeight.W_700, color=t["on_surface"]),
            ]),
            content=ft.Column(tight=True, width=400, scroll=ft.ScrollMode.ADAPTIVE, controls=[
                ft.Container(
                    border_radius=8, bgcolor=t["surface2"],
                    border=_border_side_left(3, t["error"]),
                    padding=_pad(vertical=8, horizontal=12),
                    content=ft.Text(str(error_str)[:300], size=11,
                                    color=t["error"], selectable=True),
                ),
                ft.Container(height=10),
                ft.Text(hint, size=11, color=t["on_surface2"]),
                ft.Container(height=10),
                ft.Text("Resources:", size=11, weight=ft.FontWeight.W_700,
                        color=t["on_surface"]),
                *resource_rows,
                ft.Container(height=8),
                ft.GestureDetector(
                    on_tap=lambda _: self._open_folder(LOGS),
                    content=ft.Text(f"→  Logs folder: {log_path}", size=11,
                                    color=t["on_surface2"],
                                    style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE)),
                ),
            ]),
            actions=[ft.FilledButton("OK", on_click=lambda _: _close())],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=t["surface"],
            shape=ft.RoundedRectangleBorder(radius=22),
        )
        if self.page:
            self.page.overlay.append(dialog)
            self.page.update()

    def _show_version_manager(self, e=None):
        t    = self._tokens
        sel  = self._settings.get("selected_version", "latest")
        inst = installed_versions()

        sel_label = ft.Text(
            value=self._vm_sel_text(sel, inst),
            size=12, color=t["accent"], weight=ft.FontWeight.W_600,
        )

        releases_body = ft.Column(tight=True, spacing=4, scroll=ft.ScrollMode.ADAPTIVE)
        releases_body.controls.append(ft.Row(spacing=8, controls=[
            ft.ProgressRing(width=12, height=12, stroke_width=2, color=t["primary"]),
            ft.Text("Fetching releases from GitHub...", size=12, color=t["on_surface2"]),
        ]))

        content_col = ft.Column(tight=True, spacing=0, scroll=ft.ScrollMode.ADAPTIVE,
                                controls=[])
        sheet = self._make_sheet(content_col, height_frac=0.92)

        installed_section = ft.Column(tight=True, spacing=0)
        installed_section.controls = self._vm_installed_tiles(
            inst, sel, sel_label, sheet, installed_section
        )

        import_status = ft.Text("", size=11, color=t["accent"])

        async def _pick_custom_binary(_):
            if not self._file_picker:
                import_status.value = "File picker not available."
                import_status.color = t["error"]
                if self.page: self.page.update()
                return
            try:
                files = await self._file_picker.pick_files(
                    dialog_title="Select your Luanti/Minetest binary",
                    allow_multiple=False,
                )
            except Exception as ex:
                import_status.value = f"Could not open picker: {ex}"
                import_status.color = t["error"]
                if self.page: self.page.update()
                return
            if not files:
                return
            picked = files[0]
            binary_path = Path(picked.path)
            ver_name    = custom_name_field.value.strip()
            if not ver_name:
                ver_name = binary_path.parent.parent.name or "custom"
            import_status.value = f"Importing '{ver_name}'..."
            import_status.color = t["on_surface2"]
            if self.page: self.page.update()
            try:
                import_custom_version(binary_path, ver_name)
                migrate(ver_name, self._active_ws_name())
                import_status.value = f"✓ '{ver_name}' imported and synced with your workspace!"
                import_status.color = t["accent"]
                new_inst = installed_versions()
                new_sel  = self._settings.get("selected_version", "latest")
                installed_section.controls = self._vm_installed_tiles(
                    new_inst, new_sel, sel_label, sheet, installed_section
                )
                sel_label.value = self._vm_sel_text(new_sel, new_inst)
                custom_name_field.value = ""
            except Exception as ex:
                import_status.value = f"Import failed: {ex}"
                import_status.color = t["error"]
            if self.page: self.page.update()

        custom_name_field = ft.TextField(
            hint_text="Version nickname  (e.g. my-5.9-debug)",
            hint_style=ft.TextStyle(size=11, color=t["on_surface3"]),
            text_size=12, color=t["on_surface"],
            bgcolor=t["surface2"], border_color=t["outline"],
            focused_border_color=t["primary"],
            border_radius=12, height=40,
            content_padding=_pad4(left=12, right=12, top=0, bottom=0),
        )

        custom_section = ft.Container(
            border_radius=16,
            bgcolor=t["surface2"],
            border=_border_all(1, t["outline"]),
            padding=_pad(vertical=14, horizontal=16),
            content=ft.Column(spacing=8, tight=True, controls=[
                ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Text("🔧", size=18),
                    ft.Column(spacing=1, tight=True, expand=True, controls=[
                        ft.Text("Import Custom Build", size=13,
                                weight=ft.FontWeight.W_700, color=t["on_surface"]),
                        ft.Text("For developers and power users. Point Luancher at "
                                "your own compiled binary.",
                                size=10, color=t["on_surface2"]),
                    ]),
                ]),
                custom_name_field,
                ft.Row(spacing=8, controls=[
                    ft.FilledButton(
                        "Select Binary…",
                        icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                        on_click=_pick_custom_binary,
                    ),
                ]),
                import_status,
            ]),
        )

        content_col.controls = [
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self._title("VERSION MANAGER"),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED, icon_size=16,
                        icon_color=t["on_surface2"], tooltip="Refresh releases",
                        on_click=lambda _: threading.Thread(
                            target=self._vm_load_releases,
                            args=(releases_body, sel_label, sheet),
                            daemon=True,
                        ).start(),
                    ),
                ],
            ),
            ft.Container(height=2),
            sel_label,
            ft.Container(height=2),
            ft.Text("Versions coexist independently. Pinned versions never auto-update.",
                    size=11, color=t["on_surface2"]),
            self._divider(),
            self._sec("INSTALLED"), ft.Container(height=6),
            installed_section,
            self._divider(),
            self._sec("AVAILABLE RELEASES"), ft.Container(height=6),
            releases_body,
            self._divider(),
            self._sec("CUSTOM BUILD"), ft.Container(height=6),
            custom_section,
            ft.Container(height=10),
            ft.TextButton(content="Close", on_click=lambda _: self._close_sheet(sheet)),
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

    def _vm_installed_tiles(self, inst, sel, sel_label, sheet,
                             installed_section=None):
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
            needs_net=True, warn=False, deletable=False,
            on_select=lambda _: self._vm_select("latest", sel_label, sheet),
            on_delete=None,
        ))
        for v in inst:
            is_sel_v = (sel == v)
            warn     = version_is_legacy(v)
            def _make_delete(vv, section):
                def _on_delete(_):
                    self._vm_confirm_delete(vv, sel_label, sheet, section)
                return _on_delete
            tiles.append(self._vm_tile(
                tag=v, label=f"v{v}", sublabel="Installed  ·  pinned",
                icon=ft.Icons.LAYERS_ROUNDED,
                is_selected=is_sel_v,
                badge_text=None, badge_color=None, badge_bg=None,
                needs_net=False, warn=warn, deletable=True,
                on_select=lambda _, vv=v: self._vm_select(vv, sel_label, sheet),
                on_delete=_make_delete(v, installed_section),
            ))
        return tiles

    def _vm_confirm_delete(self, version: str, sel_label, sheet, installed_section):
        t = self._tokens

        def _close_dlg():
            dlg.open = False
            if self.page: self.page.update()

        def _do_delete(_):
            _close_dlg()
            try:
                target = BUILDS / version
                if target.exists():
                    shutil.rmtree(target)
                link = BUILDS / "current"
                if link.is_symlink():
                    try:
                        if link.resolve().name == version:
                            link.unlink()
                    except Exception:
                        pass
                if self._settings.get("selected_version") == version:
                    self._settings["selected_version"] = "latest"
                    save_settings(self._settings)
                    self._refresh_ver_card()
                    self.version_badge.content.value = self._badge_text()
                if installed_section is not None:
                    new_inst = installed_versions()
                    new_sel  = self._settings.get("selected_version", "latest")
                    new_tiles = self._vm_installed_tiles(
                        new_inst, new_sel, sel_label, sheet, installed_section
                    )
                    installed_section.controls.clear()
                    for tile in new_tiles:
                        installed_section.controls.append(tile)
                    sel_label.value = self._vm_sel_text(new_sel, new_inst)
                if self.page: self.page.update()
            except Exception as ex:
                self._set_status(f"Delete failed: {ex}",
                                 ft.Icons.ERROR_OUTLINE_ROUNDED, t["error"])
                if self.page: self.page.update()

        dlg = ft.AlertDialog(
            open=True, modal=True,
            title=ft.Row(spacing=8, controls=[
                ft.Text("🧱", size=20),
                ft.Text(f"Delete v{version}?", size=15,
                        weight=ft.FontWeight.W_700, color=t["on_surface"]),
            ]),
            content=ft.Column(tight=True, width=340, controls=[
                ft.Text(
                    f"This will permanently remove v{version} from your disk. "
                    "Your workspaces and saves are not affected — only the game binary.",
                    size=12, color=t["on_surface2"],
                ),
                ft.Container(height=8),
                ft.Container(
                    border_radius=10, bgcolor=t["surface2"],
                    border=_border_side_left(3, "#ff8800"),
                    padding=_pad(vertical=8, horizontal=12),
                    content=ft.Text("You'll need to rebuild or re-download it to use it again.",
                                    size=11, color="#ff8800"),
                ),
            ]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: _close_dlg()),
                ft.FilledButton(
                    "Delete Version",
                    icon=ft.Icons.DELETE_FOREVER_ROUNDED,
                    on_click=_do_delete,
                    style=ft.ButtonStyle(bgcolor=t["error"], color="#ffffff"),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=t["surface"],
            shape=ft.RoundedRectangleBorder(radius=20),
        )
        if self.page:
            self.page.overlay.append(dlg)
            self.page.update()

    def _vm_tile(self, tag, label, sublabel, icon,
                 is_selected, badge_text, badge_color, badge_bg,
                 needs_net, warn, on_select, deletable=False, on_delete=None):
        t = self._tokens
        chips = []
        if badge_text:
            chips.append(ft.Container(
                border_radius=5, bgcolor=badge_bg or t["surface3"],
                padding=_pad(vertical=2, horizontal=6),
                content=ft.Text(badge_text, size=8, weight=ft.FontWeight.W_700,
                                color=badge_color or t["on_surface2"],
                                style=ft.TextStyle(letter_spacing=0.8)),
            ))
        if needs_net:
            chips.append(ft.Container(
                border_radius=5, bgcolor=t["surface2"],
                padding=_pad(vertical=2, horizontal=6),
                content=ft.Row(tight=True, spacing=3, controls=[
                    ft.Icon(ft.Icons.WIFI_ROUNDED, size=8, color=t["on_surface2"]),
                    ft.Text("Requires internet", size=8, color=t["on_surface2"]),
                ]),
            ))
        if warn:
            chips.append(ft.Container(
                border_radius=5, bgcolor="#2e1500",
                border=_border_all(1, "#cc6600"),
                padding=_pad(vertical=2, horizontal=6),
                content=ft.Row(tight=True, spacing=3, controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=8, color="#ff8800"),
                    ft.Text("Likely build issues (<5.13)", size=8, color="#ff8800"),
                ]),
            ))

        right_controls = [
            ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED_ROUNDED if is_selected
                    else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
                    size=18,
                    color=t["primary"] if is_selected else t["on_surface2"]),
        ]
        if deletable and on_delete:
            right_controls.append(
                ft.Container(
                    width=32, height=32, border_radius=10,
                    tooltip="Delete this version",
                    ink=True, on_click=on_delete,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.DELETE_OUTLINE_ROUNDED, size=16,
                                    color=t["on_surface3"]),
                )
            )

        return ft.Container(
            border_radius=14, ink=not is_selected,
            bgcolor=t["surface2"] if is_selected else None,
            border=_border_all(2 if is_selected else 1,
                               t["primary"] if is_selected else t["outline"]),
            padding=_pad(vertical=10, horizontal=12),
            margin=_margin_b(5),
            on_click=on_select if not is_selected else None,
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=38, height=38, border_radius=12,
                        bgcolor=t["primary_cont"] if is_selected else t["surface3"],
                        content=ft.Icon(icon, size=18,
                                        color=t["primary"] if is_selected else t["on_surface2"]),
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Container(width=10),
                    ft.Column(expand=True, spacing=3, tight=True, controls=[
                        ft.Text(label, size=13, weight=ft.FontWeight.W_600,
                                color=t["on_surface"]),
                        ft.Text(sublabel, size=10, color=t["on_surface2"]),
                        ft.Row(spacing=4, wrap=True, controls=chips) if chips else ft.Container(),
                    ]),
                    ft.Row(spacing=2, tight=True,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER,
                           controls=right_controls),
                ],
            ),
        )

    def _vm_load_releases(self, releases_body, sel_label, sheet):
        t = self._tokens
        releases_body.controls.clear()
        releases_body.controls.append(ft.Row(spacing=8, controls=[
            ft.ProgressRing(width=12, height=12, stroke_width=2, color=t["primary"]),
            ft.Text("Fetching releases...", size=11, color=t["on_surface2"]),
        ]))
        if self.page:
            self.page.update()

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
                self.page.update()
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
                    border_radius=5, bgcolor="#1e1200",
                    padding=_pad(vertical=2, horizontal=6),
                    content=ft.Text("PRE-RELEASE", size=8, color="#e8a020",
                                    style=ft.TextStyle(letter_spacing=0.8)),
                ))
            if warn:
                chips.append(ft.Container(
                    border_radius=5, bgcolor="#2e1500",
                    border=_border_all(1, "#cc6600"),
                    padding=_pad(vertical=2, horizontal=6),
                    content=ft.Row(tight=True, spacing=3, controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=8, color="#ff8800"),
                        ft.Text("May fail to build", size=8, color="#ff8800"),
                    ]),
                ))
            if is_i:
                chips.append(ft.Container(
                    border_radius=5, bgcolor=t["primary_cont"],
                    padding=_pad(vertical=2, horizontal=6),
                    content=ft.Text("INSTALLED", size=8, weight=ft.FontWeight.W_700,
                                    color=t["primary"],
                                    style=ft.TextStyle(letter_spacing=0.8)),
                ))

            action = (
                ft.FilledButton(content="Play", icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                on_click=_select_fn)
                if is_i else
                ft.OutlinedButton(content="Install", icon=ft.Icons.DOWNLOAD_ROUNDED,
                                  on_click=_install_fn)
            )

            releases_body.controls.append(ft.Container(
                border_radius=10, ink=not is_sel,
                bgcolor=t["surface2"] if is_sel else None,
                border=_border_all(2 if is_sel else 1,
                                   t["primary"] if is_sel else t["outline"]),
                padding=_pad(vertical=8, horizontal=12),
                margin=_margin_b(4),
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(expand=True, spacing=3, tight=True, controls=[
                            ft.Row(spacing=5, wrap=True, controls=[
                                ft.Text(f"v{tag}", size=12, weight=ft.FontWeight.W_600,
                                        color=t["on_surface"]),
                                *chips,
                            ]),
                            ft.Text(rel["date"], size=10, color=t["on_surface2"]),
                        ]),
                        action,
                    ],
                ),
            ))

        if self.page:
            self.page.update()

    def _vm_install(self, version: str):
        if version_is_legacy(version):
            self._set_status(f"⚠ v{version} is <5.13 — build errors are likely.",
                             ft.Icons.WARNING_AMBER_ROUNDED, "#ff8800")
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
            self.page.update()

        def _run():
            try:
                ensure_dirs()
                while not self._out_q.empty():
                    try: self._out_q.get_nowait()
                    except Exception: pass
                build_version(version, cancel_event=self.cancel_event, out_q=self._out_q)
                self._drain_build_output()
                migrate(version, self._active_ws_name())
                self._set_status(f"v{version} installed! Click START GAME to play.",
                                 ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, self._tokens["accent"])
            except InterruptedError:
                self._set_status("Cancelled.", ft.Icons.CANCEL_OUTLINED)
            except Exception as ex:
                log(f"[BUILD ERROR] {ex}")
                import traceback; log(traceback.format_exc())
                self._set_status(f"Build failed: {ex}",
                                 ft.Icons.ERROR_OUTLINE_ROUNDED, self._tokens["error"])
                self._show_build_error_dialog(str(ex), phase="build")
            finally:
                self.is_busy = False
                self.progress_bar.visible = False
                self.cancel_btn.visible   = False
                self.start_btn.on_click   = self._on_start
                self.cancel_event = None
                self.version_badge.content.value = self._badge_text()
                self._refresh_ver_card()
                if self.page:
                    self.page.update()

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
                self.page.update()

    def _set_busy(self, busy: bool):
        t = self._tokens
        self.is_busy = busy
        self.start_btn.bgcolor       = t["surface3"]    if busy else t["primary_cont"]
        self._play_icon.color        = t["on_surface2"] if busy else t["primary"]
        self._start_text.value       = "HOLD ON..."     if busy else "START GAME"
        self._start_text.color       = t["on_surface2"] if busy else t["on_surface"]
        self.start_btn.border        = _border_all(2, t["outline"] if busy else t["primary"])
        self.start_btn.on_click      = None if busy else self._on_start
        self.progress_bar.visible = busy
        self.cancel_btn.visible   = busy
        self.cancel_btn.disabled  = False
        if not busy:
            self.version_badge.content.value = self._badge_text()
        if self.page:
            self.page.update()

    def _flow(self):
        ws_name = self._active_ws_name()
        try:
            ensure_dirs()
            ensure_workspace(ws_name)
            sel = self._settings.get("selected_version", "latest")
            log(f"[FLOW] sel={sel}  workspace={ws_name}")

            if sel == "latest":
                cv = current_version()
                log(f"[FLOW] current_version={cv!r}")

                if cv is not None and find_binary(cv) is not None:
                    log(f"[FLOW] launching {cv}")
                    self._set_status("Launching...", ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                     self._tokens["accent"])
                    launch(cv, ws_name)
                    self._settings["total_sessions"] = \
                        self._settings.get("total_sessions", 0) + 1
                    save_settings(self._settings)
                else:
                    self._set_status("Fetching latest version info...",
                                     ft.Icons.MANAGE_SEARCH_ROUNDED)
                    try:
                        lv = latest_version()
                        log(f"[FLOW] latest={lv}")
                    except Exception as ex:
                        log(f"[FLOW] network error: {ex}")
                        self._set_status("Cannot reach GitHub. Check your connection.",
                                         ft.Icons.WIFI_OFF_ROUNDED, self._tokens["error"])
                        return
                    self.cancel_btn.content = "Cancel Install"
                    self._set_status(f"Installing v{lv}...",
                                     ft.Icons.DOWNLOAD_ROUNDED, self._tokens["primary"])
                    if self.page:
                        self.page.update()
                    while not self._out_q.empty():
                        try: self._out_q.get_nowait()
                        except Exception: pass
                    build_version(lv, cancel_event=self.cancel_event, out_q=self._out_q)
                    threading.Thread(target=self._drain_build_output, daemon=True).start()
                    migrate(lv, ws_name)
                    switch_current(lv)
                    self._settings["known_latest"] = lv
                    self._set_status("Launching...", ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                     self._tokens["accent"])
                    launch(lv, ws_name)
                    self._settings["total_sessions"] = \
                        self._settings.get("total_sessions", 0) + 1
                    save_settings(self._settings)
            else:
                log(f"[FLOW] pinned={sel}")
                if find_binary(sel) is None:
                    self._set_status(f"v{sel} not installed. Building now...",
                                     ft.Icons.DOWNLOAD_ROUNDED, self._tokens["primary"])
                    self.cancel_btn.content = "Cancel Install"
                    if self.page:
                        self.page.update()
                    while not self._out_q.empty():
                        try: self._out_q.get_nowait()
                        except Exception: pass
                    build_version(sel, cancel_event=self.cancel_event, out_q=self._out_q)
                    threading.Thread(target=self._drain_build_output, daemon=True).start()
                    migrate(sel, ws_name)
                self._set_status("Launching...", ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                 self._tokens["accent"])
                launch(sel, ws_name)
                self._settings["total_sessions"] = \
                    self._settings.get("total_sessions", 0) + 1
                save_settings(self._settings)

            count = self._settings.get("launch_count", 0)
            if count in LAUNCH_MILESTONES:
                msg = LAUNCH_MILESTONES[count]
                if self.page:
                    try: self._show_milestone(msg)
                    except Exception: pass

        except InterruptedError:
            self._set_status("Cancelled.", ft.Icons.CANCEL_OUTLINED)
        except subprocess.CalledProcessError as ex:
            log(f"[FLOW] BUILD ERROR: {ex}")
            import traceback; log(traceback.format_exc())
            self._set_status(f"Build failed: {ex}", ft.Icons.ERROR_OUTLINE_ROUNDED, self._tokens["error"])
            self._show_build_error_dialog(str(ex), phase="build")
        except Exception as ex:
            log(f"[FLOW] ERROR: {ex}")
            import traceback; log(traceback.format_exc())
            self._set_status(f"Error: {ex}", ft.Icons.ERROR_OUTLINE_ROUNDED, self._tokens["error"])
            ex_str = str(ex)
            if any(kw in ex_str.lower() for kw in ["cmake", "make", "compile", "build", "not found", "binary"]):
                self._show_build_error_dialog(ex_str, phase="build")
        finally:
            log("[FLOW] done")
            self._set_busy(False)
            self.quote_text.value = get_daily_tip(self._settings)
            self.cancel_event = None
            self._refresh_ver_card()
            if self.page:
                self.page.update()

    # ── ARTICLE ───────────────────────────────────────
    def _show_article(self, item):
        t     = self._tokens
        clean = html_to_text(item["full"])
        link  = item.get("link", "")
        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE,
                                expand=True, controls=[])
        sheet = self._make_sheet(content_col, height_frac=0.88)
        rows = [
            ft.Text(item["title"], size=16, weight=ft.FontWeight.W_700,
                    color=t["on_surface"]),
            ft.Text(item["date"], size=10, color=t["news_date"]),
        ]
        if link:
            rows.append(ft.GestureDetector(
                on_tap=lambda _, u=link: webbrowser.open(u),
                content=ft.Text("Read full article →", size=11, color=t["primary"],
                                style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE)),
            ))
        rows += [
            self._divider(),
            ft.Text(clean, size=12, color=t["on_surface2"], selectable=True),
            ft.Container(height=14),
            ft.TextButton(content="Close", on_click=lambda _: self._close_sheet(sheet)),
        ]
        content_col.controls = rows
        self._open_sheet(sheet)

    # ── THEMES ────────────────────────────────────────
    def _show_themes(self, e):
        t      = self._tokens
        custom = load_my_themes()
        active = self._settings.get("theme", "Vanilla")
        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE, controls=[])
        sheet = self._make_sheet(content_col)

        def on_select(name):
            result = apply_theme(name, custom_themes=custom)
            self._settings["theme"] = name
            save_settings(self._settings)
            self._set_status(result, ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, t["accent"])
            self._close_sheet(sheet)

        def tile(name, icon):
            active_tile = (name == active)
            return ft.Container(
                border_radius=8, ink=True,
                bgcolor=t["surface2"] if active_tile else None,
                padding=_pad(vertical=8, horizontal=10),
                on_click=lambda e, n=name: on_select(n),
                content=ft.Row(spacing=0, controls=[
                    ft.Icon(icon, size=14,
                            color=t["primary"] if active_tile else t["on_surface2"]),
                    ft.Container(width=10),
                    ft.Text(name, size=12, color=t["on_surface"],
                            weight=ft.FontWeight.W_600 if active_tile else ft.FontWeight.W_400),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.CHECK_ROUNDED, size=13, color=t["primary"])
                    if active_tile else ft.Container(),
                ]),
            )

        content_col.controls = [
            self._title("THEME GALLERY"),
            ft.Container(height=14),
            self._sec("IMAGE THEMES"), ft.Container(height=6),
            *[tile(n, ft.Icons.IMAGE_OUTLINED) for n in ["Vanilla"] + list(custom.keys())],
            self._divider(),
            self._sec("SOLID COLORS"), ft.Container(height=6),
            *[tile(n, ft.Icons.PALETTE_OUTLINED) for n in INTERNAL_THEMES],
            self._divider(),
            self._sec("CUSTOM THEMES"), ft.Container(height=6),
            ft.FilledButton(content="Add Image Theme",
                            icon=ft.Icons.ADD_PHOTO_ALTERNATE_ROUNDED,
                            on_click=lambda _: self._show_image_upload(sheet)),
            ft.Container(height=10),
            ft.TextButton(content="Close", on_click=lambda _: self._close_sheet(sheet)),
        ]
        self._open_sheet(sheet)

    def _show_image_upload(self, parent_sheet):
        t = self._tokens
        name_f = ft.TextField(
            label="Theme name", border_radius=10, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"], autofocus=True,
        )
        fb      = ft.Text("", size=11, color=t["on_surface2"])
        preview = ft.Container(
            width=80, height=80, border_radius=10,
            bgcolor=t["surface3"], border=_border_all(1, t["outline"]),
            alignment=ft.Alignment(0, 0),
            content=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=28, color=t["on_surface3"]),
        )
        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE, controls=[])
        sheet2 = self._make_sheet(content_col)

        _picked = {"data": None, "filename": ""}

        async def _pick_image(_):
            if not self._file_picker:
                fb.value = "File picker not ready."
                if self.page: self.page.update()
                return
            files = await self._file_picker.pick_files(
                dialog_title="Choose background image",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"],
                allow_multiple=False,
            )
            if not files:
                return
            picked_file = files[0]
            path = picked_file.path
            if not path:
                fb.value = "Could not read file path."
                if self.page: self.page.update()
                return
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                ext = Path(path).suffix.lower().lstrip(".")
                mime = {"jpg": "jpeg", "jpeg": "jpeg"}.get(ext, ext)
                b64 = base64.b64encode(raw).decode("ascii")
                _picked["data"] = f"data:image/{mime};base64,{b64}"
                _picked["filename"] = Path(path).stem
                if not name_f.value:
                    name_f.value = Path(path).stem
                fb.value = f"Loaded: {picked_file.name}  ({len(raw)//1024} KB)"
                fb.color = t["accent"]
                try:
                    img = Image.open(path).convert("RGB").resize((1, 1))
                    r, g, bv = img.getpixel((0, 0))
                    avg_hex = f"#{r:02x}{g:02x}{bv:02x}"
                    preview.bgcolor = avg_hex
                    preview.content = ft.Icon(ft.Icons.CHECK_ROUNDED, size=28, color="#ffffff")
                except Exception:
                    preview.bgcolor = t["primary_cont"]
                    preview.content = ft.Icon(ft.Icons.IMAGE_ROUNDED, size=28, color=t["primary"])
            except Exception as ex:
                fb.value = f"Error reading file: {ex}"
                fb.color = t["error"]
            if self.page: self.page.update()

        def _save(_):
            name = (name_f.value or "").strip()
            if not name:
                fb.value = "Enter a theme name."
                fb.color = t["error"]
                if self.page: self.page.update()
                return
            if not _picked["data"]:
                fb.value = "Pick an image first."
                fb.color = t["error"]
                if self.page: self.page.update()
                return
            ex = load_my_themes()
            ex[name] = _picked["data"]
            save_my_themes(ex)
            fb.value = f"Saved '{name}'! Reopen Themes to apply."
            fb.color = t["accent"]
            if self.page: self.page.update()

        content_col.controls = [
            self._title("ADD CUSTOM THEME"),
            ft.Container(height=10),
            ft.Row(
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    preview,
                    ft.Column(expand=True, spacing=8, tight=True, controls=[
                        name_f,
                        ft.FilledButton(
                            content="Pick Image File",
                            icon=ft.Icons.ADD_PHOTO_ALTERNATE_ROUNDED,
                            on_click=_pick_image,
                        ),
                    ]),
                ],
            ),
            ft.Container(height=8),
            fb,
            ft.Container(height=10),
            ft.Row(spacing=8, controls=[
                ft.FilledButton(content="Save Theme", icon=ft.Icons.SAVE_ROUNDED,
                                on_click=_save),
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
            border_radius=10, bgcolor=t["surface2"],
            border_color=t["outline"], color=t["on_surface"],
            focused_border_color=t["primary"],
        )
        fb = ft.Text("", size=12, color=t["accent"])
        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE, controls=[])
        sheet = self._make_sheet(content_col)

        def save_nick(_):
            nick = (nick_f.value or "").strip()
            self._settings["nickname"] = nick
            save_settings(self._settings)
            if hasattr(self, "_hero_greeting"):
                self._hero_greeting.value = self._make_greeting()
            fb.value = "Saved!" if nick else "Cleared."
            if self.page: self.page.update()

        def swatch(name, preset):
            col    = preset["primary"] if not self._is_light else preset["l_primary"]
            active = (name == self._accent)
            return ft.Container(
                width=32, height=32, border_radius=16, bgcolor=col,
                border=_border_all(3, t["on_surface"] if active else t["outline"]),
                tooltip=name, ink=True,
                on_click=lambda _, n=name: [self._set_accent(n),
                                            self._close_sheet(sheet)],
            )

        content_col.controls = [
            self._title("SETTINGS"),
            ft.Container(height=2),
            ft.Text(f"Member since {self._settings.get('first_seen') or 'today'}",
                    size=11, color=t["on_surface2"]),
            self._divider(),
            self._sec("NICKNAME"), ft.Container(height=6),
            nick_f, ft.Container(height=6),
            ft.FilledButton(content="Save", icon=ft.Icons.SAVE_ROUNDED, on_click=save_nick),
            fb,
            self._divider(),
            self._sec("ACCENT COLOR"), ft.Container(height=8),
            ft.Row(spacing=8, controls=[swatch(n, p) for n, p in ACCENT_PRESETS.items()]),
            self._divider(),
            self._sec("DISPLAY MODE"), ft.Container(height=6),
            ft.Row(spacing=8, controls=[
                ft.FilledButton(content="Dark", icon=ft.Icons.DARK_MODE_ROUNDED,
                                on_click=lambda _: [self._force_mode(False),
                                                    self._close_sheet(sheet)]),
                ft.FilledButton(content="Light", icon=ft.Icons.LIGHT_MODE_ROUNDED,
                                on_click=lambda _: [self._force_mode(True),
                                                    self._close_sheet(sheet)]),
            ]),
            ft.Container(height=14),
            ft.TextButton(content="Close", on_click=lambda _: self._close_sheet(sheet)),
        ]
        self._open_sheet(sheet)

    # ── STATS ─────────────────────────────────────────
    def _show_stats(self, e):
        t = self._tokens
        s = self._settings

        def row(label, value):
            return ft.Container(
                padding=_pad(vertical=8),
                border=_border_bottom(1, t["outline"]),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(label, size=12, color=t["on_surface2"]),
                        ft.Text(str(value), size=12, weight=ft.FontWeight.W_600,
                                color=t["primary"]),
                    ],
                ),
            )

        launches = s.get("launch_count", 0)
        # Find the highest reached milestone for the flavour text
        emoji_m, milestone_title, milestone_body = "⛏️", "Just getting started.", "Keep playing!"
        for thr in sorted(LAUNCH_MILESTONES, reverse=True):
            if launches >= thr:
                emoji_m, milestone_title, milestone_body = LAUNCH_MILESTONES[thr]
                break

        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE, controls=[])
        sheet = self._make_sheet(content_col)
        content_col.controls = [
            self._title("MY STATS"),
            ft.Container(height=10),
            ft.Container(
                border_radius=10, bgcolor=t["surface2"],
                padding=_pad(vertical=10, horizontal=12),
                content=ft.Row(spacing=10, controls=[
                    ft.Text(emoji_m, size=20),
                    ft.Column(expand=True, spacing=2, tight=True, controls=[
                        ft.Text(milestone_title, size=12, weight=ft.FontWeight.W_700,
                                color=t["on_surface"]),
                        ft.Text(milestone_body, size=11, color=t["on_surface2"]),
                    ]),
                ]),
            ),
            ft.Container(height=10),
            row("Player",           s.get("nickname") or "Anonymous"),
            row("Total opens",      launches),
            row("Games launched",   s.get("total_sessions", 0)),
            row("Member since",     s.get("first_seen", "unknown")),
            row("Accent",           s.get("accent", "Blue")),
            row("Mode",             "Light" if self._is_light else "Dark"),
            row("Active version",   s.get("selected_version", "latest")),
            row("Active workspace", self._active_ws_name()),
            ft.Container(height=14),
            ft.TextButton(content="Close", on_click=lambda _: self._close_sheet(sheet)),
        ]
        self._open_sheet(sheet)

    # ── BACKUPS ───────────────────────────────────────
    def _show_backups(self, e=None):
        t = self._tokens

        backup_dest_str = self._settings.get("backup_path", "").strip()
        backup_dest = Path(backup_dest_str) if backup_dest_str else None

        dest_label = ft.Text(
            value=str(backup_dest) if backup_dest else "Not set — choose a folder first",
            size=11,
            color=t["on_surface2"] if backup_dest else t["error"],
            no_wrap=False,
        )

        progress_text = ft.Text("", size=11, color=t["on_surface2"])
        progress_ring = ft.ProgressBar(
            color=t["primary"], bgcolor=t["outline"],
            visible=False, border_radius=2, height=3, value=0,
        )

        backup_list_col = ft.Column(spacing=4, scroll=ft.ScrollMode.ADAPTIVE)
        content_col = ft.Column(tight=True, scroll=ft.ScrollMode.ADAPTIVE, controls=[])
        sheet = self._make_sheet(content_col, height_frac=0.90)

        def refresh_backup_list():
            backup_list_col.controls.clear()
            dest = Path(self._settings.get("backup_path", "").strip()) \
                   if self._settings.get("backup_path", "").strip() else None
            if not dest:
                backup_list_col.controls.append(
                    ft.Text("No backup folder set.", size=11, color=t["on_surface2"])
                )
            else:
                backups = list_backups(dest)
                if not backups:
                    backup_list_col.controls.append(
                        ft.Text("No backups yet.", size=11, color=t["on_surface2"])
                    )
                else:
                    for b in backups:
                        def _open_zip(_, p=b["path"]):
                            self._open_folder(p.parent)
                        backup_list_col.controls.append(ft.Container(
                            border_radius=8, bgcolor=t["surface2"],
                            border=_border_side_left(2, t["primary"]),
                            padding=_pad(vertical=8, horizontal=12),
                            margin=_margin_b(4),
                            ink=True, on_click=_open_zip,
                            tooltip="Click to open containing folder",
                            content=ft.Row(
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Icon(ft.Icons.FOLDER_ZIP_ROUNDED, size=16,
                                            color=t["primary"]),
                                    ft.Container(width=8),
                                    ft.Column(expand=True, spacing=2, tight=True, controls=[
                                        ft.Text(b["mtime"], size=10, color=t["on_surface2"]),
                                        ft.Text(f"{b['size_mb']} MB", size=11,
                                                weight=ft.FontWeight.W_600,
                                                color=t["on_surface"]),
                                    ]),
                                    ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED, size=13,
                                            color=t["on_surface3"]),
                                ],
                            ),
                        ))
            if self.page:
                self.page.update()

        async def _pick_folder(_):
            if not self._file_picker:
                return
            path = await self._file_picker.get_directory_path(
                dialog_title="Choose backup destination folder"
            )
            if path:
                self._settings["backup_path"] = path
                save_settings(self._settings)
                dest_label.value = path
                dest_label.color = t["on_surface2"]
                refresh_backup_list()
                if self.page:
                    self.page.update()

        def _run_backup(_):
            dest_str = self._settings.get("backup_path", "").strip()
            if not dest_str:
                progress_text.value = "Set a backup folder first."
                progress_text.color = t["error"]
                if self.page: self.page.update()
                return

            dest = Path(dest_str)
            cancel_ev = threading.Event()
            progress_ring.visible = True
            progress_ring.value   = 0
            progress_text.value   = "Starting backup..."
            progress_text.color   = t["on_surface2"]
            if self.page: self.page.update()

            def _progress(frac, done, total):
                progress_ring.value = frac
                progress_text.value = f"Backing up… {done}/{total} files"
                if self.page:
                    self.page.update()

            def _do():
                try:
                    zip_path = backup_workspaces(dest, self._workspaces,
                                                 progress_cb=_progress,
                                                 cancel_event=cancel_ev)
                    progress_text.value = f"Backup complete: {zip_path.name}"
                    progress_text.color = t["accent"]
                    refresh_backup_list()
                except InterruptedError:
                    progress_text.value = "Backup cancelled."
                    progress_text.color = t["error"]
                except Exception as ex:
                    progress_text.value = f"Backup failed: {ex}"
                    progress_text.color = t["error"]
                    log(f"[BACKUP ERROR] {ex}")
                finally:
                    progress_ring.visible = False
                    if self.page: self.page.update()

            threading.Thread(target=_do, daemon=True).start()

        refresh_backup_list()

        content_col.controls = [
            self._title("BACKUPS"),
            ft.Container(height=4),
            ft.Container(
                border_radius=10, bgcolor=t["surface2"],
                border=_border_side_left(3, t["primary"]),
                padding=_pad(vertical=10, horizontal=14),
                content=ft.Column(spacing=4, tight=True, controls=[
                    ft.Row(spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                           controls=[
                        ft.Icon(ft.Icons.SHIELD_ROUNDED, size=14, color=t["primary"]),
                        ft.Text("Why backup?", size=12, weight=ft.FontWeight.W_700,
                                color=t["on_surface"]),
                    ]),
                    ft.Text(
                        "Luancher copies all your workspace files — worlds, mods, configs — "
                        "into a .zip at a location you choose. Even if the app breaks, "
                        "your data is safe.",
                        size=11, color=t["on_surface2"],
                    ),
                ]),
            ),
            ft.Container(height=10),
            self._sec("BACKUP DESTINATION"),
            ft.Container(height=6),
            ft.Container(
                border_radius=8, bgcolor=t["surface2"],
                border=_border_all(1, t["outline"]),
                padding=_pad(vertical=8, horizontal=12),
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.FOLDER_ROUNDED, size=14, color=t["on_surface2"]),
                        ft.Container(expand=True, content=dest_label),
                        ft.FilledButton(
                            content="Choose",
                            icon=ft.Icons.DRIVE_FOLDER_UPLOAD_ROUNDED,
                            on_click=_pick_folder,
                        ),
                    ],
                ),
            ),
            ft.Container(height=12),
            progress_ring,
            ft.Container(height=4),
            progress_text,
            ft.Container(height=8),
            ft.FilledButton(
                content="Back Up Now",
                icon=ft.Icons.BACKUP_ROUNDED,
                on_click=_run_backup,
            ),
            self._divider(),
            self._sec("PREVIOUS BACKUPS"),
            ft.Container(height=6),
            backup_list_col,
            ft.Container(height=14),
            ft.TextButton(content="Close", on_click=lambda _: self._close_sheet(sheet)),
        ]

        self._open_sheet(sheet)

    # ── MILESTONE ─────────────────────────────────────
    def _show_milestone(self, msg):
        t = self._tokens
        if isinstance(msg, tuple):
            emoji_str, title, body = msg
        else:
            emoji_str, title, body = "🏆", "Milestone!", str(msg)

        def _close():
            dialog.open = False
            if dialog in self.page.overlay:
                self.page.overlay.remove(dialog)
            if self.page:
                self.page.update()

        dialog = ft.AlertDialog(
            open=True, modal=False,
            content=ft.Column(
                tight=True, width=280,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(emoji_str, size=48, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=4),
                    ft.Text(title, size=15, weight=ft.FontWeight.W_800,
                            color=t["primary"], text_align=ft.TextAlign.CENTER,
                            style=ft.TextStyle(letter_spacing=-0.3)),
                    ft.Container(height=4),
                    ft.Text(body, size=12, color=t["on_surface2"],
                            text_align=ft.TextAlign.CENTER),
                ],
            ),
            actions=[ft.TextButton("Nice.", on_click=lambda _: _close())],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            bgcolor=t["surface"],
            shape=ft.RoundedRectangleBorder(radius=20),
        )
        if self.page:
            self.page.overlay.append(dialog)
            self.page.update()

    # ── FOLDERS ───────────────────────────────────────
    def _open_folder(self, path: Path):
        try:
            path.mkdir(parents=True, exist_ok=True)
            if sys.platform == "darwin":  subprocess.Popen(["open",     str(path)])
            elif sys.platform == "win32": subprocess.Popen(["explorer", str(path)])
            else:                         subprocess.Popen(["xdg-open", str(path)])
        except Exception as ex:
            self._set_status(f"Cannot open: {ex}",
                             ft.Icons.ERROR_OUTLINE_ROUNDED, self._tokens["error"])

    def _open_data(self, e):
        self._open_folder(workspace_data_dir(self._active_ws_name()) / "mods")

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
        page.window.width            = 1060
        page.window.height           = 660
        page.window.min_width        = 820
        page.window.min_height       = 520
        page.window.maximizable      = True
        page.window.full_screen      = False
        page.window.title_bar_hidden = False
    except Exception:
        pass

    ensure_dirs()
    settings   = load_settings()
    workspaces = load_workspaces()

    settings["launch_count"] = settings.get("launch_count", 0) + 1
    if not settings.get("first_seen"):
        settings["first_seen"] = datetime.date.today().isoformat()
    save_settings(settings)

    active_ws = settings.get("active_workspace", "Default")
    if active_ws not in workspaces:
        settings["active_workspace"] = "Default"
        save_settings(settings)
    ensure_workspace(settings.get("active_workspace", "Default"))

    launcher = Launcher(settings, workspaces)

    saved_theme = settings.get("theme", "Vanilla")
    if saved_theme and saved_theme != "Vanilla":
        threading.Thread(
            target=lambda: apply_theme(saved_theme, custom_themes=load_my_themes()),
            daemon=True,
        ).start()

    page.add(launcher)

    # Register FilePicker
    _file_picker = ft.FilePicker()
    try:
        page.services.append(_file_picker)
    except AttributeError:
        page._services.append(_file_picker)
    launcher._file_picker = _file_picker
    page.update()

    threading.Thread(target=launcher.load_news, daemon=True).start()

    # Greeting fade-in
    def _trigger_greeting_fade():
        import time; time.sleep(0.15)
        if launcher.page and hasattr(launcher, "_hero_greeting_wrap"):
            launcher._hero_greeting_wrap.opacity = 1
            launcher.page.update()
    threading.Thread(target=_trigger_greeting_fade, daemon=True).start()

    # Auto-backup every 3 days
    def _maybe_auto_backup():
        import time; time.sleep(1.5)
        backup_path = settings.get("backup_path", "").strip()
        if not backup_path:
            return
        last_str = settings.get("last_auto_backup", "")
        try:
            last_date = datetime.date.fromisoformat(last_str) if last_str else None
        except ValueError:
            last_date = None
        today = datetime.date.today()
        if last_date and (today - last_date).days < 3:
            return
        try:
            dest = Path(backup_path)
            zip_path = backup_workspaces(dest, launcher._workspaces)
            settings["last_auto_backup"] = today.isoformat()
            save_settings(settings)
            if launcher.page:
                launcher._set_status(
                    f"Auto-backup saved: {zip_path.name}",
                    ft.Icons.BACKUP_ROUNDED,
                    launcher._tokens["accent"],
                )
                launcher.page.update()
                time.sleep(5)
                launcher._set_status("")
                if launcher.page:
                    launcher.page.update()
        except Exception as ex:
            if launcher.page:
                launcher._set_status(
                    f"Auto-backup failed: {ex}",
                    ft.Icons.ERROR_OUTLINE_ROUNDED,
                    launcher._tokens["error"],
                )
                launcher.page.update()
    threading.Thread(target=_maybe_auto_backup, daemon=True).start()

    # Backup reminder (shown once if no backup path is set)
    if settings.get("backup_reminder", True) and not settings.get("backup_path", "").strip():
        def _show_backup_reminder():
            t = launcher._tokens
            dont_show_cb = ft.Checkbox(
                label="Don't show this again",
                value=False,
                label_style=ft.TextStyle(size=11, color=t["on_surface2"]),
            )

            def _close_dialog():
                dialog.open = False
                page.update()

            def _dismiss(_):
                if dont_show_cb.value:
                    settings["backup_reminder"] = False
                    save_settings(settings)
                _close_dialog()

            def _go_backup(_):
                if dont_show_cb.value:
                    settings["backup_reminder"] = False
                    save_settings(settings)
                _close_dialog()
                launcher._show_backups()

            dialog = ft.AlertDialog(
                open=True,
                modal=True,
                title=ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.BACKUP_ROUNDED, color=t["primary"], size=22),
                    ft.Text("Back Up Your Worlds", size=15, weight=ft.FontWeight.W_700,
                            color=t["on_surface"]),
                ]),
                content=ft.Column(tight=True, width=380, controls=[
                    ft.Text(
                        "Luancher stores all your worlds, mods, and server configs "
                        "inside its own folder. If the app breaks, your drive fails, "
                        "or you accidentally delete something, that data is gone.",
                        size=12, color=t["on_surface2"],
                    ),
                    ft.Container(height=10),
                    ft.Container(
                        border_radius=8,
                        bgcolor=t["surface2"],
                        border=_border_side_left(3, t["primary"]),
                        padding=_pad(vertical=8, horizontal=12),
                        content=ft.Column(spacing=5, tight=True, controls=[
                            ft.Row(spacing=6, controls=[
                                ft.Icon(ft.Icons.FOLDER_ZIP_ROUNDED, size=13, color=t["primary"]),
                                ft.Text("What gets backed up:", size=11,
                                        weight=ft.FontWeight.W_700, color=t["on_surface"]),
                            ]),
                            ft.Text(
                                "• All worlds from every workspace\n"
                                "• All installed mods\n"
                                "• Texture packs and configs\n"
                                "• Server favorites list\n"
                                "• Your Luancher settings",
                                size=11, color=t["on_surface2"],
                            ),
                        ]),
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Backups are saved as a single .zip to any folder you choose — "
                        "an external drive, cloud sync folder, or anywhere outside Luancher.",
                        size=11, color=t["on_surface2"], italic=True,
                    ),
                    ft.Container(height=10),
                    dont_show_cb,
                ]),
                actions=[
                    ft.TextButton("Maybe Later", on_click=_dismiss),
                    ft.FilledButton(
                        "Set Up Backups",
                        icon=ft.Icons.BACKUP_ROUNDED,
                        on_click=_go_backup,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
                bgcolor=t["surface"],
                shape=ft.RoundedRectangleBorder(radius=22),
            )
            page.overlay.append(dialog)
            page.update()

        def _delayed():
            import time; time.sleep(0.6)
            if launcher.page:
                _show_backup_reminder()
        threading.Thread(target=_delayed, daemon=True).start()


if __name__ == "__main__":
    ft.run(main)
