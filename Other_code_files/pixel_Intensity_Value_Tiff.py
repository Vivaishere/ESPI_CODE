import tkinter as tk
from tkinter import filedialog
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt

# Hide tkinter root window
root = tk.Tk()
root.withdraw()

# Open file explorer
file_path = filedialog.askopenfilename(
    title="Select a TIFF Image",
    filetypes=[("TIFF files", "*.tiff *.tif")]
)

if not file_path:
    print("No file selected.")
    exit()

# Load the TIFF image
img = Image.open(file_path)
img_array = np.array(img)

# Determine the center row
height = img_array.shape[0]
center_row = height // 2

# Extract pixel values of the center horizontal line
if img_array.ndim == 2:
    # Grayscale image
    line_pixels = img_array[center_row, :]
else:
    # RGB or multi-channel image → take brightness (or choose a channel)
    line_pixels = img_array[center_row, :, 0]   # red channel by default

# Plot image + line profile
plt.figure(figsize=(12, 5))

# Left: the image with a line drawn
plt.subplot(1, 2, 1)
plt.imshow(img_array, cmap='gray')
plt.axhline(center_row, color='red', linewidth=1)   # show sampled row
plt.title("TIFF Image (with center line)")
plt.axis('off')

# Right: dotted pixel value plot
plt.subplot(1, 2, 2)
plt.plot(line_pixels, ".", markersize=3)
plt.title("Pixel Value Profile (Center Row)")
plt.xlabel("Pixel Number (X coordinate)")
plt.ylabel("Pixel Value")

plt.tight_layout()
plt.show()
