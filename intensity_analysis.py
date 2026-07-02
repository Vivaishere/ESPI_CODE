import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
from PIL import Image
import os


def load_tiff(filepath):
    img = Image.open(filepath)
    img = img.convert("L")  # grayscale
    return np.array(img)


def compute_metrics(img):
    img = img.astype(np.float64)

    mean_intensity = np.mean(img)
    std_intensity = np.std(img)

    min_intensity = np.min(img)
    max_intensity = np.max(img)

    michelson_contrast = (max_intensity - min_intensity) / (max_intensity + min_intensity + 1e-12)

    return {
        "mean": mean_intensity,
        "std": std_intensity,
        "min": min_intensity,
        "max": max_intensity,
        "michelson": michelson_contrast
    }


def plot_and_save(img, metrics, filepath):
    folder = os.path.dirname(filepath)
    filename = os.path.splitext(os.path.basename(filepath))[0]

    save_path = os.path.join(folder, f"{filename}_analysis.png")

    fig, axs = plt.subplots(1, 2, figsize=(12, 5))

    axs[0].imshow(img, cmap='gray')
    axs[0].set_title("TIFF Image")
    axs[0].axis("off")

    axs[1].hist(img.ravel(), bins=256, color='black', alpha=0.7)
    axs[1].set_title("Intensity Distribution")
    axs[1].set_xlabel("Intensity")
    axs[1].set_ylabel("Frequency")

    plt.suptitle(
        f"{filename}\n"
        f"Mean: {metrics['mean']:.2f} | Std (RMS): {metrics['std']:.2f} | "
        f"Michelson: {metrics['michelson']:.4f}"
    )

    plt.tight_layout()

    # SAVE FIGURE HERE
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\nFigure saved to: {save_path}")

    plt.show()


def main():
    Tk().withdraw()

    filepath = filedialog.askopenfilename(
        title="Select TIFF image",
        filetypes=[("TIFF files", "*.tif *.tiff"), ("All files", "*.*")]
    )

    if not filepath:
        print("No file selected.")
        return

    img = load_tiff(filepath)
    metrics = compute_metrics(img)

    print("\n=== Image Metrics ===")
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}")

    plot_and_save(img, metrics, filepath)


if __name__ == "__main__":
    main()