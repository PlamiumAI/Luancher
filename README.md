# 🚀 Luancher
The modern, high-performance launcher for **Luanti**.|

## 🖼️ Screenshots (New)
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/b41b06e3-10b7-4e42-8346-50498df38858" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/58fb8e7b-c784-48be-8f27-4598d471767d" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/e07a4625-9f1e-463f-a68e-298de2b1a533" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/f06c4db9-96d4-42ce-8419-4ba00e5a9957" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/5529e949-898c-4cae-b58b-cf4d47b5056a" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/4f04d69e-6824-4e62-ae8d-683059799895" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/7b2855c9-976e-450c-a8bb-c3d56e0901cd" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/d597fa6f-b43b-4c56-9cde-3b365351c570" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/d810fc59-db03-4fb8-87c3-ee26e695f1ce" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/e1ef97db-4ab7-45a5-80c1-dca5ac0848c0" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/4c95e161-7d41-40e5-8a75-e8b8c524f542" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/867688fa-68d6-438f-b8c9-4bb802b33daf" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/a87ae289-bc27-48bc-92b9-fa21e5929a02" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/b1bbd346-909f-4039-83bd-ee7d1dca7941" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/f8348e4e-df2c-4389-8224-f1809a70add0" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/5d7be264-0577-44d3-bf5d-f7b89920cc95" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/7b42c921-6154-4654-8545-10bf62ffa982" />

## 🖼️ Screenshots (Old)
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/5d53b1a0-1b84-4eec-a186-87dc511d1510" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/79de8ebe-0353-43f5-a345-4aa2a28a0934" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/6733918b-b8d5-4e1b-8900-c11365dde436" />
<img width="1920" height="1001" alt="image" src="https://github.com/user-attachments/assets/b4bd3c92-66e0-437e-bbdd-4cfffa3109c3" />

## 📖 About Luancher
Luancher’s purpose is to be a launcher for Luanti, letting you manage versions and data easily.

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
## In the near future, we plan to make an installer, but currently, the process is manual.
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
