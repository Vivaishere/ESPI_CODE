import os
import numpy as np
import imageio.v2 as imageio
from tkinter import Tk, filedialog


def save_nan_profile():

    # Open file explorer
    root = Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select TIFF Image",
        filetypes=[("TIFF Images", "*.tif *.tiff")]
    )

    root.destroy()

    if not file_path:
        print("No image selected.")
        return

    # Load image
    image = imageio.imread(file_path)

    # Create NaN mask
    nan_mask = ~np.isfinite(image)

    # White = NaN, Black = valid
    output = (nan_mask * 255).astype(np.uint8)

    # Save PNG alongside original TIFF
    folder = os.path.dirname(file_path)
    filename = os.path.splitext(os.path.basename(file_path))[0]

    output_path = os.path.join(
        folder,
        f"{filename}_NaN_profile.png"
    )

    imageio.imwrite(output_path, output)

    print(f"NaN profile saved: {output_path}")
    print(f"NaN pixels: {np.count_nonzero(nan_mask)}")
    print(f"Valid pixels: {np.count_nonzero(~nan_mask)}")


if __name__ == "__main__":
    save_nan_profile()