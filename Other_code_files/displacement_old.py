# displacement.py

import os
import numpy as np
import math
from skimage import io
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from matplotlib.colors import TwoSlopeNorm
import tkinter as tk
from tkinter import filedialog, messagebox
from a__utils import select_base_folder


def get_displacement(
        base_folder=None,
        colormap="seismic",
        percentile=99.9,
        Zangle=45,
        XYrot=30):
    """
    Automatically generates displacement colormaps and 3D surface plots
    ONLY for '_UW.tiff' images that do NOT already have displacement outputs.

    Uses percentile-based robust color scaling to avoid outliers dominating
    the visualization.

    Out-of-range values are shown in magenta.
    """

    pixel_size_m = 17.0e-6  # pixel size for xy-axis plots

    # ============================
    # SELECT FOLDER IF NOT PROVIDED
    # ============================
    if not base_folder:
        root = tk.Tk()
        root.withdraw()

        base_folder = filedialog.askdirectory(
            title="Select folder containing 'UW_*.tiff' images"
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
    angle_deg = 27.2

    wavelength_m = wavelength_nm * 1e-9
    angle_rad = math.radians(angle_deg)

    coefficient = wavelength_m / (4 * np.pi * np.sin(angle_rad))

    # ============================
    # FIND ALL _UW.TIFF FILES
    # ============================
    uw_files = [
        f for f in os.listdir(base_folder)
        if f.startswith("UW_") and f.endswith(".tiff")
    ]

    if not uw_files:
        print("⚠️ No '_UW.tiff' images found in folder.")
        return 0

    processed_count = 0
    skipped_count = 0

    # ============================
    # CUSTOM COLORMAP
    # ============================
    cmap = plt.get_cmap(colormap).copy()

    # Outliers beyond percentile range
    cmap.set_over("magenta")
    cmap.set_under("magenta")

    for filename in uw_files:

        file_path = os.path.join(base_folder, filename)
        base_name, _ = os.path.splitext(filename)

        png_out = os.path.join(
            base_folder,
            f"disp_{base_name}_colormap_{colormap}_{percentile}pct.png"
        )

        surf_out = os.path.join(
            base_folder,
            f"disp_{base_name}_3D-surf_{colormap}_{percentile}pct_Z-{Zangle}_XY-{XYrot}.png"
        )

        if os.path.exists(png_out) and os.path.exists(surf_out):
            print(f"⏭ Skipping (already processed): {filename}")
            skipped_count += 1
            continue

        # ----------------------------
        # LOAD PHASE IMAGE
        # ----------------------------
        delta_phi = io.imread(file_path).astype(np.float32)

        displacement_m = coefficient * delta_phi
        displacement_um = displacement_m * 1e6

        # ----------------------------
        # SAVE DISPLACEMENT TIFF
        # ----------------------------
        tiff_out = os.path.join(
            base_folder,
            f"disp-um_{base_name}.tiff"
        )

        io.imsave(
            tiff_out,
            displacement_um.astype(np.float32)
        )

        # ============================
        # ROBUST PERCENTILE SCALING
        # ============================
        # ======================================
        # ROBUST DISTRIBUTION-BASED COLOR SCALE
        # ======================================

        valid = displacement_um[np.isfinite(displacement_um)]

        # Median of displacement field
        median_disp = np.median(valid)

        # Distance from median
        dist_from_median = valid - median_disp

        # Determine robust lower/upper limits
        lower_limit = np.percentile(dist_from_median, 100 - percentile)
        upper_limit = np.percentile(dist_from_median, percentile)

        # Shift limits back to displacement coordinates
        vmin = median_disp + lower_limit
        vmax = median_disp + upper_limit

        print(f"[INFO]")
        print(f"Median displacement = {median_disp:.4f} µm")
        print(f"{percentile}% range:")
        print(f"vmin = {vmin:.4f} µm")
        print(f"vmax = {vmax:.4f} µm")

        # IMPORTANT:
        # White stays at ZERO displacement
        norm = TwoSlopeNorm(
            vmin=vmin,
            vcenter=0.0,
            vmax=vmax
        )

        # ============================
        # 2D COLORMAP
        # ============================
        h, w = displacement_um.shape

        x_extent_mm = w * pixel_size_m * 1000
        y_extent_mm = h * pixel_size_m * 1000

        fig, ax = plt.subplots(figsize=(8, 6))

        im = ax.imshow(
            displacement_um,
            cmap=cmap,
            norm=norm,
            extent=[0, x_extent_mm, 0, y_extent_mm],
            aspect="equal"
        )

        # ----------------------------
        # COLORBAR
        # ----------------------------
        cbar = plt.colorbar(
            im,
            ax=ax,
            extend='both',
            ticks=[vmin, vmax]
        )

        cbar.set_ticklabels([
            f"{vmin:.2f}",
            f"{vmax:.2f}"
        ])

        cbar.set_label(
            "Displacement (µm)",
            fontsize=12
        )

        # ----------------------------
        # AXES
        # ----------------------------
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")

        ax.set_title(
            f"{base_name}\n"
            f"({percentile}% of data)",
            fontsize=11
        )

        # Better ticks
        ax.tick_params(
            axis='both',
            which='major',
            labelsize=10
        )

        # Grid
        ax.grid(
            linestyle='--',
            linewidth=0.4,
            alpha=0.5
        )

        plt.tight_layout()

        plt.savefig(
            png_out,
            dpi=600,
            bbox_inches='tight'
        )

        plt.close()

        print(f"✔ Saved colormap: {png_out}")

        # ============================
        # OPTIONAL 3D SURFACE PLOT
        # ============================
        # Uncomment if desired

        # x_axis = np.arange(w) * pixel_size_m * 1000
        # y_axis = np.arange(h) * pixel_size_m * 1000
        #
        # X, Y = np.meshgrid(x_axis, y_axis)
        #
        # fig = plt.figure(figsize=(10, 8))
        # ax = fig.add_subplot(111, projection="3d")
        #
        # surf = ax.plot_surface(
        #     X,
        #     Y,
        #     displacement_um,
        #     cmap=cmap,
        #     norm=norm,
        #     linewidth=0
        # )
        #
        # ax.view_init(
        #     elev=Zangle,
        #     azim=XYrot - 90
        # )
        #
        # ax.set_xlabel("X (mm)")
        # ax.set_ylabel("Y (mm)")
        # ax.set_zlabel("Displacement (µm)")
        #
        # ax.invert_yaxis()
        #
        # fig.colorbar(
        #     surf,
        #     shrink=0.5,
        #     extend='both',
        #     label="Displacement (µm)"
        # )
        #
        # plt.tight_layout()
        #
        # plt.savefig(
        #     surf_out,
        #     dpi=300,
        #     bbox_inches='tight'
        # )
        #
        # plt.close()
        #
        # print(f"✔ Saved 3D surface: {surf_out}")

        processed_count += 1

    print(
        f"\n✅ Displacement complete: "
        f"{processed_count} processed, "
        f"{skipped_count} skipped."
    )

    return processed_count


if __name__ == "__main__":

    folder = select_base_folder()

    get_displacement(
        base_folder=folder,
        colormap="seismic",   # better than jet for signed displacement
    )





