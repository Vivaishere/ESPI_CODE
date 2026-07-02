# plot_DICe_strain_and_disp.py
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from tkinter import Tk, filedialog
from skimage import io
import random
from PIL import Image
from scipy.interpolate import griddata

PIXEL_SIZE_UM = 16.6  # µm per pixel



def plot_dic_dx_color(center_adjust=True, save_plot=True, save_tiff=True):
    """
    Plots DISPLACEMENT_X from a DIC text file with color coding.
    Converts X, Y, and DX from pixels to µm.
    Lets user select file via file dialog.
    Optionally applies center adjustment to remove whole-sample horizontal movement.
    Saves a .tiff file of DX values.
    """
    # ---------------------
    # Select file
    # ---------------------
    root = Tk()
    root.withdraw()
    filename = filedialog.askopenfilename(
        title="Select DIC X-displacement file",
        initialdir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ESPI_Images", "1_RAW_new_images")),
        filetypes=[("Text files", "*.txt")]
    )
    root.destroy()

    if not filename:
        print("No file selected. Exiting.")
        return

    # ---------------------
    # Load data
    # ---------------------
    data = np.loadtxt(filename, delimiter=',', skiprows=1)
    x = data[:, 1] * PIXEL_SIZE_UM / 1000  # mm
    y = data[:, 2] * PIXEL_SIZE_UM / 1000  # mm
    dx = -data[:, 3] * PIXEL_SIZE_UM        # µm

    # ---------------------
    # Apply center adjustment (optional)
    # ---------------------
    if center_adjust:
        # Parameters
        edge_frac = 1 / 8  # fraction of x-range for edges
        center_frac = 1 / 8  # fraction around center to exclude
        frac_heights = [0.8, 0.81, 0.82, 0.83, 0.84, 0.85, 0.86, 0.87, 0.88, 0.89, 0.9, 0.91, 0.92, 0.93, 0.94, 0.95]  # multiple horizontal strips
        strip_half_width = 0.5  # mm, half-width of strip in y

        y_range = y.max() - y.min()
        x_range = x.max() - x.min()

        left_avgs = []
        right_avgs = []

        for fh in frac_heights:
            y_target = y.min() + y_range * fh

            # Build mask for the horizontal strip
            strip_mask = (y >= y_target - strip_half_width) & (y <= y_target + strip_half_width)

            # Left side: left edge to center - center_frac
            left_mask = strip_mask & (x >= x.min() + edge_frac * x_range) & \
                        (x <= x.min() + (0.5 - center_frac) * x_range)
            dx_left = dx[left_mask]

            # Right side: center + center_frac to right edge
            right_mask = strip_mask & (x >= x.min() + (0.5 + center_frac) * x_range) & \
                         (x <= x.max() - edge_frac * x_range)
            dx_right = dx[right_mask]

            # Equalize number of points by dropping randomly from longer side
            n_left = len(dx_left)
            n_right = len(dx_right)
            if n_left > n_right:
                drop_idx = random.sample(range(n_left), n_left - n_right)
                dx_left = np.delete(dx_left, drop_idx)
            elif n_right > n_left:
                drop_idx = random.sample(range(n_right), n_right - n_left)
                dx_right = np.delete(dx_right, drop_idx)

            # Store averages for this strip
            if len(dx_left) > 0 and len(dx_right) > 0:
                left_avgs.append(dx_left.mean())
                right_avgs.append(dx_right.mean())
                print(f"avg: {(dx_left.mean() + dx_right.mean())/2}")

        # Compute b as average of averages across all strips
        b = np.mean([np.mean(left_avgs), np.mean(right_avgs)])
        print(
            f"Center adjustment b = {b:.3f} µm, left_avg = {np.mean(left_avgs):.3f}, right_avg = {np.mean(right_avgs):.3f}")  # debug

        # Subtract b from all dx values
        dx = dx - b

    # Flip Y for plotting
    y_flipped = np.max(y) - y

    # ---------------------
    # Create plot
    # ---------------------
    fig, ax = plt.subplots(figsize=(10, 8))
    sc = ax.scatter(x, y_flipped, c=dx, cmap="jet", s=40, edgecolors='none')
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.invert_xaxis()
    ax.set_aspect('equal', adjustable='box')

    # Set X and Y ticks to only include 0 and max
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()
    ax.set_xticks([0, x_max])
    ax.set_yticks([0, y_max])

    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_ticks([dx.min(), 0, dx.max()])
    cbar.set_ticklabels([f"{dx.min():.2f}", 0, f"{dx.max():.2f}"])
    cbar.set_label("DX (µm)")

    # ---------------------
    # Save figure
    # ---------------------
    parent_folder = os.path.dirname(os.path.dirname(filename))
    exp_name = os.path.basename(parent_folder)
    save_name = f"{exp_name}_x-displacement.png"
    save_path = os.path.join(parent_folder, save_name)
    counter = 1
    while os.path.exists(save_path):
        save_name = f"{exp_name}_x-displacement_{counter}.png"
        save_path = os.path.join(parent_folder, save_name)
        counter += 1

    ax.set_title(f"{exp_name} x-displacement", fontsize=12, pad=10)
    plt.tight_layout()
    if save_plot:
        plt.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"✅ DIC DX plot saved as: {save_path}")

    # ---------------------
    # Save DX as 2D TIFF (preserve real displacement values)
    # ---------------------
    if save_tiff:
        # Determine original DIC pixel grid
        unique_x = np.unique(x)
        unique_y = np.unique(y)
        nx, ny = len(unique_x), len(unique_y)

        # Create regular grid
        grid_x, grid_y = np.meshgrid(unique_x, unique_y)

        # Interpolate real DX values (µm) onto grid
        dx_grid = griddata((x, y), dx, (grid_x, grid_y), method='linear')

        # Replace NaNs
        dx_grid = np.nan_to_num(dx_grid)

        # Flip axes to match scatter plot orientation
        dx_grid = np.fliplr(dx_grid)

        # Save as float32 TIFF (keeps real values)
        dx_grid_float32 = dx_grid.astype(np.float32)

        tiff_name = f"{exp_name}_DIC-x-displacement.tiff"
        tiff_path = os.path.join(parent_folder, tiff_name)
        counter = 1
        while os.path.exists(tiff_path):
            tiff_name = f"{exp_name}_DIC-x-displacement_{counter}.tiff"
            tiff_path = os.path.join(parent_folder, tiff_name)
            counter += 1

        io.imsave(tiff_path, dx_grid_float32)

        print(f"✅ DX saved as FLOAT32 TIFF: {tiff_path}")


