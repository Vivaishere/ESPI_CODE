import numpy as np
import matplotlib.pyplot as plt
import tifffile as tiff
from scipy.ndimage import gaussian_filter

def create_img_1():
    # ===============================================================
    # PARAMETERS
    # ===============================================================
    H, W = 600, 600
    num_fringes = 6
    speckle_strength = 0 # change this for speckles //////////////////////////////////////////////////////////////////

    crack_width = 3               # pixel width of the crack
    crack_color = 0               # 0 = black (choose any 0–255)

    # ===============================================================
    # BASE PHASE FIELD (Horizontal fringes)
    # ===============================================================
    x = np.linspace(0, np.pi, W)
    y = np.linspace(0, 2*np.pi * num_fringes, H)
    xx, yy = np.meshgrid(x, y)

    phase = yy + 0.6 * np.sin(xx * 3)

    # ===============================================================
    # CREATE PIXEL COORDINATES
    # ===============================================================
    center_y = H // 2
    center_x = W // 2
    xx_pix = np.linspace(0, W - 1, W)
    yy_pix = np.linspace(0, H - 1, H)
    XX, YY = np.meshgrid(xx_pix, yy_pix)

    # ===============================================================
    # SEMI-CIRCULAR FRINGES IN TOP HALF
    # ===============================================================
    theta = np.arctan2(YY - center_y, XX - center_x)
    semi_phase = (theta + np.pi) * num_fringes
    phase[0:center_y, :] = semi_phase[0:center_y, :]  # top half

    # ===============================================================
    # MIRROR TOP HALF HORIZONTALLY
    # ===============================================================
    phase[0:center_y, :] = np.flip(phase[0:center_y, :], axis=1)

    # ===============================================================
    # FLIP BOTTOM-RIGHT QUARTER UPSIDE DOWN
    # ===============================================================
    br_mask = (YY >= center_y) & (XX >= center_x)
    phase[br_mask] = -phase[br_mask]

    # ===============================================================
    # WRAP PHASE TO [-π, π]
    # ===============================================================
    wrapped = (phase + np.pi) % (2 * np.pi) - np.pi

    # ===============================================================
    # CONVERT TO 0–1 GRAYSCALE
    # ===============================================================
    gray = (wrapped + np.pi) / (2 * np.pi)

    # ===============================================================
    # ADD SPECKLE
    # ===============================================================
    rng = np.random.default_rng()
    speckle = 1 + speckle_strength * (rng.random((H, W)) - 0.5) * 2
    gray_speckled = gray * speckle
    gray_speckled = gaussian_filter(gray_speckled, sigma=0.6) # change sigma for blur original 0.6 //////////////////////////
    gray_speckled = np.clip(gray_speckled, 0, 1)

    # Convert to 8-bit
    img = (gray_speckled * 255).astype(np.uint8)

    # ===============================================================
    # ADD CRACK FROM CENTER DOWN ONLY
    # ===============================================================
    img[center_y:H, center_x - crack_width:center_x + crack_width] = crack_color

    # ===============================================================
    # SAVE TIFF
    # ===============================================================
    tiff.imwrite("no_speck_gauss0.6.tiff", img) # name //////////////////////////////////////////////
    print("Saved as vertical_fringes_crack.tiff")

    # ===============================================================
    # PREVIEW
    # ===============================================================
    plt.imshow(img, cmap='gray', vmin=0, vmax=255)
    plt.title("Top Half Semicircle Horizontally Flipped + Bottom-Right Upside-Down + Crack")
    plt.axis('off')
    plt.show()

def create_img_2():
    # ===============================================================
    # PARAMETERS
    # ===============================================================
    H, W = 600, 600
    num_fringes = 6
    speckle_strength = 0  # change this for speckles

    # ===============================================================
    # BASE PHASE FIELD (Vertical fringes)
    # ===============================================================
    x = np.linspace(0, 2*np.pi * num_fringes, W)
    y = np.linspace(0, np.pi, H)
    xx, yy = np.meshgrid(x, y)

    phase = xx + 0.6 * np.sin(yy * 3)  # vertical fringes

    # ===============================================================
    # WRAP PHASE TO [-π, π]
    # ===============================================================
    wrapped = (phase + np.pi) % (2 * np.pi) - np.pi

    # ===============================================================
    # CONVERT TO 0–1 GRAYSCALE
    # ===============================================================
    gray = (wrapped + np.pi) / (2 * np.pi)

    # ===============================================================
    # ADD SPECKLE
    # ===============================================================
    rng = np.random.default_rng()
    speckle = 1 + speckle_strength * (rng.random((H, W)) - 0.5) * 2
    gray_speckled = gray * speckle
    gray_speckled = gaussian_filter(gray_speckled, sigma=0.6)
    gray_speckled = np.clip(gray_speckled, 0, 1)

    # Convert to 8-bit
    img = (gray_speckled * 255).astype(np.uint8)

    # ===============================================================
    # SAVE TIFF
    # ===============================================================
    tiff.imwrite("espi_vertical_fringes.tiff", img)
    print("Saved as espi_vertical_fringes.tiff")

    # ===============================================================
    # PREVIEW
    # ===============================================================
    plt.imshow(img, cmap='gray', vmin=0, vmax=255)
    plt.title("Vertical Fringes")
    plt.axis('off')
    plt.show()

create_img_1()