#subtraction.py

import os
import numpy as np
from skimage import io, exposure
from tkinter import Tk, filedialog, messagebox


def split_filename_parts(filename):
    """
    Splits a filename of the form prefix_middle_timestamp.tiff
    Returns (prefix, middle, timestamp).
    Example:
        test2_load0_20251001T163335.tiff
        -> ("test2", "load0", "20251001T163335")
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    parts = base.split("_")
    if len(parts) < 3:
        raise ValueError(f"Unexpected filename format: {filename}")
    prefix = parts[0]
    middle = "_".join(parts[1:-1])  # handles cases like load_extra
    timestamp = parts[-1]
    return prefix, middle, timestamp


def subtract_two_images():
    """
    Allows user to select two TIFF images from ESPI_Images_2_Combined,
    subtracts the first from the second using a wrapped subtraction formula,
    and saves two versions in ESPI_Images_3_Subtracted:
      1. Normalized 8-bit image for visualization (_view.tiff)
      2. Float32 image for further analysis (_data.tiff)
    """

    # ==== Paths ====
    script_dir = os.path.dirname(os.path.abspath(__file__))
    unwrapped_folder = os.path.join(script_dir, "ESPI_Images_2_Combined")
    subtracted_folder = os.path.join(script_dir, "ESPI_Images_3_Subtracted")
    os.makedirs(subtracted_folder, exist_ok=True)

    # ==== GUI File Selection ====
    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="Select TWO TIFF images",
        initialdir=unwrapped_folder,
        filetypes=[("TIFF files", "*.tif *.tiff")]
    )

    if len(file_paths) != 2:
        messagebox.showerror("Selection Error", "Please select exactly TWO TIFF images.")
        return

    # ==== Load Images ====
    img1 = io.imread(file_paths[0]).astype(np.float64)
    img2 = io.imread(file_paths[1]).astype(np.float64)

    # ==== Subtract First Image from Second using wrapped formula ====
    diff = img2 - img1
    result = (diff + np.pi) % (2 * np.pi) - np.pi

    # ==== Normalize for Visualization (8-bit) ====
    result_norm = exposure.rescale_intensity(result, in_range="image", out_range=(0, 255))
    result_uint8 = result_norm.astype(np.uint8)

    # ==== Build Filenames ====
    prefix1, middle1, ts1 = split_filename_parts(file_paths[0])
    prefix2, middle2, ts2 = split_filename_parts(file_paths[1])

    if prefix1 != prefix2:
        raise ValueError("Filenames have different prefixes — cannot combine safely.")

    base_name = f"{prefix1}_{middle2}-{middle1}"
    view_name = base_name + "_view.tiff"
    data_name = base_name + "_data.tiff"

    view_path = os.path.join(subtracted_folder, view_name)
    data_path = os.path.join(subtracted_folder, data_name)

    # ==== Save Results ====
    io.imsave(view_path, result_uint8)              # 8-bit view
    io.imsave(data_path, result.astype(np.float32)) # float32 for analysis

    print(f"✅ Saved normalized (view) image to:\n{view_path}")
    print(f"✅ Saved float32 (data) image to:\n{data_path}")