def plot_dic_dy_color(save_plot=True):
    """
    Plots DISPLACEMENT_Y from a DIC text file with color coding.
    Converts X, Y, and DY from pixels to µm.
    Lets user select file via file dialog.
    """
    # ---------------------
    # Select file
    # ---------------------
    root = Tk()
    root.withdraw()
    filename = filedialog.askopenfilename(
        title="Select DIC Y-displacement file",
        initialdir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ESPI_Images", "1_RAW_new_images")),
        filetypes=[("Text files", "*.txt")]
    )
    root.destroy()

    if not filename:
        print("No file selected. Exiting.")
        return

    # ---------------------
    # Load data
    # ---------------------
    data = np.loadtxt(filename, delimiter=',', skiprows=1)
    x = data[:, 1] * PIXEL_SIZE_UM / 1000  # mm
    y = data[:, 2] * PIXEL_SIZE_UM / 1000  # mm
    dy = data[:, 4] * PIXEL_SIZE_UM        # µm

    y_flipped = np.max(y) - y

    # ---------------------
    # Create plot
    # ---------------------
    fig, ax = plt.subplots(figsize=(10, 8))
    sc = ax.scatter(x, y_flipped, c=dy, cmap="jet", s=40, edgecolors='none')
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.invert_xaxis()  # invert X-axis to switch left/right
    ax.set_aspect('equal', adjustable='box')

    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_ticks([dy.min(), 0, dy.max()])
    cbar.set_ticklabels([f"{dy.min():.1f}", 0, f"{dy.max():.1f}"])
    cbar.set_label("DY (µm)")


    # ---------------------
    # Save figure
    # ---------------------
    parent_folder = os.path.dirname(os.path.dirname(filename))
    exp_name = os.path.basename(parent_folder)
    save_name = f"{exp_name}_y-displacement.png"
    save_path = os.path.join(parent_folder, save_name)
    counter = 1
    while os.path.exists(save_path):
        save_name = f"{exp_name}_y-displacement_{counter}.png"
        save_path = os.path.join(parent_folder, save_name)
        counter += 1

    ax.set_title(f"{exp_name} y-displacement", fontsize=12, pad=10)
    plt.tight_layout()
    if save_plot:
        plt.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"✅ DIC DY plot saved as: {save_path}")


