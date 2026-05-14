"""
Desktop Mate - Animated desktop companions
Requirements: pip install pillow
"""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import random
import os
import sys
import json
import threading
from glob import glob
from PIL import Image, ImageTk

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("[Hotkey] Install 'keyboard' library for hotkey support: pip install keyboard")

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

SIZE_STEP = 20
MIN_SIZE  = 60
MAX_SIZE  = 400

# Always save config and sprites next to the .exe (or script during dev)
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "characters.json")
SPRITES_DIR = os.path.join(BASE_DIR, "sprites")

# ─── CHARACTER MANAGER ────────────────────────────────────────────────────────

class CharacterManager:
    """Loads and saves character configs to a JSON file."""

    def __init__(self):
        os.makedirs(SPRITES_DIR, exist_ok=True)
        self.configs = self._load()

    def _load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.configs, f, indent=2)

    def add(self, cfg):
        self.configs.append(cfg)
        self.save()

    def remove(self, name):
        self.configs = [c for c in self.configs if c["name"] != name]
        self.save()


# ─── SPRITE SLICER ────────────────────────────────────────────────────────────

def slice_sheet(src_path, cols, rows, prefix, force=False):
    """Slice a spritesheet PNG into individual frames inside its own subfolder."""
    # Each character gets their own subfolder: sprites/prefix/
    out_dir  = os.path.join(SPRITES_DIR, prefix)
    os.makedirs(out_dir, exist_ok=True)
    existing = sorted(glob(os.path.join(out_dir, "*.png")))
    if existing and not force:
        return len(existing)

    img = Image.open(src_path).convert("RGBA")
    w, h = img.size
    fw, fh = w // cols, h // rows
    count = 0
    for row in range(rows):
        for col in range(cols):
            idx   = row * cols + col
            frame = img.crop((col*fw, row*fh, (col+1)*fw, (row+1)*fh))
            pixels = list(frame.getdata())
            frame.putdata([(0,0,0,0) if (r<30 and g<30 and b<30) else (r,g,b,a)
                           for r,g,b,a in pixels])
            frame.save(os.path.join(out_dir, f"{idx:02d}.png"))
            count += 1
    return count


# ─── SETUP DIALOG ─────────────────────────────────────────────────────────────

class SetupDialog(tk.Toplevel):
    """First-time or add-character dialog."""

    def __init__(self, master, on_done, existing_names=None):
        super().__init__(master)
        self.on_done       = on_done
        self.existing_names = existing_names or []
        self.result        = None

        self.title("Add a Character")
        self.resizable(False, False)
        self.wm_attributes("-topmost", True)
        self.configure(bg="#1a1a2e")
        self.geometry("420x520")

        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"420x520+{(sw-420)//2}+{(sh-520)//2}")

        self._build_ui()
        self.grab_set()

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg="#1a1a2e", fg="#a8c7fa",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))

    def _entry(self, parent, default=""):
        e = tk.Entry(parent, bg="#16213e", fg="white", insertbackground="white",
                     font=("Segoe UI", 10), bd=0, relief="flat", highlightthickness=1,
                     highlightbackground="#5B8DEF", highlightcolor="#5B8DEF")
        e.pack(fill="x", ipady=6)
        if default:
            e.insert(0, default)
        return e

    def _build_ui(self):
        pad = tk.Frame(self, bg="#1a1a2e", padx=24, pady=16)
        pad.pack(fill="both", expand=True)

        # Header
        tk.Label(pad, text="✨  Add New Character", bg="#1a1a2e", fg="white",
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0,12))

        # Name
        self._label(pad, "Character name")
        self.name_entry = self._entry(pad, "MyCharacter")

        # Walk sheet
        self._label(pad, "Walk spritesheet (.png)")
        wf = tk.Frame(pad, bg="#1a1a2e")
        wf.pack(fill="x")
        self.walk_path = tk.StringVar()
        tk.Entry(wf, textvariable=self.walk_path, bg="#16213e", fg="white",
                 font=("Segoe UI", 9), bd=0, relief="flat",
                 highlightthickness=1, highlightbackground="#5B8DEF",
                 insertbackground="white").pack(side="left", fill="x", expand=True, ipady=6)
        tk.Button(wf, text="Browse", bg="#5B8DEF", fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 9), padx=10,
                  command=lambda: self.walk_path.set(
                      filedialog.askopenfilename(filetypes=[("PNG", "*.png")])
                  )).pack(side="left", padx=(6,0))

        # Walk grid
        gf = tk.Frame(pad, bg="#1a1a2e")
        gf.pack(fill="x", pady=(0,4))
        lf = tk.Frame(gf, bg="#1a1a2e")
        lf.pack(side="left", fill="x", expand=True, padx=(0,8))
        tk.Label(lf, text="Columns", bg="#1a1a2e", fg="#a8c7fa",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))
        self.walk_cols = self._entry(lf, "6")
        rf = tk.Frame(gf, bg="#1a1a2e")
        rf.pack(side="left", fill="x", expand=True)
        tk.Label(rf, text="Rows", bg="#1a1a2e", fg="#a8c7fa",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))
        self.walk_rows = self._entry(rf, "6")

        # Grab sheet (optional)
        self._label(pad, "Grab spritesheet (.png)  — optional")
        grf = tk.Frame(pad, bg="#1a1a2e")
        grf.pack(fill="x")
        self.grab_path = tk.StringVar()
        tk.Entry(grf, textvariable=self.grab_path, bg="#16213e", fg="#888",
                 font=("Segoe UI", 9), bd=0, relief="flat",
                 highlightthickness=1, highlightbackground="#333",
                 insertbackground="white").pack(side="left", fill="x", expand=True, ipady=6)
        tk.Button(grf, text="Browse", bg="#333", fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 9), padx=10,
                  command=lambda: self.grab_path.set(
                      filedialog.askopenfilename(filetypes=[("PNG", "*.png")])
                  )).pack(side="left", padx=(6,0))

        ggf = tk.Frame(pad, bg="#1a1a2e")
        ggf.pack(fill="x", pady=(0,4))
        glf = tk.Frame(ggf, bg="#1a1a2e")
        glf.pack(side="left", fill="x", expand=True, padx=(0,8))
        tk.Label(glf, text="Columns", bg="#1a1a2e", fg="#666",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))
        self.grab_cols = self._entry(glf, "3")
        grf2 = tk.Frame(ggf, bg="#1a1a2e")
        grf2.pack(side="left", fill="x", expand=True)
        tk.Label(grf2, text="Rows", bg="#1a1a2e", fg="#666",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))
        self.grab_rows = self._entry(grf2, "3")

        # Add button
        tk.Button(pad, text="Add Character  →", bg="#5B8DEF", fg="white",
                  font=("Segoe UI", 11, "bold"), bd=0, cursor="hand2",
                  pady=10, command=self._submit).pack(fill="x", pady=(20,0))

    def _submit(self):
        name      = self.name_entry.get().strip()
        walk_path = self.walk_path.get().strip()

        if not name:
            messagebox.showerror("Error", "Please enter a character name.", parent=self)
            return
        if name in self.existing_names:
            messagebox.showerror("Error", f'"{name}" already exists.', parent=self)
            return
        if not walk_path or not os.path.exists(walk_path):
            messagebox.showerror("Error", "Please select a valid walk spritesheet.", parent=self)
            return

        try:
            wcols = int(self.walk_cols.get())
            wrows = int(self.walk_rows.get())
        except ValueError:
            messagebox.showerror("Error", "Columns and rows must be numbers.", parent=self)
            return

        prefix = name.lower().replace(" ", "_")

        # Slice walk sheet
        try:
            count = slice_sheet(walk_path, wcols, wrows, f"{prefix}_walk")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to slice walk sheet:\n{e}", parent=self)
            return

        # Grab sheet (optional)
        grab_path = self.grab_path.get().strip()
        has_grab  = grab_path and os.path.exists(grab_path)
        if has_grab:
            try:
                gcols = int(self.grab_cols.get())
                grows = int(self.grab_rows.get())
                slice_sheet(grab_path, gcols, grows, f"{prefix}_grab")
            except Exception as e:
                messagebox.showwarning("Warning", f"Grab sheet failed, skipping:\n{e}", parent=self)
                has_grab = False

        # Get aspect ratio from first frame
        first = sorted(glob(os.path.join(SPRITES_DIR, f"{prefix}_walk", "*.png")))[0]
        img   = Image.open(first)
        fw, fh = img.size
        aspect = fh / fw
        default_w = 120
        default_h = int(default_w * aspect)

        cfg = {
            "name":      name,
            "prefix":    prefix,
            "has_grab":  has_grab,
            "width":     default_w,
            "height":    default_h,
            "speed":     3,
            "fps":       18,
            "flip_walk": True,   # True = sprite faces left by default, False = faces right
        }

        self.destroy()
        self.on_done(cfg)


# ─── DESKTOP MATE INSTANCE ────────────────────────────────────────────────────

