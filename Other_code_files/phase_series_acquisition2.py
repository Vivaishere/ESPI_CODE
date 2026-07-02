# phase_series_acquisition.py
import time
from datetime import datetime

import PySpin
import lc_control
from image_acquisition import capture_image, DEFAULT_CAMERA_SETTINGS, is_camera_connected
from four_image_combine import four_image_combine
from Other_code_files.crop_images import *
from utils import get_experiment_folder

# -----------------------------------------------------
# Logging setup
# -----------------------------------------------------
LOG_FILE = os.path.join(os.path.dirname(__file__), "acquisition_log.txt")

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# -----------------------------------------------------
# Helper function for LC status
# -----------------------------------------------------
def check_lc_status(label):
    try:
        ser = lc_control.find_device_port()
        if ser is None:
            label.config(text="Not Connected", fg="red")
            return False
        else:
            verified = lc_control.verify_connection(ser)
            label.config(text="Connected" if verified else "Not Connected",
                         fg="green" if verified else "red")
            try: ser.close()
            except Exception: pass
            return verified
    except Exception:
        label.config(text="Not Connected", fg="red")
        return False

# -----------------------------------------------------
# GUI for settings, load control, and live feed
# -----------------------------------------------------
class AcquisitionGUI:
    def __init__(self, defaults):
        self.root = tk.Tk()
        self.root.title("Phase Series Acquisition Setup")
        self.root.geometry("1140x696")
        self.root.resizable(False, False)
        try:
            self.root.eval('tk::PlaceWindow . center')
        except Exception:
            pass

        self.bold_font = ("Arial", 12, "bold")
        self.default_font = ("Arial", 11)
        self.mono_font = ("Arial", 11)

        self.defaults = defaults
        self.entries = {}
        self.toggles = {}
        self.settings_result = {}
        self.no_load_used = False
        self.start_mode = None
        self.load_label_text = None
        self.images_taken = False

        self.camera_present = is_camera_connected()
        self.lc_present_initial = None

        # --- Status Frame ---
        status_frame = ttk.LabelFrame(self.root, text="Hardware Status")
        status_frame.place(x=12, y=12, width=432, height=84)

        ttk.Label(status_frame, text="Camera:", font=self.default_font).grid(row=0, column=0, sticky="w", padx=10, pady=3)
        cam_status_text = "Connected" if self.camera_present else "Not Connected"
        cam_color = "green" if self.camera_present else "red"
        self.cam_label = tk.Label(status_frame, text=cam_status_text, fg=cam_color, width=22, anchor="w", font=self.default_font)
        self.cam_label.grid(row=0, column=1, sticky="w")

        ttk.Label(status_frame, text="LC Retarder:", font=self.default_font).grid(row=1, column=0, sticky="w", padx=10, pady=3)
        self.lc_label = tk.Label(status_frame, text="Unknown", fg="orange", width=22, anchor="w", font=self.default_font)
        self.lc_label.grid(row=1, column=1, sticky="w")

        # --- Experiment Name ---
        ttk.Separator(self.root, orient="horizontal").place(x=12, y=108, width=432)
        tk.Label(self.root, text="Experiment Name:", font=self.bold_font).place(x=12, y=114)
        self.exp_name_entry = ttk.Entry(self.root, width=40, font=self.default_font)
        self.exp_name_entry.insert(0, "experiment")
        self.exp_name_entry.place(x=12, y=138)

        # --- Camera Settings ---
        settings_frame = ttk.LabelFrame(self.root, text="Camera Settings")
        settings_frame.place(x=12, y=180, width=432, height=240)

        for i, (key, val) in enumerate(defaults.items()):
            row = ttk.Frame(settings_frame)
            row.pack(fill="x", pady=4, padx=6)

            ttk.Label(row, text=f"{key}:", width=13, font=self.default_font).pack(side="left")

            if key in ["ExposureAuto", "GainAuto"]:
                btn = tk.Button(row, text=val, width=10, command=lambda k=key: self.toggle_auto(k), font=self.default_font)
                btn.pack(side="left")
                self.toggles[key] = btn
            else:
                entry = ttk.Entry(row, font=self.default_font)
                entry.insert(0, str(val))
                entry.pack(side="left", fill="x", expand=True)
                self.entries[key] = entry
                entry.bind("<FocusOut>", lambda e, k=key: self.apply_live_settings())

            ttk.Label(row, text=f"(default: {val})", width=17, foreground="gray", font=self.default_font).pack(side="right")

        # --- Load Controls ---
        load_frame = ttk.LabelFrame(self.root, text="Load Condition")
        load_frame.place(x=12, y=432, width=432, height=120)

        ttk.Label(load_frame, text="Custom Load (e.g., 5N or testA):", font=self.default_font).pack(pady=(4,2))
        self.load_entry = ttk.Entry(load_frame, font=self.default_font)
        self.load_entry.pack(pady=(0,6))

        btn_frame = ttk.Frame(load_frame)
        btn_frame.pack(pady=6)

        self.no_load_btn = ttk.Button(btn_frame, text="Start: No Load", command=self.start_no_load)
        self.no_load_btn.pack(side="left", padx=6)

        self.load_btn = ttk.Button(btn_frame, text="Start: Custom Load", command=self.start_custom_load)
        self.load_btn.pack(side="right", padx=6)

        if not self.camera_present:
            self.no_load_btn.state(["disabled"])
            self.load_btn.state(["disabled"])

        # --- Filename Preview ---
        ttk.Separator(self.root, orient="horizontal").place(x=12, y=568, width=432)
        self.preview_label = ttk.Label(self.root, text="Filename Preview:", font=self.bold_font)
        self.preview_label.place(x=12, y=574)
        self.preview_value = ttk.Label(self.root, text="", font=self.mono_font)
        self.preview_value.place(x=12, y=598)

        self.exp_name_entry.bind("<KeyRelease>", lambda e: self.update_preview())
        self.load_entry.bind("<KeyRelease>", lambda e: self.update_preview())
        for e in self.entries.values():
            e.bind("<KeyRelease>", lambda ev: self.update_preview())

        self.update_preview()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Crop Images button
        self.crop_btn = ttk.Button(self.root, text="Crop Images", command=self.crop_current_series)
        self.crop_btn.place(x=10, y=645)

        self.crop_other_btn = ttk.Button(self.root, text="Crop Other Series", command=self.crop_other_series)
        self.crop_other_btn.place(x=150, y=645)

        # --- LC status check at startup ---
        self.lc_present_initial = check_lc_status(self.lc_label)

        # --- Live camera feed ---
        self.init_camera_liveview()

    # --- Toggle buttons ---
    def toggle_auto(self, key):
        btn = self.toggles[key]
        current = btn.cget("text")
        new = "Off" if current == "On" else "On"
        btn.config(text=new)
        self.apply_live_settings()

    # --- Collect camera settings ---
    def collect_settings(self):
        result = {}
        for k, e in self.entries.items():
            val = e.get().strip()
            try:
                result[k] = float(val)
            except ValueError:
                result[k] = val
        for k, btn in self.toggles.items():
            result[k] = btn.cget("text")
        return result

    # --- Filename suffix ---
    def build_suffix(self, settings):
        parts = []
        for k, v in settings.items():
            if v != self.defaults[k]:
                short = {
                    "ExposureTime": "exp",
                    "Gain": "g",
                    "Gamma": "gm",
                    "BlackLevel": "blk",
                    "ExposureAuto": "expAuto",
                    "GainAuto": "gAuto"
                }.get(k, k.lower())
                parts.append(f"{short}{str(v).replace(' ','')}")
        return "-" + "-".join(parts) if parts else ""

    # --- Filename preview ---
    def update_preview(self):
        exp_name = self.exp_name_entry.get().strip() or "experiment"
        settings = self.collect_settings()
        suffix = self.build_suffix(settings)
        load = self.load_entry.get().strip() or "0N"
        preview = f"{exp_name}{suffix}_{load}.tiff"
        self.preview_value.config(text=preview)

    # --- Apply current camera settings to live feed ---
    def apply_live_settings(self):
        if not self.camera_present or not hasattr(self, "cam"):
            return
        settings = self.collect_settings()
        try:
            if settings.get("ExposureAuto") == "On":
                self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)
            else:
                self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                self.cam.ExposureTime.SetValue(float(settings.get("ExposureTime", 200)))
            if settings.get("GainAuto") == "On":
                self.cam.GainAuto.SetValue(PySpin.GainAuto_Continuous)
            else:
                self.cam.GainAuto.SetValue(PySpin.GainAuto_Off)
                self.cam.Gain.SetValue(float(settings.get("Gain", 0)))
            self.cam.Gamma.SetValue(float(settings.get("Gamma", 1.0)))
            self.cam.BlackLevel.SetValue(float(settings.get("BlackLevel", 0)))
        except Exception as e:
            print(f"[WARN] Failed to apply live camera settings: {e}")

    # --- Run GUI ---
    def run(self):
        self.root.mainloop()
        return self.settings_result, self.start_mode, self.load_label_text

    # --- Load buttons ---
    def start_no_load(self):
        if self.no_load_used:
            messagebox.showinfo("Notice", "No Load acquisition already completed.")
            return
        self.no_load_used = True
        self.images_taken = True
        self.no_load_btn.state(["disabled"])
        self.settings_result = self.collect_settings()
        self.start_mode = "no_load"
        self.load_label_text = "0N"
        self.run_acquisition()
        log_message("[INFO] No load acquisition started. GUI remains open.")

    def start_custom_load(self):
        load_text = self.load_entry.get().strip()
        if not load_text:
            messagebox.showwarning("Missing Input", "Please enter a load description (e.g., 10N or test2).")
            return
        self.images_taken = True
        self.settings_result = self.collect_settings()
        self.start_mode = "custom_load"
        self.load_label_text = load_text
        self.run_acquisition()
        log_message(f"[INFO] Custom load acquisition started: {load_text}")

    # --- Acquisition logic ---
    def run_acquisition(self):
        exp_name = self.exp_name_entry.get().strip() or "experiment"
        exp_folder = get_experiment_folder(exp_name)
        suffix = self.build_suffix(self.settings_result)
        load_part = f"_{self.load_label_text}" if self.load_label_text else ""
        log_message(f"=== Starting acquisition series: prefix={suffix}, load={self.load_label_text} ===")
        if not is_camera_connected():
            log_message("[ERROR] Camera not connected. Aborting acquisition.")
            return
        ser = lc_control.find_device_port()
        lc_connected = False
        if ser and lc_control.verify_connection(ser):
            lc_connected = True
        if not lc_connected:
            no_ret_name = f"{suffix}{load_part}"
            log_message("[WARN] LC retarder not connected. Capturing single image without retardance.")
            if capture_image(no_ret_name, settings=self.settings_result, folder=exp_folder):
                log_message(f"[OK] Single image saved as: {no_ret_name}.tiff")
            return
        try:
            lc_control.send_cmd(ser, "OM=1")
            lc_control.send_cmd(ser, "WL=635")
        except Exception as e:
            log_message(f"[ERROR] Failed to initialize LC: {e}")
            try: ser.close()
            except Exception: pass
            return
        phase_to_retardance = {"000": 0, "090": int(0.25*633), "180": int(0.5*633), "270": int(0.75*633)}
        for phase_str, retardance_nm in phase_to_retardance.items():
            log_message(f"Setting retardance for phase {phase_str} → {retardance_nm} nm")
            lc_control.send_cmd(ser, f"RE={retardance_nm}")
            while True:
                resp = lc_control.send_cmd(ser, "RE?")
                if str(retardance_nm) in resp: break
                time.sleep(0.01)
            filename = f"{exp_name}{suffix}{load_part}_{phase_str}"
            log_message(f"Capturing image → {filename}.tiff")
            capture_image(filename, settings=self.settings_result, folder=exp_folder)
        try: ser.close()
        except Exception: pass
        log_message("=== Acquisition complete ===")
        combined_filename = f"{exp_name}{suffix}{load_part}_combined"
        four_image_combine(combined_filename, folder=exp_folder, logger=log_message)
        log_message("[INFO] Combined wrapped phase image created.")

    # --- Close popup ---
    def on_close(self):
        if self.images_taken:
            resp = messagebox.askyesno("Crop Images?", "Do you want to crop the images you took?")
            if resp:
                self.crop_current_series()
        self.root.destroy()

    # --- Live camera feed setup ---
    def init_camera_liveview(self):
        live_frame_size = 672
        live_frame = tk.Frame(self.root, width=live_frame_size, height=live_frame_size, bd=1, relief="solid")
        live_frame.place(x=456, y=12)
        self.live_size = live_frame_size
        self.zoom_factor = 1.0
        self.live_pil_image = None
        self.tk_image = None
        self.live_label = tk.Label(live_frame, relief="flat", bd=0, bg="black")
        self.live_label.place(x=0, y=0, width=self.live_size-2, height=self.live_size-2)
        self.live_label.bind("<MouseWheel>", self.zoom_livefeed)
        self.live_label.bind("<Button-4>", self.zoom_livefeed)
        self.live_label.bind("<Button-5>", self.zoom_livefeed)
        if not self.camera_present:
            self.live_label.config(bg="gray")
        else:
            try:
                self.system = PySpin.System.GetInstance()
                self.cam_list = self.system.GetCameras()
                if self.cam_list.GetSize() == 0:
                    self.live_label.config(bg="gray")
                    self.cam_list.Clear()
                else:
                    self.cam = self.cam_list[0]
                    self.cam.Init()
                    self.cam.BeginAcquisition()
                    self.apply_live_settings()
                    self.update_livefeed()
            except Exception:
                self.live_label.config(bg="gray")

    def display_live_image(self):
        self.live_pil_image = Image.fromarray(self.live_img_array)
        size = int(self.live_size * self.zoom_factor)
        resized = self.live_pil_image.resize((size, size), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.live_label.config(image=self.tk_image)

    def update_livefeed(self):
        try:
            image_result = self.cam.GetNextImage(1000)
            if not image_result.IsIncomplete():
                self.live_img_array = image_result.GetNDArray()
                self.display_live_image()
            image_result.Release()
        except Exception:
            self.live_label.config(text="Camera feed unavailable")
        self.root.after(50, self.update_livefeed)

    def zoom_livefeed(self, event):
        if event.num == 4 or event.delta > 0:
            self.zoom_factor *= 1.1
        elif event.num == 5 or event.delta < 0:
            self.zoom_factor /= 1.1
        self.zoom_factor = max(0.1, min(self.zoom_factor, 5.0))
        self.display_live_image()

    # --- Crop Images ---
    def crop_current_series(self):
        exp_name = self.exp_name_entry.get().strip() or "experiment"
        base_dir = os.path.join(os.getcwd(), "ESPI_Images", exp_name)
        if not os.path.exists(base_dir):
            messagebox.showerror("Error", f"Experiment folder not found:\n{base_dir}")
            return
        series_prefix = f"{exp_name}_"
        crop_tiff_images_series(base_dir, series_prefix, show_message=True)

    def crop_other_series(self):
        base_dir = os.path.join(os.getcwd(), "ESPI_Images")
        filepath = filedialog.askopenfilename(
            title="Select any TIFF image from the target folder",
            initialdir=base_dir,
            filetypes=[("TIFF files", "*.tiff"), ("All files", "*.*")]
        )
        if not filepath:
            return
        folder = os.path.dirname(filepath)
        messagebox.showinfo(
            "Cropping Selected Folder",
            f"Selected folder:\n{folder}\n\nAll *_combined.tiff images here will be cropped."
        )
        series_prefix = ""
        crop_tiff_images_series(folder, series_prefix, show_message=True)

# -----------------------------------------------------
# Main acquisition function
# -----------------------------------------------------
def capture_phase_series():
    gui = AcquisitionGUI(DEFAULT_CAMERA_SETTINGS)
    gui.run()
