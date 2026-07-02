# plot_disp_lines_espi.py

import os
import numpy as np
from tkinter import Tk, filedialog
from skimage import io
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


# =========================================================
# HEIGHT → ROW INDEX CONVERTER
# =========================================================
def height_to_row_index(height_mm, n_rows, pixel_size_m):
    """
    Height convention:
    -----------------
    0 mm  = bottom of image
    +Y    = upward from bottom
    -Y    = downward from top

    Examples:
    ----------
    0       -> bottom row
    1       -> 1 mm above bottom
    -0.5    -> 0.5 mm below top
    """

    pixel_size_mm = pixel_size_m * 1000
    image_height_mm = n_rows * pixel_size_mm

    if height_mm >= 0:
        # From bottom upward
        row_index = n_rows - 1 - int(round(height_mm / pixel_size_mm))
    else:
        # From top downward
        row_index = int(round(abs(height_mm) / pixel_size_mm))

    row_index = max(0, min(n_rows - 1, row_index))

    # Actual physical height
    if height_mm >= 0:
        actual_height_mm = (n_rows - 1 - row_index) * pixel_size_mm
    else:
        actual_height_mm = -row_index * pixel_size_mm

    return row_index, actual_height_mm


# =========================================================
# SINGLE TIFF LINE PLOT
# =========================================================
def plot_ux_combined_tiff(
    height_mm=0.0,
    save_plot=True
):
    """
    Plots a horizontal displacement line from a combined displacement TIFF.
    """

    # ---------------------------
    # SELECT TIFF
    # ---------------------------
    root = Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select COMBINED displacement TIFF",
        filetypes=[("TIFF files", "*COMBINED*.tiff")]
    )

    root.destroy()

    if not file_path:
        print("No TIFF selected.")
        return

    # ---------------------------
    # CONSTANTS
    # ---------------------------
    pixel_size_m = 17.0e-6

    # ---------------------------
    # LOAD IMAGE
    # ---------------------------
    img = io.imread(file_path).astype(np.float32)

    n_rows, n_cols = img.shape

    # ---------------------------
    # HEIGHT → ROW
    # ---------------------------
    row_index, actual_height_mm = height_to_row_index(
        height_mm,
        n_rows,
        pixel_size_m
    )

    row_data = img[row_index, :].copy()

    # ---------------------------
    # AUTO-SCALED X AXIS
    # ---------------------------
    center_col = n_cols // 2

    x_mm = (
        (np.arange(n_cols) - center_col)
        * pixel_size_m
        * 1000
    )

    # ===========================
    # PLOT
    # ===========================
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(
        x_mm,
        row_data,
        linewidth=1.5,
        label="ESPI (combined)"
    )

    # Auto width
    margin = 0.02 * (x_mm.max() - x_mm.min())

    ax.set_xlim(
        x_mm.min() - margin,
        x_mm.max() + margin
    )

    ax.axhline(0, color='black', linewidth=1)

    # Grid formatting
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.xaxis.set_minor_locator(mticker.MultipleLocator(1))

    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.yaxis.set_minor_locator(mticker.MultipleLocator(0.1)) # change y axis minor ticks

    #ax.minorticks_on() # automatic minor ticks

    ax.grid(
        which='major',
        linestyle='--',
        linewidth=0.5,
        color='black',
        alpha=0.8
    )

    ax.grid(
        which='minor',
        linestyle='--',
        linewidth=0.5,
        color='gray',
        alpha=0.5
    )

    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Displacement (µm)")

    ax.set_title(
        f"{os.path.basename(file_path)}\n"
        f"Line at {actual_height_mm:.3f} mm"
    )

    ax.legend()

    # ---------------------------
    # SAVE
    # ---------------------------
    if save_plot:

        folder = os.path.dirname(file_path)

        base = os.path.splitext(
            os.path.basename(file_path)
        )[0]

        save_name = (
            f"{base}_Line_at_{actual_height_mm:.3f}mm.png"
        )

        save_path = os.path.join(folder, save_name)

        plt.tight_layout()

        plt.savefig(
            save_path,
            dpi=300
        )

        print(f"Saved: {save_path}")

    else:
        print("Plot not saved.")


