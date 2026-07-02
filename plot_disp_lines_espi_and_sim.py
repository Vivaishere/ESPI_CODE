# plot_disp_lines_espi_and_sim.py

import os
import math
import numpy as np
from skimage import io
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy.interpolate import UnivariateSpline
import tkinter as tk
from tkinter import filedialog
import re


def build_espi_save_filename(
        file_paths,
        actual_distance_mm,
        center_adjust
):
    """
    Build a filename for the ESPI plot, using all of the base filename
    except what comes after the last underscore.
    """
    first_image_name = os.path.basename(file_paths[0])

    # Split on last underscore
    if "_" in first_image_name:
        first_part = first_image_name.rsplit("_", 1)[0]  # everything before last _
    else:
        first_part = os.path.splitext(first_image_name)[0]  # fallback: full name without extension

    center_str = f"centerAdj{center_adjust}"

    return f"{first_part}_DfromCENTERmm={actual_distance_mm:.2f}_{center_str}.png"


def get_simulation_ux_line(filename="nodes_disp.txt", y_height=12.0, radius=12.0, mirror=True):
    """
        Load FEA simulation displacement line from txt file and return
        X and UX (in µm) for a horizontal line at y_height.
        """
    # --- Build full path to FEA_comparison folder ---
    script_dir = os.path.dirname(os.path.abspath(__file__))  # folder where this script lives
    fea_folder = os.path.join(script_dir, "FEA_comparison")
    file_path = os.path.join(fea_folder, filename)

    data = np.loadtxt(file_path, skiprows=1)
    x = data[:, 1]
    y = data[:, 2]
    ux = data[:, 4]

    tol = 0.01 * (max(y) - min(y))
    mask = (y >= y_height - tol) & (y <= y_height + tol) & (np.abs(x) <= radius)

    x_line = x[mask]
    ux_line = ux[mask]

    if mirror:
        x_line = np.concatenate([x_line, -x_line])
        ux_line = np.concatenate([ux_line, -ux_line])

    sort_idx = np.argsort(x_line)
    x_line = x_line[sort_idx]
    ux_line = ux_line[sort_idx]

    ux_line_um = ux_line * 1000  # mm → µm

    return x_line, ux_line_um



