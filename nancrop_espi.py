import os
import glob
import numpy as np
from tkinter import filedialog, messagebox
from tifffile import imread, imwrite
from scipy.ndimage import convolve, binary_dilation
import matplotlib.pyplot as plt


# --------------------------------------------------
# Robust set-name parser
# --------------------------------------------------
def get_set_name(filename):
    name = os.path.basename(filename)
    parts = name.split("_")

    if parts[0].startswith("crop"):
        return parts[1]
    else:
        return parts[0]


# --------------------------------------------------
# Preview saver (NaNs in red)
# --------------------------------------------------
def save_nan_overlay_figure(img, invalid_mask, save_path):

    img_disp = img.copy()
    img_disp = img_disp - np.nanmin(img_disp)
    img_disp = img_disp / (np.nanmax(img_disp) + 1e-9)
    img_disp = np.nan_to_num(img_disp)

    rgb = np.stack([img_disp]*3, axis=-1)

    # red overlay for NaNs
    rgb[invalid_mask, 0] = 1.0
    rgb[invalid_mask, 1] = 0.0
    rgb[invalid_mask, 2] = 0.0

    plt.figure(figsize=(6, 6))
    plt.imshow(rgb)
    plt.axis("off")

    # 🔥 remove ALL padding
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    plt.savefig(
        save_path,
        dpi=400,
        bbox_inches="tight",
        pad_inches=0
    )
    plt.close()


