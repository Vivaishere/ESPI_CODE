# e_displacement_animation.py

import os
import re
import glob
import numpy as np
import tkinter as tk
from tkinter import filedialog

from skimage import io
import matplotlib.pyplot as plt
import matplotlib as mpl
from e_displacement_animation_prep import create_cumulative_displacement_images

from a__utils import get_unique_path


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

def extract_gif_set_name(filename):

    base = os.path.splitext(
        os.path.basename(filename)
    )[0]

    # Remove prefix
    base = base.replace(
        "Disp-RBM-adj_",
        ""
    )

    # Remove final load pair
    base = re.sub(
        r'_\d+-\d+$',
        '',
        base
    )

    return base


# ==================================================
# Create GIF
# ==================================================

def create_displacement_gif(
        folder=None,
        pixel_size_m=8.4e-6,
        cmap="jet",
        interpolation_frames=10
):

    import imageio.v2 as imageio


    # ==================================================
    # Select folder if none provided
    # ==================================================

    if folder is None:

        root = tk.Tk()
        root.withdraw()

        folder = filedialog.askdirectory(
            title="Select Disp-RBM-adjusted folder"
        )

        root.destroy()

        if not folder:
            return


    # ==================================================
    # Find Disp-RBM displacement images
    # ==================================================

    image_files = sorted(
        glob.glob(
            os.path.join(
                folder,
                "Disp-RBM-adj_*.tiff"
            )
        )
    )


    if not image_files:

        print(
            "No Disp-RBM-adj TIFF images found"
        )

        return



    # ==================================================
    # Create GIF output folder
    # ==================================================

    folder_name = os.path.basename(folder)

    gif_folder = os.path.join(
        os.path.dirname(folder),
        f"gif-set_{folder_name}"
    )

    os.makedirs(
        gif_folder,
        exist_ok=True
    )


    # ==================================================
    # Create cumulative images
    # ==================================================

    cumulative_files = (
        create_cumulative_displacement_images(
            rbm_folder=folder,
            output_folder=gif_folder,
            set_name=folder_name
        )
    )


    if not cumulative_files:
        return



    # ==================================================
    # Sort cumulative files
    # ==================================================

    cumulative_files = sorted(
        cumulative_files,
        key=lambda x:
            extract_load_pair(
                os.path.basename(x)
            )[0]
    )



    # ==================================================
    # Determine final displacement scale
    # ==================================================

    final = io.imread(
        cumulative_files[-1]
    )


    valid = final[np.isfinite(final)]


    vmax = max(
        abs(np.percentile(valid,0.1)),
        abs(np.percentile(valid,99.9))
    )


    norm = mpl.colors.Normalize(
        vmin=-vmax,
        vmax=vmax
    )


    cmap_obj = plt.get_cmap(cmap)

    # ==================================================
    # Create GIF frames with interpolation
    # ==================================================

    images = []

    # Load all displacement images
    displacement_frames = [
        io.imread(f).astype(np.float32)
        for f in cumulative_files
    ]

    # Create interpolated frames
    smooth_frames = []
    smooth_titles = []

    # Extract actual load values
    load_values = [
        extract_load_pair(
            os.path.basename(f)
        )[0]
        for f in cumulative_files
    ]

    for i in range(len(displacement_frames) - 1):

        img1 = displacement_frames[i]
        img2 = displacement_frames[i + 1]

        current_load = load_values[i]

        for j in range(interpolation_frames):
            alpha = j / interpolation_frames

            interpolated = (
                    (1 - alpha) * img1 +
                    alpha * img2
            )

            smooth_frames.append(
                interpolated
            )

            # Keep previous load during transition
            smooth_titles.append(
                current_load
            )

    # Add final frame

    smooth_frames.append(
        displacement_frames[-1]
    )

    smooth_titles.append(
        load_values[-1]
    )

    for frame_number, img in enumerate(smooth_frames):
        h, w = img.shape

        extent = (
            0,
            w * pixel_size_m * 1000,
            0,
            h * pixel_size_m * 1000
        )

        fig, ax = plt.subplots(
            figsize=(7, 6)
        )

        im = ax.imshow(
            img,
            cmap=cmap_obj,
            norm=norm,
            extent=extent
        )

        ax.set_xlabel(
            "X (mm)"
        )

        ax.set_ylabel(
            "Y (mm)"
        )

        # Determine approximate load value
        total_steps = len(displacement_frames) - 1

        load_value = (
                frame_number /
                interpolation_frames
        )

        ax.set_title(
            f"Load: {load_value:.2f}"
        )

        cbar = fig.colorbar(
            im,
            ax=ax
        )

        cbar.set_label(
            "Displacement (µm)"
        )

        fig.canvas.draw()

        frame_rgb = np.asarray(
            fig.canvas.buffer_rgba()
        )

        images.append(
            frame_rgb[:, :, :3]
        )

        plt.close(fig)



    # ==================================================
    # Save GIF
    # ==================================================

    gif_path = os.path.join(
        gif_folder,
        f"{os.path.basename(gif_folder)}.gif"
    )

    # 0.5 seconds per load step, not per interpolated frame
    frame_time = 0.5 / interpolation_frames

    durations = [
        int(frame_time * 1000)
        for _ in images
    ]

    # Hold final frame
    durations[-1] = 3000

    imageio.mimsave(
        gif_path,
        images,
        duration=durations,
        loop=0
    )


    print(
        "Saved GIF:",
        gif_path
    )



# ==================================================
# Run
# ==================================================

if __name__ == "__main__":
    create_displacement_gif(
        pixel_size_m=8.4e-6,
        cmap="jet"
    )