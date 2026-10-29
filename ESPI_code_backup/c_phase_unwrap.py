# phase_unwrap.py — auto unwrap with duplicate check and stop support
import os
import numpy as np
from skimage import io
import tkinter as tk
from tkinter import filedialog, messagebox
from skimage.restoration import unwrap_phase
from skimage.exposure import rescale_intensity
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def unwrap_all_filter_images(
        base_folder,
        image_paths=None,
        stop_flag=None
):
    """
    Automatically unwraps selected filter TIFF images.

    Parameters
    ----------
    base_folder : str
        Folder containing images.

    image_paths : list[str] or None
        Specific images to unwrap.
        If None, automatically searches folder.

    stop_flag : callable
        Optional stop callback.

    Returns
    -------
    int
        Number of images processed.
    """

    # =====================================================
    # USE PROVIDED IMAGE LIST
    # =====================================================
    if image_paths is not None:

        candidates = [
            os.path.basename(p)
            for p in image_paths
        ]

    # =====================================================
    # AUTO SEARCH (fallback)
    # =====================================================
    else:

        all_files = os.listdir(base_folder)
        valid_exts = ".tiff"

        candidates = [
            f for f in all_files
            if f.lower().endswith(valid_exts)
               and "filter" in os.path.splitext(f)[0].lower()
               and "uw_" not in os.path.splitext(f)[0].lower()
               and "disp" not in os.path.splitext(f)[0].lower()
        ]

    if not candidates:
        return 0

    processed_count = 0

    # =====================================================
    # PROCESS
    # =====================================================
    for filename in candidates:

        if stop_flag and stop_flag():
            print("⏹️ Unwrapping stopped by user.")
            break

        file_path = os.path.join(base_folder, filename)

        if not os.path.exists(file_path):
            continue

        base_name, ext = os.path.splitext(filename)

        tiff_path = os.path.join(
            base_folder,
            "UW_" + base_name + ".tiff"
        )

        png_path = os.path.join(
            base_folder,
            "UW_" + base_name + ".png"
        )

        comp_path = os.path.join(
            base_folder,
            "UW_" + base_name + "_comp.png"
        )

        # =====================================================
        # SKIP EXISTING
        # =====================================================
        if any(os.path.exists(p) for p in [tiff_path, png_path, comp_path]):
            continue

        image = io.imread(file_path).astype(np.float32)

        min_val = image.min()
        max_val = image.max()

        if max_val > 2 * np.pi or max_val <= 1.0:

            image_wrapped = (
                (image - min_val)
                / (max_val - min_val)
                * (2 * np.pi)
                - np.pi
            )

        else:
            image_wrapped = image

        # ==========================================
        # Preserve NaN mask
        # ==========================================
        nan_mask = ~np.isfinite(image_wrapped)

        print(f"NaN pixels: {np.count_nonzero(nan_mask)}")

        # Replace NaNs temporarily
        image_for_unwrap = image_wrapped.copy()
        image_for_unwrap[nan_mask] = 0.0

        # ==========================================
        # Unwrap
        # ==========================================
        image_unwrapped = unwrap_phase(image_for_unwrap)

        # ==========================================
        # Restore NaNs
        # ==========================================
        image_unwrapped[nan_mask] = np.nan

        # =====================================================
        # SAVE TIFF
        # =====================================================
        io.imsave(
            tiff_path,
            image_unwrapped.astype(np.float32)
        )

        processed_count += 1

        print(f"✅ Unwrapped: {os.path.basename(tiff_path)}")

    return processed_count