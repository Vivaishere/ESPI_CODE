# plot_espi_strain.py

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from skimage import io
from tkinter import Tk, filedialog
import os


def get_unique_path(folder, filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    new_path = os.path.join(folder, filename)

    while os.path.exists(new_path):
        new_filename = f"{base}_{counter}{ext}"
        new_path = os.path.join(folder, new_filename)
        counter += 1

    return new_path


def compute_strain_xx(
    save_plot=True,
    save_tiff=True,
    pixel_size_um=17.0,
    fit_order=1,
    gauge_sizes=(5,),
    white_band=50,
    dotsize=2,
    ssig=0,
    flip_displacement_sign=False # False in new setup
):

    print(f"Gauge sizes: {gauge_sizes}")
    print(f"SSig: {ssig}")

    # -------------------------------------------------
    # FILE SELECT
    # -------------------------------------------------
    root = Tk()
    root.withdraw()

    u_paths = filedialog.askopenfilenames(
        title="Select X-displacement TIFF(s)",
        filetypes=[("TIFF files", "*.tiff *.tif")]
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
        print(f"Processing: {os.path.basename(u_path)}")

        PIXEL_SIZE_MM = pixel_size_um * 1e-3

        save_folder = os.path.dirname(u_path)
        u_filename = os.path.basename(u_path)

        # -------------------------------------------------
        # GAUGE LOOP
        # -------------------------------------------------
        for gauge_size in gauge_sizes:

            half_gx = gauge_size // 2
            half_gy = gauge_size // 2

            strain_xx = np.full_like(u, np.nan, dtype=np.float32)

            # -------------------------------------------------
            # GRID
            # -------------------------------------------------
            x = np.arange(-half_gx, half_gx + 1) * pixel_size_um
            y = np.arange(-half_gy, half_gy + 1) * pixel_size_um

            X, Y = np.meshgrid(x, y)
            Xf, Yf = X.ravel(), Y.ravel()

            # -------------------------------------------------
            # DESIGN MATRIX
            # -------------------------------------------------
            if fit_order == 1:
                A = np.vstack([np.ones_like(Xf), Xf, Yf]).T
            else:
                A = np.vstack([
                    np.ones_like(Xf),
                    Xf, Yf,
                    Xf**2, Xf*Yf, Yf**2
                ]).T

            # -------------------------------------------------
            # WEIGHTS
            # -------------------------------------------------
            if ssig > 0:
                r2 = Xf**2 + Yf**2
                W = np.exp(-r2 / (2 * ssig**2))
            else:
                W = np.ones_like(Xf)

            # -------------------------------------------------
            # STRAIN COMPUTATION
            # -------------------------------------------------
            for i in range(half_gy, rows - half_gy):
                for j in range(half_gx, cols - half_gx):

                    win = u[i-half_gy:i+half_gy+1,
                            j-half_gx:j+half_gx+1].ravel()

                    Aw = A * W[:, None]
                    uw = win * W

                    coeffs = np.linalg.pinv(Aw.T @ Aw) @ (Aw.T @ uw)

                    strain_xx[i, j] = coeffs[1]

            # -------------------------------------------------
            # SAVE STRAIN
            # -------------------------------------------------
            strain = strain_xx * 1e6

            base_name = (
                f"ustrain-ESPI_g{gauge_size}_"
                f"fit{fit_order}_ssig{ssig}_{u_filename}"
            )

            tiff_path = get_unique_path(save_folder, base_name + ".tiff")
            fig_path = get_unique_path(save_folder, base_name + ".png")

            if save_tiff:
                io.imsave(tiff_path, strain.astype(np.float32))
                print("Saved TIFF:", tiff_path)

            # -------------------------------------------------
            # MASK EDGES
            # -------------------------------------------------
            strain_masked = strain.copy()

            strain_masked[:, :half_gx] = np.nan
            strain_masked[:, -half_gx:] = np.nan
            strain_masked[:half_gy, :] = np.nan
            strain_masked[-half_gy:, :] = np.nan

            valid = strain_masked[~np.isnan(strain_masked)]

            # -------------------------------------------------
            # MULTI-PERCENTILE LIMITS
            # -------------------------------------------------
            p99_pos = np.percentile(valid, 99)
            p999_pos = np.percentile(valid, 99.9)
            p9999_pos = np.percentile(valid, 99.99)

            p99_neg = np.percentile(valid, 1)
            p999_neg = np.percentile(valid, 0.1)
            p9999_neg = np.percentile(valid, 0.01)

            absmax = max(abs(p9999_pos), abs(p9999_neg))

            cbar_min = -absmax
            cbar_max = absmax

            # -------------------------------------------------
            # COORDS
            # -------------------------------------------------
            x_mm = (np.arange(cols) - cols / 2) * PIXEL_SIZE_MM
            y_mm = (rows - 1 - np.arange(rows)) * PIXEL_SIZE_MM

            Xg = np.repeat(x_mm[np.newaxis, :], rows, axis=0)
            Yg = np.repeat(y_mm[:, np.newaxis], cols, axis=1)

            Sf = strain_masked.ravel()
            mask = ~np.isnan(Sf)

            adaptive_size = dotsize * (1000 / max(rows, cols))

            # -------------------------------------------------
            # COLOR SETUP (MAGENTA OVER/UNDER)
            # -------------------------------------------------
            # -------------------------------------------------
            # CUSTOM COLORMAP WITH WHITE CENTER BAND
            # -------------------------------------------------
            base_cmap = plt.cm.jet

            colors = base_cmap(np.linspace(0, 1, 256))

            center_low = int(
                256 * (white_band - cbar_min) / (cbar_max - cbar_min)
            )

            center_high = int(
                256 * (-white_band - cbar_min) / (cbar_max - cbar_min)
            )

            i1 = min(center_low, center_high)
            i2 = max(center_low, center_high)

            colors[i1:i2] = [1, 1, 1, 1]

            cmap = mpl.colors.ListedColormap(colors)

            cmap.set_over("magenta")
            cmap.set_under("magenta")

            norm = mpl.colors.Normalize(
                vmin=cbar_min,
                vmax=cbar_max,
                clip=False
            )

            # -------------------------------------------------
            # PLOT
            # -------------------------------------------------
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
                    f"εxx | gauge size = {gauge_size}px\n{u_filename}",
                    pad=20
                )

                ax.set_xlabel("X (mm)")
                ax.set_ylabel("Y (mm)")
                ax.set_aspect("equal")

                ax.set_xlim(-np.max(np.abs(x_mm)), np.max(np.abs(x_mm)))
                ax.set_ylim(np.min(y_mm), np.max(y_mm))

                plt.tight_layout()

                # -------------------------------------------------
                # COLORBAR (NEW MULTI-PERCENTILE STYLE)
                # -------------------------------------------------
                cbar = plt.colorbar(im, ax=ax, extend="both")
                cbar.set_label("µstrain")

                cbar.set_ticks([
                    p9999_pos, p999_pos, p99_pos,
                    0,
                    p99_neg, p999_neg, p9999_neg
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

                # -------------------------------------------------
                # SAVE FIGURE
                # -------------------------------------------------
                plt.savefig(fig_path, dpi=600, bbox_inches="tight")
                plt.close(fig)

                print("Saved plot:", fig_path)


if __name__ == "__main__":

    compute_strain_xx(
        save_plot=True,
        save_tiff=False,
        pixel_size_um=17.0, # current 17.0, old 18.7
        fit_order=1,
        gauge_sizes=(40,),
        white_band=0,
        dotsize=1,
        flip_displacement_sign=False
    )