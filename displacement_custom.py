# displacement_custom.py
import os
import numpy as np
import math
from skimage import io
import matplotlib
matplotlib.use("TkAgg")  # ensures interactive plots
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
import tkinter as tk
from tkinter import filedialog, messagebox
from utils import select_base_folder  # optional, can be replaced with file dialog


def choose_nice_symmetric_scale(data, allowed_scales=[1, 2, 2.5, 5, 10, 20, 40]):
    """
    Returns the smallest symmetric scale ±scale that encompasses all values in data.
    """
    max_abs = np.nanmax(np.abs(data))
    # pick the first allowed scale >= max_abs
    scale = np.array(allowed_scales)[np.array(allowed_scales) >= max_abs][0]
    return -scale, scale


def displacement_custom(base_folder=None, Zangle=45, XYrot=30, consistent_scale=True):
    """
    Generates displacement colormaps and 3D surface plots for '_UW.tiff' images.
    - Colorbars are symmetric around zero and use “nice” scales (1,2,2.5,5,10,20,40).
    - Uses a custom cyclic colormap.
    - Opens file explorer if base_folder is not provided.
    """
    pixel_size_m = 22.2e-6  # pixel size for xy-axis plots

    # ============================
    # Define full color lists
    # ============================

    step = 0.05
    epsilon = 1e-4

    colors = [
        # ------------------------
        # Lower half (18)
        # ------------------------
        "red", "orange",
        "yellow", "lime",
        "green", "cyan",
        "deepskyblue", "dodgerblue",
        "blue", "navy",
        "purple", "magenta",
        "hotpink", "crimson",
        "darkred", "black",
        "dimgray", "gray",

        # ------------------------
        # Center (3)
        # ------------------------
        "black", "white", "red",

        # ------------------------
        # Upper half (18)
        # ------------------------
        "orange", "lime",
        "yellow", "green",
        "blue", "hotpink",
        "maroon", "white",
        "blue", "blue",
        "dodgerblue", "deepskyblue",
        "cyan", "green",
        "lime", "yellow",
        "orange", "red",
    ]

    # ============================
    # Positions (original behavior)
    # ============================
    positions = [
        # Lower half (paired)
        0.0, 0.04999,
        0.05, 0.09999,
        0.10, 0.14999,
        0.15, 0.19999,
        0.20, 0.24999,
        0.25, 0.29999,
        0.30, 0.34999,
        0.35, 0.39999,
        0.40, 0.44999,

        # Center (3)
        0.45,
        0.5,
        0.55,

        # Upper half (paired, just above previous step)
        0.550001, 0.60,
        0.600001, 0.65,
        0.650001, 0.70,
        0.700001, 0.75,
        0.750001, 0.80,
        0.800001, 0.85,
        0.850001, 0.90,
        0.900001, 0.95,
        0.950001, 1.0
        ]

    # ============================
    # Create colormap
    # ============================
    cyclic_cmap = LinearSegmentedColormap.from_list(
        "custom_cyclic",
        list(zip(positions, colors)),
        N=256
    )

    # ============================
    # SELECT FOLDER IF NOT PROVIDED
    # ============================
    if not base_folder:
        root = tk.Tk()
        root.withdraw()
        base_folder = filedialog.askdirectory(
            title="Select folder containing '_UW.tiff' images"
        )
        root.destroy()
        if not base_folder:
            print("❌ No folder selected. Displacement cancelled.")
            return 0

    if not os.path.isdir(base_folder):
        messagebox.showerror(
            "Invalid Folder",
            f"The selected folder does not exist:\n{base_folder}"
        )
        return 0

    # ============================
    # DISPLACEMENT CONSTANTS
    # ============================
    wavelength_nm = 633
    angle_deg = 12.5
    wavelength_m = wavelength_nm * 1e-9
    angle_rad = math.radians(angle_deg)
    coefficient = wavelength_m / (4 * np.pi * np.sin(angle_rad))

    # ============================
    # FIND ALL _UW.TIFF FILES
    # ============================
    uw_files = [f for f in os.listdir(base_folder) if f.endswith("_UW.tiff")]
    if not uw_files:
        print("⚠️ No '_UW.tiff' images found in folder.")
        return 0

    # ============================
    # COMPUTE GLOBAL MAX IF CONSISTENT SCALE
    # ============================
    if consistent_scale:
        global_max_disp = 0
        for f in uw_files:
            data = io.imread(os.path.join(base_folder, f)).astype(np.float32)
            disp_um = data * coefficient * 1e6
            global_max_disp = max(global_max_disp, np.nanmax(np.abs(disp_um)))
        min_val, max_val = -2.5, 2.5#choose_nice_symmetric_scale(np.array([-global_max_disp, global_max_disp]))
    else:
        min_val = max_val = None

    processed_count = 0
    skipped_count = 0

    for filename in uw_files:
        file_path = os.path.join(base_folder, filename)
        base_name, _ = os.path.splitext(filename)

        png_out = os.path.join(base_folder, f"{base_name}_disp_colormap_custom.png")
        surf_out = os.path.join(base_folder, f"{base_name}_disp_3D-surf_custom_Z-{Zangle}_XY-{XYrot}.png")

        if os.path.exists(png_out) and os.path.exists(surf_out):
            print(f"⏭ Skipping (already processed): {filename}")
            skipped_count += 1
            continue

        # ----------------------------
        # LOAD PHASE IMAGE
        # ----------------------------
        delta_phi = io.imread(file_path).astype(np.float32)
        displacement_um = delta_phi * coefficient * 1e6  # µm

        # ----------------------------
        # SYMMETRIC COLORBAR NORMALIZATION
        # ----------------------------
        if not consistent_scale:
            min_val, max_val = choose_nice_symmetric_scale(displacement_um)

        norm = TwoSlopeNorm(vmin=min_val, vcenter=0.0, vmax=max_val)

        # ----------------------------
        # COLORMAP PNG (2D)
        # ----------------------------
        h, w = displacement_um.shape
        x_extent_mm = w * pixel_size_m * 1000
        y_extent_mm = h * pixel_size_m * 1000

        plt.figure(figsize=(8, 6))
        im = plt.imshow(
            displacement_um,
            cmap=cyclic_cmap,
            norm=norm,
            extent=[0, x_extent_mm, y_extent_mm, 0],
            aspect="equal"
        )
        cbar = plt.colorbar(im)
        cbar.set_label("Displacement (µm)", fontsize=12)

        plt.xlabel("X (mm)")
        plt.ylabel("Y (mm)")
        plt.title(f"{base_name}")

        plt.tight_layout()
        plt.savefig(png_out, dpi=300)
        plt.close()

        # ----------------------------
        # 3D SURFACE PLOT
        # ----------------------------
        x_axis = np.arange(w) * pixel_size_m * 1000  # mm
        y_axis = np.arange(h) * pixel_size_m * 1000  # mm
        X, Y = np.meshgrid(x_axis, y_axis)

        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection="3d")

        surf = ax.plot_surface(
            X, Y, displacement_um,
            cmap=cyclic_cmap,
            norm=norm,
            linewidth=0
        )

        ax.view_init(elev=Zangle, azim=XYrot - 90)
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.set_zlabel("Displacement (µm)")
        ax.invert_yaxis()

        fig.colorbar(surf, shrink=0.5, label="Displacement (µm)")
        plt.tight_layout()
        plt.savefig(surf_out, dpi=300)
        plt.close()

        print(f"✔ 3D surface plot saved: {surf_out}")
        processed_count += 1

    print(f"\nDisplacement complete: {processed_count} processed, {skipped_count} skipped.")
    return processed_count


if __name__ == "__main__":
    folder = select_base_folder()  # or leave None to prompt folder explorer
    displacement_custom(base_folder=folder)