def nancrop_espi_images(
        ref_pix_brightness=10,      # intensity threshold: pixels below this in reference are considered "dark"
        nearby_pix_brightness=10,   # threshold for neighboring pixels used in local density check
        pix_fraction=0.25,          # fraction of dark neighbors required to classify a pixel as invalid
        pix_radius=3,               # radius (in pixels) of neighborhood used for local analysis
        radial_filter_fraction_list = [0.5, 0.5, 3/8, 0.25, 0.25],
        process_single_image=False  # if True: process only selected images (no automatic series expansion)
    ):

    # --------------------------------------------------
    # Select image(s)
    # --------------------------------------------------

    filepaths = filedialog.askopenfilenames(
        title="Select TIFF image(s) from the target folder",
        initialdir=os.path.join(os.getcwd(), "ESPI_Images"),
        filetypes=[("TIFF files", "*.tiff"), ("All files", "*.*")]
    )

    if not filepaths:
        return

    folder = os.path.dirname(filepaths[0])

    # --------------------------------------------------
    # Determine images to process
    # --------------------------------------------------

    if process_single_image:

        image_paths = list(filepaths)

    else:

        if len(filepaths) == 1:

            first_image_name = os.path.basename(filepaths[0])
            exp_name = get_set_name(first_image_name)

            all_files = glob.glob(os.path.join(folder, "*.tiff"))

            image_paths = [
                f for f in all_files
                if len(os.path.basename(f).split("_")) >= 3
                and get_set_name(f) == exp_name
            ]

        else:
            image_paths = list(filepaths)

    if not image_paths:
        messagebox.showwarning(
            "No Images Found",
            "No intensity images found."
        )
        return

    # --------------------------------------------------
    # Reference image
    # --------------------------------------------------

    ref_path = filepaths[0]
    ref_img = imread(ref_path).astype(np.float32)

    if ref_img.ndim != 2:
        raise ValueError("Reference image must be grayscale.")

    # --------------------------------------------------
    # Create mask
    # --------------------------------------------------

    dark_pixels = (ref_img < nearby_pix_brightness).astype(np.uint8)

    yy, xx = np.ogrid[
        -pix_radius:pix_radius + 1,
        -pix_radius:pix_radius + 1
    ]

    kernel = ((xx**2 + yy**2) <= pix_radius**2).astype(np.uint8)
    kernel[pix_radius, pix_radius] = 0

    kernel_pixel_count = kernel.sum()

    dark_neighbor_count = convolve(
        dark_pixels,
        kernel,
        mode="constant",
        cval=0
    )

    dark_fraction = dark_neighbor_count / kernel_pixel_count

    invalid_mask = (
        (ref_img < ref_pix_brightness)
        & (dark_fraction > pix_fraction)
    )

    # --------------------------------------------------
    # EDGE + FLOATING PIXEL CLEANING (2-STAGE)
    # --------------------------------------------------

    valid_mask = (~invalid_mask).astype(np.uint8)

    # ==================================================
    # STAGE 1 — LOCAL EDGE CLEANING (fast 3x3 filter)
    # ==================================================

    kernel8 = np.ones((3, 3), dtype=np.uint8)
    kernel8[1, 1] = 0

    for _ in range(2):  # light iterative pruning

        neighbor_count = convolve(
            valid_mask,
            kernel8,
            mode="constant",
            cval=0
        )

        # remove weakly connected pixels
        valid_mask = valid_mask & (neighbor_count >= 3)
        valid_mask = valid_mask.astype(np.uint8)

    # ==================================================
    # STAGE 2 — RADIAL STABILITY FILTER (r = 1..5)
    # ==================================================

        yy, xx = np.ogrid[-5:6, -5:6]
        dist2 = xx ** 2 + yy ** 2

        radii = [1, 2, 3, 4, 5]

        radial_filter_fraction_list = radial_filter_fraction_list

        for r, thr in zip(radii, radial_filter_fraction_list):
            ring_kernel = (
                    (dist2 >= (r - 0.5) ** 2) &
                    (dist2 <= (r + 0.5) ** 2)
            ).astype(np.uint8)

            # count valid pixels in ring
            valid_in_ring = convolve(
                valid_mask,
                ring_kernel,
                mode="constant",
                cval=0
            )

            # total available pixels in ring (edge-safe normalization)
            domain = np.ones_like(valid_mask, dtype=np.uint8)

            total_in_ring = convolve(
                domain,
                ring_kernel,
                mode="constant",
                cval=0
            )

            total_in_ring = np.maximum(total_in_ring, 1)

            fraction = valid_in_ring / total_in_ring

            # apply radius-specific threshold
            valid_mask = valid_mask & (fraction >= thr)

        valid_mask = valid_mask.astype(np.uint8)

    # ==================================================
    # FINAL MASK
    # ==================================================

    invalid_mask = ~valid_mask.astype(bool)

    # --------------------------------------------------
    # FINAL CLEANUP: 1-PIXEL NAAN DILATION (8-neighborhood)
    # --------------------------------------------------
    structure = np.array([
        [0, 1, 1, 1, 0],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [0, 1, 1, 1, 0]
    ], dtype=bool)

    invalid_mask = binary_dilation(
        invalid_mask,
        structure=structure
    )

    print(
        f"Mask created: {invalid_mask.sum()} pixels "
        f"({100 * invalid_mask.mean():.2f}% of image)"
    )

    # --------------------------------------------------
    # PREFIX
    # --------------------------------------------------

    single_image_mode = (len(image_paths) == 1 and process_single_image)

    if single_image_mode:
        param_tag = (
            f"ref{ref_pix_brightness}"
            f"-near{nearby_pix_brightness}"
            f"-frac{pix_fraction}"
            f"-rad{pix_radius}"
        )
        prefix_base = f"nancrop1-{param_tag}"
    else:
        prefix_base = "nancrop"

    # --------------------------------------------------
    # APPLY + SAVE
    # --------------------------------------------------

    saved_count = 0

    for path in image_paths:

        try:
            img = imread(path).astype(np.float32)

            if img.shape != invalid_mask.shape:
                print(f"Skipped (size mismatch): {os.path.basename(path)}")
                continue

            img[invalid_mask] = np.nan

            folder_name, filename = os.path.split(path)
            name_no_ext, ext = os.path.splitext(filename)
            base_name = name_no_ext.replace("_combined", "")

            version = 1

            save_path = os.path.join(
                folder_name,
                f"{prefix_base}{version}-{base_name}{ext}"
            )

            while os.path.exists(save_path):
                version += 1
                save_path = os.path.join(
                    folder_name,
                    f"{prefix_base}{version}-{base_name}{ext}"
                )

            # --------------------------------------------------
            # SAVE TIFF ONLY IN NORMAL MODE
            # --------------------------------------------------

            if not process_single_image:
                imwrite(save_path, img)
                print("Saved:", save_path)
            else:
                print("Skipped TIFF save (single-image preview mode)")

            saved_count += 1

            # --------------------------------------------------
            # PREVIEW (ONLY single-image mode)
            # --------------------------------------------------

            if process_single_image:

                # --------------------------------------------------
                # PREVIEW (ONLY single-image mode)
                # --------------------------------------------------

                if process_single_image:

                    folder_name, filename = os.path.split(path)
                    name_no_ext, _ = os.path.splitext(filename)

                    rad_tag = (
                            "radfilt_"
                            + "_".join([f"r{i + 1}-{v:.2f}" for i, v in enumerate(radial_filter_fraction_list)])
                    )

                    base_png = f"{prefix_base}_{rad_tag}_{name_no_ext}"

                    png_version = 1

                    preview_path = os.path.join(
                        folder_name,
                        f"{base_png}_{png_version}.png"
                    )

                    # prevent overwrite
                    while os.path.exists(preview_path):
                        png_version += 1
                        preview_path = os.path.join(
                            folder_name,
                            f"{base_png}_{png_version}.png"
                        )

                    save_nan_overlay_figure(
                        img,
                        invalid_mask,
                        preview_path
                    )

                print("Preview saved:", preview_path)

        except Exception as e:
            print(f"Failed: {path}")
            print(e)

    return invalid_mask


if __name__ == "__main__":

    nancrop_espi_images(
        ref_pix_brightness=20,      # intensity threshold: pixels below this in reference are considered "dark"
        nearby_pix_brightness=20,   # threshold for neighboring pixels used in local density check
        pix_fraction=0.2,           # fraction of dark neighbors required to classify a pixel as invalid
        pix_radius=2,               # radius (in pixels) of neighborhood used for local analysis
        radial_filter_fraction_list=[0.5, 0.5, 3/8, 3/8, 3/8], # keep <0.5 - minimum fraction of valid pixels required
        # within each radial shell for a pixel to be retained; removes floating islands / weakly supported regions
        process_single_image=False   # if True: process only selected images (no automatic series expansion)
    )

    