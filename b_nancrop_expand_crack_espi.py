import os
import glob
from collections import deque

import numpy as np

from tkinter import filedialog, messagebox

from tifffile import imread, imwrite

import matplotlib.pyplot as plt

from scipy.ndimage import (
    binary_closing,
    binary_dilation,
    binary_fill_holes,
    convolve,
    label,
    uniform_filter,
)


# --------------------------------------------------
# Robust set-name parser
# --------------------------------------------------

def get_set_name(filename):

    name = os.path.basename(filename)
    parts = name.split("_")

    if parts[0].startswith("crop"):
        return parts[1]

    return parts[0]


# --------------------------------------------------
# Preview saver (NaNs in red)
# --------------------------------------------------

def save_nan_overlay_figure(img, invalid_mask, save_path):

    img_disp = img.copy()

    img_disp -= np.nanmin(img_disp)
    img_disp /= (np.nanmax(img_disp) + 1e-9)

    img_disp = np.nan_to_num(img_disp)

    rgb = np.stack([img_disp] * 3, axis=-1)

    rgb[invalid_mask, 0] = 1
    rgb[invalid_mask, 1] = 0
    rgb[invalid_mask, 2] = 0

    plt.figure(figsize=(6,6))
    plt.imshow(rgb)
    plt.axis("off")

    plt.subplots_adjust(
        left=0,
        right=1,
        bottom=0,
        top=1
    )

    plt.savefig(
        save_path,
        dpi=400,
        bbox_inches="tight",
        pad_inches=0
    )

    plt.close()


# --------------------------------------------------
# Circular kernel
# --------------------------------------------------

def circular_kernel(radius):

    yy, xx = np.ogrid[
        -radius:radius+1,
        -radius:radius+1
    ]

    return (
        xx**2 + yy**2 <= radius**2
    )

# --------------------------------------------------
# Find automatic crack seed
# --------------------------------------------------

def find_seed(
        image,
        seed_threshold=15,
        min_component_size=100
):

    candidates = image < seed_threshold

    labels, n = label(candidates)

    if n == 0:
        return np.unravel_index(
            np.argmin(image),
            image.shape
        )

    best_component = None
    best_mean = np.inf

    for i in range(1, n + 1):

        component = labels == i

        if component.sum() < min_component_size:
            continue

        mean_intensity = image[component].mean()

        if mean_intensity < best_mean:

            best_mean = mean_intensity
            best_component = component

    if best_component is None:

        return np.unravel_index(
            np.argmin(image),
            image.shape
        )

    rows, cols = np.nonzero(best_component)

    center_row = int(rows.mean())
    center_col = int(cols.mean())

    return center_row, center_col


# --------------------------------------------------
# Region growing
# --------------------------------------------------

def grow_crack_region(
        image,
        seed,
        grow_threshold=30,
        similarity_threshold=8,
        valley_radius=4,
):

    image = image.astype(np.float32)

    rows, cols = image.shape

    valley_mean = uniform_filter(
        image,
        size=2 * valley_radius + 1,
        mode="nearest"
    )

    visited = np.zeros_like(image, dtype=bool)
    mask = np.zeros_like(image, dtype=bool)

    q = deque()

    q.append(seed)

    visited[seed] = True
    mask[seed] = True

    neighbors = [

        (-1,-1),(-1,0),(-1,1),

        (0,-1),       (0,1),

        (1,-1),(1,0),(1,1)

    ]

    while q:

        r, c = q.popleft()

        current_value = image[r, c]

        for dr, dc in neighbors:

            rr = r + dr
            cc = c + dc

            if rr < 0 or rr >= rows:
                continue

            if cc < 0 or cc >= cols:
                continue

            if visited[rr, cc]:
                continue

            visited[rr, cc] = True

            value = image[rr, cc]

            # Brightness threshold
            if value > grow_threshold:
                continue

            # Similarity to current crack
            if abs(value - current_value) > similarity_threshold:
                continue

            # Must be darker than neighborhood
            if value > valley_mean[rr, cc]:
                continue

            mask[rr, cc] = True

            q.append((rr, cc))

    return mask


# --------------------------------------------------
# Clean crack mask
# --------------------------------------------------

