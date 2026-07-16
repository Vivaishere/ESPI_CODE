import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
from PIL import Image
import os


def load_tiff(filepath):
    img = Image.open(filepath)
    img = np.array(img)

    return img


def compute_metrics(img):
    img = img.astype(np.float64)

    mean_intensity = np.mean(img)
    std_intensity = np.std(img)

    min_intensity = np.min(img)
    max_intensity = np.max(img)

    michelson_contrast = (
        (max_intensity - min_intensity)
        / (max_intensity + min_intensity + 1e-12)
    )

    return {
        "mean": mean_intensity,
        "std": std_intensity,
        "min": min_intensity,
        "max": max_intensity,
        "michelson": michelson_contrast
    }


def plot_sections(img, filepath, general=False):

    folder = os.path.dirname(filepath)
    filename = os.path.splitext(os.path.basename(filepath))[0]

    if general:
        save_path = os.path.join(
            folder,
            f"{filename}_9section_general_analysis.png"
        )
    else:
        save_path = os.path.join(
            folder,
            f"{filename}_9section_intensity_analysis.png"
        )


    height = img.shape[0]
    section_height = height // 9

    fig, axs = plt.subplots(3, 3, figsize=(18, 12))
    axs = axs.ravel()


    for i in range(9):

        y_start = i * section_height

        if i == 8:
            y_end = height
        else:
            y_end = (i + 1) * section_height


        section = img[y_start:y_end, :]

        metrics = compute_metrics(section)

        ax = axs[i]


        # ==================================================
        # HISTOGRAM RANGE SELECTION
        # ==================================================
        if general:

            section_min = metrics["min"]
            section_max = metrics["max"]

            # avoid zero width histogram
            if section_min == section_max:
                section_min -= 1
                section_max += 1

            bins = np.linspace(
                section_min,
                section_max,
                256
            )

            ax.hist(
                section.ravel(),
                bins=bins,
                color="black",
                alpha=0.7
            )

            ax.set_xlabel(
                "Value"
            )

        else:

            ax.hist(
                section.ravel(),
                bins=256,
                range=(0,255),
                color="black",
                alpha=0.7
            )

            ax.set_xlabel(
                "Intensity (0-255)"
            )


        ax.set_title(
            f"Section {i+1}/9\n"
            f"Mean={metrics['mean']:.5g}, "
            f"Std={metrics['std']:.5g}\n"
            f"Range={metrics['min']:.5g} → {metrics['max']:.5g}\n"
            f"Michelson={metrics['michelson']:.5g}"
        )

        ax.set_ylabel("Frequency")


    plt.suptitle(
        f"{filename} - 9 Height Sections Analysis",
        fontsize=16
    )

    plt.tight_layout()

    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight"
    )

    print(f"\nFigure saved to: {save_path}")

    plt.show()



# ==================================================
# STANDARD 0-255 IMAGE ANALYSIS
# ==================================================
def intensity_analysis():

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


    img = load_tiff(filepath)

    # force standard grayscale behavior
    img = img.astype(np.uint8)

    plot_sections(
        img,
        filepath,
        general=False
    )



# ==================================================
# FLOAT / GENERAL RANGE ANALYSIS
# ==================================================
def general_analysis():

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


    img = load_tiff(filepath)

    img = img.astype(np.float64)


    print("\nImage statistics:")
    print(f"Minimum: {np.min(img):.6g}")
    print(f"Maximum: {np.max(img):.6g}")
    print(f"Range:   {np.ptp(img):.6g}")


    plot_sections(
        img,
        filepath,
        general=True
    )



if __name__ == "__main__":

    # Choose one:

    #intensity_analysis()

    # or:

    general_analysis()