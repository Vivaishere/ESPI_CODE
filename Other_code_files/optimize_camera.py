import os
import numpy as np
import PySpin
from tifffile import imwrite
import matplotlib.pyplot as plt

# ==============================================================
# Configuration
# ==============================================================

# Folder where optimization test images and results will be saved
SAVE_DIR = os.path.join(os.path.dirname(__file__), "images_for_optimization")
os.makedirs(SAVE_DIR, exist_ok=True)

# --- Reference (from t2_000.tiff) ---
# These are approximate brightness statistics extracted from your known good image.
TARGET_STATS = {
    "center_mean": 185.0,   # average brightness in laser area
    "center_std": 20.0,     # contrast level in laser area
    "outer_mean": 18.0,     # background brightness
    "outer_std": 5.0        # noise in background
}


# ==============================================================
# Helper Functions
# ==============================================================

def compute_region_stats(np_img):
    """Compute mean and std for center (laser) and outer (background) regions."""
    h, w = np_img.shape
    cx, cy = w // 2, h // 2
    ys, xs = np.indices(np_img.shape)
    dist = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    center_mask = dist <= 400
    outer_mask = dist >= 600
    stats = {
        "center_mean": np.mean(np_img[center_mask]),
        "center_std": np.std(np_img[center_mask]),
        "outer_mean": np.mean(np_img[outer_mask]),
        "outer_std": np.std(np_img[outer_mask])
    }
    return stats


def capture_test_image(exposure_time, gain, black_level):
    """Capture one Mono8 image with specified camera parameters, return as numpy array."""
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    if cam_list.GetSize() == 0:
        print("No cameras found.")
        cam_list.Clear()
        system.ReleaseInstance()
        return None

    cam = cam_list[0]
    cam.Init()
    nodemap = cam.GetNodeMap()

    try:
        # Disable auto exposure
        node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode("ExposureAuto"))
        entry_off = node_exposure_auto.GetEntryByName("Off")
        node_exposure_auto.SetIntValue(entry_off.GetValue())

        # Exposure time (µs)
        node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode("ExposureTime"))
        node_exposure_time.SetValue(exposure_time)

        # Disable auto gain
        node_gain_auto = PySpin.CEnumerationPtr(nodemap.GetNode("GainAuto"))
        entry_gain_auto_off = node_gain_auto.GetEntryByName("Off")
        node_gain_auto.SetIntValue(entry_gain_auto_off.GetValue())

        # Set gain (dB)
        node_gain = PySpin.CFloatPtr(nodemap.GetNode("Gain"))
        node_gain.SetValue(gain)

        # Set black level
        node_black_level = PySpin.CFloatPtr(nodemap.GetNode("BlackLevel"))
        node_black_level.SetValue(black_level)

        # Acquisition
        cam.BeginAcquisition()
        processor = PySpin.ImageProcessor()
        processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)
        image_result = cam.GetNextImage(1000)
        if image_result.IsIncomplete():
            print(f"[WARN] Incomplete image: {image_result.GetImageStatus()}")
            image_result.Release()
            return None

        image_converted = processor.Convert(image_result, PySpin.PixelFormat_Mono8)
        img_array = image_converted.GetNDArray()
        image_result.Release()
        cam.EndAcquisition()

        return img_array

    except Exception as e:
        print(f"[ERROR] Capture failed: {e}")
        return None
    finally:
        cam.DeInit()
        del cam
        cam_list.Clear()
        system.ReleaseInstance()


# ==============================================================
# Optimization Function
# ==============================================================

