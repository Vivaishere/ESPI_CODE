import os
import re
import math
import numpy as np
from skimage import io
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import tkinter as tk
from tkinter import filedialog
from utils import select_base_folder


# =========================
# SORT KEY (loading order)
# =========================
def extract_step_sort_key(filename):
    match = re.search(r'_(\d+)-(\d+)', filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 9999, 9999


# =========================
# GROUP KEY (EXPERIMENT SET)
# =========================
def extract_set_key(filename):
    base = os.path.splitext(filename)[0]
    if base.startswith("UW_"):
        base = base[3:]
    base = re.sub(r'_\d+-\d+$', '', base)
    return base


# =========================
# RIGID BODY CORRECTION
# =========================
def robust_rigid_body_adjustment(
        img,
        pixel_size_m=17e-6,
        edge_exclusion_mm=1.0,
        percentile=99.0
):
    h, w = img.shape

    edge_px = int(edge_exclusion_mm / (pixel_size_m * 1000))

    # ----------------------------------------
    # TOP THIRD
    # ----------------------------------------
    top_end = h // 3

    top_region = img[
        edge_px:top_end,
        edge_px:w-edge_px
    ]

    # ----------------------------------------
    # BOTTOM THIRD
    # ----------------------------------------
    bottom_start = 2 * h // 3

    bottom_region = img[
        bottom_start:h-edge_px,
        edge_px:w-edge_px
    ]

    # ----------------------------------------
    # HELPER FUNCTION
    # ----------------------------------------
    def robust_mean(region):

        valid = region[np.isfinite(region)]

        low = np.percentile(
            valid,
            (100 - percentile) / 2
        )

        high = np.percentile(
            valid,
            100 - (100 - percentile) / 2
        )

        robust_values = valid[
            (valid >= low) & (valid <= high)
        ]

        return np.mean(robust_values)

    # ----------------------------------------
    # COMPUTE BOTH
    # ----------------------------------------
    top_mean = robust_mean(top_region)

    bottom_mean = robust_mean(bottom_region)

    # ----------------------------------------
    # FINAL RBM OFFSET
    # ----------------------------------------
    return (top_mean + bottom_mean) / 2


# =========================
# MAIN FUNCTION
# =========================
def get_displacement(
        base_folder=None,
        colormap="jet",
        displacement_percentile=99.9,
        rigid_body_percentile=99.0,
        edge_exclusion_mm=1.0,
        save_multi_panel=True,
        save_combined_png=True,
        angle_deg = 27.2,
        pixel_size_m = 17e-6
):

    # =========================
    # SELECT FOLDER
    # =========================
    if not base_folder:
        root = tk.Tk()
        root.withdraw()
        base_folder = filedialog.askdirectory(
            title="Select folder containing UW_*.tiff"
        )
        root.destroy()

        if not base_folder:
            return

    # =========================
    # CONSTANTS
    # =========================
    wavelength_nm = 633
    angle_deg = angle_deg
    pixel_size_m = pixel_size_m

    coefficient = -(wavelength_nm * 1e-9) / (
        4 * np.pi * np.sin(np.radians(angle_deg))
    )

    # =========================
    # FIND FILES (ONLY UW SET)
    # =========================
    all_files = [
        f for f in os.listdir(base_folder)
        if f.startswith("UW_") and f.endswith(".tiff")
    ]

    if not all_files:
        print("No UW TIFFs found.")
        return

    # =========================
    # GROUP BY SET
    # =========================
    groups = {}
    for f in all_files:
        key = extract_set_key(f)
        groups.setdefault(key, []).append(f)

    # =========================
    # PROCESS EACH SET
    # =========================
    for set_name, files in groups.items():

        files = sorted(files, key=extract_step_sort_key)

        print(f"\nProcessing set: {set_name} ({len(files)} images)")

        adjusted_images = []
        adjusted_names = []

        # =========================
        # CHECK IF ALREADY DONE
        # =========================
        steps = [extract_step_sort_key(f) for f in files]
        max_load = max(a for a, b in steps)
        min_load = min(b for a, b in steps)
        load_range = f"{max_load}-{min_load}"

        test_out = os.path.join(
            base_folder,
            f"COMBINED-Disp_RBM-adj_{set_name}_{load_range}.tiff"
        )

        if os.path.exists(test_out):
            print(f"⏭ Skipping already processed set: {set_name}")
            continue

        # =========================
        # PROCESS IMAGES
        # =========================
        for filename in files:

            file_path = os.path.join(base_folder, filename)
            base_name = os.path.splitext(filename)[0]

            # REMOVE UW_ everywhere
            clean_base = base_name.replace("UW_", "")
            clean_name = re.sub(r'^\D*', '', clean_base)  # keeps only loading like 12-8 etc.

            delta_phi = io.imread(file_path).astype(np.float32)
            displacement_um = coefficient * delta_phi * 1e6

            # ---- SAVE RAW DISPLACEMENT (clean filename) ----
            io.imsave(
                os.path.join(base_folder, f"disp-um_{clean_base}.tiff"),
                displacement_um.astype(np.float32)
            )

            offset = robust_rigid_body_adjustment(
                displacement_um,
                pixel_size_m=pixel_size_m,
                edge_exclusion_mm=edge_exclusion_mm,
                percentile=rigid_body_percentile
            )

            adjusted = displacement_um - offset

            adjusted_images.append(adjusted)
            adjusted_names.append(clean_name)

            # ---- SAVE RBM ADJUSTED (clean filename) ----
            io.imsave(
                os.path.join(base_folder, f"Disp-RBM-adj_{clean_base}.tiff"),
                adjusted.astype(np.float32)
            )

        # =========================
        # MULTI-PANEL
        # =========================
        if save_multi_panel:

            n = len(adjusted_images)
            cols = min(3, n)
            rows = math.ceil(n / cols)

            fig, axes = plt.subplots(
                rows, cols,
                figsize=(5 * cols, 4 * rows),
                constrained_layout=True
            )

            fig.suptitle(
                f"RBM Adjusted Displacement Maps\n{set_name} | load {load_range}",
                fontsize=14
            )

            axes = np.array(axes).reshape(-1)

            # ==========================================
            # EXCLUDE 5 EDGE ROWS/COLUMNS FOR COLORBAR
            # ==========================================
            cropped_pixels = []

            for img in adjusted_images:

                cropped = img[5:-5, 5:-5]

                valid = cropped[np.isfinite(cropped)]

                if valid.size > 0:
                    cropped_pixels.append(valid)

            all_pixels = np.concatenate(cropped_pixels)

            max_val = np.percentile(
                np.abs(all_pixels),
                displacement_percentile
            )

            norm = TwoSlopeNorm(vmin=-max_val, vcenter=0, vmax=max_val)

            cmap = plt.get_cmap(colormap).copy()
            cmap.set_over("magenta")
            cmap.set_under("magenta")

            for i, (img, name) in enumerate(zip(adjusted_images, adjusted_names)):

                h, w = img.shape
                extent = (
                    0, w * pixel_size_m * 1000,
                    0, h * pixel_size_m * 1000
                )

                im = axes[i].imshow(
                    img,
                    cmap=cmap,
                    norm=norm,
                    extent=extent,
                    aspect="equal"
                )

                axes[i].set_title(name)
                axes[i].set_xlabel("X (mm)")
                axes[i].set_ylabel("Y (mm)")

            for j in range(i + 1, len(axes)):
                fig.delaxes(axes[j])

            cbar = fig.colorbar(im, ax=axes.tolist(), shrink=0.8, extend="both")
            cbar.set_label("Displacement (µm)")

            fig.savefig(
                os.path.join(
                    base_folder,
                    f"Disp-multi-panel_RBM-adj_{set_name}_{load_range}.png"
                ),
                dpi=300
            )
            plt.close()

        # =========================
        # COMBINED IMAGE
        # =========================
        combined = np.sum(adjusted_images, axis=0)

        io.imsave(
            os.path.join(
                base_folder,
                f"COMBINED-Disp_RBM-adj_{set_name}_{load_range}.tiff"
            ),
            combined.astype(np.float32)
        )

        # =========================
        # COMBINED FIGURE
        # =========================
        if save_combined_png:
            # ==========================================
            # EXCLUDE 5 EDGE ROWS/COLUMNS FOR COLORBAR
            # ==========================================
            cropped_combined = combined[5:-5, 5:-5]

            valid = cropped_combined[np.isfinite(cropped_combined)]

            max_val = np.percentile(
                np.abs(valid),
                displacement_percentile
            )

            norm = TwoSlopeNorm(vmin=-max_val, vcenter=0, vmax=max_val)

            h, w = combined.shape
            extent = (
                0, w * pixel_size_m * 1000,
                0, h * pixel_size_m * 1000
            )

            fig, ax = plt.subplots(figsize=(8, 6))

            im = ax.imshow(
                combined,
                cmap=colormap,
                norm=norm,
                extent=extent,
                aspect="equal"
            )

            cbar = plt.colorbar(im, ax=ax, extend="both")
            cbar.set_label("Displacement (µm)")

            ax.set_title(
                f"Combined RBM Adjusted Displacement Maps\n{set_name} | load {load_range}"
            )

            fig.savefig(
                os.path.join(
                    base_folder,
                    f"COMBINED-Disp_RBM-adj_{set_name}_{load_range}.png"
                ),
                dpi=600
            )
            plt.close()

        print(f"✔ Finished set: {set_name} ({load_range})")


if __name__ == "__main__":
    folder = select_base_folder()

    get_displacement(
        base_folder=folder,
        colormap="jet",
        displacement_percentile=99.9,
        rigid_body_percentile=99.0,
        edge_exclusion_mm=1.0,
        angle_deg=27.2, # previously 12.577
        pixel_size_m = 17e-6 # previously 18.7
    )