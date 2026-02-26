import requests
import sys
import subprocess
import os
import shutil
import platform
import hashlib
import time
import threading

# --- CONFIG ---
RAW_URL = "https://raw.githubusercontent.com/PlamiumAI/Luancher/main/main.py"
UPDATER_URL = "https://raw.githubusercontent.com/PlamiumAI/Luancher/main/updater.py"
VERSION_URL = "https://raw.githubusercontent.com/PlamiumAI/Luancher/main/version.txt"

LOCAL_VERSION_FILE = os.path.join(os.path.dirname(__file__), ".luancher_version")

# --- ANSI COLORS ---
CLR = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
YELLOW = "\033[93m"
WHITE = "\033[97m"
BLUE = "\033[94m"
GREY = "\033[90m"

IS_DEBUG = "--debugger" in sys.argv
SKIP_UPDATE = "--noupdate" in sys.argv

# ─────────────────────────────────────────────
# SPINNER
# ─────────────────────────────────────────────

_spinner_active = False
_spinner_thread = None
_spinner_chars = ['\\', '|', '/', '—']

def _spinner_loop(label_ref):
    i = 0
    while _spinner_active:
        char = _spinner_chars[i % len(_spinner_chars)]
        sys.stdout.write(f"\r{CYAN}[Luancher]{CLR} {char} {label_ref[0]}{' ' * 10}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1

def start_spinner(label):
    global _spinner_active, _spinner_thread
    _spinner_active = True
    label_ref = [label]
    _spinner_thread = threading.Thread(target=_spinner_loop, args=(label_ref,), daemon=True)
    _spinner_thread.start()
    return label_ref

def update_spinner(label_ref, new_label):
    label_ref[0] = new_label

def stop_spinner(final_msg=None, ok=True):
    global _spinner_active
    _spinner_active = False
    if _spinner_thread:
        _spinner_thread.join(timeout=0.3)
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    if final_msg:
        icon = f"{GREEN}✓{CLR}" if ok else f"{RED}✗{CLR}"
        print(f"{CYAN}[Luancher]{CLR} {icon} {final_msg}")

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

def info(msg):
    print(f"{CYAN}[Luancher]{CLR}   {msg}")

def success(msg):
    print(f"{CYAN}[Luancher]{CLR} {GREEN}✓{CLR} {msg}")

def warn(msg):
    print(f"{CYAN}[Luancher]{CLR} {YELLOW}!{CLR} {msg}")

def error(msg):
    print(f"{CYAN}[Luancher]{CLR} {RED}✗{CLR} {msg}")

def debug(msg):
    if IS_DEBUG:
        print(f"{GREY}[DEBUG] {msg}{CLR}")

def divider():
    print(f"{GREY}{'─' * 52}{CLR}")

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

def print_header():
    os.system('clear' if os.name == 'posix' else 'cls')
    print()
    print(f"  {BOLD}{CYAN}LUANCHER{CLR}  {GREY}Bootloader v2{CLR}")
    divider()
    if IS_DEBUG:
        print(f"  {YELLOW}⚠  DEBUGGER MODE ACTIVE{CLR}")
        print(f"  {GREY}System: {platform.system()} {platform.release()}{CLR}")
        divider()
    print()

# ─────────────────────────────────────────────
# VERSION TRACKING
# ─────────────────────────────────────────────

def get_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def read_local_version():
    if os.path.exists(LOCAL_VERSION_FILE):
        try:
            with open(LOCAL_VERSION_FILE, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    return None

def write_local_version(version_hash):
    try:
        with open(LOCAL_VERSION_FILE, "w") as f:
            f.write(version_hash)
    except Exception as e:
        debug(f"Could not write version file: {e}")

# ─────────────────────────────────────────────
# SELF UPDATE (Updater itself)
# ─────────────────────────────────────────────

def self_update():
    if SKIP_UPDATE:
        return

    lbl = start_spinner("Checking bootloader for updates...")
    try:
        resp = requests.get(UPDATER_URL, timeout=10)
        if resp.status_code != 200:
            stop_spinner("Could not reach update server. Continuing offline.", ok=False)
            return

        remote_hash = hashlib.sha256(resp.content).hexdigest()
        local_hash = get_file_hash(__file__)
        debug(f"Local hash:  {local_hash[:16]}...")
        debug(f"Remote hash: {remote_hash[:16]}...")

        if remote_hash == local_hash:
            stop_spinner("Bootloader is up to date.")
        else:
            update_spinner(lbl, "Bootloader update found. Applying patch...")
            tmp = __file__ + ".tmp"
            with open(tmp, "wb") as f:
                f.write(resp.content)
            os.rename(tmp, __file__)
            os.chmod(__file__, 0o755)
            stop_spinner("Bootloader updated. Restarting...")
            time.sleep(0.4)
            os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as e:
        stop_spinner(f"Self-update skipped: {e}", ok=False)
        debug(str(e))

# ─────────────────────────────────────────────
# MAIN.PY SMART SYNC
# ─────────────────────────────────────────────

def sync_main():
    """
    Smart sync: fetch remote version hash first (lightweight).
    Only download main.py if the hash differs from what we have stored.
    Falls back to full hash comparison if no version.txt exists remotely.
    """
    if SKIP_UPDATE:
        info("Update skipped (--noupdate).")
        return

    lbl = start_spinner("Checking for app updates...")

    try:
        # Step 1: Try to get a lightweight remote version tag first
        remote_version = None
        try:
            vresp = requests.get(VERSION_URL, timeout=6)
            if vresp.status_code == 200:
                remote_version = vresp.text.strip()
                debug(f"Remote version tag: {remote_version}")
        except Exception:
            pass

        local_version = read_local_version()
        debug(f"Local version tag: {local_version}")

        if remote_version and local_version == remote_version:
            # Versions match — no need to download anything
            stop_spinner("App is already up to date.")
            return

        # Step 2: If version tags unavailable or differ, download and hash-check
        update_spinner(lbl, "Fetching latest app release...")
        resp = requests.get(RAW_URL, timeout=15)
        if resp.status_code != 200:
            stop_spinner("Could not reach update server. Using cached version.", ok=False)
            return

        remote_content = resp.content
        remote_hash = hashlib.sha256(remote_content).hexdigest()

        # Check against locally stored hash if we don't have a version tag
        if not remote_version:
            local_hash_stored = local_version  # fallback: version file stores hash
            if local_hash_stored == remote_hash:
                stop_spinner("App is already up to date.")
                write_local_version(remote_hash)
                return

        # Step 3: Write new main.py
        update_spinner(lbl, "Applying update...")
        tmp = "main.py.tmp"
        with open(tmp, "wb") as f:
            f.write(remote_content)
        os.replace(tmp, "main.py")

        # Store version identifier
        write_local_version(remote_version if remote_version else remote_hash)

        stop_spinner("App updated successfully.")

    except requests.exceptions.ConnectionError:
        stop_spinner("Offline. Using cached main.py.", ok=False)
    except Exception as e:
        stop_spinner(f"Update failed: {e}", ok=False)
        debug(str(e))

# ─────────────────────────────────────────────
# SYSTEM DEPS
# ─────────────────────────────────────────────

def check_sys_dependency(cmd):
    return shutil.which(cmd) is not None

def get_package_manager():
    managers = {
        "apt": "sudo apt-get install -y",
        "dnf": "sudo dnf install -y",
        "pacman": "sudo pacman -S --noconfirm",
        "brew": "brew install"
    }
    for name, cmd in managers.items():
        if shutil.which(name):
            return name, cmd
    return None, None

def install_system_deps():
    deps = ["git", "cmake", "gcc", "g++", "make"]
    if platform.system() == "Linux":
        name, _ = get_package_manager()
        if name == "apt":
            deps += ["libjpeg-dev", "zlib1g-dev"]

    missing = [d for d in deps if not check_sys_dependency(d)]

    if not missing:
        success("System tools verified.")
        return True

    name, cmd = get_package_manager()
    if not name:
        error("No package manager found. Install build tools manually.")
        return False

    lbl = start_spinner(f"Installing missing tools: {', '.join(missing)}")
    pkg_map = {"g++": "build-essential"} if name == "apt" else {}
    install_list = [pkg_map.get(m, m) for m in missing]

    try:
        full_cmd = cmd.split() + install_list
        subprocess.check_call(
            full_cmd,
            stdout=sys.stdout if IS_DEBUG else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        stop_spinner(f"Installed: {', '.join(missing)}")
        return True
    except subprocess.CalledProcessError:
        stop_spinner(f"Failed to install: {', '.join(missing)}", ok=False)
        return False

# ─────────────────────────────────────────────
# PYTHON DEPS
# ─────────────────────────────────────────────

def sync_python_libs():
    libraries = ["flet", "requests", "feedparser", "Pillow"]
    lbl = start_spinner("Syncing Python libraries...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade"] + libraries,
            stdout=sys.stdout if IS_DEBUG else subprocess.DEVNULL,
            stderr=subprocess.STDOUT
        )
        stop_spinner("Python environment ready.")
    except Exception as e:
        stop_spinner("Pip sync failed. App might crash.", ok=False)
        debug(str(e))

# ─────────────────────────────────────────────
# LAUNCH
# ─────────────────────────────────────────────

def launch_app():
    lbl = start_spinner("Starting Luancher...")
    time.sleep(0.3)
    stop_spinner("Handshake authorized. Launching...")
    print()

    env = os.environ.copy()
    env["LUANCHER_BOOTED"] = "TRUE"

    try:
        if IS_DEBUG:
            subprocess.run([sys.executable, "main.py", "--debugger"], env=env)
        else:
            subprocess.Popen([sys.executable, "main.py"], env=env)
            sys.exit(0)
    except Exception as e:
        error(f"Critical handover failure: {e}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print_header()

    # Phase 0: Self-update the bootloader
    self_update()

    # Phase 1: System tools
    info("Running pre-flight checks...")
    print()
    ok = install_system_deps()
    if not ok:
        warn("Missing system tools. Build may fail.")
        try:
            input(f"  {GREY}Press Enter to continue anyway...{CLR}")
        except KeyboardInterrupt:
            pass
    print()

    # Phase 2: Python libs
    sync_python_libs()
    print()

    # Phase 3: Smart main.py sync
    sync_main()
    print()

    divider()

    # Phase 4: Launch
    launch_app()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{GREY}[Luancher]{CLR} {RED}Boot cancelled.{CLR}\n")
        sys.exit(1)