def clean_crack_mask(
        mask,
        bridge_radius=2,
        dilation_radius=2,
        min_component_size=100
):

    bridge_kernel = circular_kernel(
        bridge_radius
    )

    mask = binary_closing(
        mask,
        structure=bridge_kernel
    )

    mask = binary_fill_holes(mask)

    labels, n = label(mask)

    cleaned = np.zeros_like(mask)

    largest = 0

    largest_mask = None

    for i in range(1, n + 1):

        component = labels == i

        size = component.sum()

        if size < min_component_size:
            continue

        if size > largest:

            largest = size
            largest_mask = component

    if largest_mask is None:
        return cleaned

    cleaned = largest_mask

    if dilation_radius > 0:

        cleaned = binary_dilation(
            cleaned,
            structure=circular_kernel(
                dilation_radius
            )
        )

    return cleaned


# --------------------------------------------------
# Complete crack detector
# --------------------------------------------------

def build_crack_mask(
        image,
        seed_threshold=15,
        grow_threshold=30,
        similarity_threshold=40,
        valley_radius=1,
        bridge_radius=1,
        dilation_radius=0,
        min_component_size=100,
):

    seed = find_seed(
        image,
        seed_threshold=seed_threshold,
        min_component_size=min_component_size
    )

    print(f"Seed located at {seed}")

    mask = grow_crack_region(
        image,
        seed,
        grow_threshold=grow_threshold,
        similarity_threshold=similarity_threshold,
        valley_radius=valley_radius,
    )

    mask = clean_crack_mask(
        mask,
        bridge_radius=bridge_radius,
        dilation_radius=dilation_radius,
        min_component_size=min_component_size,
    )

    print(
        f"Crack size = {mask.sum()} pixels "
        f"({100*mask.mean():.3f}% of image)"
    )

    return mask

# --------------------------------------------------
# Main crack crop function
# --------------------------------------------------

def crackcrop_espi_images(
        image_paths=None,
        seed_threshold=15,
        grow_threshold=30,
        similarity_threshold=8,
        valley_radius=4,
        bridge_radius=2,
        dilation_radius=2,
        min_component_size=100,
        process_single_image=False,
):

    # --------------------------------------------------
    # Select image(s)
    # --------------------------------------------------

    # --------------------------------------------------
    # Select image(s)
    # --------------------------------------------------

    if image_paths is None:

        filepaths = filedialog.askopenfilenames(

            title="Select TIFF image(s)",

            initialdir=os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "ESPI_Images",
                    "1_RAW_new_images"
                )
            ),

            filetypes=[
                ("TIFF files", "*.tiff"),
                ("All files", "*.*")
            ]
        )

        if not filepaths:
            return

        image_paths = list(filepaths)


    else:

        image_paths = list(image_paths)

    # --------------------------------------------------
    # Read reference image
    # --------------------------------------------------

    ref_path = image_paths[0]

    ref_img = imread(
        ref_path
    ).astype(np.float32)

    if ref_img.ndim != 2:

        raise ValueError(
            "Reference image must be grayscale."
        )

    # --------------------------------------------------
    # Build crack mask
    # --------------------------------------------------

    invalid_mask = build_crack_mask(

        ref_img,

        seed_threshold=seed_threshold,

        grow_threshold=grow_threshold,

        similarity_threshold=similarity_threshold,

        valley_radius=valley_radius,

        bridge_radius=bridge_radius,

        dilation_radius=dilation_radius,

        min_component_size=min_component_size,

    )

    print()

    print("--------------------------------------")
    print("Applying crack mask...")
    print("--------------------------------------")

    # --------------------------------------------------
    # Prefix
    # --------------------------------------------------

    single_image_mode = (
        len(image_paths) == 1
        and process_single_image
    )

    if single_image_mode:

        prefix_base = (
            f"crackcrop"
        )

    else:

        prefix_base = "crackcrop"

    saved_count = 0

    # --------------------------------------------------
    # Apply mask and save
    # --------------------------------------------------

    for path in image_paths:

        try:

            img = imread(path).astype(np.float32)

            if img.shape != invalid_mask.shape:

                print(
                    f"Skipped (size mismatch): "
                    f"{os.path.basename(path)}"
                )

                continue

            img[invalid_mask] = np.nan

            folder_name, filename = os.path.split(path)

            name_no_ext, ext = os.path.splitext(filename)

            base_name = name_no_ext.replace(
                "_combined",
                ""
            )

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

            # ------------------------------------------
            # Save TIFF
            # ------------------------------------------

            if not process_single_image:

                imwrite(
                    save_path,
                    img
                )

                print(
                    "Saved:",
                    os.path.basename(save_path)
                )

            else:

                print(
                    "Skipped TIFF save "
                    "(preview mode)"
                )

            saved_count += 1

            # ------------------------------------------
            # Preview image
            # ------------------------------------------

            if process_single_image:

                folder_name, filename = os.path.split(path)

                name_no_ext, _ = os.path.splitext(
                    filename
                )

                base_png = (

                    f"{prefix_base}"

                    f"_seed{seed_threshold}"

                    f"_grow{grow_threshold}"

                    f"_sim{similarity_threshold}"
                                        
                    f"_val{valley_radius}"
                    
                    f"_bridge{bridge_radius}"

                    f"_{name_no_ext}"

                )

                png_version = 1

                preview_path = os.path.join(

                    folder_name,

                    f"{base_png}_{png_version}.png"

                )

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

                print(

                    "Preview saved:",

                    os.path.basename(preview_path)

                )

        except Exception as e:

            print()

            print("Failed:")

            print(path)

            print(e)

            print()

    print()

    print("--------------------------------------")

    print(
        f"Finished. "
        f"Processed {saved_count} image(s)."
    )

    print("--------------------------------------")

    return invalid_mask


