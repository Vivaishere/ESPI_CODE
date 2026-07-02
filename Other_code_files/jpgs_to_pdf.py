import os
import re
from tkinter import Tk, filedialog
from PIL import Image


def numerical_sort_key(filepath):
    """
    Sort files numerically based on numbers in the filename.
    Examples:
        1.jpg -> 1
        2.jpg -> 2
        10.jpg -> 10
        image_15.jpg -> 15
    """
    filename = os.path.basename(filepath)
    numbers = re.findall(r"\d+", filename)

    if numbers:
        return int(numbers[-1])

    return 0


def get_unique_pdf_path(folder, base_name="combined_images"):
    """
    Create a unique PDF filename if one already exists.
    """
    pdf_path = os.path.join(folder, f"{base_name}.pdf")

    counter = 1
    while os.path.exists(pdf_path):
        pdf_path = os.path.join(folder, f"{base_name}_{counter}.pdf")
        counter += 1

    return pdf_path


def main():
    # Hide root Tk window
    root = Tk()
    root.withdraw()

    # Select JPG files
    jpg_files = filedialog.askopenfilenames(
        title="Select JPG Files",
        filetypes=[("JPEG files", "*.jpg *.jpeg")]
    )

    if not jpg_files:
        print("No files selected.")
        return

    # Sort files numerically by filename
    jpg_files = sorted(jpg_files, key=numerical_sort_key)

    # Save PDF in same folder as the images
    image_folder = os.path.dirname(jpg_files[0])
    output_pdf = get_unique_pdf_path(image_folder)

    # Target height for all images (pixels)
    target_height = 2000

    pdf_images = []

    for file in jpg_files:
        print(f"Processing: {os.path.basename(file)}")

        img = Image.open(file).convert("RGB")

        width, height = img.size

        # Scale proportionally to the target height
        scale = target_height / height
        new_width = int(width * scale)

        resized = img.resize(
            (new_width, target_height),
            Image.Resampling.LANCZOS
        )

        pdf_images.append(resized)

    # Save all images into one PDF
    pdf_images[0].save(
        output_pdf,
        save_all=True,
        append_images=pdf_images[1:]
    )

    print("\nPDF successfully created:")
    print(output_pdf)


if __name__ == "__main__":
    main()