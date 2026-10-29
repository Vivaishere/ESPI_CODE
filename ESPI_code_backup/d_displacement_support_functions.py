# d_displacement_support_function.py

import os
import re
import numpy as np
from skimage import io
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from a__utils import get_unique_path


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
# CREATE MULTI-PANEL FIGURE
# =========================
def save_multi_panel_figure(
        adjusted_images,
        adjusted_names,
        set_name,
        load_range,
        base_folder,
        pixel_size_m,
        colormap="jet",
        use_rbm_for_plot=True
):

    n = len(adjusted_images)
    cols = min(3, n)
    rows = int(np.ceil(n / cols))

    fig, axes = plt.subplots(
        rows,
        cols,
        figsize=(5 * cols, 4 * rows),
        constrained_layout=True
    )

    title_type = "RBM Adjusted" if use_rbm_for_plot else "Raw"

    fig.suptitle(
        f"{title_type} Displacement Maps\n{set_name} | load {load_range}\n",
        fontsize=14,
    )

    axes = np.array(axes).reshape(-1)

    base_cmap = plt.get_cmap(colormap)
    colors = base_cmap(np.linspace(0, 1, 256))
    cmap = mpl.colors.ListedColormap(colors)

    cmap.set_over("magenta")
    cmap.set_under("magenta")

    for i, (img, name) in enumerate(zip(adjusted_images, adjusted_names)):

        # ------------------------------------------
        # Ignore edge pixels
        # ------------------------------------------

        cropped = img[5:-5, 5:-5]
        valid = cropped[np.isfinite(cropped)]

        # ------------------------------------------
        # Percentiles
        # ------------------------------------------

        p99_pos = np.percentile(valid, 99)
        p999_pos = np.percentile(valid, 99.9)
        p9999_pos = np.percentile(valid, 99.99)

        p99_neg = np.percentile(valid, 1)
        p999_neg = np.percentile(valid, 0.1)
        p9999_neg = np.percentile(valid, 0.01)

        absmax = max(abs(p9999_pos), abs(p9999_neg))

        norm = mpl.colors.Normalize(
            vmin=-absmax,
            vmax=absmax,
            clip=False
        )

        h, w = img.shape

        extent = (
            0,
            w * pixel_size_m * 1000,
            0,
            h * pixel_size_m * 1000
        )

        im = axes[i].imshow(
            img,
            cmap=cmap,
            norm=norm,
            extent=extent,
            aspect="equal"
        )

        load_name = name.split("_")[-1]

        axes[i].set_title(load_name)
        axes[i].set_xlabel("X (mm)")
        axes[i].set_ylabel("Y (mm)")

        # ------------------------------------------
        # Individual colorbar
        # ------------------------------------------

        cbar = fig.colorbar(
            im,
            ax=axes[i],
            extend="both"
        )

        cbar.set_label("Displacement (µm)")

        cbar.set_ticks([
            p9999_pos,
            p999_pos,
            p99_pos,
            0,
            p99_neg,
            p999_neg,
            p9999_neg
        ])

        cbar.set_ticklabels([
            f"{p9999_pos:.3f}  99.99%",
            f"{p999_pos:.3f}  99.9%",
            f"{p99_pos:.3f}  99%",
            "0",
            f"{p99_neg:.3f}  -99%",
            f"{p999_neg:.3f}  -99.9%",
            f"{p9999_neg:.3f}  -99.99%"
        ])

        # Prevent percentile labels overlapping
        for k, label in enumerate(cbar.ax.get_yticklabels()):
            x, y = label.get_position()
            label.set_y(y + (0.015 if k % 2 else -0.015))

    # ------------------------------------------
    # Remove unused axes
    # ------------------------------------------

    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    fig.savefig(
        get_unique_path(
            base_folder,
            f"Disp-multi-panel_{'RBM-adj' if use_rbm_for_plot else 'raw'}_{set_name}_{load_range}.png"
        ),
        dpi=600,
        bbox_inches="tight"
    )

    plt.close(fig)


# =========================
# CREATE COMBINED FIGURE
# =========================
def save_combined_figure(
        combined,
        set_name,
        load_range,
        base_folder,
        pixel_size_m,
        colormap="jet"
):

    # ==========================================
    # EXCLUDE 5 EDGE ROWS/COLUMNS FOR COLORBAR
    # ==========================================
    cropped_combined = combined[5:-5, 5:-5]

    valid = cropped_combined[np.isfinite(cropped_combined)]

    # ==========================================
    # MULTI-PERCENTILE LIMITS
    # ==========================================

    p99_pos = np.percentile(valid, 99)
    p999_pos = np.percentile(valid, 99.9)
    p9999_pos = np.percentile(valid, 99.99)

    p99_neg = np.percentile(valid, 1)
    p999_neg = np.percentile(valid, 0.1)
    p9999_neg = np.percentile(valid, 0.01)

    absmax = max(abs(p9999_pos), abs(p9999_neg))

    # ==========================================
    # COLOR SETUP
    # ==========================================

    cmap = mpl.colors.ListedColormap(
        plt.get_cmap(colormap)(np.linspace(0, 1, 256))
    )

    cmap.set_over("magenta")
    cmap.set_under("magenta")

    norm = mpl.colors.Normalize(
        vmin=-absmax,
        vmax=absmax,
        clip=False
    )

    # ==========================================
    # COORDS
    # ==========================================

    h, w = combined.shape

    extent = (
        0,
        w * pixel_size_m * 1000,
        0,
        h * pixel_size_m * 1000
    )

    # ==========================================
    # PLOT
    # ==========================================

    fig, ax = plt.subplots(figsize=(8, 6))

    im = ax.imshow(
        combined,
        cmap=cmap,
        norm=norm,
        extent=extent,
        aspect="equal"
    )

    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")

    ax.set_title(
        f"Combined RBM Adjusted Displacement Maps\n{set_name} | load {load_range}"
    )

    # ==========================================
    # COLORBAR
    # ==========================================

    cbar = plt.colorbar(
        im,
        ax=ax,
        extend="both"
    )

    cbar.set_label("Displacement (µm)")

    cbar.set_ticks([
        p9999_pos,
        p999_pos,
        p99_pos,
        0,
        p99_neg,
        p999_neg,
        p9999_neg
    ])

    cbar.set_ticklabels([
        f"{p9999_pos:.3f}  99.99%",
        f"{p999_pos:.3f}  99.9%",
        f"{p99_pos:.3f}  99%",
        "0",
        f"{p99_neg:.3f}  -99%",
        f"{p999_neg:.3f}  -99.9%",
        f"{p9999_neg:.3f}  -99.99%"
    ])

    # ==========================================
    # SAVE
    # ==========================================

    fig.savefig(
        get_unique_path(
            base_folder,
            f"COMBINED-Disp_RBM-adj_{set_name}_{load_range}.png"
        ),
        dpi=600,
        bbox_inches="tight"
    )

    plt.close(fig)