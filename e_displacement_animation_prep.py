# e_displacement_animation_prep.py

import os
import re
import numpy as np
from skimage import io


# ==================================================
# Extract load step
# ==================================================

def extract_load_pair(filename):

    match = re.search(
        r'_(\d+)-(\d+)\.tiff',
        filename
    )

    if match:

        return (
            int(match.group(1)),
            int(match.group(2))
        )

    return None



# ==================================================
# Extract GIF set name
# ==================================================

def extract_gif_set_name(filename):

    base = os.path.splitext(
        os.path.basename(filename)
    )[0]

    # Remove prefix
    base = base.replace(
        "Disp-RBM-adj_",
        ""
    )

    # Remove load step
    base = re.sub(
        r'_\d+-\d+$',
        '',
        base
    )

    return base



# ==================================================
# Create cumulative displacement TIFF images
# ==================================================

def create_cumulative_displacement_images(
        rbm_folder,
        output_folder,
        set_name
):

    os.makedirs(
        output_folder,
        exist_ok=True
    )


    # ----------------------------------------------
    # Find Disp-RBM images
    # ----------------------------------------------

    image_files = [
        os.path.join(rbm_folder, f)
        for f in os.listdir(rbm_folder)
        if f.startswith("Disp-RBM-adj_")
           and f.endswith(".tiff")
    ]

    image_files.sort(
        key=lambda x: extract_load_pair(
            os.path.basename(x)
        )[0]
    )


    increments = []


    for f in image_files:

        pair = extract_load_pair(
            os.path.basename(f)
        )

        if pair:
            increments.append(
                (pair, f)
            )


    if not increments:

        print(
            "No Disp-RBM images found"
        )

        return []



    # ----------------------------------------------
    # Sort loading sequence
    # ----------------------------------------------

    increments.sort(
        key=lambda x: x[0][0]
    )


    cumulative = None

    cumulative_files = []


    gif_set_name = extract_gif_set_name(
        increments[0][1]
    )

    # Lowest load value in the loading sequence
    lowest_load = min(
        pair[1]
        for pair, _ in increments
    )


    # ----------------------------------------------
    # Generate cumulative images
    # ----------------------------------------------

    for (step, previous), filename in increments:


        img = io.imread(
            filename
        ).astype(np.float32)



        if cumulative is None:

            cumulative = img.copy()

        else:

            cumulative += img



        output_name = (
            f"gif-set-{step}_"
            f"{gif_set_name}_"
            f"{step}-{lowest_load}.tiff"
        )


        output_path = os.path.join(
            output_folder,
            output_name
        )


        io.imsave(
            output_path,
            cumulative.astype(np.float32)
        )


        print(
            "Saved:",
            output_name
        )


        cumulative_files.append(
            output_path
        )


    return cumulative_files

# ==================================================
# Prepare GIF displacement images
# ==================================================

def prepare_displacement_gif_images(
        base_folder,
        set_name
):

    print(
        f"Creating cumulative GIF images for {set_name}"
    )


    # ---------------------------------
    # Locate RBM displacement folder
    # ---------------------------------

    rbm_folder = os.path.join(
        base_folder,
        f"Disp-RBM-adjusted_{set_name}"
    )

    if not os.path.exists(rbm_folder):
        print(
            f"Missing folder: {rbm_folder}"
        )

        return [], None



    # ---------------------------------
    # Find final load step
    # ---------------------------------

    rbm_files = [
        f for f in os.listdir(rbm_folder)
        if f.startswith("Disp-RBM-adj_")
        and f.endswith(".tiff")
    ]

    if not rbm_files:
        print(
            "No RBM displacement images found"
        )

        return [], None

    final_step = max(
        extract_load_pair(f)[0]
        for f in rbm_files
    )


    # ---------------------------------
    # Create GIF output folder
    # ---------------------------------

    gif_folder_name = (
        f"gif-set_{set_name}_{final_step}-0"
    )


    gif_folder = os.path.join(
        base_folder,
        gif_folder_name
    )


    os.makedirs(
        gif_folder,
        exist_ok=True
    )



    # ---------------------------------
    # Create cumulative TIFF images
    # ---------------------------------

    cumulative_files = (
        create_cumulative_displacement_images(
            rbm_folder=rbm_folder,
            output_folder=gif_folder,
            set_name=set_name
        )
    )

    if not cumulative_files:
        print(
            "No cumulative images created"
        )

        return [], None

    return cumulative_files, gif_folder