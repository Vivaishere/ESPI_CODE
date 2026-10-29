# img_processing_main.py

import os
import numpy as np
import imageio.v2 as imageio
from skimage import io
from scipy.signal import medfilt2d, wiener
from scipy.ndimage import median_filter, generic_filter

from c_phase_unwrap import unwrap_all_filter_images
from d_displacement_calc import get_displacement

from c_img_processing_support_functions import (
    select_reference_image,
    collect_forces_for_set,
    get_filter_strength_and_num,
    save_phase_quality_diagnostics
)


def filter_and_subtract_all_sets(
        folder=None,
        do_displacement=True,
        filter3_version="B",
        include_diagnostics=False,
        pixel_size_m=8.4e-6
        ):

    lv, lh, filter_num = get_filter_strength_and_num()

    # ---- User selects ONE image ----
    folder, prefix, crop = select_reference_image(folder)

    # ---- Collect forces for this set only ----
    force_sets = collect_forces_for_set(folder, prefix, crop)
    forces = list(force_sets.keys())

    print(f"\n📁 Set selected:")
    print(f"   Prefix: {prefix}")
    print(f"   Crop:   {crop}")
    print(f"   Forces: {forces}")

    print("\n📂 Files in selected set:")
    for force, files in force_sets.items():
        print(f"\n   Force {force:g}:")
        for f in sorted(files):
            print(f"      {os.path.basename(f)}")

    generated_filter_files = []

    for f1, f2 in zip(forces[:-1], forces[1:]):

        print(f"\n🔹 Processing {f1} → {f2}")

        set1_files = sorted(force_sets[f1])
        set2_files = sorted(force_sets[f2])

        # ==================================================
        # Load Images
        # ==================================================

        p1 = np.stack(
            [imageio.imread(f).astype(np.float64) / 255.0
             for f in set1_files],
            axis=2
        )

        p2 = np.stack(
            [imageio.imread(f).astype(np.float64) / 255.0
             for f in set2_files],
            axis=2
        )

        # ==================================================
        # Phase subtraction
        # ==================================================

        ps1 = np.arctan2(
            p1[:, :, 3] - p1[:, :, 1],
            p1[:, :, 0] - p1[:, :, 2]
        )

        ps2 = np.arctan2(
            p2[:, :, 3] - p2[:, :, 1],
            p2[:, :, 0] - p2[:, :, 2]
        )

        psb = ps2 - ps1

        Im = 0.5 * np.sqrt(
            (p1[:, :, 3] - p1[:, :, 1]) ** 2 +
            (p1[:, :, 0] - p1[:, :, 2]) ** 2
        )

        # ==================================================
        # DEBUG: PHASE QUALITY DIAGNOSTICS
        # ==================================================

        if include_diagnostics:
            save_phase_quality_diagnostics(folder, Im, psb, f1, f2)


        # ==================================================
        # Ensure odd filter sizes
        # ==================================================

        if lv % 2 == 0:
            lv += 1

        if lh % 2 == 0:
            lh += 1

        kernel = (lv, lh)

        # ==================================================
        # Filtering
        # ==================================================

        if filter_num == 1:

            psb_filtered = wiener(psb, kernel)

        elif filter_num == 2:

            ss = medfilt2d(np.sin(psb), kernel)
            cc = medfilt2d(np.cos(psb), kernel)

            psb_filtered = np.arctan2(ss, cc)

        elif filter_num == 3:

            version = filter3_version.upper()

            if version == "A":

                psb_filtered = filter3A(
                    psb,
                    Im,
                    lv,
                    lh
                )

            elif version == "B":

                psb_filtered = filter3B(
                    psb,
                    Im,
                    lv,
                    lh
                )

            elif version == "C":

                psb_filtered = filter3C(
                    psb,
                    Im,
                    lv,
                    lh
                )

            else:

                raise ValueError(
                    "filter3_version must be 'A', 'B', or 'C'"
                )

        else:

            raise ValueError("Invalid filter number")

        # ==================================================
        # Save
        # ==================================================

        if crop:

            name = (
                f"filter{filter_num}-str{lv}x{lh}_"
                f"{crop}_{prefix}_{f2:g}-{f1:g}"
            )

        else:

            name = (
                f"filter{filter_num}-str{lv}x{lh}_"
                f"{prefix}_{f2:g}-{f1:g}"
            )

        out_path = os.path.join(folder, f"{name}.tiff")

        io.imsave(
            out_path,
            psb_filtered.astype(np.float32)
        )

        print(f"✅ Saved {name}.tiff")

        generated_filter_files.append(out_path)

    print("\n🎉 All adjacent force pairs processed.")

    # ==================================================
    # Phase Unwrap
    # ==================================================

    print("\n🔄 Starting phase unwrapping on following images:")

    print(generated_filter_files)

    unwrap_count = unwrap_all_filter_images(
        base_folder=folder,
        image_paths=generated_filter_files
    )

    if unwrap_count == 0:

        print("⚠️ No new images unwrapped.")

    else:

        print(
            f"✅ Phase unwrapping complete "
            f"({unwrap_count} images)."
        )

    # ==================================================
    # Displacement
    # ==================================================

    if do_displacement:

        print("\n📐 Starting displacement calculation...")

        disp_count = get_displacement(folder, pixel_size_m=pixel_size_m)

        if disp_count == 0:

            print(
                "⚠️ No new displacement images generated."
            )

        else:

            print(
                f"✅ Displacement complete."
            )

    print(
        f"✅ Processing complete."
    )




# ==========================================================
# Filter 3A
# ==========================================================

def filter3A(psb, Im, lv, lh):

    kernel = (lv, lh)

    ss = medfilt2d(
        Im * np.sin(psb),
        kernel
    )

    cc = medfilt2d(
        Im * np.cos(psb),
        kernel
    )

    return np.arctan2(ss, cc)


# ==========================================================
# Filter 3B
# ==========================================================

def filter3B(psb, Im, lv, lh):

    ss = generic_filter(
        Im * np.sin(psb),
        np.nanmedian,
        size=(lv, lh),
        mode="reflect"
    )

    cc = generic_filter(
        Im * np.cos(psb),
        np.nanmedian,
        size=(lv, lh),
        mode="reflect"
    )

    return np.arctan2(ss, cc)


# ==========================================================
# Filter 3C
# ==========================================================

def filter3C(psb, Im, lv, lh):

    valid = np.isfinite(psb)

    A = Im * np.sin(psb)
    B = Im * np.cos(psb)

    A0 = np.where(valid, A, 0.0)
    B0 = np.where(valid, B, 0.0)

    A_filt = median_filter(
        A0,
        size=(lv, lh),
        mode="reflect"
    )

    B_filt = median_filter(
        B0,
        size=(lv, lh),
        mode="reflect"
    )

    W = median_filter(
        valid.astype(np.float32),
        size=(lv, lh),
        mode="reflect"
    )

    W = np.maximum(W, 1e-6)

    A_filt /= W
    B_filt /= W

    phase = np.arctan2(A_filt, B_filt)

    phase[~valid] = np.nan

    return phase