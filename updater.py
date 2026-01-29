import requests
import sys
import subprocess
import os
import shutil
import platform

# --- CONFIG ---
RAW_URL = "https://raw.githubusercontent.com/PlamiumAI/Luancher/main/main.py"

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

# Check if debugger mode is active
IS_DEBUG = "--debugger" in sys.argv

def debug_log(msg, cmd_output=None):
    """Prints raw process logs instead of drawing a GUI."""
    print(f"{CYAN}[DEBUG]{CLR} {msg}")
    if cmd_output:
        print(f"{DIM}{cmd_output}{CLR}")

def draw_ui(status, progress_val):
    # If debugger is on, we skip the fancy UI and just print a log line
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
    missing = [d for d in deps if not check_sys_dependency(d)]
    
    if not missing:
        return True, "All system tools present."

    name, cmd = get_package_manager()
    if not name:
        return False, "No known package manager found. Install git/cmake manually."

    draw_ui(f"Missing {missing}. Requesting sudo to install...", 15)
    
    pkg_map = {"g++": "build-essential"} if name == "apt" else {}
    install_list = [pkg_map.get(m, m) for m in missing]
    
    try:
        full_cmd = cmd.split() + install_list
        # If debug is on, show the real-time installation output
        subprocess.check_call(full_cmd, stdout=sys.stdout if IS_DEBUG else subprocess.DEVNULL)
        return True, f"Installed {', '.join(missing)} via {name}."
    except subprocess.CalledProcessError:
        return False, "Failed to install system dependencies."

def main():
    if IS_DEBUG:
        print(f"{YELLOW}!!! DEBUGGER MODE ACTIVE !!!{CLR}")
        print(f"System: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}\n")

    # 1. OS & System Tool Phase
    draw_ui("Detecting OS and System Dependencies...", 5)
    success, msg = install_system_deps()
    if not success:
        draw_ui(f"{RED}SYSTEM ERR: {msg}{CLR}", 20)
        print(f"\n{YELLOW}Wait! We couldn't auto-install tools. GUI might fail to build Luanti.{CLR}")
        input("Press Enter to try continuing anyway...")
    else:
        draw_ui(msg, 30)

    # 2. Python Library Phase (The "Pip Sync")
    draw_ui("Verifying Python environment (flet, requests...)", 50)
    libraries = ["flet", "requests", "feedparser"]
    try:
        # If debugging, let the user see the pip output
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + libraries, 
                              stdout=sys.stdout if IS_DEBUG else subprocess.DEVNULL, 
                              stderr=sys.STDOUT if IS_DEBUG else subprocess.STDOUT)
        draw_ui("Python libraries verified.", 65)
    except Exception as e:
        draw_ui(f"{RED}Pip Sync Failed. Check internet connection.{CLR}", 65)
        if IS_DEBUG: print(f"Pip Error: {e}")

    # 3. Update Phase
    draw_ui("Fetching latest main.py from GitHub...", 80)
    try:
        import requests 
        response = requests.get(RAW_URL, timeout=5)
        if response.status_code == 200:
            with open("main.py", "w") as f:
                f.write(response.text)
            draw_ui("Synchronized with Remote: [v2.0-STABLE]", 90)
        else:
            draw_ui(f"Update server busy (Code {response.status_code}).", 90)
    except Exception as e:
        draw_ui("Offline Mode: Launching cached version.", 90)
        if IS_DEBUG: print(f"Network Error: {e}")

    # 4. Handover
    draw_ui("Handshake authorized. Starting Luancher...", 100)
    try:
        env = os.environ.copy()
        env["LUANCHER_BOOTED"] = "TRUE"
        
        # In debugger mode, we pass the flag down to main.py as well
        launch_cmd = [sys.executable, "main.py"]
        if IS_DEBUG:
            launch_cmd.append("--debugger")
            debug_log(f"Spawning child: {' '.join(launch_cmd)}")
            # In debug mode, we wait for the process so we can see its output
            subprocess.run(launch_cmd, env=env)
        else:
            subprocess.Popen([sys.executable, "main.py"], env=env)
            sys.exit(0)
            
    except Exception as e:
        print(f"\n{RED}Critical Handover Failure: {e}{CLR}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}Boot cancelled by user.{CLR}")
        sys.exit(1)