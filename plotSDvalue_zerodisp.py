# plotSDvalue_zerodisp.py

# =========================================================
# SD COMPARISON FOR MULTIPLE TIFF IMAGES
# WITH 4x4 REGIONAL SD TABLE
# AND 8x8 NOISE SD MAPS
# =========================================================

import os
import numpy as np
from tkinter import Tk, filedialog
from skimage import io
import matplotlib.pyplot as plt


# =========================================================
# CREATE NON-OVERWRITING FILE PATH
# =========================================================

def get_unique_filepath(
    folder,
    filename
):
    """
    Return a filepath that does not already exist.

    If filename already exists:
        filename.png
        filename_1.png
        filename_2.png
        ...

    This prevents existing PNG files from being overwritten.
    """

    base_path = os.path.join(
        folder,
        filename
    )

    if not os.path.exists(base_path):
        return base_path

    name, extension = os.path.splitext(
        filename
    )

    counter = 1

    while True:

        new_filename = (
            f"{name}_{counter}{extension}"
        )

        new_path = os.path.join(
            folder,
            new_filename
        )

        if not os.path.exists(new_path):
            return new_path

        counter += 1


# =========================================================
# CALCULATE SD
# =========================================================

def calculate_image_sd(
    image,
    outer_pixels=40
):
    """
    Calculate the sample standard deviation of the finite
    pixel values, excluding the outer `outer_pixels` pixels
    from all four sides.
    """

    if image.ndim != 2:
        raise ValueError(
            "Image must be a 2D TIFF."
        )

    n_rows, n_cols = image.shape

    if (
        n_rows <= 2 * outer_pixels
        or n_cols <= 2 * outer_pixels
    ):
        raise ValueError(
            f"Image is too small to remove "
            f"{outer_pixels} pixels from all sides."
        )

    # Remove outer pixels
    cropped = image[
        outer_pixels:-outer_pixels,
        outer_pixels:-outer_pixels
    ]

    # Ignore NaN / inf values
    valid_values = cropped[
        np.isfinite(cropped)
    ]

    if len(valid_values) == 0:
        return np.nan

    # Sample standard deviation
    sd = np.std(
        valid_values,
        ddof=1
    )

    return sd


# =========================================================
# CALCULATE REGIONAL SD GRID
# =========================================================

def calculate_image_sd_grid(
    image,
    outer_pixels=40,
    grid_rows=4,
    grid_cols=4
):
    """
    Remove the outer pixels and divide the remaining image
    into a grid.

    Returns a 2D array containing the sample SD of each
    individual region.
    """

    if image.ndim != 2:
        raise ValueError(
            "Image must be a 2D TIFF."
        )

    n_rows, n_cols = image.shape

    if (
        n_rows <= 2 * outer_pixels
        or n_cols <= 2 * outer_pixels
    ):
        raise ValueError(
            f"Image is too small to remove "
            f"{outer_pixels} pixels from all sides."
        )

    # -----------------------------------------------------
    # REMOVE OUTER PIXELS
    # -----------------------------------------------------

    cropped = image[
        outer_pixels:-outer_pixels,
        outer_pixels:-outer_pixels
    ]

    cropped_rows, cropped_cols = cropped.shape

    # -----------------------------------------------------
    # CREATE OUTPUT ARRAY
    # -----------------------------------------------------

    grid_sd = np.full(
        (grid_rows, grid_cols),
        np.nan,
        dtype=float
    )

    # -----------------------------------------------------
    # CALCULATE SD FOR EACH REGION
    # -----------------------------------------------------

    for row in range(grid_rows):

        row_start = int(
            np.floor(
                row * cropped_rows / grid_rows
            )
        )

        row_end = int(
            np.floor(
                (row + 1) * cropped_rows / grid_rows
            )
        )

        for col in range(grid_cols):

            col_start = int(
                np.floor(
                    col * cropped_cols / grid_cols
                )
            )

            col_end = int(
                np.floor(
                    (col + 1) * cropped_cols / grid_cols
                )
            )

            region = cropped[
                row_start:row_end,
                col_start:col_end
            ]

            # Ignore NaN / inf values
            valid_values = region[
                np.isfinite(region)
            ]

            if len(valid_values) >= 2:

                grid_sd[row, col] = np.std(
                    valid_values,
                    ddof=1
                )

    return grid_sd


# =========================================================
# CREATE VARIABLE-SIZE NOISE SD MAP WITH INTENSITY IMAGE
# =========================================================