# =========================================================
# MULTI TIFF SUM + INDIVIDUAL LINES
# =========================================================
def plot_ux_sum_tiff(
    height_mm=0.0,
    save_plot=True
):
    """
    Plots:
    - individual displacement profiles
    - summed displacement profile

    from multiple centered displacement TIFFs.
    """

    # ---------------------------
    # SELECT TIFFS
    # ---------------------------
    root = Tk()
    root.withdraw()

    file_paths = filedialog.askopenfilenames(
        title="Select centered displacement TIFFs",
        filetypes=[("TIFF files", "*.tif *.tiff")]
    )

    root.destroy()

    if not file_paths:
        print("No files selected.")
        return

    # ---------------------------
    # CONSTANTS
    # ---------------------------
    pixel_size_m = 17e-6

    images = []
    labels = []

    # ---------------------------
    # LOAD IMAGES
    # ---------------------------
    for fp in file_paths:

        img = io.imread(fp).astype(np.float32)

        images.append(img)

        labels.append(
            os.path.splitext(
                os.path.basename(fp)
            )[0]
        )

    n_rows, n_cols = images[0].shape

    # ---------------------------
    # HEIGHT → ROW
    # ---------------------------
    row_index, actual_height_mm = height_to_row_index(
        height_mm,
        n_rows,
        pixel_size_m
    )

    # ---------------------------
    # AUTO X AXIS
    # ---------------------------
    center_col = n_cols // 2

    x_mm = (
        (np.arange(n_cols) - center_col)
        * pixel_size_m
        * 1000
    )

    # ---------------------------
    # EXTRACT LINES
    # ---------------------------
    sum_line = np.zeros(n_cols, dtype=np.float32)

    all_lines = []

    for img in images:

        row = img[row_index, :].copy()

        all_lines.append(row)

        sum_line += row

    # ===========================
    # PLOT
    # ===========================
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, line in enumerate(all_lines):

        ax.plot(
            x_mm,
            line,
            linewidth=1.2,
            alpha=0.8,
            label=labels[i]
        )

    # SUM LINE
    ax.plot(
        x_mm,
        sum_line,
        linewidth=2.5,
        color="black",
        label="SUM"
    )

    # Auto width
    margin = 0.02 * (x_mm.max() - x_mm.min())

    ax.set_xlim(
        x_mm.min() - margin,
        x_mm.max() + margin
    )

    ax.axhline(0, color='black', linewidth=1)

    # Grid formatting
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.xaxis.set_minor_locator(mticker.MultipleLocator(1))

    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.yaxis.set_minor_locator(mticker.MultipleLocator(0.1)) # y axis ticks

    ax.minorticks_on()

    ax.grid(
        which='major',
        linestyle='--',
        linewidth=0.5,
        color='black',
        alpha=0.8
    )

    ax.grid(
        which='minor',
        linestyle='--',
        linewidth=0.5,
        color='gray',
        alpha=0.5
    )

    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Displacement (µm)")

    ax.set_title(
        "Individual + Summed Displacement Profiles\n"
        f"Line at {actual_height_mm:.3f} mm"
    )

    ax.legend()

    # ---------------------------
    # SAVE
    # ---------------------------
    if save_plot:

        folder = os.path.dirname(file_paths[0])

        save_path = os.path.join(
            folder,
            f"SUM_Line_at_{actual_height_mm:.3f}mm.png"
        )

        plt.tight_layout()

        plt.savefig(
            save_path,
            dpi=300
        )

        print(f"Saved: {save_path}")

    else:
        print("Plot not saved.")



# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":

    # Example:
    # plot_ux_combined_tiff(height_mm=0)
    # plot_ux_combined_tiff(height_mm=2)
    # plot_ux_combined_tiff(height_mm=-0.5)

    plot_ux_combined_tiff()

    # plot_ux_sum_tiff()