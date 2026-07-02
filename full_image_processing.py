# full_image_processing.py

import os
import re
from skimage import io
import numpy as np
import imageio.v2 as imageio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from scipy.signal import medfilt2d, wiener
from scipy.ndimage import gaussian_filter, median_filter

from phase_unwrap import unwrap_all_filter_images
from displacement import get_displacement
from displacement_custom import *

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

    # Handle nancrop1-crop1
    elif re.match(r"^nancrop.*-crop.*$", parts[0]):
        crop = parts.pop(0)

    if len(parts) != 3:
        raise ValueError(
            f"Unexpected filename format: {fname}\n"
            f"Parsed parts = {parts}"
        )

    prefix, force, phase, = parts
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


def collect_forces_for_set(folder, prefix, crop):
    """
    Returns:
      {
        force_value: [4 phase image paths]
      }
    for the selected prefix + crop only.
    """
    sets = {}

    for fname in os.listdir(folder):
        if not fname.lower().endswith(".tiff"):
            continue

        try:
            pfx, force, phase, cr = parse_filename(fname)
        except ValueError:
            continue

        if pfx != prefix or cr != crop:
            continue

        if phase not in PHASES:
            continue

        fval = extract_force_value(force)
        sets.setdefault(fval, [])
        sets[fval].append(os.path.join(folder, fname))

    # keep only complete phase sets
    sets = {f: imgs for f, imgs in sets.items() if len(imgs) == 4}
    print(sets)

    if len(sets) < 2:
        raise ValueError("Not enough force levels found for this set.")

    return dict(sorted(sets.items()))


def select_reference_image(initial_dir=None):
    """
    User selects ONE image to define the set (prefix + crop).
    Returns (folder, prefix, crop).
    """
    root = tk.Tk()
    root.withdraw()

    if initial_dir is None:
        initial_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "ESPI_Images",
            "1_RAW_new_images"
        ))

    file_path = filedialog.askopenfilename(
        title="Select ONE image to define the set",
        initialdir=initial_dir,
        filetypes=[("TIFF files", "*.tif *.tiff")]
    )

    if not file_path:
        raise ValueError("No image selected.")

    prefix, force, phase, crop = parse_filename(file_path)
    folder = os.path.dirname(file_path)

    return folder, prefix, crop


