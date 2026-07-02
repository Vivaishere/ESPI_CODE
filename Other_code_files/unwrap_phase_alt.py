import os
import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
from skimage.restoration import unwrap_phase
import tifffile
from PIL import Image

# ==== File selection ====
root = Tk()
root.withdraw()
file_path = filedialog.askopenfilename(
    title="Select a wrapped phase image (e.g. .tif)",
    filetypes=[("Image files", "*.tif *.tiff *.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
)
if not file_path:
    print("❌ No file selected. Exiting.")
    exit()

print(f"✅ Selected: {file_path}")

# ==== Safe image loading ====
try:
    image = tifffile.imread(file_path)
    print("✅ Loaded as valid TIFF using tifffile.")
except Exception:
    print("⚠️ File is not a real TIFF — trying Pillow instead.")
    image = np.array(Image.open(file_path))

print("Loaded shape:", image.shape, "dtype:", image.dtype)

# Handle RGB or multi-page
if image.ndim == 3:
    if image.shape[2] in [3, 4]:
        image = np.mean(image, axis=2)  # convert to grayscale
    else:
        image = image[:, :, 0]
elif image.ndim > 3:
    image = np.squeeze(image)

image = image.astype(np.float64)
min_val, max_val = image.min(), image.max()

# ==== Map to [-π, π] if it looks like intensity ====
if max_val > 2 * np.pi or max_val <= 1.0:
    print("⚠️ Detected intensity-like image. Mapping to [-π, π] range.")
    image_wrapped = (image - min_val) / (max_val - min_val) * (2 * np.pi) - np.pi
else:
    image_wrapped = image
    print("✅ Image already appears to be a wrapped phase map.")

# ==== Unwrap ====
print("🔄 Unwrapping phase...")
image_unwrapped = unwrap_phase(image_wrapped)
print("✅ Unwrapping complete.")

# ==== Save unwrapped TIFF ====
base_name, ext = os.path.splitext(file_path)
unwrapped_path = base_name + "_alt-unwrapped.tiff"
tifffile.imwrite(unwrapped_path, image_unwrapped.astype(np.float32))
print(f"💾 Saved unwrapped TIFF to:\n{unwrapped_path}")

# ==== Display and save figure ====
plt.figure(figsize=(12, 5))
plt.suptitle("Phase Unwrapping")

plt.subplot(1, 2, 1)
plt.imshow(image_wrapped, cmap="gray")
plt.title("Wrapped Phase (Input)")
plt.colorbar(label="Phase [rad]")
plt.axis("off")

plt.subplot(1, 2, 2)
plt.imshow(image_unwrapped, cmap="seismic")
plt.title("Unwrapped Phase")
plt.colorbar(label="Phase [rad]")
plt.axis("off")

plt.tight_layout()

# Save figure as PNG alongside TIFF
fig_path = base_name + "_phase_unwrapping.png"
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
print(f"💾 Saved figure to:\n{fig_path}")

plt.show()