def plot_ux_tiff_sim(
    sim_filename="nodes_disp.txt",
    sim_radius=11.5,
    dist_from_center_mm=-10,
    center_adjust=True,
    include_sim=True,
    include_sum=True,
    save_plot=True
):
    """
    Plots TIFF lines at a given vertical distance and optionally overlays the FEA simulation.
    """
    # ---------------------------
    # Select TIFF files
    # ---------------------------
    root = tk.Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="Select '.tiff' images",
        initialdir=os.path.join(os.path.dirname(__file__), "ESPI_Images"),
        filetypes=[("TIFF files", "*Disp*.tiff")]
    )
    root.destroy()

    if not file_paths:
        print("No TIFF files selected. Exiting.")
        return

    # ---------------------------
    # Displacement constants
    # ---------------------------
    wavelength_nm = 633
    angle_deg = 27.2
    pixel_size_m = 17.0e-6

    wavelength_m = wavelength_nm * 1e-9
    angle_rad = math.radians(angle_deg)
    coefficient = wavelength_m / (4 * np.pi * np.sin(angle_rad))

    # ---------------------------
    # Process TIFF lines
    # ---------------------------
    processed_rows = []
    raw_rows = []
    labels = []
    x_mm = None
    actual_distance_mm = None

    for file_path in file_paths:
        img = io.imread(file_path).astype(np.float32)
        n_rows, n_cols = img.shape
        displacement_um = img # displacement_um = coefficient * img * 1e6

        center_row_index = n_rows // 2
        pixel_offset = int(round(-dist_from_center_mm / (pixel_size_m * 1000)))
        row_index = center_row_index + pixel_offset
        row_index = max(0, min(n_rows - 1, row_index))

        actual_distance_mm = -(row_index - center_row_index) * pixel_size_m * 1000
        row_data = displacement_um[row_index, :]
        raw_rows.append(row_data.copy())

        if x_mm is None:
            center_col_index = n_cols // 2
            x_mm = (np.arange(n_cols) - center_col_index) * pixel_size_m * 1000

        row_data = displacement_um[row_index, :]
        raw_rows.append(row_data.copy())
        processed_row = row_data.copy()

        # if center_adjust:
        #     m, b = np.polyfit(x_mm, processed_row, 1)
        #     processed_row -= b

        if center_adjust:
            # Parameters
            edge_margin = 1.0  # mm from left/right edges
            center_exclude = 2.0  # mm around x=0 to exclude

            # Build mask: exclude ±center_exclude around x=0, and exclude ±edge_margin at the edges
            mask = (x_mm > x_mm.min() + edge_margin) & (x_mm < x_mm.max() - edge_margin) & \
                   ((x_mm < -center_exclude) | (x_mm > center_exclude))

            # Values used for linear fit
            x_fit = x_mm[mask]
            y_fit = processed_row[mask]

            # Fit linear trendline on subset
            m, b = np.polyfit(x_fit, y_fit, 1)

            # Only subtract intercept (shift so trendline passes through zero at x=0)
            processed_row -= b

        processed_rows.append(processed_row)

        # Extract "xx-xx" label
        fname = os.path.basename(file_path)
        match = re.search(r'_(\d+-\d+)', fname)
        label = match.group(1) if match else fname
        labels.append(label)

    sum_rows = np.sum(processed_rows, axis=0)

    # ===========================
    # PLOT EVERYTHING
    # ===========================
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot individual TIFF lines
    for row, label in zip(processed_rows, labels):
        ax.plot(x_mm, row, linewidth=1, alpha=1, label=label)

    # Optionally Plot sum of TIFF lines
    if include_sum:
        ax.plot(x_mm, sum_rows, color="black", linewidth=1.5, label="ESPI (sum)")

    # Optionally plot simulation line

    # Correction for FEA line = 0.932x
    if include_sim:
        x_sim, ux_sim = get_simulation_ux_line(
            filename=sim_filename,
            y_height=dist_from_center_mm + 12,
            radius=sim_radius
        )
        ax.plot(x_sim, ux_sim*0.932, color="red", linewidth=1.5, linestyle="--", label="FEA corrected")
        # Adjust X-axis to fit both TIFF and FEA
        all_x = np.concatenate([x_mm, x_sim])
    else:
        all_x = x_mm

    padding = 0.5
    ax.set_xlim(all_x.min() - padding, all_x.max() + padding)
    ax.axhline(0, color='black', linewidth=1, linestyle='-', alpha=0.8)

    # ---------------------------
    # FORCE AXES (robust visibility)
    # ---------------------------
    ax.tick_params(axis='both', which='major', labelsize=10, length=6, width=1)
    ax.tick_params(axis='both', which='minor', length=3, width=0.8)

    ax.xaxis.set_major_locator(mticker.AutoLocator())
    ax.yaxis.set_major_locator(mticker.AutoLocator())

    ax.xaxis.set_minor_locator(mticker.AutoMinorLocator())
    ax.yaxis.set_minor_locator(mticker.AutoMinorLocator())

    # Gridlines
    ax.grid(which='major', linestyle='--', linewidth=0.5, color='black', alpha=0.8)
    ax.grid(which='minor', linestyle='--', linewidth=0.5, color='gray', alpha=0.5)

    # Labels and legend
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Displacement (µm)")
    ax.legend()

    # ---------------------------
    # Save figure
    # ---------------------------
    save_filename = build_espi_save_filename(file_paths, actual_distance_mm, center_adjust)
    if include_sim:
        save_filename = save_filename.replace(".png", "_Comparison.png")

    # Save in the same folder as the TIFF images
    tiff_folder = os.path.dirname(file_paths[0])
    save_path = os.path.join(tiff_folder, save_filename)

    plt.title(save_filename.replace(".png", ""), fontsize=11, pad=12)

    # Force axis visibility
    ax.tick_params(axis='both', which='both', direction='in', length=4, width=1)

    # Explicitly force ticks to exist (important for ESPI-style plots)
    ax.yaxis.set_major_locator(mticker.AutoLocator())
    ax.xaxis.set_major_locator(mticker.AutoLocator())

    # Ensure labels are not clipped
    plt.subplots_adjust(left=0.12, bottom=0.12)

    plt.tight_layout()
    if save_plot:
        plt.savefig(save_path, dpi=300)
        print(f"Plot saved as: {save_path}")
    else:
        print("Plot not saved")


    # return fig, ax, r2_dict



