# 🚀 Luancher
The modern, high-performance launcher for **Luanti**.

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
## Notice
Luancher currently doesn't have any official binaries. To run Luancher, download the source code, and then do:
`python3 -m venv .luancher`
`source luancher/bin/activate`
`pip install flet requests feedparser`
`python3 updater.py`
---
*Made with passion in Ukraine*
