#displacement_calc.py

import os
import math
import numpy as np
from skimage import io
import tkinter as tk
from tkinter import filedialog

from a__utils import select_base_folder
from d_displacement_support_functions import (
    extract_step_sort_key,
    extract_set_key,
    robust_rigid_body_adjustment,
    save_multi_panel_figure,
    save_combined_figure
)


# =========================
# MAIN FUNCTION
# =========================
def get_displacement(
        base_folder=None,
        colormap="jet",
        rigid_body_percentile=99.0,
        edge_exclusion_mm=1.0,
        save_raw_disp=False,
        save_rbm_adjusted=True,
        save_multi_panel=True,
        use_rbm_for_multi_panel=True,
        save_combined_png=True,
        angle_deg=27.2,
        pixel_size_m=8.4e-6
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
        raw_images = []

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
            clean_name = clean_base

            delta_phi = io.imread(file_path).astype(np.float32)
            displacement_um = coefficient * delta_phi * 1e6
            raw_images.append(displacement_um)

            # ---- SAVE RAW DISPLACEMENT ----
            if save_raw_disp:
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
            

            # ---- SAVE RBM ADJUSTED ----
            if save_rbm_adjusted:
                io.imsave(
                    os.path.join(base_folder, f"Disp-RBM-adj_{clean_base}.tiff"),
                    adjusted.astype(np.float32)
                )

        # =========================
        # MULTI-PANEL
        # =========================
        if save_multi_panel:
            save_multi_panel_figure(
                adjusted_images=adjusted_images if use_rbm_for_multi_panel else raw_images,
                adjusted_names=adjusted_names,
                set_name=set_name,
                load_range=load_range,
                base_folder=base_folder,
                pixel_size_m=pixel_size_m,
                colormap="jet")

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
            save_combined_figure(
                combined=combined,
                set_name=set_name,
                load_range=load_range,
                base_folder=base_folder,
                pixel_size_m=pixel_size_m,
                colormap=colormap
            )

        print(f"✔ Finished set: {set_name} ({load_range})")


if __name__ == "__main__":

    get_displacement(
        colormap="jet",
        rigid_body_percentile=99.0,
        edge_exclusion_mm=1.0,
        angle_deg=27.2,      # previously 12.577
        pixel_size_m=8.4e-6   # 18.7, 17.0, 8.4
    )