def optimize_camera_settings(max_iterations=10):
    """
    Iteratively adjusts camera exposure, gain, and black level
    to match predefined target brightness values (from t2_000.tiff).
    Saves iteration images and plots convergence.
    """
    print("\n=== Optimizing Camera Settings ===")
    print("[Target stats]", TARGET_STATS)

    # Tracking results
    history = {
        "iter": [],
        "center_mean": [],
        "outer_mean": [],
        "loss": []
    }

    # Initial guesses
    exposure_time = 30.0  # µs
    gain = 35.0           # dB
    black_level = 0.0     # %

    for i in range(max_iterations):
        print(f"\n--- Iteration {i+1}/{max_iterations} ---")
        print(f"Trying Exposure={exposure_time:.2f} µs, Gain={gain:.2f} dB, BlackLevel={black_level:.2f}")

        img = capture_test_image(exposure_time, gain, black_level)
        if img is None:
            print("[ERROR] Image capture failed.")
            break

        stats = compute_region_stats(img)
        print("[Captured stats]", stats)

        # Compute difference from target
        diff_center = stats["center_mean"] - TARGET_STATS["center_mean"]
        diff_outer = stats["outer_mean"] - TARGET_STATS["outer_mean"]
        loss = abs(diff_center) + abs(diff_outer)

        # Save iteration image
        iter_path = os.path.join(SAVE_DIR, f"iter_{i+1:02d}.tiff")
        imwrite(iter_path, img, photometric='minisblack', compression=None)
        print(f"[Saved] {iter_path}")

        # Record history
        history["iter"].append(i + 1)
        history["center_mean"].append(stats["center_mean"])
        history["outer_mean"].append(stats["outer_mean"])
        history["loss"].append(loss)

        # Adjust parameters
        if abs(diff_center) > 3:
            exposure_time *= (1 - 0.2 * np.sign(diff_center))  # adjust exposure
        if abs(diff_outer) > 2:
            black_level -= diff_outer * 0.3                   # adjust black level
        if stats["outer_std"] > TARGET_STATS["outer_std"] + 1:
            gain = max(0, gain - 3)                           # reduce gain if noisy

        # Clamp values
        exposure_time = max(5.0, min(exposure_time, 100.0))
        gain = max(0.0, min(gain, 40.0))
        black_level = max(0.0, min(black_level, 20.0))

        if loss < 5:
            print("\n[OK] Optimization converged early.")
            break

    # ==============================================================
    # Plot results and save to files
    # ==============================================================

    # Brightness convergence
    plt.figure(figsize=(8, 5))
    plt.plot(history["iter"], history["center_mean"], '-o', label="Center Mean")
    plt.plot(history["iter"], history["outer_mean"], '-o', label="Outer Mean")
    plt.axhline(TARGET_STATS["center_mean"], color='r', linestyle='--', label="Target Center")
    plt.axhline(TARGET_STATS["outer_mean"], color='gray', linestyle='--', label="Target Outer")
    plt.title("Brightness Convergence")
    plt.xlabel("Iteration")
    plt.ylabel("Mean Intensity (0–255)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plot1_path = os.path.join(SAVE_DIR, "brightness_convergence.png")
    plt.savefig(plot1_path)
    print(f"[Saved Plot] {plot1_path}")
    plt.close()

    # Loss convergence
    plt.figure(figsize=(6, 4))
    plt.plot(history["iter"], history["loss"], '-o', color='orange')
    plt.title("Loss Convergence (|ΔCenter| + |ΔOuter|)")
    plt.xlabel("Iteration")
    plt.ylabel("Loss")
    plt.grid(True)
    plt.tight_layout()

    plot2_path = os.path.join(SAVE_DIR, "loss_convergence.png")
    plt.savefig(plot2_path)
    print(f"[Saved Plot] {plot2_path}")
    plt.close()

    # ==============================================================
    # Save final results to text file
    # ==============================================================
    results_path = os.path.join(SAVE_DIR, "optimization_results.txt")
    with open(results_path, "w") as f:
        f.write("=== Optimization Results ===\n\n")
        f.write(f"Final Exposure Time: {exposure_time:.2f} µs\n")
        f.write(f"Final Gain: {gain:.2f} dB\n")
        f.write(f"Final Black Level: {black_level:.2f} %\n")
        f.write(f"Iterations Run: {len(history['iter'])}\n\n")
        f.write("Iteration History:\n")
        f.write("Iter\tCenterMean\tOuterMean\tLoss\n")
        for i, cm, om, l in zip(history["iter"], history["center_mean"], history["outer_mean"], history["loss"]):
            f.write(f"{i}\t{cm:.2f}\t{om:.2f}\t{l:.2f}\n")

    print(f"[Saved Results] {results_path}")

    # ==============================================================
    # Final Summary
    # ==============================================================
    print("\nFinal recommended parameters:")
    print(f"Exposure: {exposure_time:.2f} µs")
    print(f"Gain: {gain:.2f} dB")
    print(f"Black Level: {black_level:.2f} %")
    print("=== Optimization complete ===")

    return exposure_time, gain, black_level, history


# ==============================================================
# Main entry point
# ==============================================================

if __name__ == "__main__":
    optimize_camera_settings(max_iterations=10)
