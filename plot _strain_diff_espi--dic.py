# plot _strain_diff_espi--dic.py

import numpy as np
import matplotlib.pyplot as plt
from skimage import io
import tkinter as tk
from tkinter import filedialog
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


def compute_strain_difference(
    save_fig=True,
    save_tiff=True,
    save_csv=True,
    dic_pixel_um=16.6,
    scale_factor=20,
    vlim=None  # optional (vmin, vmax)
):
    """
    Compute strain difference: ESPI - DIC

    Assumes:
    - Both inputs are strain TIFFs (µstrain)
    - Same resolution

    Outputs:
    - TIFF (µstrain difference)
    - PNG figure
    - CSV with coordinates + values
    """

    # ---------------------------
    # Effective pixel size
    # ---------------------------
    PIXEL_SIZE_UM = dic_pixel_um * scale_factor
    PIXEL_SIZE_MM = PIXEL_SIZE_UM * 1e-3

    print(f"Pixel size: {PIXEL_SIZE_UM:.2f} µm ({PIXEL_SIZE_MM:.4f} mm)")

    # ---------------------------
    # File selection
    # ---------------------------
    root = tk.Tk()
    root.withdraw()

    espi_path = filedialog.askopenfilename(
        title="Select ESPI strain TIFF",
        filetypes=[("TIFF files", "*.tiff *.tif")]
    )
    if not espi_path:
        print("No ESPI file selected.")
        return

    dic_path = filedialog.askopenfilename(
        title="Select DIC strain TIFF",
        filetypes=[("TIFF files", "*.tiff *.tif")]
    )
    root.destroy()
    if not dic_path:
        print("No DIC file selected.")
        return

    # ---------------------------
    # Load images
    # ---------------------------
    espi = io.imread(espi_path).astype(np.float32)
    dic = io.imread(dic_path).astype(np.float32)

    print(f"ESPI size: {espi.shape}")
    print(f"DIC size: {dic.shape}")

    if espi.shape != dic.shape:
        raise ValueError("ESPI and DIC strain maps must be the same size.")

    # ---------------------------
    # Compute difference (µstrain)
    # ---------------------------
    diff = espi - dic

    # ---------------------------
    # Prepare save paths
    # ---------------------------
    save_folder = os.path.dirname(espi_path)
    name_no_ext = os.path.splitext(os.path.basename(espi_path))[0]

    # ---------------------------
    # Save TIFF (raw µstrain diff)
    # ---------------------------
    if save_tiff:
        tiff_name = f"strain-diff-espi-dic_{name_no_ext}.tiff"
        tiff_path = get_unique_path(save_folder, tiff_name)
        io.imsave(tiff_path, diff.astype(np.float32))
        print(f"✅ Saved TIFF: {tiff_path}")

    # ---------------------------
    # Coordinates in mm
    # ---------------------------
    rows, cols = diff.shape

    x = (np.arange(cols) - cols // 2) * PIXEL_SIZE_MM
    y = (np.arange(rows) - rows // 2) * PIXEL_SIZE_MM

    # ---------------------------
    # Save CSV
    # ---------------------------
    if save_csv:
        X, Y = np.meshgrid(x, y)

        Xf = X.flatten()
        Yf = Y.flatten()
        espi_f = espi.flatten()
        dic_f = dic.flatten()
        diff_f = diff.flatten()

        # Optional: remove NaNs
        mask = ~np.isnan(diff_f)

        data_out = np.column_stack((
            Xf[mask],
            Yf[mask],
            espi_f[mask],
            dic_f[mask],
            diff_f[mask]
        ))

        header = "x_coord_mm,y_coord_mm,espi_strain_ustrain,dic_strain_ustrain,strain_diff_ustrain"

        csv_name = f"strain-diff-espi-dic_{name_no_ext}.csv"
        csv_path = get_unique_path(save_folder, csv_name)

        np.savetxt(
            csv_path,
            data_out,
            delimiter=",",
            header=header,
            comments=""
        )

        print(f"✅ Saved CSV: {csv_path}")

    # ---------------------------
    # Color limits
    # ---------------------------
    if vlim is not None:
        vmin, vmax = vlim
    else:
        max_abs = np.nanmax(np.abs(diff))
        vmin, vmax = -max_abs, max_abs

    print(f"Colorbar limits: {vmin:.2f} to {vmax:.2f} µstrain")

    # ---------------------------
    # Plot
    # ---------------------------
    if save_fig:
        fig, ax = plt.subplots(figsize=(8, 6))

        im = ax.imshow(
            diff,
            cmap='jet',
            vmin=vmin,
            vmax=vmax,
            extent=[x.min(), x.max(), y.max(), y.min()]  # correct orientation
        )

        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.set_title("Strain Difference (ESPI - DIC)")

        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Strain Difference (µstrain)")

        plt.tight_layout()

        fig_name = f"strain-diff-espi-dic_{name_no_ext}.png"
        fig_path = get_unique_path(save_folder, fig_name)
        plt.savefig(fig_path, dpi=300)
        print(f"✅ Saved figure: {fig_path}")

        plt.close(fig)


def get_tiff_min_max():
    # File picker
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select TIFF file",
        filetypes=[("TIFF files", "*.tif *.tiff")]
    )
    root.destroy()

    if not file_path:
        print("No file selected.")
        return

    # Load image
    img = io.imread(file_path).astype(np.float32)

    # Handle NaNs safely
    img_valid = img[~np.isnan(img)]

    print(f"File: {file_path}")
    print(f"Min value: {np.min(img_valid)}")
    print(f"Max value: {np.max(img_valid)}")


def count_nans_in_tiff():
    # File picker
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select TIFF file",
        filetypes=[("TIFF files", "*.tif *.tiff")]
    )
    root.destroy()

    if not file_path:
        print("No file selected.")
        return

    # Load image
    img = io.imread(file_path).astype(np.float32)

    # Count NaNs
    nan_count = np.sum(np.isnan(img))
    total_pixels = img.size
    valid_count = total_pixels - nan_count

    print(f"File: {file_path}")
    print(f"Total pixels: {total_pixels}")
    print(f"NaN pixels: {nan_count}")
    print(f"Valid pixels: {valid_count}")
    print(f"NaN percentage: {100 * nan_count / total_pixels:.3f}%")




if __name__ == "__main__":
    compute_strain_difference(
        save_fig=True,
        save_tiff=True,
        save_csv=True,
        dic_pixel_um=16.6,  # use pixel size
        scale_factor=20,    # use step size from DICe used to create diplacement img.
        vlim=None  # or e.g. (-500, 500)
    )

    #get_tiff_min_max()

    #count_nans_in_tiff()

