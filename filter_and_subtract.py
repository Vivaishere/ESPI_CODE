# filter_and_subtract.py

import os
import re
from skimage import io
import numpy as np
import imageio.v2 as imageio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from scipy.signal import medfilt2d, wiener
from scipy.ndimage import gaussian_filter

from phase_unwrap import unwrap_all_filter_images
from displacement import get_displacement

# Define the 4 phases
PHASES = ["000", "090", "180", "270"]


def parse_filename(fname):
    """
    Parses filenames like:
      - crop1_expname_force_phase.tiff
      - expname_force_phase.tiff

    Returns: prefix, force, phase, crop (crop is None if not present)
    """
    name = os.path.splitext(os.path.basename(fname))[0]
    parts = name.split("_")

    crop = None
    if parts[0].startswith("crop"):
        crop = parts.pop(0)  # remove cropX from front

    if len(parts) != 3:
        raise ValueError(f"Unexpected filename format: {fname}")

    prefix, force, phase = parts
    return prefix, force, phase, crop


def extract_force_value(force_str):
    """
    Extracts numeric value from force strings like:
    '10N', '5kg', '0030', '12.5N'

    Returns float
    """
    match = re.search(r"[-+]?\d*\.?\d+", force_str)
    if not match:
        raise ValueError(f"Cannot extract numeric force from '{force_str}'")
    return float(match.group())


def select_image_sets(initial_dir=None):
    """
    Open the system file dialog to select TWO images (one from each set for subtraction).
    Returns two lists of 4 filenames each corresponding to the 4-phase images.
    If initial_dir is provided, the dialog opens there (typically inside ESPI_Images/exp_*).
    """
    root = tk.Tk()
    root.withdraw()

    # Default to ESPI_Images directory if none given
    if initial_dir is None:
        initial_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ESPI_Images", "1_RAW_new_images"))

    file_paths = filedialog.askopenfilenames(
        title="Select TWO images (one from each set for subtraction)",
        initialdir=initial_dir,
        filetypes=[("TIFF files", "*.tif *.tiff")]
    )

    if len(file_paths) != 2:
        raise ValueError("Please select exactly TWO images (one from each set).")

    folder = os.path.dirname(file_paths[0])
    sets = []
    for f in file_paths:
        prefix, force, phase, crop = parse_filename(f)

        if crop:
            image_set = [os.path.join(folder, f"{crop}_{prefix}_{force}_{p}.tiff") for p in PHASES]
        else:
            image_set = [os.path.join(folder, f"{prefix}_{force}_{p}.tiff") for p in PHASES]

        forces_in_set = [parse_filename(img)[1] for img in image_set]
        if len(set(forces_in_set)) > 1:
            raise ValueError(f"Not all 4 images in the set have the same force: {image_set}")
        sets.append(image_set)

    # --------------------------------------------------
    # ENSURE SET1 FORCE < SET2 FORCE (NUMERIC COMPARISON)
    # --------------------------------------------------

    force1_str = parse_filename(sets[0][0])[1]
    force2_str = parse_filename(sets[1][0])[1]

    force1_val = extract_force_value(force1_str)
    force2_val = extract_force_value(force2_str)

    if force1_val == force2_val:
        raise ValueError(
            f"Selected image sets have the same force value: {force1_str} and {force2_str}"
        )

    # Order sets so that set1 < set2
    if force1_val < force2_val:
        set1_files, set2_files = sets
    else:
        set2_files, set1_files = sets

    # Ensure both have same crop if applicable
    crop1 = parse_filename(set1_files[0])[3]
    crop2 = parse_filename(set2_files[0])[3]
    if crop1 and crop2 and crop1 != crop2:
        raise ValueError("Selected images have different crop numbers.")

    return set1_files, set2_files


def get_filter_strength_and_num():
    """
    Opens a popup window to select filter strength and filter number.

    Defaults:
      - filter strength = 1
      - filter number = 3

    Returns
    -------
    filter_str : int
    filter_num : int
    """

    result = {"filter_str": 1, "filter_num": 3}  # defaults

    def on_confirm():
        try:
            result["filter_str"] = int(strength_var.get())
        except Exception:
            result["filter_str"] = 1

        try:
            result["filter_num"] = int(filter_var.get())
        except Exception:
            result["filter_num"] = 3

        popup.destroy()

    popup = tk.Tk()
    popup.title("Select Filter Parameters")
    popup.geometry("300x200")
    popup.resizable(False, False)
    popup.eval("tk::PlaceWindow . center")

    # -------------------------
    # VARIABLES
    # -------------------------
    strength_values = [1, 3, 5, 7, 9, 11, 13, 17, 21, 27, 51, 81]
    filter_values = [1, 2, 3, 4]

    strength_var = tk.StringVar(value="11")
    filter_var = tk.StringVar(value="3")

    # -------------------------
    # LAYOUT
    # -------------------------
    frame = tk.Frame(popup, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="Filter Strength", anchor="w").pack(fill=tk.X)
    ttk.Combobox(
        frame,
        textvariable=strength_var,
        values=strength_values,
        state="readonly"
    ).pack(fill=tk.X, pady=(0, 15))

    tk.Label(frame, text="Filter Number", anchor="w").pack(fill=tk.X)
    ttk.Combobox(
        frame,
        textvariable=filter_var,
        values=filter_values,
        state="readonly"
    ).pack(fill=tk.X, pady=(0, 20))

    ttk.Button(frame, text="Confirm", command=on_confirm).pack()

    # -------------------------
    # MODAL BEHAVIOR
    # -------------------------
    popup.grab_set()
    popup.mainloop()

    return result["filter_str"], result["filter_num"]


