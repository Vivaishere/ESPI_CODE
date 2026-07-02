# plot_espi--dic_disp_diff.py

import numpy as np
import matplotlib.pyplot as plt
from skimage import io
from skimage.transform import resize
import tkinter as tk
from tkinter import filedialog
import os

# ESPI pixel size
PIXEL_SIZE_M = 18.7e-6
PIXEL_SIZE_MM = PIXEL_SIZE_M * 1e3  # mm

def get_unique_path(folder, filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    new_path = os.path.join(folder, filename)
    while os.path.exists(new_path):
        new_filename = f"{base}_{counter}{ext}"
        new_path = os.path.join(folder, new_filename)
        counter += 1
    return new_path

def compute_difference_and_plot(save_fig=True, save_tiff=True, plot_lines=True):

    # ---------------------------
    # Default folder
    # ---------------------------
    base_dir = os.path.dirname(__file__)
    espi_folder = os.path.abspath(os.path.join(base_dir, "..", "ESPI_Images", "1_RAW_new_images"))

    # ---------------------------
    # File selection
    # ---------------------------
    root = tk.Tk()
    root.withdraw()
    espi_path = filedialog.askopenfilename(
        title="Select ESPI displacement TIFF",
        initialdir=espi_folder,
        filetypes=[("TIFF files", "*.tiff *.tif")]
    )
    if not espi_path:
        print("No ESPI image selected.")
        return

    dic_path = filedialog.askopenfilename(
        title="Select DIC displacement TIFF",
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
    print(f"ESPI size: {espi.shape}")
    print(f"DIC size: {dic.shape}")

    # ---------------------------
    # Resize DIC → ESPI size
    # ---------------------------
    if dic.shape != espi.shape:
        dic = resize(
            dic,
            espi.shape,
            preserve_range=True,
            anti_aliasing=True
        ).astype(np.float32)
        print(f"DIC resized to: {dic.shape}")

    # ---------------------------
    # Compute difference (ESPI - DIC)
    # ---------------------------
    diff = espi - dic

    # ---------------------------
    # Prepare filenames
    # ---------------------------
    espi_filename = os.path.basename(espi_path)
    name_no_ext = os.path.splitext(espi_filename)[0]
    save_folder = os.path.dirname(espi_path)

    # ---------------------------
    # Save TIFF
    # ---------------------------
    if save_tiff:
        tiff_name = f"disp-diff-espi-dic_{name_no_ext}.tiff"
        tiff_path = get_unique_path(save_folder, tiff_name)
        io.imsave(tiff_path, diff.astype(np.float32))
        print(f"Saved TIFF: {tiff_path}")

    # ---------------------------
    # X and Y axis in mm
    # ---------------------------
    rows, cols = diff.shape
    x = (np.arange(cols) - cols // 2) * PIXEL_SIZE_MM  # X in mm
    y = (np.arange(rows) - rows // 2) * PIXEL_SIZE_MM  # Y in mm

    # ---------------------------
    # Plot horizontal line profiles with trendlines
    # ---------------------------
    if plot_lines:
        heights = [0.6, 0.7, 0.8, 0.9]
        row_indices = [int(rows * h) for h in heights]

        # Compute plotting domain relative to full X range
        x_min, x_max = x.min(), x.max()
        x_range = x_max - x_min
        left_mask = (x >= x_min + 0.01 * x_range) & (x <= x_min + 0.43 * x_range)
        right_mask = (x >= x_min + 0.57 * x_range) & (x <= x_min + 0.99 * x_range)
        plot_mask = left_mask | right_mask

        y_values_all = []
        lines = []

        # Standard colors: blue, orange, green, red
        colors = [
            np.array([0, 0, 1]),
            np.array([1, 0.55, 0]),
            np.array([0, 0.5, 0]),
            np.array([1, 0, 0])
        ]

        for r in row_indices:
            line = diff[r, :]
            lines.append(line)
            y_values_all.append(line[left_mask])
            y_values_all.append(line[right_mask])

        y_values_all = np.concatenate(y_values_all)
        y_min_plot = np.min(y_values_all)
        y_max_plot = np.max(y_values_all)

        # ---------------------------
        # Plotting
        # ---------------------------
        fig_lines, ax_lines = plt.subplots(figsize=(10, 5))
        line_width = 1
        trend_width = 1.5

        for i, line in enumerate(lines):
            base_color = colors[i]

            # Plot value line (transparent)
            ax_lines.plot(x[plot_mask], line[plot_mask],
                          label=f"{int(heights[i]*100)}% height",
                          color=base_color,
                          alpha=0.5,
                          linewidth=line_width)

            # Trendlines for left and right
            for side_mask in [left_mask, right_mask]:
                xi = x[side_mask]
                yi = line[side_mask]
                if len(xi) > 1:
                    coef = np.polyfit(xi, yi, 1)
                    trend = np.poly1d(coef)(xi)
                    ax_lines.plot(xi, trend, color=base_color, alpha=1, linewidth=trend_width)

        ax_lines.set_xlim(x.min(), x.max())
        ax_lines.set_ylim(y_min_plot, y_max_plot)
        ax_lines.set_xlabel("X (mm)")
        ax_lines.set_ylabel("Displacement Difference (µm)")
        ax_lines.set_title("Horizontal Profiles (ESPI - DIC)")
        ax_lines.axhline(0, color='black', linewidth=1)
        ax_lines.legend()
        ax_lines.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()

        # Save line plot
        line_fig_name = f"disp-diff-lines_{name_no_ext}.png"
        line_fig_path = get_unique_path(save_folder, line_fig_name)
        plt.savefig(line_fig_path, dpi=300)
        print(f"Saved line plot: {line_fig_path}")
        plt.close(fig_lines)

    # ---------------------------
    # Visualization of difference with axes
    # ---------------------------
    if save_fig:
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(diff, cmap='jet', vmin=-1, vmax=1,
                       extent=[x.min(), x.max(), y.max(), y.min()])
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.set_title("Displacement Difference (ESPI - DIC)")
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Displacement Difference (µm)")
        plt.tight_layout()

        fig_name = f"disp-diff-espi-dic_{name_no_ext}.png"
        fig_path = get_unique_path(save_folder, fig_name)
        plt.savefig(fig_path, dpi=300)
        print(f"Saved difference figure: {fig_path}")
        plt.close(fig)

if __name__ == "__main__":
    compute_difference_and_plot(save_fig=True, save_tiff=True, plot_lines=False)
