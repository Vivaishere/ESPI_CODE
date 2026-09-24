# plot_espi_strain.py

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from skimage import io
from tkinter import Tk, filedialog
import os


# ==================================================
# UNIQUE PATH
# ==================================================

def get_unique_path(folder, filename):

    base, ext = os.path.splitext(filename)

    counter = 1
    new_path = os.path.join(folder, filename)

    while os.path.exists(new_path):

        new_filename = f"{base}_{counter}{ext}"

        new_path = os.path.join(
            folder,
            new_filename
        )

        counter += 1

    return new_path


# ==================================================
# COMPUTE STRAIN XX
# ==================================================

def compute_strain_xx(
    save_plot=True,
    save_tiff=True,
    pixel_size_um=17.0,
    fit_order=1,
    gauge_sizes=(5,),
    white_band=50,
    dotsize=2,
    ssig=0,
    flip_displacement_sign=False,
    edge_exclusion_pixels=5
):

    print(f"Gauge sizes: {gauge_sizes}")
    print(f"SSig: {ssig}")
    print(
        f"Displacement edge exclusion: "
        f"{edge_exclusion_pixels} pixels"
    )

    # -------------------------------------------------
    # FILE SELECT
    # -------------------------------------------------

    root = Tk()
    root.withdraw()

    u_paths = filedialog.askopenfilenames(
        title="Select X-displacement TIFF(s)",
        filetypes=[
            ("TIFF files", "*.tiff *.tif")
        ]
    )

    root.destroy()

    if not u_paths:

        print("No files selected.")

        return

    # -------------------------------------------------
    # LOOP THROUGH FILES
    # -------------------------------------------------

    for u_path in u_paths:

        u = io.imread(u_path).astype(np.float32)

        if flip_displacement_sign:

            u = -u

        rows, cols = u.shape

        print(f"\nLoaded: {u.shape}")
        print(
            f"Processing: "
            f"{os.path.basename(u_path)}"
        )

        # -------------------------------------------------
        # PIXEL SIZE
        # -------------------------------------------------

        PIXEL_SIZE_MM = pixel_size_um * 1e-3

        # -------------------------------------------------
        # SAVE FOLDER
        # -------------------------------------------------

        save_folder = os.path.dirname(u_path)

        os.makedirs(
            save_folder,
            exist_ok=True
        )

        # Original filename without extension
        u_stem = os.path.splitext(
            os.path.basename(u_path)
        )[0]

        # -------------------------------------------------
        # EXTRACT LOAD PAIR
        #
        # Example:
        #
        # Disp-RBM-adj_..._20-16
        #
        # becomes:
        #
        # 20-16
        # -------------------------------------------------

        load_pair = u_stem.split("_")[-1]

        # =================================================
        # GAUGE LOOP
        # =================================================

        for gauge_size in gauge_sizes:

            half_gx = gauge_size // 2
            half_gy = gauge_size // 2

            strain_xx = np.full_like(
                u,
                np.nan,
                dtype=np.float32
            )

            # =================================================
            # VALID DISPLACEMENT REGION
            #
            # The outer edge_exclusion_pixels of the ORIGINAL
            # displacement image is completely excluded from
            # the strain calculation.
            #
            # Example:
            #
            # edge_exclusion_pixels = 5
            #
            # pixels:
            #
            # 0 1 2 3 4 | 5 ............ rows-6 | rows-5 ... rows-1
            # ----------+-----------------------+------------
            #   ignored        usable              ignored
            #
            # =================================================

            edge = edge_exclusion_pixels

            # Check that the image is large enough
            minimum_rows = (
                2 * edge
                + 2 * half_gy
                + 1
            )

            minimum_cols = (
                2 * edge
                + 2 * half_gx
                + 1
            )

            if rows < minimum_rows:

                print(
                    f"WARNING: gauge_size={gauge_size} "
                    f"with edge exclusion of {edge} pixels "
                    f"requires at least {minimum_rows} rows."
                )

                continue

            if cols < minimum_cols:

                print(
                    f"WARNING: gauge_size={gauge_size} "
                    f"with edge exclusion of {edge} pixels "
                    f"requires at least {minimum_cols} columns."
                )

                continue

            # -------------------------------------------------
            # STRAIN-CENTER LIMITS
            #
            # The center of the gauge must be far enough away
            # from both:
            #
            # 1. The physical image edge
            # 2. The excluded 5-pixel border
            #
            # Therefore the first possible strain center is:
            #
            # edge + half_g
            #
            # -------------------------------------------------

            row_start = edge + half_gy
            row_end = rows - edge - half_gy

            col_start = edge + half_gx
            col_end = cols - edge - half_gx

            # -------------------------------------------------
            # GRID
            # -------------------------------------------------

            x = (
                np.arange(
                    -half_gx,
                    half_gx + 1
                )
                * pixel_size_um
            )

            y = (
                np.arange(
                    -half_gy,
                    half_gy + 1
                )
                * pixel_size_um
            )

            X, Y = np.meshgrid(x, y)

            Xf = X.ravel()
            Yf = Y.ravel()

            # -------------------------------------------------
            # DESIGN MATRIX
            # -------------------------------------------------

            if fit_order == 1:

                A = np.vstack([
                    np.ones_like(Xf),
                    Xf,
                    Yf
                ]).T

            else:

                A = np.vstack([
                    np.ones_like(Xf),
                    Xf,
                    Yf,
                    Xf**2,
                    Xf * Yf,
                    Yf**2
                ]).T

            # -------------------------------------------------
            # WEIGHTS
            # -------------------------------------------------

            if ssig > 0:

                r2 = Xf**2 + Yf**2

                W = np.exp(
                    -r2 / (2 * ssig**2)
                )

                # Standard weighted least squares:
                #
                # A_w = sqrt(W) A
                # u_w = sqrt(W) u
                #
                # This gives:
                #
                # (A^T W A)^-1 A^T W u

                sqrt_W = np.sqrt(W)

            else:

                sqrt_W = np.ones_like(Xf)

            # -------------------------------------------------
            # PRE-COMPUTE WEIGHTED DESIGN MATRIX
            # -------------------------------------------------

            Aw = A * sqrt_W[:, None]

            # -------------------------------------------------
            # STRAIN COMPUTATION
            #
            # IMPORTANT:
            #
            # The loops begin AFTER the excluded edge AND
            # include enough additional space for the gauge.
            #
            # Consequently, none of the outer 5 pixels can
            # enter any local displacement fit.
            # -------------------------------------------------

            for i in range(
                row_start,
                row_end
            ):

                for j in range(
                    col_start,
                    col_end
                ):

                    win = u[
                        i-half_gy:i+half_gy+1,
                        j-half_gx:j+half_gx+1
                    ].ravel()

                    # Apply the same square-root weights
                    # to the displacement values.
                    uw = win * sqrt_W

                    # -------------------------------------------------
                    # LEAST-SQUARES FIT
                    # -------------------------------------------------

                    coeffs = (
                        np.linalg.pinv(
                            Aw.T @ Aw
                        )
                        @ (
                            Aw.T @ uw
                        )
                    )

                    # -------------------------------------------------
                    # dU/dX
                    # -------------------------------------------------

                    strain_xx[i, j] = coeffs[1]

            # =================================================
            # CONVERT TO MICROSTRAIN
            # =================================================

            strain = strain_xx * 1e6

            # =================================================
            # OUTPUT FILENAMES
            # =================================================

            base_name = (
                f"ustrain_g{gauge_size}_"
                f"fit{fit_order}_"
                f"ssig{ssig}_"
                f"edge{edge_exclusion_pixels}_"
                f"{load_pair}"
            )

            # -------------------------------------------------
            # UNIQUE OUTPUT PATHS
            # -------------------------------------------------

            tiff_path = get_unique_path(
                save_folder,
                base_name + ".tiff"
            )

            fig_path = get_unique_path(
                save_folder,
                base_name + ".png"
            )

            # =================================================
            # SAVE STRAIN TIFF
            # =================================================

            if save_tiff:

                io.imsave(
                    tiff_path,
                    strain.astype(np.float32)
                )

                print(
                    "Saved TIFF:",
                    tiff_path
                )

            # =================================================
            # MASK EDGES FOR PLOTTING
            # =================================================

            strain_masked = strain.copy()

            # -------------------------------------------------
            # Mask the original 5-pixel excluded border.
            #
            # These pixels are already NaN from the calculation,
            # but explicitly masking them makes the intention
            # clear and protects the plotting stage.
            # -------------------------------------------------

            if edge > 0:

                strain_masked[
                    :edge,
                    :
                ] = np.nan

                strain_masked[
                    -edge:,
                    :
                ] = np.nan

                strain_masked[
                    :,
                    :edge
                ] = np.nan

                strain_masked[
                    :,
                    -edge:
                ] = np.nan

            # -------------------------------------------------
            # Mask gauge boundary
            # -------------------------------------------------

            strain_masked[
                :half_gy,
                :
            ] = np.nan

            strain_masked[
                -half_gy:,
                :
            ] = np.nan

            strain_masked[
                :,
                :half_gx
            ] = np.nan

            strain_masked[
                :,
                -half_gx:
            ] = np.nan

            # -------------------------------------------------
            # VALID VALUES
            # -------------------------------------------------

            valid = strain_masked[
                ~np.isnan(strain_masked)
            ]

            if valid.size == 0:

                print(
                    "WARNING: No valid strain "
                    "pixels available for plotting."
                )

                continue

            # =================================================
            # MULTI-PERCENTILE LIMITS
            # =================================================

            p99_pos = np.percentile(
                valid,
                99
            )

            p999_pos = np.percentile(
                valid,
                99.9
            )

            p9999_pos = np.percentile(
                valid,
                99.99
            )

            p99_neg = np.percentile(
                valid,
                1
            )

            p999_neg = np.percentile(
                valid,
                0.1
            )

            p9999_neg = np.percentile(
                valid,
                0.01
            )

            absmax = max(
                abs(p9999_pos),
                abs(p9999_neg)
            )

            cbar_min = -absmax
            cbar_max = absmax

            # =================================================
            # COORDINATES
            # =================================================

            x_mm = (
                np.arange(cols)
                - cols / 2
            ) * PIXEL_SIZE_MM

            y_mm = (
                rows
                - 1
                - np.arange(rows)
            ) * PIXEL_SIZE_MM

            Xg = np.repeat(
                x_mm[np.newaxis, :],
                rows,
                axis=0
            )

            Yg = np.repeat(
                y_mm[:, np.newaxis],
                cols,
                axis=1
            )

            Sf = strain_masked.ravel()

            mask = ~np.isnan(Sf)

            # =================================================
            # ADAPTIVE DOT SIZE
            # =================================================

            adaptive_size = (
                dotsize
                * (1000 / max(rows, cols))
            )

            # =================================================
            # CUSTOM COLORMAP
            # =================================================

            base_cmap = plt.cm.jet

            colors = base_cmap(
                np.linspace(0, 1, 256)
            )

            # =================================================
            # WHITE CENTER BAND
            # =================================================

            if white_band > 0:

                center_low = int(
                    256
                    * (
                        (white_band - cbar_min)
                        / (cbar_max - cbar_min)
                    )
                )

                center_high = int(
                    256
                    * (
                        (-white_band - cbar_min)
                        / (cbar_max - cbar_min)
                    )
                )

                i1 = min(
                    center_low,
                    center_high
                )

                i2 = max(
                    center_low,
                    center_high
                )

                i1 = max(
                    0,
                    min(255, i1)
                )

                i2 = max(
                    0,
                    min(256, i2)
                )

                colors[i1:i2] = [
                    1,
                    1,
                    1,
                    1
                ]

            cmap = mpl.colors.ListedColormap(
                colors
            )

            cmap.set_over("magenta")
            cmap.set_under("magenta")

            norm = mpl.colors.Normalize(
                vmin=cbar_min,
                vmax=cbar_max,
                clip=False
            )

            # =================================================
            # PLOT
            # =================================================

            if save_plot:

                fig, ax = plt.subplots()

                im = ax.scatter(
                    Xg.ravel()[mask],
                    Yg.ravel()[mask],
                    c=Sf[mask],
                    cmap=cmap,
                    norm=norm,
                    s=adaptive_size,
                    edgecolors="none"
                )

                ax.set_title(
                    f"εxx | gauge size = "
                    f"{gauge_size}px | "
                    f"edge exclusion = "
                    f"{edge_exclusion_pixels}px\n"
                    f"{os.path.basename(u_path)}",
                    pad=20
                )

                ax.set_xlabel(
                    "X (mm)"
                )

                ax.set_ylabel(
                    "Y (mm)"
                )

                ax.set_aspect(
                    "equal"
                )

                ax.set_xlim(
                    -np.max(np.abs(x_mm)),
                    np.max(np.abs(x_mm))
                )

                ax.set_ylim(
                    np.min(y_mm),
                    np.max(y_mm)
                )

                plt.tight_layout()

                # =================================================
                # COLORBAR
                # =================================================

                cbar = plt.colorbar(
                    im,
                    ax=ax,
                    extend="both"
                )

                cbar.set_label(
                    "µstrain"
                )

                cbar.set_ticks([
                    p9999_pos,
                    p999_pos,
                    p99_pos,
                    0,
                    p99_neg,
                    p999_neg,
                    p9999_neg
                ])

                cbar.set_ticklabels([
                    f"{p9999_pos:.0f}  99.99%",
                    f"{p999_pos:.0f}  99.9%",
                    f"{p99_pos:.0f}  99%",
                    "0",
                    f"{p99_neg:.0f}  -99%",
                    f"{p999_neg:.0f}  -99.9%",
                    f"{p9999_neg:.0f}  -99.99%"
                ])

                # =================================================
                # SAVE FIGURE
                # =================================================

                fig.savefig(
                    fig_path,
                    dpi=600,
                    bbox_inches="tight"
                )

                plt.close(fig)

                print(
                    "Saved plot:",
                    fig_path
                )


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":

    compute_strain_xx(
        save_plot=True,
        save_tiff=False,
        pixel_size_um=17.0,  # current 17.0, old 18.7
        fit_order=1,
        gauge_sizes=(20,),
        white_band=0,
        dotsize=1,
        ssig=0,
        flip_displacement_sign=False,
        edge_exclusion_pixels=5
    )
