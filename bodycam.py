# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
import time
import json
import os
import sys
from fractions import Fraction
import threading
import subprocess
import tempfile
import urllib.request
import urllib.error
import webbrowser
from tkinter import messagebox
try:
    import win32api
    import win32con
    import win32gui
except Exception:
    win32api = win32con = win32gui = None
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
    "rec_label": {"x": 180, "y": 32, "width": 40, "height": 20},
    "dot": {"x": 225, "y": 28, "width": 10, "height": 10},
    "axon_label": {"x": 245, "y": 32, "width": 150, "height": 20},
    "tm_label": {"x": 392, "y": 27, "width": 25, "height": 14},
    "identity_label": {"x": 400, "y": 60, "width": 400, "height": 20},
    "dept_label": {"x": 400, "y": 90, "width": 300, "height": 20},
    "time_label": {"x": 400, "y": 120, "width": 300, "height": 20},
    "logo": {"x": 0, "y": -5, "scale": 1.0}
}
LOGO_HEIGHT = 98

class AxonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Axon Generator v1.0.0 - Control Panel")
        gui_width = GUI_LAYOUT["window_size"]["width"]
        gui_height = GUI_LAYOUT["window_size"]["height"]
        self.root.geometry(f"{gui_width}x{gui_height}")

        self._frozen = getattr(sys, 'frozen', False)

        if self._frozen:
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self._settings_path = os.path.join(base_dir, 'settings.json')

        main_frame = ttk.Frame(root, padding="8")
        main_frame.pack(fill="both", expand=True)
        self.gui_widgets = {
            "title": ttk.Label(main_frame, text="AXON Overlay program v1.0.0", font=("Arial", 13, "bold")),
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
        self.update_status_label = ttk.Label(main_frame, textvariable=self.update_status, font=("Arial", 8))
        self.creator_label = ttk.Label(main_frame, text="Created by HezoY | Licensed under the MIT License", font=("Arial", 8))
        self.gui_widgets.update({
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
        for name, widget in self.gui_widgets.items():
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
        self.root.after(100, self.check_for_updates)

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
            self.overlay.enable_click_through()
        self.overlay.update_text(identity_line, dept)
        self.on_slider_move()

    def on_slider_move(self, val=None):
        if hasattr(self, 'overlay') and self.overlay_window.winfo_exists():
            self.overlay.update_geometry(
                int(self.x_slider.get()),
                int(self.y_slider.get()),
                float(self.scale_slider.get()),
                int(self.logo_offset_slider.get())
            )

    @staticmethod
    def _version_tuple(version):
        version = str(version).strip().lower().lstrip("v")
        parts = []
        for part in version.split("."):
            digits = "".join(character for character in part if character.isdigit())
            parts.append(int(digits or 0))
        return tuple(parts)

    def check_for_updates(self):
        self.update_status.set(f"Checking for updates... (v{APP_VERSION})")
        threading.Thread(target=self._fetch_latest_release, daemon=True).start()

    def _fetch_latest_release(self):
        try:
            request = urllib.request.Request(
                GITHUB_RELEASES_URL,
                headers={"User-Agent": "Axon-Bodycam-Overlay"}
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                release = json.loads(response.read().decode("utf-8"))
            self.root.after(0, lambda: self._handle_release(release))
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError) as error:
            self.root.after(0, lambda error=error: self.update_status.set(f"Unable to check for updates: {error}"))

    def _handle_release(self, release):
        latest_version = release.get("tag_name", "").strip()
        if not latest_version or self._version_tuple(latest_version) <= self._version_tuple(APP_VERSION):
            self.update_status.set(f"Up to date! (v{APP_VERSION})")
            return

        self.update_status.set(f"Update available: {latest_version}")
        if messagebox.askyesno("Update", f"Version {latest_version} is available. Download it now?"):
            self._download_update(release)

    def _download_update(self, release):
        if not self._frozen:
            self.update_status.set("Run the .exe version to install updates automatically.")
            webbrowser.open(release.get("html_url", "https://github.com/" + GITHUB_REPOSITORY + "/releases"))
            return

        executable_name = os.path.basename(sys.executable)
        assets = release.get("assets", [])
        asset = next((item for item in assets if item.get("name") == executable_name), None)
        if asset is None:
            asset = next((item for item in assets if item.get("name", "").lower().endswith(".exe")), None)
        if asset is None:
            self.update_status.set("No .exe file found in the latest GitHub release.")
            return

        self.update_status.set("Downloading update...")
        threading.Thread(target=self._download_and_install, args=(asset["browser_download_url"],), daemon=True).start()

    def _download_and_install(self, download_url):
        temporary_file = None
        try:
            temporary_file = tempfile.NamedTemporaryFile(delete=False, suffix=".exe").name
            request = urllib.request.Request(download_url, headers={"User-Agent": "Axon-Bodycam-Overlay"})
            with urllib.request.urlopen(request, timeout=60) as response, open(temporary_file, "wb") as destination:
                destination.write(response.read())

            script_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ps1", encoding="utf-8")
            script_file.write(
                "param([string]$Current, [string]$New)\n"
                "Start-Sleep -Seconds 2\n"
                "Copy-Item -Path $New -Destination $Current -Force\n"
                "Start-Process -FilePath $Current\n"
                "Remove-Item -Path $New -Force\n"
                "Remove-Item -Path $PSCommandPath -Force\n"
            )
            script_file.close()
            subprocess.Popen([
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", script_file.name, sys.executable, temporary_file
            ])
            self.root.after(0, lambda: self.update_status.set("Update downloaded. The program will restart."))
            self.root.after(1500, self.root.destroy)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
            if temporary_file and os.path.exists(temporary_file):
                os.remove(temporary_file)
            self.root.after(0, lambda error=error: self.update_status.set(f"Update error: {error}"))

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

    def safe_toggle_trigger(self): self.root.after(10, self.toggle_visibility)
    def toggle_visibility(self):
        if hasattr(self, 'overlay_window') and self.overlay_window.winfo_exists():
            if self.overlay_window.winfo_viewable(): self.overlay_window.withdraw()
            else: self.overlay_window.deiconify()

class AxonOverlay:
    def __init__(self, window, identity_line, dept):
        self.window = window
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.config(bg="black")
        self.window.attributes("-transparentcolor", "black")
        self.canvas = tk.Canvas(self.window, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.identity_line, self.dept = identity_line, dept
        self.dot_visible = True
        self.update_live_time()
        self.blink_rec_dot()

    def enable_click_through(self):
        if win32gui is None or win32con is None:
            return
        try:
            hwnd = int(self.window.winfo_id())
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
            if win32api: win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(0, 0, 0), 0, win32con.LWA_COLORKEY)
        except Exception: pass

    def update_text(self, identity_line, dept): self.identity_line, self.dept = identity_line, dept

    def update_geometry(self, x, y, scale, logo_offset=0, logo_scale=None):
        w, h = (
            int(ABO_LAYOUT["window_size"]["width"] * scale),
            int(ABO_LAYOUT["window_size"]["height"] * scale)
        )
        self.window.geometry(f"{w}x{h}+{x}+{y}")
        self.canvas.delete("all")
        fs = max(8, int(15 * scale))

        rec = ABO_LAYOUT["rec_label"]
        dot = ABO_LAYOUT["dot"]
        axon = ABO_LAYOUT["axon_label"]
        tm = ABO_LAYOUT["tm_label"]
        identity = ABO_LAYOUT["identity_label"]
        dept = ABO_LAYOUT["dept_label"]
        current_time = ABO_LAYOUT["time_label"]

        self.canvas.create_text(rec["x"] * scale, rec["y"] * scale, text="REC", fill="white", font=("Consolas", fs, "bold"), anchor="w")
        self.dot_obj = self.canvas.create_oval(dot["x"] * scale, dot["y"] * scale, (dot["x"] + dot["width"]) * scale, (dot["y"] + dot["height"]) * scale, fill="red" if self.dot_visible else "#444", outline="")
        self.canvas.create_text(axon["x"] * scale, axon["y"] * scale, text="Axon Body Cam", fill="white", font=("Consolas", fs, "bold"), anchor="w")
        self.canvas.create_text(tm["x"] * scale, tm["y"] * scale, text="TM", fill="white", font=("Consolas", max(6, int(fs * 0.6)), "bold"), anchor="w")
        self.canvas.create_text(identity["x"] * scale, identity["y"] * scale, text=self.identity_line, fill="white", font=("Consolas", fs, "bold"), anchor="e")
        self.canvas.create_text(dept["x"] * scale, dept["y"] * scale, text=self.dept, fill="white", font=("Consolas", fs, "bold"), anchor="e")
        self.time_obj = self.canvas.create_text(current_time["x"] * scale, current_time["y"] * scale, text="", fill="white", font=("Consolas", fs, "bold"), anchor="e")

        try:
            resource_base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            executable_base = os.path.dirname(sys.executable)
            logo_candidates = (
                os.path.join(resource_base, "png", "AXON.png"),
                os.path.join(resource_base, "AXON.png"),
                os.path.join(executable_base, "png", "AXON.png"),
                os.path.join(executable_base, "AXON.png"),
                os.path.join(os.getcwd(), "png", "AXON.png"),
                os.path.join(os.getcwd(), "AXON.png")
            )
            logo_path = next((path for path in logo_candidates if os.path.isfile(path)), None)
            if logo_path:
                logo_layout = ABO_LAYOUT["logo"]
                if logo_scale is None:
                    logo_scale = logo_layout["scale"]
                effective_logo_scale = scale * logo_scale
                if Image is not None and ImageTk is not None:
                    logo_img = Image.open(logo_path).convert("RGBA")
                    original_height = logo_img.height if LOGO_HEIGHT is None else LOGO_HEIGHT
                    target_h = max(1, int(original_height * effective_logo_scale))
                    logo_resized = logo_img.resize((int(target_h * (logo_img.width/logo_img.height)), target_h), Image.LANCZOS)
                    self._logo_photo = ImageTk.PhotoImage(logo_resized)
                    logo_width, logo_height = logo_resized.width, logo_resized.height
                else:
                    self._logo_photo = tk.PhotoImage(file=logo_path)
                    if effective_logo_scale != 1:
                        scale_ratio = Fraction(str(effective_logo_scale)).limit_denominator(10)
                        if scale_ratio.numerator > 1:
                            self._logo_photo = self._logo_photo.zoom(scale_ratio.numerator, scale_ratio.numerator)
                        if scale_ratio.denominator > 1:
                            self._logo_photo = self._logo_photo.subsample(scale_ratio.denominator, scale_ratio.denominator)
                    logo_width, logo_height = self._logo_photo.width(), self._logo_photo.height()

                logo_x = w - logo_width - int(40 * scale) + int(logo_offset * scale) + int(logo_layout["x"] * scale)
                required_width = max(w, logo_x + logo_width + int(20 * scale))
                required_height = max(h, logo_height + int(20 * scale))
                logo_y = int(required_height/2 - logo_height/2) + int(logo_layout["y"] * scale)
                self.canvas.create_image(logo_x, logo_y, image=self._logo_photo, anchor="nw")
                required_width = max(required_width, logo_x + logo_width + int(20 * scale))
                if required_width != w or required_height != h:
                    self.window.geometry(f"{required_width}x{required_height}+{x}+{y}")
        except Exception: pass

    def update_live_time(self):
        t = time.strftime("%b %d %Y  %H : %M : %S PDT").upper()
        if hasattr(self, 'time_obj'): self.canvas.itemconfig(self.time_obj, text=t)
        self.window.after(1000, self.update_live_time)
        
    def blink_rec_dot(self):
        self.dot_visible = not self.dot_visible
        if hasattr(self, 'dot_obj'): self.canvas.itemconfig(self.dot_obj, fill="red" if self.dot_visible else "#444")
        self.window.after(600, self.blink_rec_dot)

if __name__ == "__main__":
    root = tk.Tk(); app = AxonApp(root); root.mainloop()