class DesktopMate:
    def __init__(self, cfg, master, manager):
        self.cfg     = cfg
        self.master  = master
        self.manager = manager
        self.name    = cfg["name"]
        self.prefix  = cfg["prefix"]
        self.speed   = cfg["speed"]
        self.fps     = cfg["fps"]

        self.base_w  = cfg["width"]
        self.base_h  = cfg["height"]
        self.aspect  = cfg["height"] / cfg["width"]
        self.W       = cfg["width"]
        self.H       = cfg["height"]

        self.dragging     = False
        self.drag_x       = 0
        self.drag_y       = 0
        self.facing_right = True
        self.walking      = False
        self.target_x     = None
        self.frame_index  = 0
        self.mode         = "walk"

        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        self.win.wm_attributes("-transparentcolor", "black")
        self.win.config(bg="black")

        self.sw = self.win.winfo_screenwidth()
        self.sh = self.win.winfo_screenheight()
        self.x  = random.randint(40, self.sw - self.W - 40)
        self.y  = self.sh - self.H - 80
        self.win.geometry(f"{self.W}x{self.H}+{self.x}+{self.y}")

        self.canvas = tk.Canvas(self.win, width=self.W, height=self.H,
                                bg="black", highlightthickness=0)
        self.canvas.pack()

        self.raw_walk  = self._load_raw(f"{self.prefix}_walk")
        self.raw_grab  = self._load_raw(f"{self.prefix}_grab") if cfg["has_grab"] else self.raw_walk

        self.walk_right  = []
        self.walk_left   = []
        self.grab_frames = []
        self.sprite_item = self.canvas.create_image(self.W//2, self.H//2, anchor="center")
        self._rebuild_frames()

        if not self.walk_right:
            self._draw_fallback()

        self.canvas.bind("<ButtonPress-1>",  self._start_drag)
        self.canvas.bind("<B1-Motion>",       self._do_drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)
        self.canvas.bind("<Button-3>",        self._show_menu)

        self._tick()
        self._pick_next_walk()

    def _load_raw(self, prefix):
        out_dir = os.path.join(SPRITES_DIR, prefix)
        paths   = sorted(glob(os.path.join(out_dir, "*.png")))
        images  = []
        for p in paths:
            try:
                images.append(Image.open(p).convert("RGBA"))
            except Exception as e:
                print(f"[Load] {p}: {e}")
        return images

    def _rebuild_frames(self):
        def make(raw, flip=False):
            frames = []
            for img in raw:
                i = img.transpose(Image.FLIP_LEFT_RIGHT) if flip else img
                i = i.resize((self.W, self.H), Image.LANCZOS)
                frames.append(ImageTk.PhotoImage(i))
            return frames

        flip = self.cfg.get("flip_walk", True)
        self.walk_right  = make(self.raw_walk, flip=flip)
        self.walk_left   = make(self.raw_walk, flip=not flip)
        self.grab_frames = make(self.raw_grab, flip=False)
        self.canvas.config(width=self.W, height=self.H)
        self.canvas.coords(self.sprite_item, self.W//2, self.H//2)
        self.win.geometry(f"{self.W}x{self.H}+{self.x}+{self.y}")

    def _draw_fallback(self):
        cx, cy = self.W//2, self.H//2
        r = min(self.W, self.H)//2 - 6
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                fill="#5B8DEF", outline="#3A6AD4", width=2)
        self.canvas.create_text(cx, cy, text="😊", font=("Arial", 24))

    # ── CONTEXT MENU ────────────────────────────────────────────────────────

    def _show_menu(self, event):
        menu = tk.Menu(self.win, tearoff=0,
                       bg="#1a1a2e", fg="white",
                       activebackground="#5B8DEF", activeforeground="white",
                       font=("Segoe UI", 10), bd=0, relief="flat")

        menu.add_command(label=f"  🔍  Enlarge  (+{SIZE_STEP}px)", command=self._enlarge)
        menu.add_command(label=f"  🔎  Shrink   (-{SIZE_STEP}px)", command=self._shrink)
        menu.add_command(label=f"  📐  Reset size",                command=self._reset_size)
        menu.add_separator()
        if self.walking:
            menu.add_command(label="  ⏸   Pause",    command=self._pause)
        else:
            menu.add_command(label="  ▶️   Resume",   command=self._resume)
        menu.add_separator()
        menu.add_command(label="  ➕  Add character",             command=self._add_character)
        menu.add_command(label=f"  🔄  Change spritesheet",       command=self._change_sheet)
        menu.add_command(label=f"  🔁  Flip direction",           command=self._flip_direction)
        menu.add_separator()
        menu.add_command(label=f"  ✕   Hide {self.name}",          command=self._hide)
        menu.add_command(label=f"  🗑   Remove {self.name}",         command=self._remove)
        menu.tk_popup(event.x_root, event.y_root)

    def _enlarge(self):
        if self.W + SIZE_STEP <= MAX_SIZE:
            self._pause()
            self.W += SIZE_STEP
            self.H  = int(self.W * self.aspect)
            self._rebuild_frames()

    def _shrink(self):
        if self.W - SIZE_STEP >= MIN_SIZE:
            self._pause()
            self.W -= SIZE_STEP
            self.H  = int(self.W * self.aspect)
            self._rebuild_frames()

    def _reset_size(self):
        self._pause()
        self.W = self.base_w
        self.H = self.base_h
        self._rebuild_frames()

    def _pause(self):
        self.walking  = False
        self.target_x = None

    def _resume(self):
        self.walking = False
        self._pick_next_walk()

    def _hide(self):
        """Temporarily hide — character stays in JSON, comes back on next launch."""
        self.win.destroy()

    def _remove(self):
        """Permanently remove — deletes from JSON."""
        from tkinter import messagebox
        if messagebox.askyesno("Remove", f"Permanently remove {self.name}?\nThis cannot be undone.", parent=self.win):
            self.manager.remove(self.name)
            self.win.destroy()

    def _add_character(self):
        existing = [c["name"] for c in self.manager.configs]
        def on_done(cfg):
            self.manager.add(cfg)
            DesktopMate(cfg, self.master, self.manager)
        SetupDialog(self.master, on_done, existing_names=existing)

    def _flip_direction(self):
        """Flip which way the sprite faces when walking right."""
        self.cfg["flip_walk"] = not self.cfg.get("flip_walk", True)
        self.manager.save()
        self._rebuild_frames()

    def _change_sheet(self):
        """Replace this character's walk spritesheet."""
        path = filedialog.askopenfilename(
            title="Select new walk spritesheet",
            filetypes=[("PNG", "*.png")]
        )
        if not path:
            return

        # Ask for grid size
        cols_str = simpledialog.askstring("Columns", "How many columns?", initialvalue="6", parent=self.win)
        rows_str = simpledialog.askstring("Rows",    "How many rows?",    initialvalue="6", parent=self.win)
        if not cols_str or not rows_str:
            return

        try:
            cols = int(cols_str)
            rows = int(rows_str)
        except ValueError:
            messagebox.showerror("Error", "Columns and rows must be numbers.", parent=self.win)
            return

        self._pause()
        try:
            slice_sheet(path, cols, rows, f"{self.prefix}_walk", force=True)
            self.raw_walk = self._load_raw(f"{self.prefix}_walk")
            self._rebuild_frames()
            self._resume()
        except Exception as e:
            messagebox.showerror("Error", f"Failed:\n{e}", parent=self.win)

    # ── ANIMATION / MOVEMENT ────────────────────────────────────────────────

    def _tick(self):
        if not self.dragging and self.walking and self.target_x is not None:
            diff = self.target_x - self.x
            if abs(diff) <= self.speed:
                # Arrived at edge — snap, flip, pick next target
                self.x = self.target_x
                self.win.geometry(f"+{self.x}+{self.y}")
                self.walking      = False
                self.facing_right = not self.facing_right
                self._pick_next_walk()
            else:
                self.x += self.speed if diff > 0 else -self.speed
                self.win.geometry(f"+{self.x}+{self.y}")

        frames = (self.grab_frames if self.mode == "grab"
                  else self.walk_right if self.facing_right
                  else self.walk_left)

        if frames:
            self.canvas.itemconfig(self.sprite_item, image=frames[self.frame_index])
            self.frame_index = (self.frame_index + 1) % len(frames)

        self.win.after(int(1000 / self.fps), self._tick)

    def _pick_next_walk(self):
        # Don't schedule while dragging — _end_drag will call this once on release
        if self.dragging:
            return

        left_edge  = 0
        right_edge = self.sw - self.W

        # Walk toward whichever edge we are now facing
        self.target_x = right_edge if self.facing_right else left_edge
        self.walking  = True

    def _start_drag(self, e):
        self.dragging    = True
        self.walking     = False
        self.mode        = "grab"
        self.frame_index = 0
        self.drag_x      = e.x
        self.drag_y      = e.y

    def _do_drag(self, e):
        new_x = self.win.winfo_x() + e.x - self.drag_x
        self.facing_right = new_x > self.x
        self.x = new_x
        self.y = self.win.winfo_y() + e.y - self.drag_y
        self.win.geometry(f"+{self.x}+{self.y}")

    def _end_drag(self, e):
        self.dragging    = False
        self.mode        = "walk"
        self.frame_index = 0
        self._pick_next_walk()   # resume walking cleanly after drag


# ─── HOTKEY MANAGER ──────────────────────────────────────────────────────────

class HotkeyManager:
    """Global hotkey: Ctrl+Shift+H to toggle show/hide all characters."""

    HOTKEY = "ctrl+shift+h"

    def __init__(self, root, get_mates):
        self.root      = root
        self.get_mates = get_mates   # callable returning current list of mates
        self.visible   = True

        if not KEYBOARD_AVAILABLE:
            return

        # Run in background thread — keyboard library needs its own thread
        threading.Thread(target=self._listen, daemon=True).start()
        print(f"[Hotkey] {self.HOTKEY} → toggle show/hide all characters")

    def _listen(self):
        keyboard.add_hotkey(self.HOTKEY, self._toggle)
        keyboard.wait()

    def _toggle(self):
        self.visible = not self.visible
        # Must update tkinter from main thread
        self.root.after(0, self._apply)

    def _apply(self):
        for mate in self.get_mates():
            try:
                if self.visible:
                    mate.win.deiconify()
                else:
                    mate.win.withdraw()
            except Exception:
                pass


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(SPRITES_DIR, exist_ok=True)

    root = tk.Tk()
    root.withdraw()

    manager = CharacterManager()
    mates   = []

    def launch(cfg):
        mates.append(DesktopMate(cfg, root, manager))

    if not manager.configs:
        # First time — show setup dialog
        def on_first(cfg):
            manager.add(cfg)
            launch(cfg)
        SetupDialog(root, on_first)
    else:
        for cfg in manager.configs:
            launch(cfg)

    # Global hotkey: Ctrl+Shift+H to toggle all characters
    hotkey = HotkeyManager(root, lambda: mates)
    if KEYBOARD_AVAILABLE:
        print("[Hotkey] Press Ctrl+Shift+H to hide/show all characters")
    else:
        print("[Hotkey] pip install keyboard to enable Ctrl+Shift+H toggle")

    root.mainloop()

    # # """
    # # Desktop Mate - Animated roaming desktop companion
    # # Requirements: pip install pillow
    # # """
    # #
    # # import tkinter as tk
    # # import random
    # # import os
    # # from glob import glob
    # # from PIL import Image, ImageTk
    # #
    # # # ─── CONFIG ───────────────────────────────────────────────────────────────────
    # #
    # # MASCOT_NAME   = "Buddy"
    # # MASCOT_WIDTH  = 120
    # # MASCOT_HEIGHT = 187
    # # ANIMATION_FPS = 18
    # # WALK_SPEED    = 3
    # #
    # # # Spritesheet settings
    # # WALK_SHEET = "sprites/walk.png"
    # # WALK_COLS  = 6
    # # WALK_ROWS  = 6
    # #
    # # GRAB_SHEET = "sprites/grab.png"
    # # GRAB_COLS  = 3
    # # GRAB_ROWS  = 3
    # #
    # # # ─── AUTO-SETUP ───────────────────────────────────────────────────────────────
    # #
    # # def slice_sheet(path, cols, rows, prefix):
    # #     """Slice a spritesheet into individual frames with a given prefix."""
    # #     existing = sorted(glob(os.path.join("sprites", f"{prefix}_*.png")))
    # #     if existing:
    # #         print(f"[Setup] {prefix}: {len(existing)} frames already exist, skipping.")
    # #         return
    # #
    # #     if not os.path.exists(path):
    # #         print(f"[Setup] {prefix}: no sheet found at {path}, skipping.")
    # #         return
    # #
    # #     print(f"[Setup] Slicing {path}...")
    # #     img = Image.open(path).convert("RGBA")
    # #     w, h = img.size
    # #     fw, fh = w // cols, h // rows
    # #     count = 0
    # #     for row in range(rows):
    # #         for col in range(cols):
    # #             idx   = row * cols + col
    # #             frame = img.crop((col*fw, row*fh, (col+1)*fw, (row+1)*fh))
    # #             pixels = list(frame.getdata())
    # #             frame.putdata([(0,0,0,0) if (r<30 and g<30 and b<30) else (r,g,b,a)
    # #                            for r,g,b,a in pixels])
    # #             frame.save(os.path.join("sprites", f"{prefix}_{idx:02d}.png"))
    # #             count += 1
    # #     print(f"[Setup] {prefix}: {count} frames saved.")
    # #
    # # def setup_frames():
    # #     os.makedirs("sprites", exist_ok=True)
    # #     slice_sheet(WALK_SHEET, WALK_COLS, WALK_ROWS, "walk")
    # #     slice_sheet(GRAB_SHEET, GRAB_COLS, GRAB_ROWS, "grab")
    # #
    # # # ─── DESKTOP MATE ─────────────────────────────────────────────────────────────
    # #
    # # class DesktopMate:
    # #     def __init__(self):
    # #         setup_frames()
    # #
    # #         self.root = tk.Tk()
    # #         self.root.title(MASCOT_NAME)
    # #         self.root.overrideredirect(True)
    # #         self.root.wm_attributes("-topmost", True)
    # #         self.root.wm_attributes("-transparentcolor", "black")
    # #         self.root.config(bg="black")
    # #
    # #         self.dragging     = False
    # #         self.drag_x       = 0
    # #         self.drag_y       = 0
    # #         self.facing_right = True
    # #         self.walking      = False
    # #         self.target_x     = None
    # #         self.frame_index  = 0
    # #         self.mode         = "walk"   # "walk" or "grab"
    # #
    # #         self.sw = self.root.winfo_screenwidth()
    # #         self.sh = self.root.winfo_screenheight()
    # #         self.x  = self.sw - MASCOT_WIDTH - 40
    # #         self.y  = self.sh - MASCOT_HEIGHT - 80
    # #         self.root.geometry(f"{MASCOT_WIDTH}x{MASCOT_HEIGHT}+{self.x}+{self.y}")
    # #
    # #         self.canvas = tk.Canvas(self.root, width=MASCOT_WIDTH, height=MASCOT_HEIGHT,
    # #                                 bg="black", highlightthickness=0)
    # #         self.canvas.pack()
    # #
    # #         # Load all frame sets
    # #         self.walk_right = self._load_frames("walk", flip=True)
    # #         self.walk_left  = self._load_frames("walk", flip=False)
    # #         self.grab_frames = self._load_frames("grab", flip=False)
    # #
    # #         self.sprite_item = self.canvas.create_image(
    # #             MASCOT_WIDTH//2, MASCOT_HEIGHT//2, anchor="center"
    # #         )
    # #
    # #         if not self.walk_right:
    # #             self._draw_fallback()
    # #
    # #         self.canvas.bind("<ButtonPress-1>",  self._start_drag)
    # #         self.canvas.bind("<B1-Motion>",       self._do_drag)
    # #         self.canvas.bind("<ButtonRelease-1>", self._end_drag)
    # #         self.canvas.bind("<Button-3>",        lambda e: self.root.destroy())
    # #
    # #         self._tick()
    # #         self._pick_next_walk()
    # #
    # #     def _load_frames(self, prefix, flip=False):
    # #         paths = sorted(glob(os.path.join("sprites", f"{prefix}_*.png")))
    # #         if not paths:
    # #             return []
    # #         frames = []
    # #         for p in paths:
    # #             try:
    # #                 img = Image.open(p).convert("RGBA")
    # #                 if flip:
    # #                     img = img.transpose(Image.FLIP_LEFT_RIGHT)
    # #                 img = img.resize((MASCOT_WIDTH, MASCOT_HEIGHT), Image.LANCZOS)
    # #                 frames.append(ImageTk.PhotoImage(img))
    # #             except Exception as e:
    # #                 print(f"[Load] {p}: {e}")
    # #         print(f"[Load] {prefix} {'flipped' if flip else 'normal'}: {len(frames)} frames")
    # #         return frames
    # #
    # #     def _draw_fallback(self):
    # #         cx, cy = MASCOT_WIDTH//2, MASCOT_HEIGHT//2
    # #         r = min(MASCOT_WIDTH, MASCOT_HEIGHT)//2 - 6
    # #         self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
    # #                                 fill="#5B8DEF", outline="#3A6AD4", width=2)
    # #         self.canvas.create_text(cx, cy, text="😊", font=("Arial", 28))
    # #
    # #     def _tick(self):
    # #         # Move x if walking
    # #         if not self.dragging and self.walking and self.target_x is not None:
    # #             diff = self.target_x - self.x
    # #             if abs(diff) <= WALK_SPEED:
    # #                 self.x = self.target_x
    # #                 self.walking = False
    # #             else:
    # #                 self.x += WALK_SPEED if diff > 0 else -WALK_SPEED
    # #             self.root.geometry(f"+{self.x}+{self.y}")
    # #
    # #         # Pick correct frame set
    # #         if self.mode == "grab" and self.grab_frames:
    # #             frames = self.grab_frames
    # #         elif self.facing_right:
    # #             frames = self.walk_right
    # #         else:
    # #             frames = self.walk_left
    # #
    # #         if frames:
    # #             self.canvas.itemconfig(self.sprite_item, image=frames[self.frame_index])
    # #             self.frame_index = (self.frame_index + 1) % len(frames)
    # #
    # #         self.root.after(int(1000 / ANIMATION_FPS), self._tick)
    # #
    # #     def _pick_next_walk(self):
    # #         if not self.dragging:
    # #             tx = random.randint(40, self.sw - MASCOT_WIDTH - 40)
    # #             self.facing_right = tx > self.x
    # #             self.target_x     = tx
    # #             self.walking      = True
    # #
    # #         travel_time = abs((self.target_x or self.x) - self.x) / WALK_SPEED * (1000 / ANIMATION_FPS)
    # #         pause = random.randint(1500, 4000)
    # #         self.root.after(int(travel_time + pause), self._pick_next_walk)
    # #
    # #     def _start_drag(self, e):
    # #         self.dragging = True
    # #         self.walking  = False
    # #         self.mode     = "grab"        # ← switch to grab animation
    # #         self.frame_index = 0          # reset so grab starts from frame 0
    # #         self.drag_x = e.x
    # #         self.drag_y = e.y
    # #
    # #     def _do_drag(self, e):
    # #         new_x = self.root.winfo_x() + e.x - self.drag_x
    # #         self.facing_right = new_x > self.x
    # #         self.x = new_x
    # #         self.y = self.root.winfo_y() + e.y - self.drag_y
    # #         self.root.geometry(f"+{self.x}+{self.y}")
    # #
    # #     def _end_drag(self, e):
    # #         self.dragging    = False
    # #         self.mode        = "walk"     # ← switch back to walk
    # #         self.frame_index = 0
    # #
    # #     def run(self):
    # #         print(f"\n{'='*40}")
    # #         print(f"  {MASCOT_NAME} is roaming! 🎉")
    # #         print(f"  Drag to grab | Right-click to quit")
    # #         print(f"{'='*40}\n")
    # #         self.root.mainloop()
    # #
    # # if __name__ == "__main__":
    # #     DesktopMate().run()
    #
    #
    #
    #
    #
    #
    #
    #
    # """
    # Desktop Mate - Multiple animated roaming companions
    # Requirements: pip install pillow
    # """
    #
    # import tkinter as tk
    # import random
    # import os
    # from glob import glob
    # from PIL import Image, ImageTk
    #
    # # ─── CHARACTER CONFIGS ────────────────────────────────────────────────────────
    #
    # CHARACTERS = [
    #     {
    #         "name":       "Kurisu",
    #         "walk_sheet": "sprites/walk.png",
    #         "walk_cols":  6,
    #         "walk_rows":  6,
    #         "grab_sheet": "sprites/grab.png",
    #         "grab_cols":  3,
    #         "grab_rows":  3,
    #         "width":      120,
    #         "height":     187,
    #         "speed":      3,
    #         "fps":        18,
    #         "start_x":    None,   # None = auto (bottom-right)
    #         "start_y":    None,
    #     },
    #     {
    #         "name":       "Yuki",
    #         "walk_sheet": "sprites/char2_walk.png",
    #         "walk_cols":  4,
    #         "walk_rows":  4,
    #         "grab_sheet": None,   # No grab animation — uses walk frames instead
    #         "grab_cols":  0,
    #         "grab_rows":  0,
    #         "width":      100,
    #         "height":     228,
    #         "speed":      2,
    #         "fps":        14,
    #         "start_x":    None,
    #         "start_y":    None,
    #     },
    # ]
    #
    # # ─── AUTO-SETUP ───────────────────────────────────────────────────────────────
    #
    # def slice_sheet(path, cols, rows, prefix):
    #     if not path or not os.path.exists(path):
    #         return
    #     existing = sorted(glob(os.path.join("sprites", f"{prefix}_*.png")))
    #     if existing:
    #         print(f"[Setup] {prefix}: {len(existing)} frames found, skipping.")
    #         return
    #     print(f"[Setup] Slicing {path} → {prefix}_*.png ...")
    #     img = Image.open(path).convert("RGBA")
    #     w, h = img.size
    #     fw, fh = w // cols, h // rows
    #     for row in range(rows):
    #         for col in range(cols):
    #             idx   = row * cols + col
    #             frame = img.crop((col*fw, row*fh, (col+1)*fw, (row+1)*fh))
    #             pixels = list(frame.getdata())
    #             frame.putdata([(0,0,0,0) if (r<30 and g<30 and b<30) else (r,g,b,a)
    #                            for r,g,b,a in pixels])
    #             frame.save(os.path.join("sprites", f"{prefix}_{idx:02d}.png"))
    #     print(f"[Setup] {prefix}: {cols*rows} frames saved.")
    #
    # def setup_all():
    #     os.makedirs("sprites", exist_ok=True)
    #     for cfg in CHARACTERS:
    #         name = cfg["name"].lower()
    #         slice_sheet(cfg["walk_sheet"], cfg["walk_cols"], cfg["walk_rows"], f"{name}_walk")
    #         if cfg["grab_sheet"]:
    #             slice_sheet(cfg["grab_sheet"], cfg["grab_cols"], cfg["grab_rows"], f"{name}_grab")
    #
    # # ─── DESKTOP MATE INSTANCE ────────────────────────────────────────────────────
    #
    # class DesktopMate:
    #     def __init__(self, cfg, master):
    #         self.cfg     = cfg
    #         self.name    = cfg["name"]
    #         self.W       = cfg["width"]
    #         self.H       = cfg["height"]
    #         self.speed   = cfg["speed"]
    #         self.fps     = cfg["fps"]
    #         self.prefix  = self.name.lower()
    #
    #         self.dragging     = False
    #         self.drag_x       = 0
    #         self.drag_y       = 0
    #         self.facing_right = True
    #         self.walking      = False
    #         self.target_x     = None
    #         self.frame_index  = 0
    #         self.mode         = "walk"
    #
    #         # Create toplevel window per character
    #         self.win = tk.Toplevel(master)
    #         self.win.overrideredirect(True)
    #         self.win.wm_attributes("-topmost", True)
    #         self.win.wm_attributes("-transparentcolor", "black")
    #         self.win.config(bg="black")
    #
    #         self.sw = self.win.winfo_screenwidth()
    #         self.sh = self.win.winfo_screenheight()
    #
    #         # Stagger starting positions so they don't overlap
    #         idx = CHARACTERS.index(cfg)
    #         self.x = cfg["start_x"] or (self.sw - self.W - 40 - idx * 200)
    #         self.y = cfg["start_y"] or (self.sh - self.H - 80)
    #         self.win.geometry(f"{self.W}x{self.H}+{self.x}+{self.y}")
    #
    #         self.canvas = tk.Canvas(self.win, width=self.W, height=self.H,
    #                                 bg="black", highlightthickness=0)
    #         self.canvas.pack()
    #
    #         # Load frames
    #         self.walk_right  = self._load_frames(f"{self.prefix}_walk", flip=True)
    #         self.walk_left   = self._load_frames(f"{self.prefix}_walk", flip=False)
    #         has_grab         = bool(cfg["grab_sheet"])
    #         self.grab_frames = self._load_frames(f"{self.prefix}_grab") if has_grab else self.walk_right
    #
    #         self.sprite_item = self.canvas.create_image(self.W//2, self.H//2, anchor="center")
    #
    #         if not self.walk_right:
    #             self._draw_fallback()
    #
    #         self.canvas.bind("<ButtonPress-1>",  self._start_drag)
    #         self.canvas.bind("<B1-Motion>",       self._do_drag)
    #         self.canvas.bind("<ButtonRelease-1>", self._end_drag)
    #         self.canvas.bind("<Button-3>",        lambda e: self.win.destroy())
    #
    #         self._tick()
    #         self._pick_next_walk()
    #
    #     def _load_frames(self, prefix, flip=False):
    #         paths = sorted(glob(os.path.join("sprites", f"{prefix}_*.png")))
    #         if not paths:
    #             return []
    #         frames = []
    #         for p in paths:
    #             try:
    #                 img = Image.open(p).convert("RGBA")
    #                 if flip:
    #                     img = img.transpose(Image.FLIP_LEFT_RIGHT)
    #                 img = img.resize((self.W, self.H), Image.LANCZOS)
    #                 frames.append(ImageTk.PhotoImage(img))
    #             except Exception as e:
    #                 print(f"[Load] {p}: {e}")
    #         print(f"[{self.name}] {prefix} {'flipped' if flip else 'normal'}: {len(frames)} frames")
    #         return frames
    #
    #     def _draw_fallback(self):
    #         cx, cy = self.W//2, self.H//2
    #         r = min(self.W, self.H)//2 - 6
    #         self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
    #                                 fill="#5B8DEF", outline="#3A6AD4", width=2)
    #         self.canvas.create_text(cx, cy, text="😊", font=("Arial", 24))
    #
    #     def _tick(self):
    #         if not self.dragging and self.walking and self.target_x is not None:
    #             diff = self.target_x - self.x
    #             if abs(diff) <= self.speed:
    #                 self.x = self.target_x
    #                 self.walking = False
    #             else:
    #                 self.x += self.speed if diff > 0 else -self.speed
    #             self.win.geometry(f"+{self.x}+{self.y}")
    #
    #         if self.mode == "grab":
    #             frames = self.grab_frames
    #         elif self.facing_right:
    #             frames = self.walk_right
    #         else:
    #             frames = self.walk_left
    #
    #         if frames:
    #             self.canvas.itemconfig(self.sprite_item, image=frames[self.frame_index])
    #             self.frame_index = (self.frame_index + 1) % len(frames)
    #
    #         self.win.after(int(1000 / self.fps), self._tick)
    #
    #     def _pick_next_walk(self):
    #         if not self.dragging:
    #             tx = random.randint(40, self.sw - self.W - 40)
    #             self.facing_right = tx > self.x
    #             self.target_x     = tx
    #             self.walking      = True
    #         travel_time = abs((self.target_x or self.x) - self.x) / self.speed * (1000 / self.fps)
    #         pause = random.randint(1500, 4000)
    #         self.win.after(int(travel_time + pause), self._pick_next_walk)
    #
    #     def _start_drag(self, e):
    #         self.dragging    = True
    #         self.walking     = False
    #         self.mode        = "grab"
    #         self.frame_index = 0
    #         self.drag_x = e.x
    #         self.drag_y = e.y
    #
    #     def _do_drag(self, e):
    #         new_x = self.win.winfo_x() + e.x - self.drag_x
    #         self.facing_right = new_x > self.x
    #         self.x = new_x
    #         self.y = self.win.winfo_y() + e.y - self.drag_y
    #         self.win.geometry(f"+{self.x}+{self.y}")
    #
    #     def _end_drag(self, e):
    #         self.dragging    = False
    #         self.mode        = "walk"
    #         self.frame_index = 0
    #
    #
    # # ─── MAIN ─────────────────────────────────────────────────────────────────────
    #
    # if __name__ == "__main__":
    #     setup_all()
    #
    #     root = tk.Tk()
    #     root.withdraw()  # hidden master window — keeps app alive
    #
    #     mates = [DesktopMate(cfg, root) for cfg in CHARACTERS]
    #
    #     print(f"\n{'='*40}")
    #     print(f"  {len(mates)} companions roaming!")
    #     print(f"  Drag to grab | Right-click to close one")
    #     print(f"{'='*40}\n")
    #
    #     root.mainloop()

    # """
    # Desktop Mate - Multiple animated roaming companions
    # Requirements: pip install pillow
    # """
    #
    # import tkinter as tk
    # import random
    # import os
    # from glob import glob
    # from PIL import Image, ImageTk
    #
    # # ─── CHARACTER CONFIGS ────────────────────────────────────────────────────────
    #
    # CHARACTERS = [
    #     {
    #         "name":       "Kurisu",
    #         "walk_sheet": "sprites/walk.png",
    #         "walk_cols":  6,
    #         "walk_rows":  6,
    #         "grab_sheet": "sprites/grab.png",
    #         "grab_cols":  3,
    #         "grab_rows":  3,
    #         "width":      120,
    #         "height":     187,
    #         "speed":      3,
    #         "fps":        18,
    #         "start_x":    None,
    #         "start_y":    None,
    #     },
    #     {
    #         "name":       "Yuki",
    #         "walk_sheet": "sprites/char2_walk.png",
    #         "walk_cols":  4,
    #         "walk_rows":  4,
    #         "grab_sheet": None,
    #         "grab_cols":  0,
    #         "grab_rows":  0,
    #         "width":      100,
    #         "height":     228,
    #         "speed":      3,
    #         "fps":        9,
    #         "start_x":    None,
    #         "start_y":    None,
    #     },
    # ]
    #
    # SIZE_STEP = 20      # how many pixels to grow/shrink per click
    # MIN_SIZE  = 60      # minimum width
    # MAX_SIZE  = 400     # maximum width
    #
    # # ─── AUTO-SETUP ───────────────────────────────────────────────────────────────
    #
    # def slice_sheet(path, cols, rows, prefix):
    #     if not path or not os.path.exists(path):
    #         return
    #     existing = sorted(glob(os.path.join("sprites", f"{prefix}_*.png")))
    #     if existing:
    #         print(f"[Setup] {prefix}: {len(existing)} frames found, skipping.")
    #         return
    #     print(f"[Setup] Slicing {path} → {prefix}_*.png ...")
    #     img = Image.open(path).convert("RGBA")
    #     w, h = img.size
    #     fw, fh = w // cols, h // rows
    #     for row in range(rows):
    #         for col in range(cols):
    #             idx   = row * cols + col
    #             frame = img.crop((col*fw, row*fh, (col+1)*fw, (row+1)*fh))
    #             pixels = list(frame.getdata())
    #             frame.putdata([(0,0,0,0) if (r<30 and g<30 and b<30) else (r,g,b,a)
    #                            for r,g,b,a in pixels])
    #             frame.save(os.path.join("sprites", f"{prefix}_{idx:02d}.png"))
    #     print(f"[Setup] {prefix}: {cols*rows} frames saved.")
    #
    # def setup_all():
    #     os.makedirs("sprites", exist_ok=True)
    #     for cfg in CHARACTERS:
    #         name = cfg["name"].lower()
    #         slice_sheet(cfg["walk_sheet"], cfg["walk_cols"], cfg["walk_rows"], f"{name}_walk")
    #         if cfg["grab_sheet"]:
    #             slice_sheet(cfg["grab_sheet"], cfg["grab_cols"], cfg["grab_rows"], f"{name}_grab")
    #
    # # ─── DESKTOP MATE INSTANCE ────────────────────────────────────────────────────
    #
    # class DesktopMate:
    #     def __init__(self, cfg, master):
    #         self.cfg        = cfg
    #         self.name       = cfg["name"]
    #         self.prefix     = self.name.lower()
    #         self.speed      = cfg["speed"]
    #         self.fps        = cfg["fps"]
    #
    #         # Base aspect ratio from config — used to keep proportions when resizing
    #         self.base_w     = cfg["width"]
    #         self.base_h     = cfg["height"]
    #         self.aspect     = cfg["height"] / cfg["width"]
    #         self.W          = cfg["width"]
    #         self.H          = cfg["height"]
    #
    #         self.dragging     = False
    #         self.drag_x       = 0
    #         self.drag_y       = 0
    #         self.facing_right = True
    #         self.walking      = False
    #         self.target_x     = None
    #         self.frame_index  = 0
    #         self.mode         = "walk"
    #
    #         self.win = tk.Toplevel(master)
    #         self.win.overrideredirect(True)
    #         self.win.wm_attributes("-topmost", True)
    #         self.win.wm_attributes("-transparentcolor", "black")
    #         self.win.config(bg="black")
    #
    #         self.sw = self.win.winfo_screenwidth()
    #         self.sh = self.win.winfo_screenheight()
    #
    #         idx    = CHARACTERS.index(cfg)
    #         self.x = cfg["start_x"] or (self.sw - self.W - 40 - idx * 200)
    #         self.y = cfg["start_y"] or (self.sh - self.H - 80)
    #         self.win.geometry(f"{self.W}x{self.H}+{self.x}+{self.y}")
    #
    #         self.canvas = tk.Canvas(self.win, width=self.W, height=self.H,
    #                                 bg="black", highlightthickness=0)
    #         self.canvas.pack()
    #
    #         # Store raw PIL images for resizing without quality loss
    #         self.raw_walk  = self._load_raw(f"{self.prefix}_walk")
    #         self.raw_grab  = self._load_raw(f"{self.prefix}_grab") if cfg["grab_sheet"] else self.raw_walk
    #
    #         # Build display frames at current size
    #         self.walk_right  = []
    #         self.walk_left   = []
    #         self.grab_frames = []
    #
    #         self.sprite_item = self.canvas.create_image(self.W//2, self.H//2, anchor="center")
    #         self._rebuild_frames()
    #
    #         if not self.walk_right:
    #             self._draw_fallback()
    #
    #         # Left click = drag
    #         self.canvas.bind("<ButtonPress-1>",  self._start_drag)
    #         self.canvas.bind("<B1-Motion>",       self._do_drag)
    #         self.canvas.bind("<ButtonRelease-1>", self._end_drag)
    #
    #         # Right click = context menu
    #         self.canvas.bind("<Button-3>", self._show_menu)
    #
    #         self._tick()
    #         self._pick_next_walk()
    #
    #     # ── RAW IMAGE LOADING ────────────────────────────────────────────────────
    #
    #     def _load_raw(self, prefix):
    #         """Load frames as raw PIL images (no resize yet)."""
    #         paths = sorted(glob(os.path.join("sprites", f"{prefix}_*.png")))
    #         images = []
    #         for p in paths:
    #             try:
    #                 images.append(Image.open(p).convert("RGBA"))
    #             except Exception as e:
    #                 print(f"[Load] {p}: {e}")
    #         print(f"[{self.name}] {prefix}: {len(images)} raw frames loaded")
    #         return images
    #
    #     def _rebuild_frames(self):
    #         """Resize raw frames to current W/H and rebuild all frame lists."""
    #         def make_frames(raw_list, flip=False):
    #             frames = []
    #             for img in raw_list:
    #                 i = img.transpose(Image.FLIP_LEFT_RIGHT) if flip else img
    #                 i = i.resize((self.W, self.H), Image.LANCZOS)
    #                 frames.append(ImageTk.PhotoImage(i))
    #             return frames
    #
    #         self.walk_right  = make_frames(self.raw_walk, flip=True)
    #         self.walk_left   = make_frames(self.raw_walk, flip=False)
    #         self.grab_frames = make_frames(self.raw_grab, flip=False)
    #
    #         # Resize canvas and window
    #         self.canvas.config(width=self.W, height=self.H)
    #         self.canvas.coords(self.sprite_item, self.W//2, self.H//2)
    #         self.win.geometry(f"{self.W}x{self.H}+{self.x}+{self.y}")
    #         print(f"[{self.name}] Rebuilt at {self.W}x{self.H}")
    #
    #     # ── CONTEXT MENU ────────────────────────────────────────────────────────
    #
    #     def _show_menu(self, event):
    #         menu = tk.Menu(self.win, tearoff=0,
    #                        bg="#1a1a2e", fg="white",
    #                        activebackground="#5B8DEF", activeforeground="white",
    #                        font=("Segoe UI", 10), bd=0, relief="flat")
    #         menu.add_command(label=f"  🔍  Enlarge  (+{SIZE_STEP}px)", command=self._enlarge)
    #         menu.add_command(label=f"  🔎  Shrink   (-{SIZE_STEP}px)", command=self._shrink)
    #         menu.add_separator()
    #         menu.add_command(label=f"  📐  Reset size",               command=self._reset_size)
    #         menu.add_separator()
    #         if self.walking:
    #             menu.add_command(label=f"  ⏸   Pause",               command=self._pause)
    #         else:
    #             menu.add_command(label=f"  ▶️   Resume",              command=self._resume)
    #         menu.add_separator()
    #         menu.add_command(label=f"  ✕   Close {self.name}",        command=self.win.destroy)
    #         menu.tk_popup(event.x_root, event.y_root)
    #
    #     def _enlarge(self):
    #         if self.W + SIZE_STEP <= MAX_SIZE:
    #             self._pause()
    #             self.W += SIZE_STEP
    #             self.H  = int(self.W * self.aspect)
    #             self._rebuild_frames()
    #
    #     def _shrink(self):
    #         if self.W - SIZE_STEP >= MIN_SIZE:
    #             self._pause()
    #             self.W -= SIZE_STEP
    #             self.H  = int(self.W * self.aspect)
    #             self._rebuild_frames()
    #
    #     def _reset_size(self):
    #         self._pause()
    #         self.W = self.base_w
    #         self.H = self.base_h
    #         self._rebuild_frames()
    #
    #     def _pause(self):
    #         self.walking  = False
    #         self.target_x = None
    #
    #     def _resume(self):
    #         self.walking = False
    #         self._pick_next_walk()
    #
    #     # ── FALLBACK ────────────────────────────────────────────────────────────
    #
    #     def _draw_fallback(self):
    #         cx, cy = self.W//2, self.H//2
    #         r = min(self.W, self.H)//2 - 6
    #         self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
    #                                 fill="#5B8DEF", outline="#3A6AD4", width=2)
    #         self.canvas.create_text(cx, cy, text="😊", font=("Arial", 24))
    #
    #     # ── TICK / ANIMATION ────────────────────────────────────────────────────
    #
    #     def _tick(self):
    #         if not self.dragging and self.walking and self.target_x is not None:
    #             diff = self.target_x - self.x
    #             if abs(diff) <= self.speed:
    #                 self.x = self.target_x
    #                 self.walking = False
    #             else:
    #                 self.x += self.speed if diff > 0 else -self.speed
    #             self.win.geometry(f"+{self.x}+{self.y}")
    #
    #         if self.mode == "grab":
    #             frames = self.grab_frames
    #         elif self.facing_right:
    #             frames = self.walk_right
    #         else:
    #             frames = self.walk_left
    #
    #         if frames:
    #             self.canvas.itemconfig(self.sprite_item, image=frames[self.frame_index])
    #             self.frame_index = (self.frame_index + 1) % len(frames)
    #
    #         self.win.after(int(1000 / self.fps), self._tick)
    #
    #     def _pick_next_walk(self):
    #         if not self.dragging:
    #             tx = random.randint(40, self.sw - self.W - 40)
    #             self.facing_right = tx > self.x
    #             self.target_x     = tx
    #             self.walking      = True
    #             travel_time = abs(tx - self.x) / self.speed * (1000 / self.fps)
    #         else:
    #             travel_time = 0
    #         self.win.after(int(travel_time), self._pick_next_walk)
    #
    #     # ── DRAG ────────────────────────────────────────────────────────────────
    #
    #     def _start_drag(self, e):
    #         self.dragging    = True
    #         self.walking     = False
    #         self.mode        = "grab"
    #         self.frame_index = 0
    #         self.drag_x      = e.x
    #         self.drag_y      = e.y
    #
    #     def _do_drag(self, e):
    #         new_x = self.win.winfo_x() + e.x - self.drag_x
    #         self.facing_right = new_x > self.x
    #         self.x = new_x
    #         self.y = self.win.winfo_y() + e.y - self.drag_y
    #         self.win.geometry(f"+{self.x}+{self.y}")
    #
    #     def _end_drag(self, e):
    #         self.dragging    = False
    #         self.mode        = "walk"
    #         self.frame_index = 0
    #
    #
    # # ─── MAIN ─────────────────────────────────────────────────────────────────────
    #
    # if __name__ == "__main__":
    #     setup_all()
    #
    #     root = tk.Tk()
    #     root.withdraw()
    #
    #     mates = [DesktopMate(cfg, root) for cfg in CHARACTERS]
    #
    #     print(f"\n{'='*40}")
    #     print(f"  {len(mates)} companions roaming!")
    #     print(f"  Drag to grab | Right-click for menu")
    #     print(f"{'='*40}\n")
    #
    #     root.mainloop()

    # #BEST ONE
    #
    # """
    # Desktop Mate - Animated desktop companions
    # Requirements: pip install pillow
    # """
    #
    # import tkinter as tk
    # from tkinter import filedialog, messagebox, simpledialog
    # import random
    # import os
    # import sys
    # import json
    # import threading
    # from glob import glob
    # from PIL import Image, ImageTk
    #
    # try:
    #     import keyboard
    #     KEYBOARD_AVAILABLE = True
    # except ImportError:
    #     KEYBOARD_AVAILABLE = False
    #     print("[Hotkey] Install 'keyboard' library for hotkey support: pip install keyboard")
    #
    # # ─── CONSTANTS ────────────────────────────────────────────────────────────────
    #
    # SIZE_STEP = 20
    # MIN_SIZE  = 60
    # MAX_SIZE  = 400
    #
    # # Always save config and sprites next to the .exe (or script during dev)
    # if getattr(sys, "frozen", False):
    #     BASE_DIR = os.path.dirname(sys.executable)
    # else:
    #     BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    #
    # CONFIG_FILE = os.path.join(BASE_DIR, "characters.json")
    # SPRITES_DIR = os.path.join(BASE_DIR, "sprites")
    #
    # # ─── CHARACTER MANAGER ────────────────────────────────────────────────────────
    #
    # class CharacterManager:
    #     """Loads and saves character configs to a JSON file."""
    #
    #     def __init__(self):
    #         os.makedirs(SPRITES_DIR, exist_ok=True)
    #         self.configs = self._load()
    #
    #     def _load(self):
    #         if os.path.exists(CONFIG_FILE):
    #             try:
    #                 with open(CONFIG_FILE) as f:
    #                     return json.load(f)
    #             except Exception:
    #                 pass
    #         return []
    #
    #     def save(self):
    #         with open(CONFIG_FILE, "w") as f:
    #             json.dump(self.configs, f, indent=2)
    #
    #     def add(self, cfg):
    #         self.configs.append(cfg)
    #         self.save()
    #
    #     def remove(self, name):
    #         self.configs = [c for c in self.configs if c["name"] != name]
    #         self.save()
    #
    #
    # # ─── SPRITE SLICER ────────────────────────────────────────────────────────────
    #
    # def slice_sheet(src_path, cols, rows, prefix, force=False):
    #     """Slice a spritesheet PNG into individual frames."""
    #     existing = sorted(glob(os.path.join(SPRITES_DIR, f"{prefix}_*.png")))
    #     if existing and not force:
    #         return len(existing)
    #
    #     img = Image.open(src_path).convert("RGBA")
    #     w, h = img.size
    #     fw, fh = w // cols, h // rows
    #     count = 0
    #     for row in range(rows):
    #         for col in range(cols):
    #             idx   = row * cols + col
    #             frame = img.crop((col*fw, row*fh, (col+1)*fw, (row+1)*fh))
    #             pixels = list(frame.getdata())
    #             frame.putdata([(0,0,0,0) if (r<30 and g<30 and b<30) else (r,g,b,a)
    #                            for r,g,b,a in pixels])
    #             frame.save(os.path.join(SPRITES_DIR, f"{prefix}_{idx:02d}.png"))
    #             count += 1
    #     return count
    #
    #
    # # ─── SETUP DIALOG ─────────────────────────────────────────────────────────────
    #
    # class SetupDialog(tk.Toplevel):
    #     """First-time or add-character dialog."""
    #
    #     def __init__(self, master, on_done, existing_names=None):
    #         super().__init__(master)
    #         self.on_done       = on_done
    #         self.existing_names = existing_names or []
    #         self.result        = None
    #
    #         self.title("Add a Character")
    #         self.resizable(False, False)
    #         self.wm_attributes("-topmost", True)
    #         self.configure(bg="#1a1a2e")
    #         self.geometry("420x520")
    #
    #         # Center on screen
    #         self.update_idletasks()
    #         sw = self.winfo_screenwidth()
    #         sh = self.winfo_screenheight()
    #         self.geometry(f"420x520+{(sw-420)//2}+{(sh-520)//2}")
    #
    #         self._build_ui()
    #         self.grab_set()
    #
    #     def _label(self, parent, text):
    #         tk.Label(parent, text=text, bg="#1a1a2e", fg="#a8c7fa",
    #                  font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))
    #
    #     def _entry(self, parent, default=""):
    #         e = tk.Entry(parent, bg="#16213e", fg="white", insertbackground="white",
    #                      font=("Segoe UI", 10), bd=0, relief="flat", highlightthickness=1,
    #                      highlightbackground="#5B8DEF", highlightcolor="#5B8DEF")
    #         e.pack(fill="x", ipady=6)
    #         if default:
    #             e.insert(0, default)
    #         return e
    #
    #     def _build_ui(self):
    #         pad = tk.Frame(self, bg="#1a1a2e", padx=24, pady=16)
    #         pad.pack(fill="both", expand=True)
    #
    #         # Header
    #         tk.Label(pad, text="✨  Add New Character", bg="#1a1a2e", fg="white",
    #                  font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0,12))
    #
    #         # Name
    #         self._label(pad, "Character name")
    #         self.name_entry = self._entry(pad, "MyCharacter")
    #
    #         # Walk sheet
    #         self._label(pad, "Walk spritesheet (.png)")
    #         wf = tk.Frame(pad, bg="#1a1a2e")
    #         wf.pack(fill="x")
    #         self.walk_path = tk.StringVar()
    #         tk.Entry(wf, textvariable=self.walk_path, bg="#16213e", fg="white",
    #                  font=("Segoe UI", 9), bd=0, relief="flat",
    #                  highlightthickness=1, highlightbackground="#5B8DEF",
    #                  insertbackground="white").pack(side="left", fill="x", expand=True, ipady=6)
    #         tk.Button(wf, text="Browse", bg="#5B8DEF", fg="white", bd=0, cursor="hand2",
    #                   font=("Segoe UI", 9), padx=10,
    #                   command=lambda: self.walk_path.set(
    #                       filedialog.askopenfilename(filetypes=[("PNG", "*.png")])
    #                   )).pack(side="left", padx=(6,0))
    #
    #         # Walk grid
    #         gf = tk.Frame(pad, bg="#1a1a2e")
    #         gf.pack(fill="x", pady=(0,4))
    #         lf = tk.Frame(gf, bg="#1a1a2e")
    #         lf.pack(side="left", fill="x", expand=True, padx=(0,8))
    #         tk.Label(lf, text="Columns", bg="#1a1a2e", fg="#a8c7fa",
    #                  font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))
    #         self.walk_cols = self._entry(lf, "6")
    #         rf = tk.Frame(gf, bg="#1a1a2e")
    #         rf.pack(side="left", fill="x", expand=True)
    #         tk.Label(rf, text="Rows", bg="#1a1a2e", fg="#a8c7fa",
    #                  font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))
    #         self.walk_rows = self._entry(rf, "6")
    #
    #         # Grab sheet (optional)
    #         self._label(pad, "Grab spritesheet (.png)  — optional")
    #         grf = tk.Frame(pad, bg="#1a1a2e")
    #         grf.pack(fill="x")
    #         self.grab_path = tk.StringVar()
    #         tk.Entry(grf, textvariable=self.grab_path, bg="#16213e", fg="#888",
    #                  font=("Segoe UI", 9), bd=0, relief="flat",
    #                  highlightthickness=1, highlightbackground="#333",
    #                  insertbackground="white").pack(side="left", fill="x", expand=True, ipady=6)
    #         tk.Button(grf, text="Browse", bg="#333", fg="white", bd=0, cursor="hand2",
    #                   font=("Segoe UI", 9), padx=10,
    #                   command=lambda: self.grab_path.set(
    #                       filedialog.askopenfilename(filetypes=[("PNG", "*.png")])
    #                   )).pack(side="left", padx=(6,0))
    #
    #         ggf = tk.Frame(pad, bg="#1a1a2e")
    #         ggf.pack(fill="x", pady=(0,4))
    #         glf = tk.Frame(ggf, bg="#1a1a2e")
    #         glf.pack(side="left", fill="x", expand=True, padx=(0,8))
    #         tk.Label(glf, text="Columns", bg="#1a1a2e", fg="#666",
    #                  font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))
    #         self.grab_cols = self._entry(glf, "3")
    #         grf2 = tk.Frame(ggf, bg="#1a1a2e")
    #         grf2.pack(side="left", fill="x", expand=True)
    #         tk.Label(grf2, text="Rows", bg="#1a1a2e", fg="#666",
    #                  font=("Segoe UI", 9)).pack(anchor="w", pady=(10,2))
    #         self.grab_rows = self._entry(grf2, "3")
    #
    #         # Add button
    #         tk.Button(pad, text="Add Character  →", bg="#5B8DEF", fg="white",
    #                   font=("Segoe UI", 11, "bold"), bd=0, cursor="hand2",
    #                   pady=10, command=self._submit).pack(fill="x", pady=(20,0))
    #
    #     def _submit(self):
    #         name      = self.name_entry.get().strip()
    #         walk_path = self.walk_path.get().strip()
    #
    #         if not name:
    #             messagebox.showerror("Error", "Please enter a character name.", parent=self)
    #             return
    #         if name in self.existing_names:
    #             messagebox.showerror("Error", f'"{name}" already exists.', parent=self)
    #             return
    #         if not walk_path or not os.path.exists(walk_path):
    #             messagebox.showerror("Error", "Please select a valid walk spritesheet.", parent=self)
    #             return
    #
    #         try:
    #             wcols = int(self.walk_cols.get())
    #             wrows = int(self.walk_rows.get())
    #         except ValueError:
    #             messagebox.showerror("Error", "Columns and rows must be numbers.", parent=self)
    #             return
    #
    #         prefix = name.lower().replace(" ", "_")
    #
    #         # Slice walk sheet
    #         try:
    #             count = slice_sheet(walk_path, wcols, wrows, f"{prefix}_walk")
    #         except Exception as e:
    #             messagebox.showerror("Error", f"Failed to slice walk sheet:\n{e}", parent=self)
    #             return
    #
    #         # Grab sheet (optional)
    #         grab_path = self.grab_path.get().strip()
    #         has_grab  = grab_path and os.path.exists(grab_path)
    #         if has_grab:
    #             try:
    #                 gcols = int(self.grab_cols.get())
    #                 grows = int(self.grab_rows.get())
    #                 slice_sheet(grab_path, gcols, grows, f"{prefix}_grab")
    #             except Exception as e:
    #                 messagebox.showwarning("Warning", f"Grab sheet failed, skipping:\n{e}", parent=self)
    #                 has_grab = False
    #
    #         # Get aspect ratio from first frame
    #         first = sorted(glob(os.path.join(SPRITES_DIR, f"{prefix}_walk_*.png")))[0]
    #         img   = Image.open(first)
    #         fw, fh = img.size
    #         aspect = fh / fw
    #         default_w = 120
    #         default_h = int(default_w * aspect)
    #
    #         cfg = {
    #             "name":      name,
    #             "prefix":    prefix,
    #             "has_grab":  has_grab,
    #             "width":     default_w,
    #             "height":    default_h,
    #             "speed":     3,
    #             "fps":       18,
    #         }
    #
    #         self.destroy()
    #         self.on_done(cfg)
    #
    #
    # # ─── DESKTOP MATE INSTANCE ────────────────────────────────────────────────────
    #
    # class DesktopMate:
    #     def __init__(self, cfg, master, manager):
    #         self.cfg     = cfg
    #         self.master  = master
    #         self.manager = manager
    #         self.name    = cfg["name"]
    #         self.prefix  = cfg["prefix"]
    #         self.speed   = cfg["speed"]
    #         self.fps     = cfg["fps"]
    #
    #         self.base_w  = cfg["width"]
    #         self.base_h  = cfg["height"]
    #         self.aspect  = cfg["height"] / cfg["width"]
    #         self.W       = cfg["width"]
    #         self.H       = cfg["height"]
    #
    #         self.dragging     = False
    #         self.drag_x       = 0
    #         self.drag_y       = 0
    #         self.facing_right = True
    #         self.walking      = False
    #         self.target_x     = None
    #         self.frame_index  = 0
    #         self.mode         = "walk"
    #
    #         self.win = tk.Toplevel(master)
    #         self.win.overrideredirect(True)
    #         self.win.wm_attributes("-topmost", True)
    #         self.win.wm_attributes("-transparentcolor", "black")
    #         self.win.config(bg="black")
    #
    #         self.sw = self.win.winfo_screenwidth()
    #         self.sh = self.win.winfo_screenheight()
    #         self.x  = random.randint(40, self.sw - self.W - 40)
    #         self.y  = self.sh - self.H - 80
    #         self.win.geometry(f"{self.W}x{self.H}+{self.x}+{self.y}")
    #
    #         self.canvas = tk.Canvas(self.win, width=self.W, height=self.H,
    #                                 bg="black", highlightthickness=0)
    #         self.canvas.pack()
    #
    #         self.raw_walk  = self._load_raw(f"{self.prefix}_walk")
    #         self.raw_grab  = self._load_raw(f"{self.prefix}_grab") if cfg["has_grab"] else self.raw_walk
    #
    #         self.walk_right  = []
    #         self.walk_left   = []
    #         self.grab_frames = []
    #         self.sprite_item = self.canvas.create_image(self.W//2, self.H//2, anchor="center")
    #         self._rebuild_frames()
    #
    #         if not self.walk_right:
    #             self._draw_fallback()
    #
    #         self.canvas.bind("<ButtonPress-1>",  self._start_drag)
    #         self.canvas.bind("<B1-Motion>",       self._do_drag)
    #         self.canvas.bind("<ButtonRelease-1>", self._end_drag)
    #         self.canvas.bind("<Button-3>",        self._show_menu)
    #
    #         self._tick()
    #         self._pick_next_walk()
    #
    #     def _load_raw(self, prefix):
    #         paths = sorted(glob(os.path.join(SPRITES_DIR, f"{prefix}_*.png")))
    #         images = []
    #         for p in paths:
    #             try:
    #                 images.append(Image.open(p).convert("RGBA"))
    #             except Exception as e:
    #                 print(f"[Load] {p}: {e}")
    #         return images
    #
    #     def _rebuild_frames(self):
    #         def make(raw, flip=False):
    #             frames = []
    #             for img in raw:
    #                 i = img.transpose(Image.FLIP_LEFT_RIGHT) if flip else img
    #                 i = i.resize((self.W, self.H), Image.LANCZOS)
    #                 frames.append(ImageTk.PhotoImage(i))
    #             return frames
    #
    #         self.walk_right  = make(self.raw_walk, flip=True)
    #         self.walk_left   = make(self.raw_walk, flip=False)
    #         self.grab_frames = make(self.raw_grab, flip=False)
    #         self.canvas.config(width=self.W, height=self.H)
    #         self.canvas.coords(self.sprite_item, self.W//2, self.H//2)
    #         self.win.geometry(f"{self.W}x{self.H}+{self.x}+{self.y}")
    #
    #     def _draw_fallback(self):
    #         cx, cy = self.W//2, self.H//2
    #         r = min(self.W, self.H)//2 - 6
    #         self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
    #                                 fill="#5B8DEF", outline="#3A6AD4", width=2)
    #         self.canvas.create_text(cx, cy, text="😊", font=("Arial", 24))
    #
    #     # ── CONTEXT MENU ────────────────────────────────────────────────────────
    #
    #     def _show_menu(self, event):
    #         menu = tk.Menu(self.win, tearoff=0,
    #                        bg="#1a1a2e", fg="white",
    #                        activebackground="#5B8DEF", activeforeground="white",
    #                        font=("Segoe UI", 10), bd=0, relief="flat")
    #
    #         menu.add_command(label=f"  🔍  Enlarge  (+{SIZE_STEP}px)", command=self._enlarge)
    #         menu.add_command(label=f"  🔎  Shrink   (-{SIZE_STEP}px)", command=self._shrink)
    #         menu.add_command(label=f"  📐  Reset size",                command=self._reset_size)
    #         menu.add_separator()
    #         if self.walking:
    #             menu.add_command(label="  ⏸   Pause",    command=self._pause)
    #         else:
    #             menu.add_command(label="  ▶️   Resume",   command=self._resume)
    #         menu.add_separator()
    #         menu.add_command(label="  ➕  Add character",             command=self._add_character)
    #         menu.add_command(label=f"  🔄  Change spritesheet",       command=self._change_sheet)
    #         menu.add_separator()
    #         menu.add_command(label=f"  ✕   Hide {self.name}",          command=self._hide)
    #         menu.add_command(label=f"  🗑   Remove {self.name}",         command=self._remove)
    #         menu.tk_popup(event.x_root, event.y_root)
    #
    #     def _enlarge(self):
    #         if self.W + SIZE_STEP <= MAX_SIZE:
    #             self._pause()
    #             self.W += SIZE_STEP
    #             self.H  = int(self.W * self.aspect)
    #             self._rebuild_frames()
    #
    #     def _shrink(self):
    #         if self.W - SIZE_STEP >= MIN_SIZE:
    #             self._pause()
    #             self.W -= SIZE_STEP
    #             self.H  = int(self.W * self.aspect)
    #             self._rebuild_frames()
    #
    #     def _reset_size(self):
    #         self._pause()
    #         self.W = self.base_w
    #         self.H = self.base_h
    #         self._rebuild_frames()
    #
    #     def _pause(self):
    #         self.walking  = False
    #         self.target_x = None
    #
    #     def _resume(self):
    #         self.walking = False
    #         self._pick_next_walk()
    #
    #     def _hide(self):
    #         """Temporarily hide — character stays in JSON, comes back on next launch."""
    #         self.win.destroy()
    #
    #     def _remove(self):
    #         """Permanently remove — deletes from JSON."""
    #         from tkinter import messagebox
    #         if messagebox.askyesno("Remove", f"Permanently remove {self.name}?\nThis cannot be undone.", parent=self.win):
    #             self.manager.remove(self.name)
    #             self.win.destroy()
    #
    #     def _add_character(self):
    #         existing = [c["name"] for c in self.manager.configs]
    #         def on_done(cfg):
    #             self.manager.add(cfg)
    #             DesktopMate(cfg, self.master, self.manager)
    #         SetupDialog(self.master, on_done, existing_names=existing)
    #
    #     def _change_sheet(self):
    #         """Replace this character's walk spritesheet."""
    #         path = filedialog.askopenfilename(
    #             title="Select new walk spritesheet",
    #             filetypes=[("PNG", "*.png")]
    #         )
    #         if not path:
    #             return
    #
    #         # Ask for grid size
    #         cols_str = simpledialog.askstring("Columns", "How many columns?", initialvalue="6", parent=self.win)
    #         rows_str = simpledialog.askstring("Rows",    "How many rows?",    initialvalue="6", parent=self.win)
    #         if not cols_str or not rows_str:
    #             return
    #
    #         try:
    #             cols = int(cols_str)
    #             rows = int(rows_str)
    #         except ValueError:
    #             messagebox.showerror("Error", "Columns and rows must be numbers.", parent=self.win)
    #             return
    #
    #         self._pause()
    #         try:
    #             slice_sheet(path, cols, rows, f"{self.prefix}_walk", force=True)
    #             self.raw_walk = self._load_raw(f"{self.prefix}_walk")
    #             self._rebuild_frames()
    #             self._resume()
    #         except Exception as e:
    #             messagebox.showerror("Error", f"Failed:\n{e}", parent=self.win)
    #
    #     # ── ANIMATION / MOVEMENT ────────────────────────────────────────────────
    #
    #     def _tick(self):
    #         if not self.dragging and self.walking and self.target_x is not None:
    #             diff = self.target_x - self.x
    #             if abs(diff) <= self.speed:
    #                 self.x = self.target_x
    #                 self.walking = False
    #             else:
    #                 self.x += self.speed if diff > 0 else -self.speed
    #             self.win.geometry(f"+{self.x}+{self.y}")
    #
    #         frames = (self.grab_frames if self.mode == "grab"
    #                   else self.walk_right if self.facing_right
    #                   else self.walk_left)
    #
    #         if frames:
    #             self.canvas.itemconfig(self.sprite_item, image=frames[self.frame_index])
    #             self.frame_index = (self.frame_index + 1) % len(frames)
    #
    #         self.win.after(int(1000 / self.fps), self._tick)
    #
    #     def _pick_next_walk(self):
    #         if not self.dragging:
    #             tx = random.randint(40, self.sw - self.W - 40)
    #             self.facing_right = tx > self.x
    #             self.target_x     = tx
    #             self.walking      = True
    #             travel_time = abs(tx - self.x) / self.speed * (1000 / self.fps)
    #         else:
    #             travel_time = 0
    #         self.win.after(int(travel_time), self._pick_next_walk)
    #
    #     def _start_drag(self, e):
    #         self.dragging    = True
    #         self.walking     = False
    #         self.mode        = "grab"
    #         self.frame_index = 0
    #         self.drag_x      = e.x
    #         self.drag_y      = e.y
    #
    #     def _do_drag(self, e):
    #         new_x = self.win.winfo_x() + e.x - self.drag_x
    #         self.facing_right = new_x > self.x
    #         self.x = new_x
    #         self.y = self.win.winfo_y() + e.y - self.drag_y
    #         self.win.geometry(f"+{self.x}+{self.y}")
    #
    #     def _end_drag(self, e):
    #         self.dragging    = False
    #         self.mode        = "walk"
    #         self.frame_index = 0
    #
    #
    # # ─── HOTKEY MANAGER ──────────────────────────────────────────────────────────
    #
    # class HotkeyManager:
    #     """Global hotkey: Ctrl+Shift+H to toggle show/hide all characters."""
    #
    #     HOTKEY = "ctrl+shift+h"
    #
    #     def __init__(self, root, get_mates):
    #         self.root      = root
    #         self.get_mates = get_mates   # callable returning current list of mates
    #         self.visible   = True
    #
    #         if not KEYBOARD_AVAILABLE:
    #             return
    #
    #         # Run in background thread — keyboard library needs its own thread
    #         threading.Thread(target=self._listen, daemon=True).start()
    #         print(f"[Hotkey] {self.HOTKEY} → toggle show/hide all characters")
    #
    #     def _listen(self):
    #         keyboard.add_hotkey(self.HOTKEY, self._toggle)
    #         keyboard.wait()
    #
    #     def _toggle(self):
    #         self.visible = not self.visible
    #         # Must update tkinter from main thread
    #         self.root.after(0, self._apply)
    #
    #     def _apply(self):
    #         for mate in self.get_mates():
    #             try:
    #                 if self.visible:
    #                     mate.win.deiconify()
    #                 else:
    #                     mate.win.withdraw()
    #             except Exception:
    #                 pass
    #
    #
    # # ─── MAIN ─────────────────────────────────────────────────────────────────────
    #
    # if __name__ == "__main__":
    #     os.makedirs(SPRITES_DIR, exist_ok=True)
    #
    #     root = tk.Tk()
    #     root.withdraw()
    #
    #     manager = CharacterManager()
    #     mates   = []
    #
    #     def launch(cfg):
    #         mates.append(DesktopMate(cfg, root, manager))
    #
    #     if not manager.configs:
    #         # First time — show setup dialog
    #         def on_first(cfg):
    #             manager.add(cfg)
    #             launch(cfg)
    #         SetupDialog(root, on_first)
    #     else:
    #         for cfg in manager.configs:
    #             launch(cfg)
    #
    #     # Global hotkey: Ctrl+Shift+H to toggle all characters
    #     hotkey = HotkeyManager(root, lambda: mates)
    #     if KEYBOARD_AVAILABLE:
    #         print("[Hotkey] Press Ctrl+Shift+H to hide/show all characters")
    #     else:
    #         print("[Hotkey] pip install keyboard to enable Ctrl+Shift+H toggle")
    #
    #     root.mainloop()
