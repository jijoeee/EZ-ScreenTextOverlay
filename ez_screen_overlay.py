# ==============================================================================
# EZ SCREEN OVERLAY TOOL v1.0 - WITH EDGE SNAPPING
# ==============================================================================
# HOW TO RUN:
#   1. pip install keyboard customtkinter
#   2. python ez_screen_overlay.py
#
# HOW TO PACKAGE (Windows):
#   pyinstaller --noconfirm --onefile --windowed --name "EZ_ScreenOverlay" --collect-all customtkinter ez_screen_overlay.py
# ==============================================================================

import tkinter as tk
from tkinter import colorchooser, simpledialog, messagebox, filedialog
import customtkinter as ctk
import json
import os
import sys
import ctypes
import keyboard

# --- Path Handling ---
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
SESSION_DIR = os.path.join(BASE_DIR, "Saved Session")
DEFAULT_PRESETS_FILE = os.path.join(BASE_DIR, "default_presets.json")

if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

# --- App Configuration ---
APP_WIDTH = 950
APP_HEIGHT = 500

ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  

# ==========================================
# PRESET MANAGER
# ==========================================
class PresetManager:
    def __init__(self, filename):
        self.filename = filename
        self.presets = []
        self.load_presets()

    def load_presets(self):
        if not os.path.exists(self.filename):
            self.presets = []
            return
        try:
            with open(self.filename, 'r') as f:
                self.presets = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.presets = []

    def save_presets(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.presets, f, indent=4)
        except IOError as e:
            print(f"Error saving presets: {e}")

    def import_session(self, filepath):
        try:
            with open(filepath, 'r') as f:
                self.presets = json.load(f)
            self.filename = filepath
            return True
        except Exception:
            return False

    def export_session(self, filepath):
        try:
            with open(filepath, 'w') as f:
                json.dump(self.presets, f, indent=4)
            self.filename = filepath
            return True
        except Exception:
            return False

    def add_preset(self, preset_dict):
        for p in self.presets:
            if p['name'] == preset_dict['name']:
                p.update(preset_dict)
                self.save_presets()
                return
        self.presets.append(preset_dict)
        self.save_presets()

    def delete_preset(self, name):
        self.presets = [p for p in self.presets if p['name'] != name]
        self.save_presets()

    def get_names(self):
        return [p['name'] for p in self.presets]

    def get_preset(self, name):
        for p in self.presets:
            if p['name'] == name:
                return p
        return None