def create_noise_sd_map(
    image,
    filename,
    folder,
    outer_pixels=40,
    grid_size=8
):
    """
    Remove the outer pixels, divide the remaining image
    into a square grid, calculate the SD of each region,
    and create a two-panel figure:

        LEFT:
            Intensity image with grid overlay.

        RIGHT:
            Noise SD map with colorbar.

    grid_size controls both the X and Y dimensions.

    Examples:

        grid_size=8   -> 8x8
        grid_size=10  -> 10x10
        grid_size=20  -> 20x20

    The same grid boundaries are used on both panels,
    so each intensity region corresponds directly to
    the same noise SD region.

    The resulting PNG is named:

        noiseSD_<filename>.png

    If that file already exists, a counter is added.
    """

    # -----------------------------------------------------
    # CHECK IMAGE
    # -----------------------------------------------------

    if image.ndim != 2:

        raise ValueError(
            "Image must be a 2D TIFF."
        )

    n_rows, n_cols = image.shape

    if (
        n_rows <= 2 * outer_pixels
        or n_cols <= 2 * outer_pixels
    ):

        raise ValueError(
            f"Image is too small to remove "
            f"{outer_pixels} pixels from all sides."
        )

    # -----------------------------------------------------
    # CHECK GRID SIZE
    # -----------------------------------------------------

    if grid_size < 1:

        raise ValueError(
            "grid_size must be at least 1."
        )

    if not isinstance(
        grid_size,
        int
    ):

        raise ValueError(
            "grid_size must be an integer."
        )

    # -----------------------------------------------------
    # REMOVE OUTER PIXELS
    # -----------------------------------------------------

    cropped = image[
        outer_pixels:-outer_pixels,
        outer_pixels:-outer_pixels
    ]

    cropped_rows, cropped_cols = cropped.shape

    # =====================================================
    # CALCULATE SD GRID
    # =====================================================

    grid_sd = calculate_image_sd_grid(
        image,
        outer_pixels=outer_pixels,
        grid_rows=grid_size,
        grid_cols=grid_size
    )

    # =====================================================
    # CREATE UNIQUE OUTPUT FILE
    # =====================================================

    output_filename = (
        f"noiseSD_{filename}.png"
    )

    save_path = get_unique_filepath(
        folder,
        output_filename
    )

    # =====================================================
    # CREATE FIGURE
    # =====================================================

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(15, 7)
    )

    ax_intensity = axes[0]
    ax_noise = axes[1]

    # =====================================================
    # LEFT PANEL — INTENSITY IMAGE
    # =====================================================

    ax_intensity.imshow(
        cropped,
        interpolation="nearest",
        origin="upper",
        cmap="gray"
    )

    ax_intensity.set_title(
        f"Intensity Image\n{filename}"
    )

    ax_intensity.set_xlabel(
        "X pixel"
    )

    ax_intensity.set_ylabel(
        "Y pixel"
    )

    # -----------------------------------------------------
    # GRID BOUNDARIES
    # -----------------------------------------------------

    x_boundaries = [
        col * cropped_cols / grid_size
        for col in range(grid_size + 1)
    ]

    y_boundaries = [
        row * cropped_rows / grid_size
        for row in range(grid_size + 1)
    ]

    # -----------------------------------------------------
    # DRAW GRID ON INTENSITY IMAGE
    # -----------------------------------------------------

    for x in x_boundaries:

        ax_intensity.axvline(
            x - 0.5,
            linewidth=1
        )

    for y in y_boundaries:

        ax_intensity.axhline(
            y - 0.5,
            linewidth=1
        )

    # -----------------------------------------------------
    # LABEL INTENSITY GRID
    # -----------------------------------------------------

    # Only label the cells if the grid is reasonably small.
    #
    # For very large grids such as 20x20, putting labels
    # in every cell can make the intensity image difficult
    # to read.

    if grid_size <= 20:

        for row in range(grid_size):

            for col in range(grid_size):

                x_center = (
                    (
                        x_boundaries[col]
                        + x_boundaries[col + 1]
                    )
                    / 2
                    - 0.5
                )

                y_center = (
                    (
                        y_boundaries[row]
                        + y_boundaries[row + 1]
                    )
                    / 2
                    - 0.5
                )

                ax_intensity.text(
                    x_center,
                    y_center,
                    f"{row + 1},{col + 1}",
                    ha="center",
                    va="center",
                    fontsize=max(
                        4,
                        9 - grid_size * 0.25
                    )
                )

    # =====================================================
    # RIGHT PANEL — NOISE SD MAP
    # =====================================================

    finite_sd = grid_sd[
        np.isfinite(grid_sd)
    ]

    if len(finite_sd) == 0:

        vmin = 0
        vmax = 1

    else:

        vmin = np.min(
            finite_sd
        )

        vmax = np.max(
            finite_sd
        )

        # Prevent a zero-width color scale
        # if all regions have exactly the
        # same SD.

        if vmin == vmax:

            if vmin == 0:

                vmax = 1

            else:

                vmin = vmin * 0.9
                vmax = vmax * 1.1

    # -----------------------------------------------------
    # DISPLAY SD MAP
    # -----------------------------------------------------

    noise_plot = ax_noise.imshow(
        grid_sd,
        interpolation="nearest",
        origin="upper",
        cmap="viridis",
        vmin=vmin,
        vmax=vmax
    )

    ax_noise.set_title(
        f"Noise SD — {grid_size}×{grid_size}\n"
        f"{filename}"
    )

    ax_noise.set_xlabel(
        f"Grid column (1–{grid_size})"
    )

    ax_noise.set_ylabel(
        f"Grid row (1–{grid_size})"
    )

    # =====================================================
    # DRAW GRID ON NOISE MAP
    # =====================================================

    # Each pixel in this image represents one
    # calculated SD region.

    ax_noise.set_xticks(
        np.arange(
            -0.5,
            grid_size,
            1
        ),
        minor=True
    )

    ax_noise.set_yticks(
        np.arange(
            -0.5,
            grid_size,
            1
        ),
        minor=True
    )

    ax_noise.grid(
        which="minor",
        linewidth=1
    )

    ax_noise.tick_params(
        which="minor",
        bottom=False,
        left=False
    )

    # -----------------------------------------------------
    # LABEL GRID AXES
    # -----------------------------------------------------

    ax_noise.set_xticks(
        np.arange(
            grid_size
        )
    )

    ax_noise.set_yticks(
        np.arange(
            grid_size
        )
    )

    # =====================================================
    # DISPLAY SD VALUE IN EACH CELL
    # =====================================================

    for row in range(grid_size):

        for col in range(grid_size):

            value = grid_sd[
                row,
                col
            ]

            if np.isfinite(value):

                value_text = (
                    f"{value:.4f}"
                )

            else:

                value_text = "N/A"

            # Reduce font size as the grid gets larger.

            if grid_size <= 10:

                fontsize = 6

            elif grid_size <= 20:

                fontsize = 4

            else:

                fontsize = 3

            ax_noise.text(
                col,
                row,
                value_text,
                ha="center",
                va="center",
                fontsize=fontsize
            )

    # =====================================================
    # COLORBAR
    # =====================================================

    colorbar = fig.colorbar(
        noise_plot,
        ax=ax_noise,
        fraction=0.046,
        pad=0.04
    )

    colorbar.set_label(
        "Noise SD"
    )

    # =====================================================
    # OVERALL FIGURE TITLE
    # =====================================================

    fig.suptitle(
        f"Noise SD Analysis — {filename}\n"
        f"{grid_size}×{grid_size} grid — "
        f"Outer {outer_pixels} pixels excluded",
        fontsize=14
    )

    # =====================================================
    # SAVE
    # =====================================================

    plt.tight_layout(
        rect=[
            0,
            0,
            1,
            0.94
        ]
    )

    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(
        f"Saved noise SD map: {save_path}"
    )