def plot_dic_strainxx(save_plot=True, save_tiff=True):
    """
    Plots VSG_STRAIN_XX from a DIC text/CSV file as a color-coded scatter plot.
    Converts X and Y from pixels to mm.
    Optionally saves the plot and interpolated 2D TIFF.
    """

    # ---------------------
    # File selection
    # ---------------------
    root = Tk()
    root.withdraw()
    filename = filedialog.askopenfilename(
        title="Select DIC Displacement file",
        initialdir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ESPI_Images", "1_RAW_new_images")),
        filetypes=[("Text files", "*.txt")]
    )
    root.destroy()

    if not filename:
        print("No file selected. Exiting.")
        return

    # ---------------------
    # Load data
    # ---------------------
    data = np.loadtxt(filename, delimiter=',', skiprows=1)
    x = data[:, 1] * PIXEL_SIZE_UM /1000 # um
    y = data[:, 2] * PIXEL_SIZE_UM /1000 # um
    strain_xx = data[:, 10] * 1000000 # convert to µstrain (µm/µm)

    # Flip Y for plotting
    y_flipped = np.max(y) - y

    # Remove NaNs consistently
    mask = ~np.isnan(strain_xx)

    x_plot = x[mask]
    y_plot = y_flipped[mask]
    strain_plot = strain_xx[mask]

    # Define consistent limits
    vmin = np.min(strain_plot)
    vmax = np.max(strain_plot)

    # Optional: symmetric colorbar (recommended for strain)
    # max_abs = np.max(np.abs(strain_plot))
    # vmin, vmax = -max_abs, max_abs

    fig, ax = plt.subplots(figsize=(10, 8))

    sc = ax.scatter(
        x_plot,
        y_plot,
        c=strain_plot,
        cmap="jet",
        s=10,
        edgecolors='none',
        vmin=vmin,
        vmax=vmax
    )

    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.invert_xaxis()
    ax.set_aspect('equal', adjustable='box')

    # Colorbar (now correct)
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_ticks([vmin, 0, vmax])
    cbar.set_ticklabels([f"{vmin:.2f}", "0", f"{vmax:.2f}"])
    cbar.set_label("µstrain")

    # ---------------------
    # Save plot
    # ---------------------
    parent_folder = os.path.dirname(os.path.dirname(filename))
    exp_name = os.path.basename(parent_folder)
    save_name = f"{exp_name}_strain_xx.png"
    save_path = os.path.join(parent_folder, save_name)
    counter = 1
    while os.path.exists(save_path):
        save_name = f"{exp_name}_strain_xx_{counter}.png"
        save_path = os.path.join(parent_folder, save_name)
        counter += 1

    ax.set_title(f"{exp_name} εxx (strain X)", fontsize=12, pad=10)
    plt.tight_layout()
    if save_plot:
        plt.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"✅ DIC εxx plot saved as: {save_path}")

    # ---------------------
    # Save interpolated 2D TIFF
    # ---------------------
    if save_tiff:
        unique_x = np.unique(x)
        unique_y = np.unique(y)
        grid_x, grid_y = np.meshgrid(unique_x, unique_y)

        strain_grid = griddata((x, y), strain_xx, (grid_x, grid_y), method='linear')
        strain_grid = np.nan_to_num(strain_grid)

        # Flip X to match plot
        strain_grid = np.fliplr(strain_grid)

        strain_grid_float32 = strain_grid.astype(np.float32)
        tiff_name = f"{exp_name}_strain_xx.tiff"
        tiff_path = os.path.join(parent_folder, tiff_name)
        counter = 1
        while os.path.exists(tiff_path):
            tiff_name = f"{exp_name}_strain_xx_{counter}.tiff"
            tiff_path = os.path.join(parent_folder, tiff_name)
            counter += 1
        io.imsave(tiff_path, strain_grid_float32)
        print(f"✅ εxx saved as FLOAT32 TIFF: {tiff_path}")


# ============================================================
# Example usage (optional)
# ============================================================
if __name__ == "__main__":
    plot_dic_dx_color(center_adjust=True, save_plot=True, save_tiff=True)
    #plot_dic_dy_color(save_plot=True)
    plot_dic_strainxx()
