# img_processing_support_functions.py

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
from scipy.signal import medfilt2d
from scipy.ndimage import median_filter, generic_filter

# Define the 4 phases
PHASES = ["000", "090", "180", "270"]


# ==========================================================
# File parsing
# ==========================================================

def parse_filename(fname):
    """
    Parses filenames like:
      crop1_expname_force_phase.tiff
      expname_force_phase.tiff

    Returns:
        prefix, force, phase, crop
    """

    name = os.path.splitext(os.path.basename(fname))[0]
    parts = name.split("_")

    crop = None

    if parts[0].startswith("crop"):
        crop = parts.pop(0)

    elif re.match(r"^nancrop.*-crop.*$", parts[0]):
        crop = parts.pop(0)

    elif re.match(r"^crackcrop.*-crop.*$", parts[0]):
        crop = parts.pop(0)

    if len(parts) != 3:
        raise ValueError(
            f"Unexpected filename format:\n{fname}\n"
            f"Parsed parts = {parts}"
        )

    prefix, force, phase = parts

    return prefix, force, phase, crop


# ==========================================================
# Force value
# ==========================================================

def extract_force_value(force_str):

    match = re.search(r"[-+]?\d*\.?\d+", force_str)

    if not match:
        raise ValueError(
            f"Cannot extract numeric force from '{force_str}'"
        )

    return float(match.group())


# ==========================================================
# Collect force sets
# ==========================================================

def collect_forces_for_set(folder, prefix, crop):

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

    sets = {
        f: imgs
        for f, imgs in sets.items()
        if len(imgs) == 4
    }

    print(sets)

    if len(sets) < 2:
        raise ValueError(
            "Not enough force levels found for this set."
        )

    return dict(sorted(sets.items()))


# ==========================================================
# Image selection
# ==========================================================

def select_reference_image(initial_dir=None):

    root = tk.Tk()
    root.withdraw()

    if initial_dir is None:

        initial_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "ESPI_Images",
                "1_RAW_new_images"
            )
        )

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


# ==========================================================
# GUI
# ==========================================================

def get_filter_strength_and_num():

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

    size_values = [
        1, 3, 5, 7, 9, 11, 13, 15, 17, 19,
        21, 23, 25, 27, 29, 31, 33, 35, 37, 39
    ]

    filter_values = [1, 2, 3, 4]

    vertical_var = tk.StringVar(value="11")
    horizontal_var = tk.StringVar(value="11")
    filter_var = tk.StringVar(value="3")

    frame = tk.Frame(
        popup,
        padx=20,
        pady=20
    )

    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        frame,
        text="Vertical Size",
        anchor="w"
    ).pack(fill=tk.X)

    ttk.Combobox(
        frame,
        textvariable=vertical_var,
        values=size_values,
        state="readonly"
    ).pack(fill=tk.X, pady=(0, 15))

    tk.Label(
        frame,
        text="Horizontal Size",
        anchor="w"
    ).pack(fill=tk.X)

    ttk.Combobox(
        frame,
        textvariable=horizontal_var,
        values=size_values,
        state="readonly"
    ).pack(fill=tk.X, pady=(0, 15))

    tk.Label(
        frame,
        text="Filter Number",
        anchor="w"
    ).pack(fill=tk.X)

    ttk.Combobox(
        frame,
        textvariable=filter_var,
        values=filter_values,
        state="readonly"
    ).pack(fill=tk.X, pady=(0, 20))

    ttk.Button(
        frame,
        text="Confirm",
        command=on_confirm
    ).pack()

    popup.grab_set()
    popup.mainloop()

    return (
        result["lv"],
        result["lh"],
        result["filter_num"]
    )

# ==================================================
# DEBUG: PHASE QUALITY DIAGNOSTICS
# ==================================================

def save_phase_quality_diagnostics(folder, Im, psb, f1, f2):
    """
    Saves diagnostic plots for phase quality analysis.
    """

    import os
    import numpy as np
    import matplotlib.pyplot as plt

    # ----- Histogram of fringe modulation -----
    plt.figure(figsize=(8, 5))
    plt.hist(Im.ravel(), bins=200)
    plt.title("Histogram of Fringe Modulation (Im)")
    plt.xlabel("Im")
    plt.ylabel("Pixel Count")
    plt.grid(True)

    plt.savefig(
        os.path.join(folder, f"DEBUG_Histogram_Im_{f1:g}_to_{f2:g}.png"),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # ----- Image of fringe modulation -----
    plt.figure(figsize=(8, 6))
    plt.imshow(Im, cmap="viridis")
    plt.colorbar(label="Im")
    plt.title("Fringe Modulation (Im)")

    plt.savefig(
        os.path.join(folder, f"DEBUG_ModulationMap_{f1:g}_to_{f2:g}.png"),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # ----- Wrapped phase -----
    plt.figure(figsize=(8, 6))
    plt.imshow(psb, cmap="jet", vmin=-np.pi, vmax=np.pi)
    plt.colorbar(label="Phase (rad)")
    plt.title("Wrapped Phase")

    plt.savefig(
        os.path.join(folder, f"DEBUG_WrappedPhase_{f1:g}_to_{f2:g}.png"),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # ----- High-modulation mask -----
    threshold = 0.10 * np.max(Im)

    plt.figure(figsize=(8, 6))
    plt.imshow(Im > threshold, cmap="gray")
    plt.title(f"High Modulation Pixels (>{threshold:.3f})")

    plt.savefig(
        os.path.join(folder, f"DEBUG_ModulationMask_{f1:g}_to_{f2:g}.png"),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()