# =========================================================
# MAIN
# =========================================================

def calculate_sd_multiple_tiffs(
    outer_pixels=40,
    save_png=True
):

    # -----------------------------------------------------
    # SELECT TIFFS
    # -----------------------------------------------------

    root = Tk()
    root.withdraw()

    file_paths = filedialog.askopenfilenames(
        title="Select displacement or strain TIFFs",
        filetypes=[
            ("TIFF files", "*.tif *.tiff")
        ]
    )

    root.destroy()

    if not file_paths:

        print(
            "No TIFF files selected."
        )

        return

    # -----------------------------------------------------
    # CALCULATE SD FOR EACH IMAGE
    # -----------------------------------------------------

    results = []

    for file_path in file_paths:

        filename = os.path.splitext(
            os.path.basename(file_path)
        )[0]

        folder = os.path.dirname(
            file_path
        )

        try:

            image = io.imread(
                file_path
            ).astype(np.float64)

            # Overall SD
            sd = calculate_image_sd(
                image,
                outer_pixels=outer_pixels
            )

            # 4x4 regional SD
            grid_sd = calculate_image_sd_grid(
                image,
                outer_pixels=outer_pixels,
                grid_rows=4,
                grid_cols=4
            )

            results.append(
                (
                    filename,
                    sd,
                    grid_sd
                )
            )

            # -------------------------------------------------
            # CREATE 8x8 NOISE SD MAP
            # -------------------------------------------------

            create_noise_sd_map(
                image=image,
                filename=filename,
                folder=folder,
                outer_pixels=outer_pixels,
                grid_size=8
            )

        except Exception as e:

            results.append(
                (
                    filename,
                    np.nan,
                    np.full(
                        (4, 4),
                        np.nan
                    )
                )
            )

            print(
                f"Error reading {filename}: {e}"
            )

    # =====================================================
    # TERMINAL OUTPUT
    # =====================================================

    print()

    print(
        f"Standard deviation "
        f"(outer {outer_pixels} pixels excluded)"
    )

    print()

    for (
        filename,
        overall_sd,
        grid_sd
    ) in results:

        print(
            f"Image: {filename}"
        )

        if np.isfinite(
            overall_sd
        ):

            print(
                f"Overall SD: "
                f"{overall_sd:.6f}"
            )

        else:

            print(
                "Overall SD: N/A"
            )

        print()

        print(
            "4x4 regional SD:"
        )

        for row in grid_sd:

            row_text = "  ".join(
                f"{value:.6f}"
                if np.isfinite(value)
                else "N/A"
                for value in row
            )

            print(
                row_text
            )

        print()
        print(
            "-" * 70
        )
        print()

    # =====================================================
    # SAVE TIFF SD COMPARISON PNG
    # =====================================================

    if save_png:

        folder = os.path.dirname(
            file_paths[0]
        )

        base_name = (
            "TIFF_SD_comparison.png"
        )

        # -------------------------------------------------
        # GET UNIQUE FILEPATH
        # -------------------------------------------------

        save_path = get_unique_filepath(
            folder,
            base_name
        )

        # -------------------------------------------------
        # COLUMN WIDTH
        # -------------------------------------------------

        filename_width = max(
            [
                len(name)
                for name, _, _ in results
            ] + [10]
        )

        # -------------------------------------------------
        # FIGURE SIZE
        # -------------------------------------------------

        fig_width = max(
            14,
            filename_width * 0.14 + 10
        )

        image_block_height = 2.8

        fig_height = max(
            5,
            len(results)
            * image_block_height
            + 1
        )

        fig, ax = plt.subplots(
            figsize=(
                fig_width,
                fig_height
            )
        )

        ax.axis("off")

        # -------------------------------------------------
        # BUILD PNG CONTENT
        # -------------------------------------------------

        text_blocks = []

        for (
            filename,
            overall_sd,
            grid_sd
        ) in results:

            block = []

            block.append(
                f"Image: {filename}"
            )

            if np.isfinite(
                overall_sd
            ):

                block.append(
                    f"Overall SD: "
                    f"{overall_sd:.6f}"
                )

            else:

                block.append(
                    "Overall SD: N/A"
                )

            block.append(
                "4x4 regional SD:"
            )

            # ---------------------------------------------
            # 4x4 GRID
            # ---------------------------------------------

            cell_width = 12

            horizontal_line = (
                "+"
                + "+".join(
                    "-" * cell_width
                    for _ in range(4)
                )
                + "+"
            )

            block.append(
                horizontal_line
            )

            for row in range(4):

                row_values = []

                for col in range(4):

                    value = grid_sd[
                        row,
                        col
                    ]

                    if np.isfinite(
                        value
                    ):

                        value_text = (
                            f"{value:.6f}"
                        )

                    else:

                        value_text = "N/A"

                    row_values.append(
                        f"{value_text:^{cell_width}}"
                    )

                block.append(
                    "|"
                    + "|".join(
                        row_values
                    )
                    + "|"
                )

                block.append(
                    horizontal_line
                )

            text_blocks.append(
                "\n".join(block)
            )

        # -------------------------------------------------
        # COMBINE BLOCKS
        # -------------------------------------------------

        table_text = (
            "\n\n"
            + (
                "\n\n"
                + "=" * 80
                + "\n\n"
            ).join(
                text_blocks
            )
        )

        # -------------------------------------------------
        # ADD TEXT TO FIGURE
        # -------------------------------------------------

        ax.text(
            0.01,
            0.99,
            (
                f"TIFF Standard Deviation "
                f"Comparison\n"
                f"(outer {outer_pixels} pixels excluded)"
                f"\n"
                f"{table_text}"
            ),
            transform=ax.transAxes,
            fontsize=10,
            fontfamily="monospace",
            verticalalignment="top",
            horizontalalignment="left"
        )

        plt.tight_layout()

        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

        plt.savefig(
            save_path,
            dpi=300,
            bbox_inches="tight"
        )

        plt.close()

        print(
            f"Saved: {save_path}"
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    calculate_sd_multiple_tiffs(
        outer_pixels=40,
        save_png=True
    )
