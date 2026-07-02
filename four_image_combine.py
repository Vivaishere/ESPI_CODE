# four_image_combine.py

import os
import glob
import numpy as np
from skimage import io
from skimage.util import img_as_float
import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend to save figures
import matplotlib.pyplot as plt

def four_image_combine(filename, folder, logger=print):
    """
    Combine 4 phase-shifted images using the 4-step method
    and save the wrapped phase image and visualization in the same folder.
    Does not create extra folders.
    """

    # --- Step 1: Find the 4 images for the latest series ---
    latest_4 = get_latest_series(folder)

    # Map them to I1, I2, I3, I4
    img_paths = {
        'I1': latest_4[0],
        'I2': latest_4[1],
        'I3': latest_4[2],
        'I4': latest_4[3],
    }

    logger(f"Using images for combination: {list(img_paths.values())}")
    for key, path in img_paths.items():
        logger(f" {key}: {os.path.basename(path)}")

    # === Load and convert images to float ===
    images = {key: img_as_float(io.imread(path)) for key, path in img_paths.items()}

    # === Compute wrapped phase using 4-step method ===
    numerator = images['I4'] - images['I2']
    denominator = images['I3'] - images['I1']
    phi_wrapped = arctan2_custom(numerator, denominator)

    # === Save TIFF in the same folder ===
    save_path_tiff = os.path.join(folder, f"{filename}.tiff")
    io.imsave(save_path_tiff, phi_wrapped.astype(np.float32))
    logger(f"✅ Combined wrapped phase image saved as: {save_path_tiff}")


# --- Utility functions ---

def sgn(x):
    return np.where(x > 0, 1, np.where(x < 0, -1, 0))


def arctan2_custom(x, y):
    x = np.asarray(x)
    y = np.asarray(y)
    result = np.zeros_like(x)
    mask_pos = y > 0
    result[mask_pos] = sgn(x[mask_pos]) * np.arctan(np.abs(x[mask_pos] / y[mask_pos]))
    mask_zero = y == 0
    result[mask_zero] = sgn(x[mask_zero]) * (np.pi / 2)
    mask_neg = y < 0
    result[mask_neg] = sgn(x[mask_neg]) * (np.pi - np.arctan(np.abs(x[mask_neg] / y[mask_neg])))
    return result


def get_latest_series(folder):
    """
    Get the latest group of 4 images based on file modification time.
    Looks for files ending in _000.tiff, _090.tiff, _180.tiff, _270.tiff.
    """
    required_suffixes = ["_000.tiff", "_090.tiff", "_180.tiff", "_270.tiff"]
    series = {}
    for suffix in required_suffixes:
        files = glob.glob(os.path.join(folder, f"*{suffix}"))
        if not files:
            raise FileNotFoundError(f"No file found ending with {suffix}")
        latest_file = max(files, key=os.path.getmtime)
        series[suffix] = latest_file

    return [
        series["_000.tiff"],
        series["_090.tiff"],
        series["_180.tiff"],
        series["_270.tiff"]
    ]
