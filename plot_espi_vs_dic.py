# plot_espi_vs_dic.py

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from skimage import io
from skimage.transform import resize
import tkinter as tk
from tkinter import filedialog
import os
import re

# ---------------------------
# ESPI constants
# ---------------------------
PIXEL_SIZE_M = 18.7e-6  # meters per pixel (from ESPI)
PIXEL_SIZE_UM = PIXEL_SIZE_M * 1e6  # µm
PIXEL_SIZE_MM = PIXEL_SIZE_UM / 1000  # mm


def compute_percent_diff_average(y_true, y_pred, x_axis):
    """
    Compute average percent difference between ESPI (y_true) and DIC (y_pred)
    for two edge regions: -10 < x < -2 and 2 < x < 10.
    Returns the average of the two percentages.
    """
    # Left edge
    left_mask = (x_axis > -10) & (x_axis < -2)
    avg_left_true = np.mean(y_true[left_mask])
    avg_left_pred = np.mean(y_pred[left_mask])
    percent_left = abs(avg_left_true - avg_left_pred) / abs(avg_left_true) * 100

    # Right edge
    right_mask = (x_axis > 2) & (x_axis < 10)
    avg_right_true = np.mean(y_true[right_mask])
    avg_right_pred = np.mean(y_pred[right_mask])
    percent_right = abs(avg_right_true - avg_right_pred) / abs(avg_right_true) * 100

    # Average of the two percentages
    percent_avg = (percent_left + percent_right) / 2
    return percent_avg


def compare_espi_dic_profiles(save_plot=True):

    # ---------------------------
    # Default folder (ESPI_Images)
    # ---------------------------
    base_dir = os.path.dirname(__file__)
    espi_folder = os.path.join(base_dir, "ESPI_Images")

    # ---------------------------
    # Select ESPI image (larger)
    # ---------------------------
    root = tk.Tk()
    root.withdraw()

    espi_path = filedialog.askopenfilename(
        title="Select ESPI displacement TIFF (larger image)",
        initialdir=espi_folder,
        filetypes=[("TIFF files", "*.tiff *.tif")]
    )

    if not espi_path:
        print("No ESPI image selected.")
        return

    # Extract digits after "str" in filename for filter label
    espi_filename = os.path.basename(espi_path)
    match = re.search(r'str(\d+)', espi_filename, re.IGNORECASE)
    filter_label = f"filter{match.group(1)}" if match else "filter"

    # ---------------------------
    # Select DIC image (smaller)
    # ---------------------------
    dic_path = filedialog.askopenfilename(
        title="Select DIC displacement TIFF (smaller image)",
        initialdir=espi_folder,
        filetypes=[("TIFF files", "*.tiff *.tif")]
    )

    root.destroy()

    if not dic_path:
        print("No DIC image selected.")
        return

    # ---------------------------
    # Load images
    # ---------------------------
    espi = io.imread(espi_path).astype(np.float32)
    dic = io.imread(dic_path).astype(np.float32)

    espi_rows, espi_cols = espi.shape
    dic_rows, dic_cols = dic.shape

    print(f"ESPI size: {espi.shape}")
    print(f"DIC size: {dic.shape}")

    # ---------------------------
    # Resize DIC to ESPI size
    # ---------------------------
    if dic.shape != espi.shape:
        dic = resize(
            dic,
            (espi_rows, espi_cols),
            preserve_range=True,
            anti_aliasing=True
        ).astype(np.float32)
        print(f"DIC resized to: {dic.shape}")

    # ---------------------------
    # X axis in mm using ESPI pixel size (centered)
    # ---------------------------
    center_col = espi_cols // 2
    x = (np.arange(espi_cols) - center_col) * PIXEL_SIZE_MM  # mm

    # ---------------------------
    # Heights to extract
    # ---------------------------
    heights = {
        "0.3_height": int(espi_rows * 0.3),
        "0.4_height": int(espi_rows * 0.4),
        "0.9_height": int(espi_rows * 0.9),
        "0.95_height": int(espi_rows * 0.95)
    }

    # ---------------------------
    # Plot profiles
    # ---------------------------
    for label, row_index in heights.items():

        espi_line = espi[row_index, :]
        dic_line = dic[row_index, :]

        # Compute average percent difference of two edges
        percent_diff = compute_percent_diff_average(espi_line, dic_line, x)

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(x, espi_line, linewidth=1.5, label="ESPI")
        ax.plot(x, dic_line, linewidth=1.5, label="DIC")

        ax.axhline(0, color='black', linewidth=1)

        # Tick spacing
        ax.xaxis.set_major_locator(mticker.MultipleLocator(2))
        ax.xaxis.set_minor_locator(mticker.MultipleLocator(0.5))

        ax.minorticks_on()
        ax.grid(which='major', linestyle='--', linewidth=0.5, color='black', alpha=0.8)
        ax.grid(which='minor', linestyle='--', linewidth=0.5, color='gray', alpha=0.5)

        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Displacement (µm)")
        ax.set_title(f"ESPI vs DIC at {label.replace('_',' ')}")

        ax.legend()

        # Add percent difference text
        ax.text(
            0.95, 0.05, f"Avg percent diff (-10 <-> -2 & 2 <-> 10) = {percent_diff:.2f}%",
            transform=ax.transAxes,
            fontsize=12,
            verticalalignment='bottom',
            horizontalalignment='right',
            bbox=dict(facecolor='white', alpha=0.6, edgecolor='gray')
        )

        plt.tight_layout()

        # ---------------------------
        # Save figure
        # ---------------------------
        if save_plot:
            filename = f"ESPI_DIC_Comparison_{filter_label}_{label}.png"
            save_folder = os.path.dirname(espi_path)
            save_path = os.path.join(save_folder, filename)
            plt.savefig(save_path, dpi=300)
            print(f"Saved: {save_path}")

        plt.close(fig)


if __name__ == "__main__":
    compare_espi_dic_profiles()