# ==========================================
# FLOATING MINI TOOLBAR (WITH EDGE SNAP)
# ==========================================
class MiniToolbar:
    def __init__(self, main_app):
        self.main_app = main_app
        self.window = tk.Toplevel(main_app.root)
        self.window.geometry("320x80")
        self.window.overrideredirect(True) # Removes OS borders
        self.window.attributes("-topmost", True)
        self.window.configure(bg="#1e1e1e")
        
        # Center the toolbar on launch
        sw = self.window.winfo_screenwidth()
        self.window.geometry(f"+{sw//2 - 160}+50")

        self._offsetx = 0
        self._offsety = 0
        
        # Auto-hide states
        self.snapped_edge = None
        self.is_hidden = False

        self.build_ui()
        self.update_display()

    def build_ui(self):
        # 1. Custom Title Bar (Draggable)
        title_bar = ctk.CTkFrame(self.window, height=30, corner_radius=0, fg_color="#2b2b2b")
        title_bar.pack(fill=tk.X, side=tk.TOP)
        title_bar.pack_propagate(False)

        title_bar.bind("<Button-1>", self.click_window)
        title_bar.bind("<B1-Motion>", self.drag_window)
        title_bar.bind("<ButtonRelease-1>", self.on_drag_release)

        # Drag Hint (Text updated)
        drag_lbl = ctk.CTkLabel(title_bar, text="⠿ EZ Toolbar", font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaaaaa")
        drag_lbl.pack(side=tk.LEFT, padx=10)
        drag_lbl.bind("<Button-1>", self.click_window)
        drag_lbl.bind("<B1-Motion>", self.drag_window)
        drag_lbl.bind("<ButtonRelease-1>", self.on_drag_release)

        # Window Controls
        btn_close = ctk.CTkButton(title_bar, text="✕", width=30, height=20, fg_color="transparent", hover_color="#c22929", command=self.close_toolbar)
        btn_close.pack(side=tk.RIGHT, padx=2)
        
        btn_min = ctk.CTkButton(title_bar, text="—", width=30, height=20, fg_color="transparent", hover_color="#555555", command=self.minimize_toolbar)
        btn_min.pack(side=tk.RIGHT, padx=2)

        # 2. Status / Preset Name Display
        self.lbl_preset = ctk.CTkLabel(self.window, text="No Preset Loaded", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00d4aa")
        self.lbl_preset.pack(fill=tk.X, pady=(2, 2))

        # 3. Action Buttons
        btn_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        btn_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        b_kw = {"height": 24, "font": ctk.CTkFont(size=11, weight="bold")}
        
        btn_prev = ctk.CTkButton(btn_frame, text="◀ Prev", width=60, fg_color="#444444", hover_color="#666666", command=self.main_app.prev_preset, **b_kw)
        btn_prev.pack(side=tk.LEFT, expand=True, padx=2)

        btn_show = ctk.CTkButton(btn_frame, text="SHOW", width=70, fg_color="#107c41", hover_color="#0c5e31", command=self.main_app.show_overlay, **b_kw)
        btn_show.pack(side=tk.LEFT, expand=True, padx=2)

        btn_hide = ctk.CTkButton(btn_frame, text="HIDE", width=70, fg_color="#c22929", hover_color="#9c1f1f", command=self.main_app.hide_overlay, **b_kw)
        btn_hide.pack(side=tk.LEFT, expand=True, padx=2)

        btn_next = ctk.CTkButton(btn_frame, text="Next ▶", width=60, fg_color="#444444", hover_color="#666666", command=self.main_app.next_preset, **b_kw)
        btn_next.pack(side=tk.LEFT, expand=True, padx=2)

    def update_display(self):
        current = self.main_app.preset_menu.get()
        if current and current != "No Presets Saved":
            self.lbl_preset.configure(text=f"Loaded: {current}")
        else:
            self.lbl_preset.configure(text="No Preset Selected")

    # --- Window Drag & Snapping Mechanics ---
    def click_window(self, event):
        self.snapped_edge = None # Unsnap when clicked
        self._offsetx = event.x
        self._offsety = event.y

    def drag_window(self, event):
        x = self.window.winfo_pointerx() - self._offsetx
        y = self.window.winfo_pointery() - self._offsety
        self.window.geometry(f"+{x}+{y}")

    def on_drag_release(self, event):
        y = self.window.winfo_y()
        sh = self.window.winfo_screenheight()
        threshold = 30 # Trigger snapping if released within 30px of top or bottom
        
        was_snapped = self.snapped_edge is not None

        if y <= threshold:
            self.snapped_edge = 'top'
            self.is_hidden = False
            if not was_snapped:
                self._check_snap_hover()
        elif y + self.window.winfo_height() >= sh - threshold:
            self.snapped_edge = 'bottom'
            self.is_hidden = False
            if not was_snapped:
                self._check_snap_hover()
        else:
            self.snapped_edge = None
            self.is_hidden = False

    def _check_snap_hover(self):
        if not self.snapped_edge:
            return

        px = self.window.winfo_pointerx()
        py = self.window.winfo_pointery()
        wx = self.window.winfo_rootx()
        wy = self.window.winfo_rooty()
        ww = self.window.winfo_width()
        wh = self.window.winfo_height()

        # Is the mouse cursor over the toolbar?
        is_hovering = (wx <= px <= wx + ww) and (wy <= py <= wy + wh)

        if is_hovering and self.is_hidden:
            self.snap_show()
        elif not is_hovering and not self.is_hidden:
            self.snap_hide()

        # Poll again in 100ms
        self.window.after(100, self._check_snap_hover)

    def snap_hide(self):
        self.is_hidden = True
        wx = self.window.winfo_x()
        wh = self.window.winfo_height()
        sh = self.window.winfo_screenheight()
        leave_pixels = 8 # Leave a tiny 8px bar to hover over
        
        if self.snapped_edge == 'top':
            self.window.geometry(f"+{wx}+{-wh + leave_pixels}")
        elif self.snapped_edge == 'bottom':
            self.window.geometry(f"+{wx}+{sh - leave_pixels}")

    def snap_show(self):
        self.is_hidden = False
        wx = self.window.winfo_x()
        wh = self.window.winfo_height()
        sh = self.window.winfo_screenheight()
        
        if self.snapped_edge == 'top':
            self.window.geometry(f"+{wx}+0")
        elif self.snapped_edge == 'bottom':
            self.window.geometry(f"+{wx}+{sh - wh}")

    def minimize_toolbar(self):
        self.window.withdraw()
        self.main_app.update_status("Mini Toolbar minimized.")

    def close_toolbar(self):
        self.window.destroy()
        self.main_app.mini_toolbar = None
        self.main_app.update_status("Mini Toolbar closed.")

    def restore(self):
        self.window.deiconify()
        self.window.lift()

# ==========================================
# MAIN APPLICATION
# ==========================================
class OverlayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EZ Screen Overlay Tool v1.0")
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True) 

        self.preset_manager = PresetManager(DEFAULT_PRESETS_FILE)
        self.current_preset_index = -1

        self.font_size_var = ctk.StringVar(value="48")
        self.font_color_var = ctk.StringVar(value="#FFFFFF")
        self.bg_color_var = ctk.StringVar(value="#000000")
        self.is_transparent_var = ctk.BooleanVar(value=True)
        self.position_var = ctk.StringVar(value="Bottom-Center")
        self.timer_var = ctk.StringVar(value="Manual")
        
        self.offset_x = 0
        self.offset_y = 0
        
        self.overlay_window = None
        self.overlay_label = None
        self.mini_toolbar = None
        self.fade_job = None
        self.hide_job = None
        self.is_visible = False
        
        self.build_ui()
        self.setup_hotkeys()
        self.update_status("System Ready.")

    def build_ui(self):
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # ==========================================
        # COLUMN 1: TEXT INPUT
        # ==========================================
        self.col1 = ctk.CTkFrame(self.main_container)
        self.col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        ctk.CTkLabel(self.col1, text="Overlay Text", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        
        self.text_input = ctk.CTkTextbox(self.col1, font=ctk.CTkFont(size=16), wrap="word")
        self.text_input.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        self.text_input.bind('<KeyRelease>', self.sync_overlay_event)

        # ==========================================
        # COLUMN 2: SETTINGS & NUDGE
        # ==========================================
        self.col2 = ctk.CTkFrame(self.main_container, width=300)
        self.col2.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        self.col2.pack_propagate(False) 

        ctk.CTkLabel(self.col2, text="Appearance & Layout", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15, 10))

        row1 = ctk.CTkFrame(self.col2, fg_color="transparent")
        row1.pack(fill=tk.X, padx=15, pady=5)
        
        ctk.CTkLabel(row1, text="Size:", width=40, anchor="w").pack(side=tk.LEFT)
        ctk.CTkOptionMenu(row1, variable=self.font_size_var, values=["16", "24", "32", "40", "48", "60", "72", "96"], width=70, command=self.sync_overlay).pack(side=tk.LEFT, padx=(0, 10))

        ctk.CTkLabel(row1, text="Pos:", width=30, anchor="w").pack(side=tk.LEFT)
        ctk.CTkOptionMenu(row1, variable=self.position_var, values=["Top-Left", "Top-Center", "Top-Right", "Center", "Bottom-Left", "Bottom-Center", "Bottom-Right"], width=120, command=self.on_position_change).pack(side=tk.LEFT)

        row2 = ctk.CTkFrame(self.col2, fg_color="transparent")
        row2.pack(fill=tk.X, padx=15, pady=10)

        self.btn_font_color = ctk.CTkButton(row2, text="Font Color", fg_color=self.font_color_var.get(), text_color="#000000", width=120, command=self.pick_font_color)
        self.btn_font_color.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_bg_color = ctk.CTkButton(row2, text="BG Color", fg_color=self.bg_color_var.get(), text_color="#FFFFFF", width=120, command=self.pick_bg_color)
        self.btn_bg_color.pack(side=tk.LEFT)

        ctk.CTkSwitch(self.col2, text="Transparent Background", variable=self.is_transparent_var, command=self.sync_overlay).pack(anchor="w", padx=15, pady=10)

        row3 = ctk.CTkFrame(self.col2, fg_color="transparent")
        row3.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(row3, text="Auto-Hide Timer:", anchor="w").pack(side=tk.LEFT, padx=(0, 10))
        ctk.CTkOptionMenu(row3, variable=self.timer_var, values=["Manual", "3s", "5s", "10s", "15s", "30s"], width=100).pack(side=tk.LEFT)

        nudge_frame = ctk.CTkFrame(self.col2, fg_color="transparent")
        nudge_frame.pack(fill=tk.X, padx=15, pady=(10, 0))
        
        ctk.CTkLabel(nudge_frame, text="Fine-tune Pos:", anchor="w").pack(side=tk.LEFT, padx=(0, 10))
        grid_frame = ctk.CTkFrame(nudge_frame, fg_color="transparent")
        grid_frame.pack(side=tk.LEFT)

        btn_kw = {"width": 30, "height": 30, "font": ctk.CTkFont(size=14)}
        ctk.CTkButton(grid_frame, text="▲", command=lambda: self.nudge(0, -15), **btn_kw).grid(row=0, column=1, pady=2)
        ctk.CTkButton(grid_frame, text="◄", command=lambda: self.nudge(-15, 0), **btn_kw).grid(row=1, column=0, padx=2)
        ctk.CTkButton(grid_frame, text="●", fg_color="#555", hover_color="#777", command=self.reset_nudge, **btn_kw).grid(row=1, column=1, padx=2)
        ctk.CTkButton(grid_frame, text="►", command=lambda: self.nudge(15, 0), **btn_kw).grid(row=1, column=2, padx=2)
        ctk.CTkButton(grid_frame, text="▼", command=lambda: self.nudge(0, 15), **btn_kw).grid(row=2, column=1, pady=2)

        # ==========================================
        # COLUMN 3: PRESETS & ACTIONS
        # ==========================================
        self.col3 = ctk.CTkFrame(self.main_container, width=280)
        self.col3.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        self.col3.pack_propagate(False)

        # Session & Presets
        preset_frame = ctk.CTkFrame(self.col3, fg_color="#2b2b2b")
        preset_frame.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        session_frame = ctk.CTkFrame(preset_frame, fg_color="transparent")
        session_frame.pack(fill=tk.X, padx=10, pady=(10, 10))
        ctk.CTkButton(session_frame, text="💾 Save", width=90, fg_color="#1f5a82", command=self.save_session).pack(side=tk.LEFT, expand=True, padx=(0, 2))
        ctk.CTkButton(session_frame, text="📂 Load", width=90, fg_color="#1f5a82", command=self.load_session).pack(side=tk.RIGHT, expand=True)

        ctk.CTkLabel(preset_frame, text="Individual Presets", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(0, 2))
        
        self.preset_menu = ctk.CTkOptionMenu(preset_frame, values=["No Presets Saved"] if not self.preset_manager.get_names() else self.preset_manager.get_names(), command=self.load_preset_ui)
        self.preset_menu.pack(fill=tk.X, padx=10, pady=5)
        
        # CORRECTED BUTTON LAYOUT
        p_btn_frame = ctk.CTkFrame(preset_frame, fg_color="transparent")
        p_btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ctk.CTkButton(p_btn_frame, text="Save Preset", command=self.save_preset_ui).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ctk.CTkButton(p_btn_frame, text="Delete", width=60, fg_color="#636363", hover_color="#8a2020", command=self.delete_preset_ui).pack(side=tk.RIGHT)

        # Launch Toolbar Button
        ctk.CTkButton(self.col3, text="🚀 LAUNCH MINI TOOLBAR", font=ctk.CTkFont(size=13, weight="bold"), height=35, fg_color="#c97e06", hover_color="#a86905", command=self.launch_toolbar).pack(fill=tk.X, padx=15, pady=5)

        # Action Buttons
        self.btn_show = ctk.CTkButton(self.col3, text="SHOW OVERLAY", font=ctk.CTkFont(size=15, weight="bold"), height=40, fg_color="#107c41", command=self.show_overlay)
        self.btn_show.pack(fill=tk.X, padx=15, pady=(5, 5))

        self.btn_hide = ctk.CTkButton(self.col3, text="HIDE OVERLAY", font=ctk.CTkFont(size=15, weight="bold"), height=40, fg_color="#c22929", command=self.hide_overlay)
        self.btn_hide.pack(fill=tk.X, padx=15, pady=0)

        # Status Bar
        self.status_var = ctk.StringVar()
        self.status_bar = ctk.CTkLabel(self.root, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color="#aaaaaa", anchor="w", fg_color="#1e1e1e", height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10)

    # --- Methods ---
    def launch_toolbar(self):
        if self.mini_toolbar is None or not self.mini_toolbar.window.winfo_exists():
            self.mini_toolbar = MiniToolbar(self)
        else:
            self.mini_toolbar.restore()

    def sync_toolbar_display(self):
        if self.mini_toolbar and self.mini_toolbar.window.winfo_exists():
            self.mini_toolbar.update_display()

    def pick_font_color(self):
        color = colorchooser.askcolor(initialcolor=self.font_color_var.get(), title="Select Font Color")[1]
        if color:
            self.font_color_var.set(color)
            self.btn_font_color.configure(fg_color=color, text_color="#000000" if self.is_bright(color) else "#FFFFFF")
            self.sync_overlay()

    def pick_bg_color(self):
        color = colorchooser.askcolor(initialcolor=self.bg_color_var.get(), title="Select Background Color")[1]
        if color:
            self.bg_color_var.set(color)
            self.btn_bg_color.configure(fg_color=color, text_color="#000000" if self.is_bright(color) else "#FFFFFF")
            self.sync_overlay()

    def is_bright(self, hex_color):
        hex_color = hex_color.lstrip('#')
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (0.299*r + 0.587*g + 0.114*b) > 160
        except ValueError: return False

    def on_position_change(self, value):
        self.reset_nudge()
        self.sync_overlay()

    def nudge(self, dx, dy):
        self.offset_x += dx
        self.offset_y += dy
        if self.is_visible and self.overlay_window:
            self.position_overlay()

    def reset_nudge(self):
        self.offset_x = 0
        self.offset_y = 0
        if self.is_visible and self.overlay_window:
            self.position_overlay()

    def save_session(self):
        filepath = filedialog.asksaveasfilename(initialdir=SESSION_DIR, defaultextension=".json", filetypes=[("JSON Session", "*.json")], title="Save Session")
        if filepath and self.preset_manager.export_session(filepath):
            self.update_status(f"Session saved.")

    def load_session(self):
        filepath = filedialog.askopenfilename(initialdir=SESSION_DIR, filetypes=[("JSON Session", "*.json")], title="Load Session")
        if filepath and self.preset_manager.import_session(filepath):
            self.update_preset_dropdown()
            self.update_status(f"Session loaded.")

    def get_current_state_dict(self):
        return {
            "text": self.text_input.get("1.0", tk.END).strip(),
            "font_size": self.font_size_var.get(), "font_color": self.font_color_var.get(),
            "bg_color": self.bg_color_var.get(), "is_transparent": self.is_transparent_var.get(),
            "position": self.position_var.get(), "timer": self.timer_var.get(),
            "offset_x": self.offset_x, "offset_y": self.offset_y
        }

    def save_preset_ui(self):
        name = simpledialog.askstring("Save", "Preset name:", parent=self.root)
        if not name: return
        data = self.get_current_state_dict()
        data['name'] = name
        self.preset_manager.add_preset(data)
        self.update_preset_dropdown()
        self.preset_menu.set(name)
        self.sync_toolbar_display()
        self.update_status(f"Preset '{name}' saved.")

    def delete_preset_ui(self):
        name = self.preset_menu.get()
        if not name or name == "No Presets Saved": return
        if messagebox.askyesno("Delete", f"Delete '{name}'?"):
            self.preset_manager.delete_preset(name)
            self.update_preset_dropdown()
            self.sync_toolbar_display()

    def update_preset_dropdown(self):
        names = self.preset_manager.get_names()
        if not names:
            self.preset_menu.configure(values=["No Presets Saved"])
            self.preset_menu.set("No Presets Saved")
        else:
            self.preset_menu.configure(values=names)

    def load_preset_ui(self, selected_name):
        if selected_name == "No Presets Saved": return
        data = self.preset_manager.get_preset(selected_name)
        if data:
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert(tk.END, data.get("text", ""))
            self.font_size_var.set(data.get("font_size", "48"))
            self.font_color_var.set(data.get("font_color", "#FFFFFF"))
            self.bg_color_var.set(data.get("bg_color", "#000000"))
            self.is_transparent_var.set(data.get("is_transparent", True))
            self.position_var.set(data.get("position", "Bottom-Center"))
            self.timer_var.set(data.get("timer", "Manual"))
            self.offset_x = data.get("offset_x", 0)
            self.offset_y = data.get("offset_y", 0)
            
            self.btn_font_color.configure(fg_color=self.font_color_var.get(), text_color="#000000" if self.is_bright(self.font_color_var.get()) else "#FFFFFF")
            self.btn_bg_color.configure(fg_color=self.bg_color_var.get(), text_color="#000000" if self.is_bright(self.bg_color_var.get()) else "#FFFFFF")
            
            self.current_preset_index = self.preset_manager.get_names().index(selected_name)
            self.sync_overlay()
            self.sync_toolbar_display()
            self.update_status(f"Loaded: '{selected_name}'.")

    # --- Hotkeys & Preset Navigation ---
    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey('ctrl+shift+s', lambda: self.root.after(0, self.show_overlay))
            keyboard.add_hotkey('ctrl+shift+h', lambda: self.root.after(0, self.hide_overlay))
            keyboard.add_hotkey('ctrl+shift+n', lambda: self.root.after(0, self.next_preset_and_show))
        except Exception: pass

    def next_preset(self):
        names = self.preset_manager.get_names()
        if not names: return
        self.current_preset_index = (self.current_preset_index + 1) % len(names)
        self.preset_menu.set(names[self.current_preset_index])
        self.load_preset_ui(names[self.current_preset_index])

    def prev_preset(self):
        names = self.preset_manager.get_names()
        if not names: return
        self.current_preset_index = (self.current_preset_index - 1) % len(names)
        self.preset_menu.set(names[self.current_preset_index])
        self.load_preset_ui(names[self.current_preset_index])

    def next_preset_and_show(self):
        self.next_preset()
        self.show_overlay()

    # --- Overlay Rendering Engine ---
    def sync_overlay_event(self, event=None):
        self.sync_overlay()

    def sync_overlay(self, value=None):
        if self.is_visible and self.overlay_window:
            self.create_overlay_window()
            self.overlay_window.attributes("-alpha", 1.0)

    def create_overlay_window(self):
        if self.overlay_window is not None:
            self.overlay_window.destroy()

        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.overrideredirect(True)
        self.overlay_window.attributes("-topmost", True)
        self.overlay_window.attributes("-alpha", 0.0) 

        self.make_window_click_through(self.overlay_window)

        bg_color = self.bg_color_var.get()
        if self.is_transparent_var.get():
            trans_key = "#000001"
            self.overlay_window.config(bg=trans_key)
            self.overlay_window.wm_attributes("-transparentcolor", trans_key)
            label_bg = trans_key
        else:
            self.overlay_window.config(bg=bg_color)
            label_bg = bg_color

        font = ("Helvetica", int(self.font_size_var.get()), "bold")
        self.overlay_label = tk.Label(self.overlay_window, text=self.text_input.get("1.0", tk.END).strip(), font=font, fg=self.font_color_var.get(), bg=label_bg, justify=tk.CENTER)
        self.overlay_label.pack(padx=20, pady=20)
        self.position_overlay()

    def make_window_click_through(self, window):
        try:
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            GWL_EXSTYLE = -20
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except Exception: pass 

    def position_overlay(self):
        if not self.overlay_window: return
        self.overlay_window.update_idletasks()
        w = self.overlay_window.winfo_width()
        h = self.overlay_window.winfo_height()
        sw = self.overlay_window.winfo_screenwidth()
        sh = self.overlay_window.winfo_screenheight()

        pos = self.position_var.get()
        pad = 60

        if pos == "Top-Left": x, y = pad, pad
        elif pos == "Top-Center": x, y = (sw - w) // 2, pad
        elif pos == "Top-Right": x, y = sw - w - pad, pad
        elif pos == "Center": x, y = (sw - w) // 2, (sh - h) // 2
        elif pos == "Bottom-Left": x, y = pad, sh - h - pad - 60
        elif pos == "Bottom-Right": x, y = sw - w - pad, sh - h - pad - 60
        else: x, y = (sw - w) // 2, sh - h - pad - 60

        self.overlay_window.geometry(f"+{x+self.offset_x}+{y+self.offset_y}")

    def show_overlay(self):
        text = self.text_input.get("1.0", tk.END).strip()
        if not text: return

        if self.fade_job: self.root.after_cancel(self.fade_job)
        if self.hide_job: self.root.after_cancel(self.hide_job)

        self.create_overlay_window()
        self.is_visible = True
        self.fade_in(0.0)

        timer_val = self.timer_var.get()
        if timer_val != "Manual":
            ms = int(timer_val.replace("s", "")) * 1000
            self.hide_job = self.root.after(ms, self.hide_overlay)

    def fade_in(self, alpha):
        if not self.overlay_window: return
        target = 0.90 if not self.is_transparent_var.get() else 1.0 
        alpha += 0.1
        if alpha >= target:
            self.overlay_window.attributes("-alpha", target)
        else:
            self.overlay_window.attributes("-alpha", alpha)
            self.fade_job = self.root.after(25, lambda: self.fade_in(alpha))

    def hide_overlay(self):
        if not self.is_visible or not self.overlay_window: return
        if self.fade_job: self.root.after_cancel(self.fade_job)
        if self.hide_job: self.root.after_cancel(self.hide_job)
        self.fade_out(self.overlay_window.attributes("-alpha"))

    def fade_out(self, alpha):
        if not self.overlay_window: return
        alpha -= 0.1
        if alpha <= 0.0:
            self.overlay_window.destroy()
            self.overlay_window = None
            self.is_visible = False
        else:
            self.overlay_window.attributes("-alpha", alpha)
            self.fade_job = self.root.after(25, lambda: self.fade_out(alpha))

    def update_status(self, msg):
        self.status_var.set(f" STATUS: {msg}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = OverlayApp(root)
    root.mainloop()
