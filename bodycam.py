# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import threading
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import ttk

APP_VERSION = "1.0.1"
ABO = f"Axon Bodycam Overlay {APP_VERSION}"
GITHUB_REPO = "HezoY/Axon-Bodycam-Overlay"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

try:
    import win32con
    import win32gui
except Exception:
    win32con = win32gui = None

try:
    import keyboard
except Exception:
    keyboard = None

try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

DEPARTMENTS = {
    "LSPD (Los Santos Police Department)": "Los Santos Police Department",
    "LSSD (Los Santos County Sheriff's Department)": "Los Santos County Sheriff's Dept.",
    "BCSO (Blaine County Sheriff's Office)": "Blaine County Sheriff's Office",
    "SAHP (San Andreas Highway Patrol)": "San Andreas Highway Patrol"
}

GUI_LAYOUT = {
    "window_size": {"width": 370, "height": 475},
    "title": {"x": 58, "y": 5, "width": 250, "height": 24},
    "name_label": {"x": 0, "y": 36, "width": 250, "height": 20},
    "name_entry": {"x": 0, "y": 57, "width": 350, "height": 24},
    "badge_label": {"x": 0, "y": 84, "width": 250, "height": 20},
    "badge_entry": {"x": 0, "y": 105, "width": 350, "height": 24},
    "department_label": {"x": 0, "y": 132, "width": 250, "height": 20},
    "department_combo": {"x": 0, "y": 153, "width": 350, "height": 24},
    "x_slider": {"x": 0, "y": 180, "width": 350, "height": 50},
    "y_slider": {"x": 0, "y": 228, "width": 350, "height": 50},
    "scale_slider": {"x": 0, "y": 276, "width": 350, "height": 50},
    "logo_offset_slider": {"x": 0, "y": 326, "width": 350, "height": 50},
    "overlay_button": {"x": 0, "y": 378, "width": 350, "height": 34},
    "update_status": {"x": 0, "y": 416, "width": 350, "height": 20},
    "creator_label": {"x": 0, "y": 438, "width": 350, "height": 20}
}

ABO_LAYOUT = {
    "window_size": {"width": 700, "height": 165},
    "rec_label": {"x": 180, "y": 32},
    "dot": {"x": 225, "y": 28, "width": 10, "height": 10},
    "axon_label": {"x": 245, "y": 32},
    "tm_label": {"x": 392, "y": 27},
    "identity_label": {"x": 400, "y": 60},
    "dept_label": {"x": 400, "y": 90},
    "time_label": {"x": 400, "y": 120},
    "logo": {"x": 0, "y": -5, "scale": 1.0}
}
LOGO_HEIGHT = 98

class AxonApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{ABO} - Control Panel")
        gui_width = GUI_LAYOUT["window_size"]["width"]
        gui_height = GUI_LAYOUT["window_size"]["height"]
        self.root.geometry(f"{gui_width}x{gui_height}")

        self._frozen = getattr(sys, 'frozen', False)
        base_dir = os.path.dirname(sys.executable) if self._frozen else os.path.dirname(os.path.abspath(__file__))
        self._settings_path = os.path.join(base_dir, 'settings.json')

        main_frame = ttk.Frame(root, padding="8")
        main_frame.pack(fill="both", expand=True)

        gui_widgets = {
            "title": ttk.Label(main_frame, text=f"{ABO}", font=("Arial", 13, "bold")),
            "name_label": ttk.Label(main_frame, text="Officer name (First Last):", font=("Arial", 9)),
            "badge_label": ttk.Label(main_frame, text="Badge / ID:", font=("Arial", 9)),
            "department_label": ttk.Label(main_frame, text="Select department:", font=("Arial", 9))
        }

        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.bind('<FocusOut>', lambda e: self.save_settings())

        self.badge_entry = ttk.Entry(main_frame, width=40)
        self.badge_entry.bind('<FocusOut>', lambda e: self.save_settings())

        self.dept_combo = ttk.Combobox(main_frame, values=list(DEPARTMENTS.keys()), state="readonly")
        self.dept_combo.bind('<<ComboboxSelected>>', lambda e: self.save_settings())

        slider_options = {"font": ("Arial", 8), "bd": 0, "highlightthickness": 0}
        self.x_slider = tk.Scale(main_frame, from_=0, to=2000, orient="horizontal", label="X Position", command=self.on_slider_move, **slider_options)
        self.y_slider = tk.Scale(main_frame, from_=0, to=1000, orient="horizontal", label="Y Position", command=self.on_slider_move, **slider_options)
        self.scale_slider = tk.Scale(main_frame, from_=0.5, to=1.0, resolution=0.01, orient="horizontal", label="Scale", command=self.on_slider_move, **slider_options)
        self.logo_offset_slider = tk.Scale(main_frame, from_=-300, to=300, resolution=1, orient="horizontal", label="AXON.png horizontal offset", command=self.on_slider_move, **slider_options)

        self.overlay_button = ttk.Button(main_frame, text="Create/Update", command=self.start_overlay)
        self.update_status = tk.StringVar(value="Checking for updates...")
        self.update_status_label = ttk.Label(main_frame, textvariable=self.update_status, font=("Arial", 8), cursor="hand2")
        self.update_status_label.bind("<Button-1>", self.on_update_label_click)
        self.creator_label = ttk.Label(main_frame, text="Created by HezoY | Licensed under the MIT License", font=("Arial", 8))

        self.latest_release_url = f"https://github.com/{GITHUB_REPO}/releases"

        gui_widgets.update({
            "name_entry": self.name_entry,
            "badge_entry": self.badge_entry,
            "department_combo": self.dept_combo,
            "x_slider": self.x_slider,
            "y_slider": self.y_slider,
            "scale_slider": self.scale_slider,
            "logo_offset_slider": self.logo_offset_slider,
            "overlay_button": self.overlay_button,
            "update_status": self.update_status_label,
            "creator_label": self.creator_label
        })

        for name, widget in gui_widgets.items():
            position = GUI_LAYOUT[name]
            widget.place(
                x=position["x"],
                y=position["y"],
                width=position["width"],
                height=position["height"]
            )

        for slider in (self.x_slider, self.y_slider, self.scale_slider, self.logo_offset_slider):
            slider.bind('<ButtonRelease-1>', lambda e: self.save_settings(), add='+')

        if keyboard is not None:
            try:
                keyboard.add_hotkey('F10', self.safe_toggle_trigger)
            except Exception:
                pass

        self.load_settings()
        threading.Thread(target=self.check_updates, daemon=True).start()

    def check_updates(self):
        try:
            req = urllib.request.Request(
                GITHUB_RELEASES_URL,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    latest_tag = data.get("tag_name", "").lstrip("v").strip()
                    self.latest_release_url = data.get("html_url", self.latest_release_url)
                    
                    if latest_tag and latest_tag != APP_VERSION:
                        self.root.after(0, lambda: self.update_status.set(f"Update available: v{APP_VERSION} (Click here)"))
                    else:
                        self.root.after(0, lambda: self.update_status.set("App is up to date"))
                else:
                    self.root.after(0, lambda: self.update_status.set("Check update failed"))
        except Exception:
            self.root.after(0, lambda: self.update_status.set("Offline / Unable to check update"))

    def on_update_label_click(self, event):
        if "Update available" in self.update_status.get():
            webbrowser.open(self.latest_release_url)

    def start_overlay(self):
        name = self.name_entry.get().strip()
        badge = self.badge_entry.get().strip()
        identity_line = f"{badge} | {name} [{badge}]"
        department_key = self.dept_combo.get()
        dept = DEPARTMENTS.get(department_key)
        if dept is None:
            department_key = next(iter(DEPARTMENTS))
            self.dept_combo.set(department_key)
            dept = DEPARTMENTS[department_key]

        self.save_settings()
        if not hasattr(self, 'overlay') or not self.overlay_window.winfo_exists():
            self.overlay_window = tk.Toplevel(self.root)
            self.overlay = AxonOverlay(self.overlay_window, identity_line, dept)
        self.overlay.update_text(identity_line, dept)
        self.on_slider_move()

    def on_slider_move(self, val=None):
        if hasattr(self, 'overlay') and self.overlay_window.winfo_exists():
            geometry = (
                int(self.x_slider.get()),
                int(self.y_slider.get()),
                float(self.scale_slider.get()),
                int(self.logo_offset_slider.get())
            )
            self._pending_geometry = geometry
            if not getattr(self, "_geometry_update_pending", False):
                self._geometry_update_pending = True
                self.root.after_idle(self._apply_pending_geometry)

    def _apply_pending_geometry(self):
        self._geometry_update_pending = False
        if hasattr(self, "_pending_geometry") and self.overlay_window.winfo_exists():
            self.overlay.update_geometry(*self._pending_geometry)

    def save_settings(self):
        data = {
            'name': self.name_entry.get(),
            'badge': self.badge_entry.get(),
            'dept': self.dept_combo.get(),
            'x': self.x_slider.get(),
            'y': self.y_slider.get(),
            'scale': self.scale_slider.get(),
            'logo_offset': self.logo_offset_slider.get()
        }
        try:
            with open(self._settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except (OSError, TypeError, ValueError):
            pass

    def load_settings(self):
        if os.path.exists(self._settings_path):
            try:
                with open(self._settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Settings must be a JSON object")
                self.name_entry.insert(0, str(data.get('name', '')))
                self.badge_entry.insert(0, str(data.get('badge', '')))
                department = data.get('dept', next(iter(DEPARTMENTS)))
                self.dept_combo.set(department if department in DEPARTMENTS else next(iter(DEPARTMENTS)))
                self.x_slider.set(data.get('x', 100))
                self.y_slider.set(data.get('y', 100))
                self.scale_slider.set(data.get('scale', 1.0))
                self.logo_offset_slider.set(data.get('logo_offset', 0))
            except (OSError, json.JSONDecodeError, TypeError, ValueError, tk.TclError):
                self.dept_combo.set(next(iter(DEPARTMENTS)))

    def safe_toggle_trigger(self):
        self.root.after(10, self.toggle_visibility)

    def toggle_visibility(self):
        if hasattr(self, 'overlay_window') and self.overlay_window.winfo_exists():
            if self.overlay_window.winfo_viewable():
                self.overlay_window.withdraw()
            else:
                self.overlay_window.deiconify()

class AxonOverlay:
    def __init__(self, window, identity_line, dept):
        self.window = window
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        self.trans_color = "#000001"
        self.window.config(bg=self.trans_color)
        self.window.wm_attributes("-transparentcolor", self.trans_color)

        self.canvas = tk.Canvas(self.window, bg=self.trans_color, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        self.identity_line = identity_line
        self.dept = dept
        self.dot_visible = True
        
        self._logo_source = None
        self._logo_photo = None
        self._logo_path = None
        self._logo_cache_key = None
        self._logo_dimensions = (0, 0)
        self._logo_path_candidates = self._get_logo_candidates()
        self._canvas_items = {}
        self._window_geometry = None

        self.window.update_idletasks()
        self.hwnd = int(self.window.winfo_id())
        
        if win32gui and win32con:
            ex_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                self.hwnd, 
                win32con.GWL_EXSTYLE, 
                ex_style | win32con.WS_EX_TRANSPARENT
            )

        self.update_live_time()
        self.blink_rec_dot()

    @staticmethod
    def _get_logo_candidates():
        resource_base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        executable_base = os.path.dirname(sys.executable)
        return (
            os.path.join(resource_base, "png", "AXON.png"),
            os.path.join(resource_base, "AXON.png"),
            os.path.join(executable_base, "png", "AXON.png"),
            os.path.join(executable_base, "AXON.png"),
            os.path.join(os.getcwd(), "png", "AXON.png"),
            os.path.join(os.getcwd(), "AXON.png")
        )

    def update_text(self, identity_line, dept):
        self.identity_line = identity_line
        self.dept = dept
        if "identity" in self._canvas_items:
            self.canvas.itemconfig(self._canvas_items["identity"], text=self.identity_line)
        if "dept" in self._canvas_items:
            self.canvas.itemconfig(self._canvas_items["dept"], text=self.dept)

    def update_geometry(self, x, y, scale, logo_offset=0, logo_scale=None):
        w, h = (
            int(ABO_LAYOUT["window_size"]["width"] * scale),
            int(ABO_LAYOUT["window_size"]["height"] * scale)
        )
        geometry = f"{w}x{h}+{x}+{y}"
        if geometry != self._window_geometry:
            self.window.geometry(geometry)
            self._window_geometry = geometry
        fs = max(8, int(15 * scale))

        rec = ABO_LAYOUT["rec_label"]
        dot = ABO_LAYOUT["dot"]
        axon = ABO_LAYOUT["axon_label"]
        tm = ABO_LAYOUT["tm_label"]
        identity = ABO_LAYOUT["identity_label"]
        dept = ABO_LAYOUT["dept_label"]
        current_time = ABO_LAYOUT["time_label"]

        font = ("Consolas", fs, "bold")
        small_font = ("Consolas", max(6, int(fs * 0.6)), "bold")
        if not self._canvas_items:
            self._canvas_items = {
                "rec": self.canvas.create_text(0, 0, text="REC", fill="white", font=font, anchor="w"),
                "dot": self.canvas.create_oval(0, 0, 0, 0, fill="red", outline=""),
                "axon": self.canvas.create_text(0, 0, text="Axon Body Cam", fill="white", font=font, anchor="w"),
                "tm": self.canvas.create_text(0, 0, text="TM", fill="white", font=font, anchor="w"),
                "identity": self.canvas.create_text(0, 0, text=self.identity_line, fill="white", font=font, anchor="e"),
                "dept": self.canvas.create_text(0, 0, text=self.dept, fill="white", font=font, anchor="e"),
                "time": self.canvas.create_text(0, 0, text="", fill="white", font=font, anchor="e")
            }
            self.time_obj = self._canvas_items["time"]

        self.canvas.coords(self._canvas_items["rec"], rec["x"] * scale, rec["y"] * scale)
        self.canvas.coords(self._canvas_items["dot"], dot["x"] * scale, dot["y"] * scale, (dot["x"] + dot["width"]) * scale, (dot["y"] + dot["height"]) * scale)
        self.canvas.coords(self._canvas_items["axon"], axon["x"] * scale, axon["y"] * scale)
        self.canvas.coords(self._canvas_items["tm"], tm["x"] * scale, tm["y"] * scale)
        self.canvas.coords(self._canvas_items["identity"], identity["x"] * scale, identity["y"] * scale)
        self.canvas.coords(self._canvas_items["dept"], dept["x"] * scale, dept["y"] * scale)
        self.canvas.coords(self._canvas_items["time"], current_time["x"] * scale, current_time["y"] * scale)

        for item in ("rec", "axon", "identity", "dept", "time"):
            self.canvas.itemconfig(self._canvas_items[item], font=font)
        self.canvas.itemconfig(self._canvas_items["tm"], font=small_font)
        self.canvas.itemconfig(self._canvas_items["dot"], fill="red" if self.dot_visible else "#444")

        try:
            logo_path = next((path for path in self._logo_path_candidates if os.path.isfile(path)), None)
            if logo_path:
                logo_layout = ABO_LAYOUT["logo"]
                if logo_scale is None:
                    logo_scale = logo_layout["scale"]
                effective_logo_scale = scale * logo_scale
                cache_key = (logo_path, effective_logo_scale)
                if cache_key != self._logo_cache_key:
                    if Image is not None and ImageTk is not None:
                        if logo_path != self._logo_path:
                            with Image.open(logo_path) as source:
                                self._logo_source = source.convert("RGBA")
                            self._logo_path = logo_path
                        original_height = self._logo_source.height if LOGO_HEIGHT is None else LOGO_HEIGHT
                        target_h = max(1, int(original_height * effective_logo_scale))
                        target_w = int(target_h * (self._logo_source.width / self._logo_source.height))
                        
                        logo_resized = self._logo_source.resize((target_w, target_h), Image.LANCZOS)
                        
                        bw, bh = logo_resized.width, logo_resized.height
                        outlined_logo = Image.new("RGBA", (bw + 2, bh + 2), (0, 0, 0, 0))
                        
                        alpha_channel = logo_resized.split()[3]
                        black_mask = Image.new("RGBA", logo_resized.size, (0, 0, 0, 255))
                        black_mask.putalpha(alpha_channel)

                        for dx in (0, 1, 2):
                            for dy in (0, 1, 2):
                                outlined_logo.paste(black_mask, (dx, dy), black_mask)

                        outlined_logo.paste(logo_resized, (1, 1), logo_resized)

                        clean_logo = outlined_logo.copy()
                        pixels = clean_logo.load()
                        for py in range(clean_logo.height):
                            for px in range(clean_logo.width):
                                cr, cg, cb, ca = pixels[px, py]
                                if ca < 30:
                                    pixels[px, py] = (0, 0, 0, 0)
                                else:
                                    pixels[px, py] = (cr, cg, cb, 255)

                        self._logo_photo = ImageTk.PhotoImage(clean_logo)
                        self._logo_dimensions = (clean_logo.width, clean_logo.height)
                    else:
                        self._logo_photo = tk.PhotoImage(file=logo_path)
                        self._logo_dimensions = (self._logo_photo.width(), self._logo_photo.height())
                    self._logo_cache_key = cache_key

                logo_width, logo_height = self._logo_dimensions
                logo_x = w - logo_width - int(40 * scale) + int(logo_offset * scale) + int(logo_layout["x"] * scale)
                required_width = max(w, logo_x + logo_width + int(20 * scale))
                required_height = max(h, logo_height + int(20 * scale))
                logo_y = int(required_height/2 - logo_height/2) + int(logo_layout["y"] * scale)

                if "logo" not in self._canvas_items:
                    self._canvas_items["logo"] = self.canvas.create_image(logo_x, logo_y, image=self._logo_photo, anchor="nw")
                else:
                    self.canvas.coords(self._canvas_items["logo"], logo_x, logo_y)
                    self.canvas.itemconfig(self._canvas_items["logo"], image=self._logo_photo)

                if required_width != w or required_height != h:
                    geometry = f"{required_width}x{required_height}+{x}+{y}"
                    if geometry != self._window_geometry:
                        self.window.geometry(geometry)
                        self._window_geometry = geometry
        except Exception:
            pass

    def update_live_time(self):
        t_str = time.strftime("%b %d %Y  %H : %M : %S PDT").upper()
        if hasattr(self, 'time_obj') and self.time_obj:
            self.canvas.itemconfig(self.time_obj, text=t_str)
        self.window.after(1000, self.update_live_time)

    def blink_rec_dot(self):
        self.dot_visible = not self.dot_visible
        if "dot" in self._canvas_items:
            self.canvas.itemconfig(self._canvas_items["dot"], fill="red" if self.dot_visible else "#444")
        self.window.after(600, self.blink_rec_dot)

if __name__ == "__main__":
    root = tk.Tk()
    app = AxonApp(root)
    root.mainloop()