def plot_simulation_uy_line(
    filename="nodes_disp.txt",
    y_height=12.0,
    radius=12.0,
    mirror=True,
    save_plot=True
):
    """
    Plot X vs UY (vertical displacement) from FEA simulation data
    for a horizontal line at y = y_height.

    Highlights and annotates the maximum absolute UY value.
    """

    # --- Build full path to FEA_comparison folder ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fea_folder = os.path.join(script_dir, "FEA_comparison")
    file_path = os.path.join(fea_folder, filename)

    # --- Load data ---
    # Expected columns:
    # [node_id, x, y, z, ux, uy, uz]
    data = np.loadtxt(file_path, skiprows=1)

    x = data[:, 1]
    y = data[:, 2]
    uy = data[:, 5]   # UY column

    # --- Select horizontal line ---
    tol = 0.01 * (max(y) - min(y))
    mask = (y >= y_height - tol) & (y <= y_height + tol) & (np.abs(x) <= radius)

    x_line = x[mask]
    uy_line = uy[mask]

    # --- Mirror for symmetry ---
    if mirror:
        x_line = np.concatenate([x_line, -x_line])
        uy_line = np.concatenate([uy_line, -uy_line])

    # --- Sort by X ---
    sort_idx = np.argsort(x_line)
    x_line = x_line[sort_idx]
    uy_line = uy_line[sort_idx]

    # Convert mm → µm
    uy_line_um = uy_line * 1000

    # --- Find maximum absolute UY ---
    idx_max = np.argmax(np.abs(uy_line_um))
    x_max = x_line[idx_max]
    uy_max = uy_line_um[idx_max]

    # ===========================
    # Plot
    # ===========================
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(x_line, uy_line_um, linewidth=1.5, label="FEA UY")
    ax.axhline(0, color="black", linewidth=1, alpha=0.8)

    # Highlight max |UY|
    ax.plot(x_max, uy_max, "ro")
    ax.annotate(
        f"Max |UY| = {uy_max:.2f} µm\nat X = {x_max:.2f} mm",
        xy=(x_max, uy_max),
        xytext=(x_max + 0.5, uy_max),
        arrowprops=dict(arrowstyle="->", color="red"),
        fontsize=9
    )

    # --- Automatic ticks, major grid only ---
    ax.tick_params(axis='both', which='major', labelsize=10)
    ax.xaxis.set_major_locator(mticker.AutoLocator())
    ax.yaxis.set_major_locator(mticker.AutoLocator())
    ax.minorticks_off()
    ax.grid(which='major', linestyle='--', linewidth=0.6, color='black', alpha=0.6)

    # --- Labels & title ---
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Vertical Displacement UY (µm)")
    ax.set_title(f"FEA Vertical Displacement (y = {y_height:.2f} mm)")
    ax.legend()

    plt.tight_layout()

    # --- Save plot ---
    if save_plot:
        save_name = f"FEA_UY_y{y_height:.2f}.png"
        save_path = os.path.join(fea_folder, save_name)
        plt.savefig(save_path, dpi=300)
        print(f"UY plot saved as: {save_path}")

    return x_line, uy_line_um, x_max, uy_max
