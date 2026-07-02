import numpy as np
import imageio.v2 as imageio
import matplotlib.pyplot as plt
from scipy.signal import medfilt2d, wiener
from scipy.ndimage import gaussian_filter
import os

def fasegbg(p1, p2, lg, hg, sgl, sgh, lw, hw, filter_type=3):
    """
    Python equivalent of fasegbg.m
    Computes and saves wrapped phase maps for two loading steps as 32-bit TIFFs.
    """

    # === Compute wrapped phase maps ===
    ps1 = np.arctan2((p1[:, :, 3] - p1[:, :, 1]), (p1[:, :, 0] - p1[:, :, 2]))
    ps2 = np.arctan2((p2[:, :, 3] - p2[:, :, 1]), (p2[:, :, 0] - p2[:, :, 2]))

    # === Wrapped phase difference ===
    psb = ps2 - ps1

    # === Modulation (for weighted filtering) ===
    Im = 0.5 * np.sqrt((p1[:, :, 3] - p1[:, :, 1]) ** 2 +
                       (p1[:, :, 0] - p1[:, :, 2]) ** 2)

    # === Select filter type ===
    if filter_type == 1:
        psb = wiener(psb, (lw, hw))
    elif filter_type == 2:
        ss = medfilt2d(np.sin(psb), (lw, hw))
        cc = medfilt2d(np.cos(psb), (lw, hw))
        psb = np.arctan2(ss, cc)
    elif filter_type == 3:
        ss = medfilt2d(Im * np.sin(psb), (lw, hw))
        cc = medfilt2d(Im * np.cos(psb), (lw, hw))
        psb = np.arctan2(ss, cc)
    elif filter_type == 4:
        sigma = np.mean([sgl, sgh])
        psb = np.arctan2(gaussian_filter(np.sin(psb), sigma),
                         gaussian_filter(np.cos(psb), sigma))

    # === Plot results ===
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    for ax, data, title in zip(
        axs,
        [ps1, ps2, psb],
        ["Wrapped Phase - Step 1", "Wrapped Phase - Step 2", "Wrapped Phase Difference"]
    ):
        im = ax.imshow(data, cmap='jet')
        ax.set_title(title)
        plt.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.show()

    # === Save results as 32-bit .tiff ===
    output_dir = "wrapped_phase_results"
    os.makedirs(output_dir, exist_ok=True)

    def save_tiff(name, data):
        save_path = os.path.join(output_dir, name)
        imageio.imwrite(save_path, data.astype(np.float32), format='TIFF')
        print(f"💾 Saved: {save_path}")

    save_tiff("wrapped_phase_step1.tiff", ps1)
    save_tiff("wrapped_phase_step2.tiff", ps2)
    save_tiff("wrapped_phase_difference.tiff", psb)

    print(f"\n✅ Wrapped phase maps saved in: {os.path.abspath(output_dir)}")

    return psb


# === Test script equivalent to TestunwrapVETRO.m ===
if __name__ == "__main__":
    # --- Parameters ---
    lg, hg = 2, 1
    sgl, sgh = 2, 1
    lw, hw = 7 * 4, 10 * 3
    filter_type = 3

    # --- Load image sets (example filenames) ---
    # Replace these with your actual files
    def load_set(prefix, timestamp):
        imgs = []
        for phase in ['000', '090', '180', '270']:
            fname = f"{prefix}_{phase}_{timestamp}.tiff"
            imgs.append(imageio.imread(fname).astype(np.float64) / 255.0)
        return np.stack(imgs, axis=2)

    p1 = load_set("10usopt_0", "20251009T172933")
    p2 = load_set("10usopt_1", "20251009T172957")

    # --- Compute wrapped phase difference ---
    psb = fasegbg(p1, p2, lg, hg, sgl, sgh, lw, hw, filter_type)

    # --- Display final difference ---
    plt.figure()
    plt.imshow(psb, cmap='jet')
    plt.colorbar()
    plt.title("Wrapped Phase Difference (Python Version)")
    plt.axis('image')
    plt.show()