def filter_and_subtract_one_set(folder=None, sgl=2, sgh=1):
    """
    Computes wrapped phase difference, applies the selected filter, and saves the filtered image.
    If folder is provided, the file dialog will open in that folder.
    Works with filenames with or without '_crop' parts.
    """
    filter_str, filter_num = get_filter_strength_and_num()

    lw = hw = filter_str or 11
    filter_num = filter_num or 3

    # --- Step 1: Select image sets ---
    set1_files, set2_files = select_image_sets(initial_dir=folder)

    # --- Step 2: Load images ---
    p1 = np.stack([imageio.imread(f).astype(np.float64) / 255.0 for f in set1_files], axis=2)
    p2 = np.stack([imageio.imread(f).astype(np.float64) / 255.0 for f in set2_files], axis=2)

    # --- Step 3: Compute wrapped phases ---
    ps1 = np.arctan2((p1[:, :, 3] - p1[:, :, 1]), (p1[:, :, 0] - p1[:, :, 2]))
    ps2 = np.arctan2((p2[:, :, 3] - p2[:, :, 1]), (p2[:, :, 0] - p2[:, :, 2]))
    psb = ps1 - ps2 # combined not filtered image

    # --- Step 4: Modulation ---
    Im = 0.5 * np.sqrt((p1[:, :, 3] - p1[:, :, 1]) ** 2 + (p1[:, :, 0] - p1[:, :, 2]) ** 2)

    # --- Step 5: Apply selected filter ---
    if lw % 2 == 0:
        lw += 1
    if hw % 2 == 0:
        hw += 1

    if filter_num == 1:
        psb_filtered = wiener(psb, (lw, hw))
    elif filter_num == 2:
        ss = medfilt2d(np.sin(psb), (lw, hw))
        cc = medfilt2d(np.cos(psb), (lw, hw))
        psb_filtered = np.arctan2(ss, cc)
    elif filter_num == 3:
        ss = medfilt2d(Im * np.sin(psb), (lw, hw))
        cc = medfilt2d(Im * np.cos(psb), (lw, hw))
        psb_filtered = np.arctan2(ss, cc)
    elif filter_num == 4:
        sigma = np.mean([sgl, sgh])
        ss = gaussian_filter(np.sin(psb), sigma)
        cc = gaussian_filter(np.cos(psb), sigma)
        psb_filtered = np.arctan2(ss, cc)
    else:
        raise ValueError("filter_num must be 1, 2, 3, or 4")

    # --- Step 6: Save results ---
    folder = os.path.dirname(set1_files[0])
    os.makedirs(folder, exist_ok=True)
    prefix = parse_filename(set1_files[0])[0]
    force1 = parse_filename(set1_files[0])[1]
    force2 = parse_filename(set2_files[0])[1]
    crop = parse_filename(set1_files[0])[3]

    if crop:
        name = f"filter{filter_num}-str{lw}_{crop}_{prefix}_{force2}-{force1}"
    else:
        name = f"filter{filter_num}-str{lw}_{prefix}_{force2}-{force1}"

    data_path = os.path.join(folder, f"{name}.tiff")
    io.imsave(data_path, psb_filtered.astype(np.float32))

    # Compute relative path for printing
    try:
        espi_root = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "ESPI_Images"
        )
        rel_path = os.path.relpath(data_path, espi_root)
    except ValueError:
        rel_path = data_path  # fallback

    print(f"✅ Filtered and subtracted phase saved to:\n  {rel_path}")

    # ==================================================
    # Step 7: Phase Unwrap (auto, skip existing)
    # ==================================================
    print("\n🔄 Starting phase unwrapping...")
    unwrap_count = unwrap_all_filter_images(folder)

    if unwrap_count == 0:
        print("⚠️ No new images unwrapped.")
    else:
        print(f"✅ Phase unwrapping complete ({unwrap_count} images).")

    # ==================================================
    # Step 8: Displacement Calculation (auto, skip existing)
    # ==================================================
    # print("\n📐 Starting displacement calculation...")
    # disp_count = get_displacement(folder)
    #
    # if disp_count == 0:
    #     print("⚠️ No new displacement images generated.")
    # else:
    #     print(f"✅ Displacement complete ({disp_count} images).")

    return folder




# --- Optional test code ---
if __name__ == "__main__":
    try:
        result = filter_and_subtract_one_set()
    except Exception as e:
        messagebox.showerror("Error", str(e))