def get_filter_strength_and_num():
    """
    Opens a popup window to select:
      - vertical filter size (lv)
      - horizontal filter size (lh)
      - filter number

    Returns
    -------
    lv : int
    lh : int
    filter_num : int
    """

    result = {
        "lv": 11,
        "lh": 11,
        "filter_num": 3
    }

    def on_confirm():
        try:
            result["lv"] = int(vertical_var.get())
        except Exception:
            result["lv"] = 11

        try:
            result["lh"] = int(horizontal_var.get())
        except Exception:
            result["lh"] = 11

        try:
            result["filter_num"] = int(filter_var.get())
        except Exception:
            result["filter_num"] = 3

        popup.destroy()

    popup = tk.Tk()
    popup.title("Select Filter Parameters")
    popup.geometry("300x260")
    popup.resizable(False, False)
    popup.eval("tk::PlaceWindow . center")

    # -------------------------
    # VARIABLES
    # -------------------------
    size_values = [
        1, 3, 5, 7, 9, 11, 13, 15, 17, 19,
        21, 23, 25, 27, 29, 31, 33, 35, 37, 39
    ]

    filter_values = [1, 2, 3, 4]

    vertical_var = tk.StringVar(value="11")
    horizontal_var = tk.StringVar(value="11")
    filter_var = tk.StringVar(value="3")

    # -------------------------
    # LAYOUT
    # -------------------------
    frame = tk.Frame(popup, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="Vertical Size", anchor="w").pack(fill=tk.X)
    ttk.Combobox(
        frame,
        textvariable=vertical_var,
        values=size_values,
        state="readonly"
    ).pack(fill=tk.X, pady=(0, 15))

    tk.Label(frame, text="Horizontal Size", anchor="w").pack(fill=tk.X)
    ttk.Combobox(
        frame,
        textvariable=horizontal_var,
        values=size_values,
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

    return result["lv"], result["lh"], result["filter_num"]


def filter_and_subtract_all_sets(folder=None, do_displacement=True):

    lv, lh, filter_num = get_filter_strength_and_num()

    # ---- User selects ONE image ----
    folder, prefix, crop = select_reference_image(folder)

    # ---- Collect forces for this set only ----
    force_sets = collect_forces_for_set(folder, prefix, crop)
    forces = list(force_sets.keys())

    print(f"\n📁 Set selected:")
    print(f"   Prefix: {prefix}")
    print(f"   Crop:   {crop}")
    print(f"   Forces: {forces}")

    print("\n📂 Files in selected set:")
    for force, files in force_sets.items():
        print(f"\n   Force {force:g}:")

        for f in sorted(files):
            print(f"      {os.path.basename(f)}")

    generated_filter_files = []

    for f1, f2 in zip(forces[:-1], forces[1:]):
        print(f"\n🔹 Processing {f1} → {f2}")

        set1_files = sorted(force_sets[f1])
        set2_files = sorted(force_sets[f2])

        # ---------- Load ----------
        p1 = np.stack(
            [imageio.imread(f).astype(np.float64) / 255.0 for f in set1_files],
            axis=2
        )

        p2 = np.stack(
            [imageio.imread(f).astype(np.float64) / 255.0 for f in set2_files],
            axis=2
        )

        # ---------- Phase subtraction ----------
        ps1 = np.arctan2(
            p1[:, :, 3] - p1[:, :, 1],
            p1[:, :, 0] - p1[:, :, 2]
        )

        ps2 = np.arctan2(
            p2[:, :, 3] - p2[:, :, 1],
            p2[:, :, 0] - p2[:, :, 2]
        )

        psb = ps2 - ps1

        Im = 0.5 * np.sqrt(
            (p1[:, :, 3] - p1[:, :, 1]) ** 2 +
            (p1[:, :, 0] - p1[:, :, 2]) ** 2
        )

        # ---------- Ensure odd filter sizes ----------
        if lv % 2 == 0:
            lv += 1

        if lh % 2 == 0:
            lh += 1

        kernel = (lv, lh)

        # ---------- Filter ----------
        if filter_num == 1:
            psb_filtered = wiener(psb, kernel)

        elif filter_num == 2:
            ss = medfilt2d(np.sin(psb), kernel)
            cc = medfilt2d(np.cos(psb), kernel)
            psb_filtered = np.arctan2(ss, cc)

        elif filter_num == 3:
            # A) Ferreti version:
            ss = medfilt2d(Im * np.sin(psb), kernel)
            cc = medfilt2d(Im * np.cos(psb), kernel)
            psb_filtered = np.arctan2(ss, cc)

            # B) generic filter version: ////// replaced previous ss and cc to not affect edges and work with NaNs ////////
            # from scipy.ndimage import generic_filter

            # ss = generic_filter(
            #     Im * np.sin(psb),
            #     np.nanmedian,
            #     size=(lv, lh),
            #     mode="reflect"
            # )

            # cc = generic_filter(
            #     Im * np.cos(psb),
            #     np.nanmedian,
            #     size=(lv, lh),
            #     mode="reflect"
            # )

            # psb_filtered = np.arctan2(ss, cc)
            # //////////////////////////////////////////////////////////////////////////////////////////////////////////

            # C) fast version with edge preservaton and NaNs - should work (to try)/////////////////////////////////////
            # ==================================================
            # NaN mask
            # ==================================================
            # valid = np.isfinite(psb)
            #
            # # Work with phase-weighted signals
            # A = Im * np.sin(psb)
            # B = Im * np.cos(psb)
            #
            # # Replace NaNs temporarily (DO NOT use generic_filter)
            # A0 = np.where(valid, A, 0.0)
            # B0 = np.where(valid, B, 0.0)
            #
            # # ==================================================
            # # Core filtering (FAST C implementation)
            # # ==================================================
            # A_filt = median_filter(
            #     A0,
            #     size=(lv, lh),
            #     mode="reflect"
            # )
            #
            # B_filt = median_filter(
            #     B0,
            #     size=(lv, lh),
            #     mode="reflect"
            # )
            #
            # # ==================================================
            # # Validity normalization (key step)
            # # compensates for NaN regions correctly
            # # ==================================================
            # W = median_filter(
            #     valid.astype(np.float32),
            #     size=(lv, lh),
            #     mode="reflect"
            # )
            #
            # # Avoid division by zero
            # W = np.maximum(W, 1e-6)
            #
            # A_filt = A_filt / W
            # B_filt = B_filt / W
            #
            # # ==================================================
            # # Reconstruct phase
            # # ==================================================
            # psb_filtered = np.arctan2(A_filt, B_filt)
            #
            # # ==================================================
            # # Restore NaN regions
            # # ==================================================
            # psb_filtered[~valid] = np.nan

            # //////////////////////////////////////////////////////////////////////////////////////////////////////////


        else:
            raise ValueError("Invalid filter number")

        # ---------- Save ----------
        if crop:
            name = (
                f"filter{filter_num}-str{lv}x{lh}_"
                f"{crop}_{prefix}_{f2:g}-{f1:g}"
            )
        else:
            name = (
                f"filter{filter_num}-str{lv}x{lh}_"
                f"{prefix}_{f2:g}-{f1:g}"
            )

        out_path = os.path.join(folder, f"{name}.tiff")
        io.imsave(out_path, psb_filtered.astype(np.float32))

        print(f"✅ Saved {name}.tiff")
        generated_filter_files.append(out_path)

    print("\n🎉 All adjacent force pairs processed.")

    # ==================================================
    # Step 7: Phase Unwrap (auto, skip existing)
    # ==================================================
    print("\n🔄 Starting phase unwrapping on following images: ")
    print(generated_filter_files)
    unwrap_count = unwrap_all_filter_images(
        base_folder=folder,
        image_paths=generated_filter_files
    )

    if unwrap_count == 0:
        print("⚠️ No new images unwrapped.")
    else:
        print(f"✅ Phase unwrapping complete ({unwrap_count} images).")

    # ==================================================
    # Step 8: Displacement Calculation (auto, skip existing)
    # ==================================================
    if do_displacement:
        print("\n📐 Starting displacement calculation...")
        disp_count = get_displacement(folder)

        if disp_count == 0:
            print("⚠️ No new displacement images generated.")
        else:
            print(f"✅ Displacement complete ({disp_count} images).")

    return folder