#disp_3D_plot.py

import os
import numpy as np
import math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa
from matplotlib.colors import TwoSlopeNorm
from tkinter import Tk, filedialog
from skimage import io

def plot_3D_from_tiff(colormap="jet", Zangle=45, XYrot=-30):
    """
    Creates 3D surface plots from selected TIFF images.

    If filename contains 'disp-um_' → values already represent displacement (µm).
    If filename contains 'UW' only → phase values are converted to displacement.

    Saved output filename:
    3D_<original_filename>.png
    """

    pixel_size_m = 18.7e-6

    # ==========================
    # Select TIFF files
    # ==========================
    root = Tk()
    root.withdraw()

    files = filedialog.askopenfilenames(
        title="Select TIFF images",
        filetypes=[("TIFF files", "*.tiff")]
    )

    root.destroy()

    if not files:
        print("No files selected.")
        return

    # ==========================
    # Displacement constants
    # ==========================
    wavelength_nm = 633
    angle_deg = 12.3

    wavelength_m = wavelength_nm * 1e-9
    angle_rad = math.radians(angle_deg)

    coefficient = wavelength_m / (4 * np.pi * np.sin(angle_rad))

    # ==========================
    # Process files
    # ==========================
    for file_path in files:

        filename = os.path.basename(file_path)
        folder = os.path.dirname(file_path)

        print(f"\nProcessing: {filename}")

        img = io.imread(file_path).astype(np.float32)

        # --------------------------
        # Determine if conversion needed
        # --------------------------
        if "disp-um_" in filename:
            displacement_um = img
            print("Detected displacement image (no conversion).")

        elif "UW" in filename:
            displacement_m = coefficient * img
            displacement_um = displacement_m * 1e6
            print("Detected unwrapped phase → converting to displacement.")

        else:
            print("Skipping file (not recognized format).")
            continue

        # ==========================
        # Normalization
        # ==========================
        max_abs_disp = np.nanmax(np.abs(displacement_um))

        norm = TwoSlopeNorm(
            vmin=-max_abs_disp,
            vcenter=0.0,
            vmax=max_abs_disp
        )

        # ==========================
        # Build coordinate grid
        # ==========================
        h, w = displacement_um.shape

        x_axis = np.arange(w) * pixel_size_m * 1000
        y_axis = np.arange(h) * pixel_size_m * 1000

        X, Y = np.meshgrid(x_axis, y_axis)

        # ==========================
        # Create 3D plot
        # ==========================
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection="3d")

        surf = ax.plot_surface(
            X,
            Y,
            displacement_um,
            cmap=colormap,
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

        # ==========================
        # Save
        # ==========================
        save_name = f"3D_{os.path.splitext(filename)[0]}.png"
        save_path = os.path.join(folder, save_name)

        plt.savefig(save_path, dpi=300)
        plt.close()

        print(f"✔ Saved: {save_path}")

if __name__ == "__main__":
    plot_3D_from_tiff(Zangle=10, XYrot=-60)