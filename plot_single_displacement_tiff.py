# plot_single_displacement_tiff.py

import os
import numpy as np
from skimage import io
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import tkinter as tk
from tkinter import filedialog


def plot_single_displacement_tiffs(
        filepath=None,
        colormap="jet",
        percentile=99.9,
        pixel_size_m=17e-6,
        save_png=True
):

    # =========================
    # SELECT FILE(S)
    # =========================
    if filepath is None:

        root = tk.Tk()
        root.withdraw()

        filepath = filedialog.askopenfilenames(
            title="Select displacement TIFF(s)",
            filetypes=[("TIFF files", "*.tiff *.tif")]
        )

        root.destroy()

        if not filepath:
            return

    file_list = list(filepath)

    # =========================
    # PROCESS EACH IMAGE
    # =========================
    for filepath in file_list:

        # =========================
        # LOAD IMAGE
        # =========================
        img = io.imread(filepath).astype(np.float32)

        # =========================
        # EXCLUDE EDGE PIXELS
        # =========================
        cropped = img[5:-5, 5:-5]
        valid = cropped[np.isfinite(cropped)]

        if valid.size == 0:
            print("No valid pixels found.")
            continue

        # =========================
        # COLOR LIMITS
        # =========================
        low_percentile = 100.0 - percentile

        low_val = np.percentile(valid, low_percentile)
        high_val = np.percentile(valid, percentile)

        if low_val == high_val:
            low_val -= 1e-6
            high_val += 1e-6

        if low_val >= 0:
            low_val = min(low_val, -1e-6)

        if high_val <= 0:
            high_val = max(high_val, 1e-6)

        norm = TwoSlopeNorm(
            vmin=low_val,
            vcenter=0,
            vmax=high_val
        )

        # =========================
        # COLORMAP
        # =========================
        cmap = plt.get_cmap(colormap).copy()
        cmap.set_over("magenta")
        cmap.set_under("magenta")

        # =========================
        # IMAGE EXTENT
        # =========================
        h, w = img.shape

        extent = (
            0, w * pixel_size_m * 1000,
            0, h * pixel_size_m * 1000
        )

        # =========================
        # PLOT
        # =========================
        fig, ax = plt.subplots(figsize=(8, 6))

        im = ax.imshow(
            img,
            cmap=cmap,
            norm=norm,
            extent=extent,
            aspect="equal"
        )

        # =========================
        # COLORBAR
        # =========================
        cbar = plt.colorbar(im, ax=ax, extend="both")

        cbar.set_label(f"Displacement (µm) | Percentile = {percentile}")

        # ONLY min / 0 / max
        ticks = [low_val, 0, high_val]
        cbar.set_ticks(ticks)

        cbar.set_ticklabels([
            f"{low_val:.3f}",
            "0",
            f"{high_val:.3f}"
        ])

        # =========================
        # LABELS
        # =========================
        filename = os.path.basename(filepath)

        ax.set_title(filename, pad=20)
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")

        # =========================
        # SAVE
        # =========================
        if save_png:

            folder = os.path.dirname(filepath)
            name = os.path.splitext(filename)[0]

            out_name = f"p{percentile}_{name}.png"
            out_path = os.path.join(folder, out_name)

            fig.savefig(out_path, dpi=600)
            print("✅ Saved:", out_path)


if __name__ == "__main__":

    plot_single_displacement_tiffs(
        colormap="jet",
        percentile=99.9,
        pixel_size_m=17e-6,
        save_png=True
    )