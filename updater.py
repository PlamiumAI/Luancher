import requests
import sys
import subprocess
import os
import shutil
import platform
import hashlib

# --- CONFIG ---
RAW_URL = "https://raw.githubusercontent.com/PlamiumAI/Luancher/main/main.py"
UPDATER_URL = "https://raw.githubusercontent.com/PlamiumAI/Luancher/main/updater.py"
HASH_URL = "https://raw.githubusercontent.com/PlamiumAI/Luancher/main/updater.py" 

# --- ANSI COLORS ---
CLR = "\033[0m"
BOLD = "\033[1m"
BLUE_BG = "\033[44m"
WHITE_FG = "\033[97m"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
YELLOW = "\033[93m"

# Check if debugger or noupdate mode is active
IS_DEBUG = "--debugger" in sys.argv
SKIP_UPDATE = "--noupdate" in sys.argv

def get_file_hash(filepath):
    """Generates SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def debug_log(msg, cmd_output=None):
    """Prints raw process logs instead of drawing a GUI."""
    print(f"{CYAN}[DEBUG]{CLR} {msg}")
    if cmd_output:
        print(f"{DIM}{cmd_output}{CLR}")

def draw_ui(status, progress_val):
    if IS_DEBUG:
        debug_log(f"Status: {status} ({progress_val}%)")
        return

    os.system('clear' if os.name == 'posix' else 'cls')
    width = 64
    print(f"{BLUE_BG}{WHITE_FG}{' ' * width}{CLR}")
    print(f"{BLUE_BG}{WHITE_FG}{'LUANCHER BOOTLOADER'.center(width)}{CLR}")
    print(f"{BLUE_BG}{WHITE_FG}{' ' * width}{CLR}\n")
    
    logo = r"""
    __    __  __  ___    _   __  ______ __  __  ______  ____ 
   / /    / / / / /   |  / | / / / ____// / / / / ____/ / __ \
  / /    / / / / / /| | /  |/ / / /    / /_/ / / __/   / /_/ /
 / /___/ /_/ / / ___ |/ /|  / / /___ / __  / / /___  / _, _/ 
/_____/\____/ /_/  |_/_/ |_/  \____//_/ /_/ /_____/ /_/ |_|  
    """
    print(f"{CYAN}{logo}{CLR}")
    
    bar_width = 40
    filled = int(bar_width * (progress_val / 100))
    bar = f"{GREEN}{'█' * filled}{CLR}{DIM}{'░' * (bar_width - filled)}{CLR}"
    
    print(f"\n {BOLD}PRE-FLIGHT SYSTEM CHECKS:{CLR}")
    print(f" ┌────────────────────────────────────────────────────────────┐")
    print(f" │ {status[:58]:<58} │")
    print(f" └────────────────────────────────────────────────────────────┘")
    print(f"\n Progress: [{bar}] {progress_val}%")

def self_update():
    """Checks if the local updater differs from the remote version via hashing."""
    if SKIP_UPDATE:
        return

    draw_ui("Checking for Bootloader updates...", 0)
    try:
        code_resp = requests.get(UPDATER_URL, timeout=10)
        if code_resp.status_code != 200:
            return

        remote_code = code_resp.content
        remote_hash = hashlib.sha256(remote_code).hexdigest()
        local_hash = get_file_hash(__file__)

        if remote_hash != local_hash:
            draw_ui("Local Bootloader differs. Synchronizing...", 2)
            
            target_file = __file__
            tmp_file = target_file + ".tmp"
            
            with open(tmp_file, "wb") as f:
                f.write(remote_code)
            
            os.rename(tmp_file, target_file)
            os.chmod(target_file, 0o755)
            
            draw_ui("Bootloader updated. Restarting...", 5)
            os.execv(sys.executable, [sys.executable] + sys.argv)
                
    except Exception as e:
        if IS_DEBUG: debug_log(f"Self-update hash check failed: {e}")

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
    # Add Python Imaging Library system headers for Linux if needed
    if platform.system() == "Linux":
        name, _ = get_package_manager()
        if name == "apt":
            deps.append("libjpeg-dev")
            deps.append("zlib1g-dev")

    missing = [d for d in deps if not check_sys_dependency(d)]
    
    if not missing:
        return True, "All system tools present."

    name, cmd = get_package_manager()
    if not name:
        return False, "No package manager found. Install build tools manually."

    draw_ui(f"Missing {missing}. Requesting sudo to install...", 15)
    
    pkg_map = {"g++": "build-essential"} if name == "apt" else {}
    install_list = [pkg_map.get(m, m) for m in missing]
    
    try:
        full_cmd = cmd.split() + install_list
        subprocess.check_call(full_cmd, stdout=sys.stdout if IS_DEBUG else subprocess.DEVNULL)
        return True, f"Installed {', '.join(missing)} via {name}."
    except subprocess.CalledProcessError:
        return False, "Failed to install system dependencies."

def main():
    self_update()

    if IS_DEBUG:
        print(f"{YELLOW}!!! DEBUGGER MODE ACTIVE !!!{CLR}")
        print(f"System: {platform.system()} {platform.release()}\n")

    # Phase 1: System Tools
    draw_ui("Detecting OS and System Dependencies...", 5)
    success, msg = install_system_deps()
    if not success:
        draw_ui(f"{RED}SYSTEM ERR: {msg}{CLR}", 20)
        input("Press Enter to try continuing anyway...")
    else:
        draw_ui(msg, 30)

    # Phase 2: Python Libs
    draw_ui("Verifying Python environment...", 50)
    libraries = ["flet", "requests", "feedparser", "Pillow"]
    
    # Ensure pip itself is available
    try:
        import pip
    except ImportError:
        draw_ui("Pip missing. Attempting to bootstrap pip...", 55)
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--default-pip"])

    try:
        draw_ui(f"Syncing libraries: {', '.join(libraries)}", 60)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + libraries, 
                              stdout=sys.stdout if IS_DEBUG else subprocess.DEVNULL, 
                              stderr=subprocess.STDOUT)
        draw_ui("Python libraries verified.", 65)
    except Exception as e:
        draw_ui(f"{RED}Pip Sync Failed. Build might crash.{CLR}", 65)
        if IS_DEBUG: debug_log(f"Pip Error: {e}")

    # Phase 3: main.py Sync
    if SKIP_UPDATE:
        draw_ui("Update skipped.", 80)
    else:
        draw_ui("Fetching latest main.py...", 80)
        try:
            response = requests.get(RAW_URL, timeout=5)
            if response.status_code == 200:
                with open("main.py", "w") as f:
                    f.write(response.text)
                draw_ui("Main logic synchronized.", 90)
        except Exception as e:
            draw_ui("Offline Mode: Using cached main.py.", 90)

    # Phase 4: Handover
    draw_ui("Handshake authorized. Starting...", 100)
    try:
        env = os.environ.copy()
        env["LUANCHER_BOOTED"] = "TRUE"
        
        if IS_DEBUG:
            subprocess.run([sys.executable, "main.py", "--debugger"], env=env)
        else:
            subprocess.Popen([sys.executable, "main.py"], env=env)
            sys.exit(0)
            
    except Exception as e:
        print(f"\n{RED}Critical Handover Failure: {e}{CLR}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}Boot cancelled.{CLR}")
        sys.exit(1)