# --------------------------------------------------
# Process complete ESPI image sets
# --------------------------------------------------

def crackcrop_all_espi_sets(
        seed_threshold=5,
        grow_threshold=30,
        similarity_threshold=40,
        valley_radius=1,
        bridge_radius=1,
        dilation_radius=0,
        min_component_size=100,
):


    # --------------------------------------------------
    # Select image(s)
    # --------------------------------------------------

    filepaths = filedialog.askopenfilenames(

        title="Select ESPI image(s) from target set",

        initialdir=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "ESPI_Images",
                "1_RAW_new_images"
            )
        ),

        filetypes=[
            ("TIFF files", "*.tiff"),
            ("All files", "*.*")
        ]
    )


    if not filepaths:
        return


    folder = os.path.dirname(
        filepaths[0]
    )


    # --------------------------------------------------
    # Determine set name
    # --------------------------------------------------

    first_image_name = os.path.basename(
        filepaths[0]
    )

    exp_name = get_set_name(
        first_image_name
    )


    print()
    print("--------------------------------------")
    print(
        "Selected set:",
        exp_name
    )
    print("--------------------------------------")


    # --------------------------------------------------
    # Find all images belonging to this set
    # --------------------------------------------------

    all_files = glob.glob(
        os.path.join(
            folder,
            "*.tiff"
        )
    )


    image_paths = [

        f for f in all_files

        if len(
            os.path.basename(f).split("_")
        ) >= 3

        and get_set_name(f) == exp_name

    ]


    if not image_paths:

        messagebox.showwarning(
            "No Images Found",
            "No intensity images found."
        )

        return


    print(
        f"Found {len(image_paths)} images "
        f"for set {exp_name}"
    )


    # --------------------------------------------------
    # Group images by load value
    # --------------------------------------------------

    load_groups = {}


    for f in image_paths:

        filename = os.path.basename(f)

        parts = filename.split("_")


        # Remove final phase number
        #
        # Example:
        #
        # UW_Test_10-0.tiff
        # UW_Test_10-1.tiff
        # UW_Test_10-2.tiff
        # UW_Test_10-3.tiff
        #
        # becomes:
        #
        # UW_Test_10

        load_key = "_".join(
            parts[:-1]
        )


        load_groups.setdefault(
            load_key,
            []
        ).append(f)

    print()
    print("--------------------------------------")
    print(
        f"Found {len(load_groups)} load groups"
    )
    print("--------------------------------------")


    # --------------------------------------------------
    # Process each load group
    # --------------------------------------------------
    processed = 0

    for load_name, group in load_groups.items():


        group = sorted(group)


        if len(group) != 4:

            print(
                f"Skipping {load_name}: "
                f"found {len(group)} images"
            )

            continue

        print()
        print(
            "Processing:",
            load_name
        )

        crackcrop_espi_images(
            image_paths=group,
            seed_threshold=seed_threshold,
            grow_threshold=grow_threshold,
            similarity_threshold=similarity_threshold,
            valley_radius=valley_radius,
            bridge_radius=bridge_radius,
            dilation_radius=dilation_radius,
            min_component_size=min_component_size,
            process_single_image=False,
        )

        processed += 1

    print()
    print("--------------------------------------")
    print(
        f"Finished. Processed {processed} load groups."
    )
    print("--------------------------------------")

# --------------------------------------------------
# Example
# --------------------------------------------------

if __name__ == "__main__":

    # for previewing one image
    #crackcrop_espi_images(process_single_image=True)

    # for processing sets

    crackcrop_all_espi_sets(
        seed_threshold=5,
        grow_threshold=30, # 30
        similarity_threshold=20, # 40
        valley_radius=1,
        bridge_radius=1,
        dilation_radius=0,
        min_component_size=100
    )