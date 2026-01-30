# 🚀 Luancher
The modern, high-performance launcher for **Luanti**.
## 🖼️ Screenshots
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/5d53b1a0-1b84-4eec-a186-87dc511d1510" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/79de8ebe-0353-43f5-a345-4aa2a28a0934" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/6733918b-b8d5-4e1b-8900-c11365dde436" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/b4bd3c92-66e0-437e-bbdd-4cfffa3109c3" />

## 📖 About Luancher
Published on **January 28, 2026**.  
Luancher’s purpose is to provide a modern interface for Luanti, handling updates and maintenance so you can focus on the gameplay.

## ⚠️ Stability & Support
**Use at your own risk.** Luancher is stable on my machine, but bugs exist everywhere.  
* **OS Support:** 🐧 Linux Only (Tested on Ubuntu 25.10).
* **Note:** Windows and macOS are not supported due to fundamental architectural differences.

## ❓ What is a "Luancher"?
It’s a portmanteau of **Luanti** + **Launcher**. Simple, clean, and unique.

## ✨ Key Features
* **Modern UI:** Built with **Python + Flet** for a sleek, responsive experience.
* **Auto-Updates:** Never manually download a `.tar.gz` again. Whether it's 5.16.0 or beyond, Luancher handles it.
* **Integrated News:** Stay updated with the official Luanti blogpost RSS feed right in your sidebar.
* **Theme Engine:** One-click menu background injection. Switch between *Cyberpunk*, *Retro Terminal*, and more without digging through file directories.

## ⬇️ Installation guide (Linux only, for now, unfortunately)

To run Luancher and build the Luanti engine, you must install the core system dependencies, clone the repository, set up a virtual environment, and initialize the project.

### 1. System Dependencies
Run the command corresponding to your Linux distribution to install the necessary compilers and development libraries.

**Debian / Ubuntu / Mint:**
``
sudo apt update && sudo apt install -y g++ make libc6-dev cmake libpng-dev libjpeg-dev libgl1-mesa-dev libsqlite3-dev libogg-dev libvorbis-dev libopenal-dev libcurl4-gnutls-dev libfreetype6-dev zlib1g-dev libgmp-dev libjsoncpp-dev libzstd-dev libluajit-5.1-dev gettext libsdl2-dev python3-venv git
``

**Arch Linux:**
``
sudo pacman -S --needed base-devel cmake libpng libjpeg-turbo mesa sqlite libogg libvorbis openal curl freetype2 zlib gmp jsoncpp zstd luajit gettext sdl2 git
``

**Fedora:**
``
sudo dnf install make gcc-c++ cmake libpng-devel libjpeg-turbo-devel mesa-libGL-devel sqlite-devel libogg-devel libvorbis-devel openal-soft-devel libcurl-devel freetype-devel zlib-devel gmp-devel jsoncpp-devel zstd-devel luajit-devel gettext-devel SDL2-devel git
``

**openSUSE (Tumbleweed/Leap):**
``
sudo zypper install gcc-c++ cmake libpng16-devel libjpeg8-devel mesa-libGL-devel sqlite3-devel libogg-devel libvorbis-devel libopenal1-devel libcurl-devel freetype2-devel zlib-devel libgmp-devel libjsoncpp-devel libzstd-devel luajit-devel gettext-runtime SDL2-devel git
``

**Void Linux:**
``
sudo xbps-install -S base-devel cmake libpng-devel libjpeg-turbo-devel MesaLib-devel sqlite-devel libogg-devel libvorbis-devel openal-soft-devel libcurl-devel freetype-devel zlib-devel gmp-devel jsoncpp-devel libzstd-devel LuaJIT-devel gettext SDL2-devel python3-venv git
``

**Alpine Linux:**
``
apk add build-base cmake libpng-dev libjpeg-turbo-dev mesa-dev sqlite-dev libogg-dev libvorbis-dev openal-soft-dev curl-dev freetype-dev zlib-dev gmp-dev jsoncpp-dev zstd-dev luajit-dev gettext-dev sdl2-dev python3 py3-pip git
``

### 2. Clone and Environment Setup
Clone the repository and initialize a virtual environment (`venv`) to keep your system clean.

# Clone the repository
``
git clone https://github.com/PlamiumAI/Luancher.git && cd Luancher
``
# Create and activate the virtual environment
``
python3 -m venv venv
``
``
source venv/bin/activate
``

### 3. Python Dependencies
With the virtual environment active, install the required libraries for the UI, networking, and theme engine.

``
pip install flet Pillow requests feedparser
``

### 4. Initialization
Run the updater to sync the engine source code and prepare the environment for the first launch.

``
python3 updater.py
``




*Made with passion in Ukraine*
