# general_plot.py

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from tkinter import Tk, filedialog
from PIL import Image


def general_plot():

    # ==========================================
    # SELECT TIFF FILE
    # ==========================================

    Tk().withdraw()

    filepath = filedialog.askopenfilename(
        title="Select TIFF image",
        filetypes=[
            ("TIFF files", "*.tif *.tiff"),
            ("All files", "*.*")
        ]
    )

    if not filepath:
        print("No file selected.")
        return


    # ==========================================
    # LOAD IMAGE
    # ==========================================

    img = np.array(
        Image.open(filepath)
    ).astype(np.float64)


    filename = os.path.splitext(
        os.path.basename(filepath)
    )[0]

    folder = os.path.dirname(filepath)


    # ==========================================
    # VALID PIXELS
    # ==========================================

    valid = img[np.isfinite(img)]


    # ==========================================
    # MULTI-PERCENTILE LIMITS
    # ==========================================

    p99_pos = np.percentile(valid, 99)
    p999_pos = np.percentile(valid, 99.9)
    p9999_pos = np.percentile(valid, 99.99)

    p99_neg = np.percentile(valid, 1)
    p999_neg = np.percentile(valid, 0.1)
    p9999_neg = np.percentile(valid, 0.01)

    absmax = max(
        abs(p9999_pos),
        abs(p9999_neg)
    )


    # ==========================================
    # COLOR SETUP
    # ==========================================

    colormap = "jet"

    cmap = mpl.colors.ListedColormap(
        plt.get_cmap(colormap)(
            np.linspace(0, 1, 256)
        )
    )

    cmap.set_over("magenta")
    cmap.set_under("magenta")


    norm = mpl.colors.Normalize(
        vmin=-absmax,
        vmax=absmax,
        clip=False
    )


    # ==========================================
    # COORDINATES (PIXELS)
    # ==========================================

    h, w = img.shape

    extent = (
        0,
        w,
        0,
        h
    )


    # ==========================================
    # PLOT
    # ==========================================

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    im = ax.imshow(
        img,
        cmap=cmap,
        norm=norm,
        extent=extent,
        aspect="equal"
    )


    ax.set_xlabel("X (pixels)")
    ax.set_ylabel("Y (pixels)")

    ax.set_title(
        f"{filename}\n"
        f"Range ±{absmax:.5g}"
    )


    # ==========================================
    # COLORBAR
    # ==========================================

    cbar = plt.colorbar(
        im,
        ax=ax,
        extend="both"
    )

    cbar.set_label(
        "Value"
    )

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
        f"{p9999_pos:.5g}  99.99%",
        f"{p999_pos:.5g}  99.9%",
        f"{p99_pos:.5g}  99%",
        "0",
        f"{p99_neg:.5g}  -99%",
        f"{p999_neg:.5g}  -99.9%",
        f"{p9999_neg:.5g}  -99.99%"
    ])


    # ==========================================
    # SAVE
    # ==========================================

    save_path = os.path.join(
        folder,
        f"general-{filename}.png"
    )

    fig.savefig(
        save_path,
        dpi=600,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"\nSaved plot:")
    print(save_path)

if __name__ == "__main__":
    general_plot()