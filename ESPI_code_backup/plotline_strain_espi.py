# plotline_strain_espi.py

import os
import numpy as np
from tkinter import Tk, filedialog
from skimage import io
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from a__utils import get_unique_path


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
        row_index = n_rows - 1 - int(
            round(height_mm / pixel_size_mm)
        )

    else:

        # From top downward
        row_index = int(
            round(abs(height_mm) / pixel_size_mm)
        )

    row_index = max(
        0,
        min(n_rows - 1, row_index)
    )

    # Actual physical height
    if height_mm >= 0:

        actual_height_mm = (
            (n_rows - 1 - row_index)
            * pixel_size_mm
        )

    else:

        actual_height_mm = (
            -row_index
            * pixel_size_mm
        )

    return row_index, actual_height_mm


# =========================================================
# SINGLE TIFF STRAIN LINE PLOT + Linear FIT
# =========================================================
def plot_strain_line_tiffs(
    pixel_size_m=8.4e-6,
    height_mm=0.0,
    x_bounds=(-10, 10),
    fit_order=2,
    save_plot=True
):
    """
    Plots a horizontal strain line directly from a
    calculated strain TIFF.

    The TIFF is assumed to already contain εxx strain values.

    Parameters
    ----------
    height_mm : float
        Requested physical height of the horizontal line.

    x_bounds : tuple
        X region used for the polynomial fit, in mm.

        Example:
            x_bounds=(-10, 10)

    fit_order : int
        Polynomial order.

        0 = forced zero-strain line (εxx = 0)
        1 = linear
        2 = quadratic
        etc.

    save_plot : bool
        Save the resulting plot if True.
    """

    # =====================================================
    # SELECT TIFFs
    # =====================================================

    root = Tk()
    root.withdraw()

    file_paths = filedialog.askopenfilenames(
        title="Select strain TIFFs",
        filetypes=[
            ("TIFF files", "*.tif *.tiff")
        ]
    )

    root.destroy()

    if not file_paths:
        print("No TIFFs selected.")
        return
    
    # =====================================================
    # PROCESS EACH TIFF
    # =====================================================

    for file_path in file_paths:

        print()
        print("=" * 60)
        print(f"Processing: {os.path.basename(file_path)}")
        print("=" * 60)

        # =====================================================
        # CONSTANTS
        # =====================================================

        # Pixel size of the strain TIFF
        pixel_size_m = pixel_size_m

        # =====================================================
        # LOAD STRAIN IMAGE
        # =====================================================

        img = io.imread(
            file_path
        ).astype(np.float32)

        n_rows, n_cols = img.shape

        # =====================================================
        # HEIGHT → ROW
        # =====================================================

        row_index, actual_height_mm = height_to_row_index(
            height_mm,
            n_rows,
            pixel_size_m
        )

        # =====================================================
        # EXTRACT STRAIN LINE
        # =====================================================

        row_data = img[row_index, :].copy()

        # =====================================================
        # X AXIS
        # =====================================================

        center_col = n_cols // 2

        x_mm = (
            (np.arange(n_cols) - center_col)
            * pixel_size_m
            * 1000
        )

        # =====================================================
        # SELECT FIT REGION
        # =====================================================

        x_min, x_max = x_bounds

        fit_mask = (
            np.isfinite(x_mm)
            & np.isfinite(row_data)
            & (x_mm >= x_min)
            & (x_mm <= x_max)
        )

        x_fit = x_mm[fit_mask]
        strain_fit = row_data[fit_mask]

        if len(x_fit) <= fit_order:

            print(
                f"Not enough points for a polynomial "
                f"of order {fit_order}."
            )

            return

        # =====================================================
        # POLYNOMIAL BEST FIT
        # =====================================================

        if fit_order == 0:

            # Force zero-strain reference line
            coefficients = np.array([0.0])
            polynomial = np.poly1d(coefficients)

        else:

            coefficients = np.polyfit(
                x_fit,
                strain_fit,
                fit_order
            )

            polynomial = np.poly1d(
                coefficients
            )

        # Fitted values at measured points
        strain_fit_predicted = polynomial(
            x_fit
        )

        # =====================================================
        # STANDARD DEVIATION OF RESIDUALS
        # =====================================================

        residuals = (
            strain_fit
            - strain_fit_predicted
        )

        sd = np.std(
            residuals,
            ddof=1
        )

        # Smooth X values for displaying fit
        x_fit_plot = np.linspace(
            x_min,
            x_max,
            500
        )

        strain_fit_plot = polynomial(
            x_fit_plot
        )

        # =====================================================
        # PRINT FIT INFORMATION
        # =====================================================

        print()
        print("Strain polynomial fit")
        print("-----------------------------")
        print(
            f"Fit region: "
            f"{x_min:.3f} to {x_max:.3f} mm"
        )
        print(
            f"Polynomial order: "
            f"{fit_order}"
        )
        print(
            f"Number of points: "
            f"{len(x_fit)}"
        )
        print(
            f"Standard deviation: "
            f"{sd:.6f}"
        )
        print()
        print("Polynomial coefficients:")
        print(coefficients)
        print()

        # =====================================================
        # PLOT
        # =====================================================

        fig, ax = plt.subplots(
            figsize=(12, 6)
        )

        # ---------------------------
        # Original strain line
        # ---------------------------

        ax.plot(
            x_mm,
            row_data,
            linewidth=1.5,
            label="ESPI εxx"
        )

        # ---------------------------
        # Quadratic fit
        # ---------------------------

        if fit_order == 0:
            fit_label = (
                f"Zero-strain reference  |  "
                f"SD = {sd:.2f}"
            )
        else:
            fit_label = (
                f"Polynomial fit (order {fit_order})  |  "
                f"SD = {sd:.2f}"
            )

        ax.plot(
            x_fit_plot,
            strain_fit_plot,
            linewidth=2.5,
            linestyle="--",
            label=fit_label
        )

        # ---------------------------
        # Fit boundaries
        # ---------------------------

        ax.axvline(
            x_min,
            linestyle=":",
            linewidth=1
        )

        ax.axvline(
            x_max,
            linestyle=":",
            linewidth=1
        )

        # ---------------------------
        # Zero strain line
        # ---------------------------

        ax.axhline(
            0,
            color="black",
            linewidth=1
        )

        # =====================================================
        # AUTO X WIDTH
        # =====================================================

        margin = 0.02 * (
            x_mm.max() - x_mm.min()
        )

        ax.set_xlim(
            x_mm.min() - margin,
            x_mm.max() + margin
        )

        # =====================================================
        # GRID FORMATTING
        # =====================================================

        ax.xaxis.set_major_locator(
            mticker.MultipleLocator(1)
        )

        ax.xaxis.set_minor_locator(
            mticker.MultipleLocator(1)
        )

        ax.yaxis.set_major_locator(
            mticker.MultipleLocator(100)
        )

        ax.yaxis.set_minor_locator(
            mticker.MultipleLocator(20)
        )

        ax.grid(
            which="major",
            linestyle="--",
            linewidth=0.5,
            color="black",
            alpha=0.8
        )

        ax.grid(
            which="minor",
            linestyle="--",
            linewidth=0.5,
            color="gray",
            alpha=0.5
        )

        # =====================================================
        # LABELS
        # =====================================================

        ax.set_xlabel(
            "X (mm)"
        )

        ax.set_ylabel(
            "εxx"
        )

        ax.set_title(
            f"{os.path.basename(file_path)}\n"
            f"Line at {actual_height_mm:.3f} mm   |   "
            f"Linear fit: "
            f"{x_min:g} < X < {x_max:g}   |   "
            f"SD = {sd:.2f}"
        )

        ax.legend()

        # =====================================================
        # SAVE
        # =====================================================

        if save_plot:

            folder = os.path.dirname(
                file_path
            )

            base = os.path.splitext(
                os.path.basename(file_path)
            )[0]

            save_path = get_unique_path(
                folder,
                (
                    f"{base}_"
                    f"Line_at_"
                    f"{actual_height_mm:.3f}mm_"
                    f"Fit_{x_min:g}_{x_max:g}.png"
                )
            )

            plt.tight_layout()

            plt.savefig(
                save_path,
                dpi=300
            )

            print(
                f"Saved: {save_path}"
            )

        else:

            print(
                "Plot not saved."
            )



# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":

    # Example:
    #
    # Plot the strain line at Y = 0 mm
    # and fit a Linear fit between X = -x and +x mm.

    plot_strain_line_tiffs(
        pixel_size_m=8.4e-6,
        height_mm=2,
        x_bounds=(-4, 4),
        fit_order=0
    )
