# utils.py
import os
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import a__liq_crystal_retarder_control


def get_image_data_dir():
    """Return the folder that stores the raw/processed ESPI image data."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(script_dir, "..", "ESPI_Images", "1_RAW_new_images")),
        os.path.abspath(os.path.join(script_dir, "ESPI_Images", "1_RAW_new_images")),
        os.path.abspath(os.path.join(os.getcwd(), "ESPI_Images", "1_RAW_new_images")),
        os.path.abspath(os.path.join(os.getcwd(), "1_RAW_new_images")),
        os.path.abspath(os.path.join(script_dir, "..", "ESPI_Images")),
        os.path.abspath(os.path.join(script_dir, "ESPI_Images")),
        os.path.abspath(os.path.join(os.getcwd(), "ESPI_Images")),
    ]

    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate

    return os.path.abspath(os.path.join(script_dir, "..", "ESPI_Images", "1_RAW_new_images"))


def select_base_folder():
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(
        title="Select folder for unwrap and displacement"
    )
    root.destroy()

    if not folder:
        print("❌ No folder selected. Operation cancelled.")
        return None

    return folder

def get_experiment_folder(exp_name):
    base_dir = get_image_data_dir()

    # Add timestamp to the experiment folder name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder_name = f"{timestamp}_{exp_name}"

    full_dir = os.path.join(base_dir, folder_name)
    os.makedirs(full_dir, exist_ok=True)

    return full_dir



def validate_folder(folder_path: str) -> bool:
    """
    Checks if a folder exists and is accessible.
    Returns True if valid, False otherwise.
    Does NOT create or modify any folders.
    """
    try:
        return os.path.isdir(folder_path) and os.access(folder_path, os.R_OK | os.W_OK)
    except Exception:
        return False

# -----------------------------------------------------
# Logging setup
# -----------------------------------------------------
def log_message(message):
    LOG_FILE = os.path.join(os.path.dirname(__file__), "acquisition_log.txt")
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
        ser = a__liq_crystal_retarder_control.find_device_port()
        if ser is None:
            label.config(text="Not Connected", fg="red")
            return False
        else:
            verified = a__liq_crystal_retarder_control.verify_connection(ser)
            label.config(text="Connected" if verified else "Not Connected",
                         fg="green" if verified else "red")
            try: ser.close()
            except Exception: pass
            return verified
    except Exception:
        label.config(text="Not Connected", fg="red")
        return False
    

# =========================
# UNIQUE FILE PATH
# =========================
def get_unique_path(folder, filename):

    base, ext = os.path.splitext(filename)

    path = os.path.join(folder, filename)

    counter = 1

    while os.path.exists(path):
        path = os.path.join(
            folder,
            f"{base}_{counter}{ext}"
        )
        counter += 1

    return path