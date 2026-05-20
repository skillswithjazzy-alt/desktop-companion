# 🖥️ DesktopMate — Animated Desktop Companion

> A lightweight animated desktop companion that lives on your screen, walks edge to edge, and uses under 50MB of RAM. Fully custom character. No launcher. Auto starts on boot. Completely free.

![DesktopMate Demo](demo.gif)

---

## ✨ What is this?

DesktopMate is a transparent always-on-top desktop companion built in Python. Your character walks across your screen, reacts when you pick her up, and starts automatically every time you boot your PC.

No heavy launcher. No DLC paywalls. No bloat. Just your character living on your desktop.

---

## 🚀 Quick Start

### Option 1 — Download the EXE (recommended)
No Python required. No setup. Nothing.

1. Download `desktop_mate.exe` from the [Releases](../../releases) page
2. Double click it
3. First launch asks for your spritesheet and character name
4. Done — she appears on your desktop immediately

> Every launch after that she loads automatically. No dialog.

### Option 2 — Run from source
```bash
# Clone the repo
git clone https://github.com/skillswithjazzy-alt/desktop-companion

# Install dependencies
pip install pillow keyboard

# Run
python desktop_mate.py
```

---

## 🎨 Getting Your Character

You need a spritesheet — a single image with every animation frame laid out in a grid.

**Step 1 — Generate your character**
Go to [Nano Banana](https://nanobanana.ai) and generate an anime character with a plain white background.

**Step 2 — Remove the background**
Upload to [remove.bg](https://remove.bg) — free, takes 5 seconds.

**Step 3 — Animate it**
Upload to [Ludo.ai](https://app.ludo.ai), select a walking motion, set your FPS, and export the spritesheet.

**Step 4 — Add to the app**
When the app launches for the first time it asks for your spritesheet path and grid size. That's it.

> Don't have a character? Use mine — she's in the `default_sprites` folder.

---

## 🎮 Controls

| Action | Result |
|--------|--------|
| **Drag** | Move character around |
| **Right-click** | Open menu |
| **Ctrl+Shift+H** | Hide / show all characters |

### Right-click menu
- 🔍 Enlarge / 🔎 Shrink / 📐 Reset size
- ⏸ Pause / ▶️ Resume walking
- ➕ Add another character
- 🔄 Change spritesheet
- 🔁 Flip walking direction
- ✕ Hide (session only)
- 🗑 Remove permanently

---

## ⚙️ Adding to Startup (Windows)

So she appears automatically every time you boot:

1. Press `Win + R`
2. Type `shell:startup` and hit Enter
3. Create a shortcut of `desktop_mate.exe` and drop it in the folder

Done. She'll be waiting for you every morning.

---

## 📁 Folder Structure

```
desktop-companion/
├── desktop_mate.py          ← main app
├── requirements.txt         ← dependencies
├── characters.json          ← your saved characters (auto generated)
└── sprites/                 ← your sprite frames (auto generated)
    └── charactername_walk/
        ├── 00.png
        ├── 01.png
        └── ...
```

---

## 🛠️ Built With

- Python 3.12
- tkinter — transparent window
- Pillow — image processing and spritesheet slicing
- keyboard — global hotkey support

---

## 📋 Requirements

```
pillow
keyboard
```

```bash
pip install pillow keyboard
```

---

## ⚠️ DISCLAIMER

**Character Ownership**
This repository does not include any copyrighted characters. The default character included is an original AI-generated design with no affiliation to any existing anime, game, or media franchise. Any resemblance to existing characters is coincidental.

**Third Party Characters**
Do not use characters from copyrighted franchises (anime, games, movies, etc.) in public releases or commercial projects without permission from the rights holder. Using them privately on your own PC is generally fine but distributing them is not.

**No Liability**
This software is provided as-is for personal use. The developer is not responsible for any issues arising from use of this software including but not limited to productivity loss from having a cute character on your screen.

**Not Affiliated**
DesktopMate is an independent open source project. It is not affiliated with, endorsed by, or connected to any existing desktop companion software, anime studio, or game publisher.

---

## 🤝 Contributing

Found a bug? Have a feature idea? Open an issue or submit a pull request. All contributions welcome.

---

## 📄 License

MIT License — free to use, modify, and distribute. See [LICENSE](LICENSE) for details.

> If you use this in your own project a credit or star would be appreciated but is not required.

---

## 🎬 See It in Action

Full build video on YouTube → [RuntimeRiot](https://youtube.com/@runtimeriot)

---

*Built by a CS student who was tired of boring desktop companions and had an all nighter to spare.*