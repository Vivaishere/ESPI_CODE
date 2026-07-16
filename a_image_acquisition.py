# image_acquisition.py
import os
import numpy as np
from tifffile import imwrite
import PySpin
from a__utils import get_experiment_folder  # <-- new

# =====================================================
# Default camera settings
# =====================================================
DEFAULT_CAMERA_SETTINGS = {
    "ExposureAuto": "Off",
    "ExposureTime": 10000,   # µs 13000 max
    "GainAuto": "Off",
    "Gain": 1,            # dB
    "Gamma": 1,
    "BlackLevel": 1,      # %
}

# =====================================================
# Camera detection helper
# =====================================================
def is_camera_connected() -> bool:
    """
    Check for presence of a PySpin camera without leaving instances open.
    Returns True if at least one camera is found, otherwise False.
    """
    system = None
    try:
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        size = cam_list.GetSize()
        cam_list.Clear()
        return size > 0
    except Exception:
        return False
    finally:
        if system is not None:
            try:
                system.ReleaseInstance()
            except Exception:
                pass

# =====================================================
# Capture function
# =====================================================
def capture_image(name: str, settings: dict = None, exp_name: str = "experiment", folder: str = None) -> bool:
    """
    Acquire one image and save it as TIFF.
    If no camera or PySpin unavailable, creates a mock image for testing.
    """
    if settings is None:
        settings = DEFAULT_CAMERA_SETTINGS.copy()

    # --- Use provided folder if available, otherwise fallback ---
    if folder is None:
        folder = get_experiment_folder(exp_name)

    filename = os.path.join(folder, f"{name}.tiff")

    # --- MOCK MODE (no hardware) ---
    if not is_camera_connected():
        print(f"[MOCK] Capturing image '{name}' (no camera detected).")
        mock_image = np.random.randint(0, 255, (1024, 1280), dtype=np.uint8)
        imwrite(filename, mock_image, photometric='minisblack', compression=None)
        print(f"[MOCK] Saved mock image: {filename}")
        return True

    # --- REAL CAMERA MODE ---
    system = None
    cam = None
    try:
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()

        if cam_list.GetSize() == 0:
            print("[ERROR] No cameras found.")
            cam_list.Clear()
            return False

        cam = cam_list[0]
        cam.Init()
        nodemap = cam.GetNodeMap()

        # --- Acquisition Mode ---
        try:
            node_acq_mode = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
            entry_continuous = node_acq_mode.GetEntryByName("Continuous")
            node_acq_mode.SetIntValue(entry_continuous.GetValue())
            print("[OK] Acquisition Mode: Continuous")
        except Exception as e:
            print(f"[ERROR] Acquisition Mode config failed: {e}")

        # --- Exposure ---
        try:
            node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode("ExposureAuto"))
            entry_exposure_auto_off = node_exposure_auto.GetEntryByName(settings["ExposureAuto"])
            node_exposure_auto.SetIntValue(entry_exposure_auto_off.GetValue())
            node_exposure_mode = PySpin.CEnumerationPtr(nodemap.GetNode("ExposureMode"))
            entry_exposure_mode_timed = node_exposure_mode.GetEntryByName("Timed")
            node_exposure_mode.SetIntValue(entry_exposure_mode_timed.GetValue())
            node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode("ExposureTime"))
            node_exposure_time.SetValue(settings["ExposureTime"])
            print(f"[OK] Exposure: {settings['ExposureTime']} µs")
        except Exception as e:
            print(f"[ERROR] Exposure configuration failed: {e}")

        # --- Gain ---
        try:
            node_gain_auto = PySpin.CEnumerationPtr(nodemap.GetNode("GainAuto"))
            entry_gain_auto_off = node_gain_auto.GetEntryByName(settings["GainAuto"])
            node_gain_auto.SetIntValue(entry_gain_auto_off.GetValue())
            node_gain = PySpin.CFloatPtr(nodemap.GetNode("Gain"))
            node_gain.SetValue(settings["Gain"])
            print(f"[OK] Gain: {settings['Gain']} dB")
        except Exception as e:
            print(f"[ERROR] Gain configuration failed: {e}")

        # --- Gamma ---
        try:
            node_gamma = PySpin.CFloatPtr(nodemap.GetNode("Gamma"))
            node_gamma.SetValue(settings["Gamma"])
            print(f"[OK] Gamma: {settings['Gamma']}")
        except Exception as e:
            print(f"[ERROR] Gamma configuration failed: {e}")

        # --- Black Level ---
        try:
            node_black_level = PySpin.CFloatPtr(nodemap.GetNode("BlackLevel"))
            node_black_level.SetValue(settings["BlackLevel"])
            print(f"[OK] Black Level: {settings['BlackLevel']} %")
        except Exception as e:
            print(f"[ERROR] Black Level configuration failed: {e}")


        # --- Start Acquisition ---
        # Ensure camera is not already streaming
        if cam.IsStreaming():
            cam.EndAcquisition()
            print("[OK] Previous acquisition stopped.")
            import time
            time.sleep(0.05)  # small delay

        cam.BeginAcquisition()
        processor = PySpin.ImageProcessor()
        processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)

        image_result = cam.GetNextImage(1000)
        if image_result.IsIncomplete():
            print(f"[WARN] Incomplete: {image_result.GetImageStatus()}")
            image_result.Release()
            return False

        image_converted = processor.Convert(image_result, PySpin.PixelFormat_Mono8)
        array = image_converted.GetNDArray()
        imwrite(filename, array, photometric='minisblack', compression=None)
        print(f"[OK] Saved (Mono8, uncompressed TIFF): {filename}")
        image_result.Release()
        return True

    except Exception as e:
        print(f"[ERROR] Exception during capture: {e}")
        return False

    finally:
        try:
            if cam is not None:
                cam.EndAcquisition()
                cam.DeInit()
                del cam
        except Exception:
            pass
        try:
            if system is not None:
                cam_list = system.GetCameras()
                cam_list.Clear()
                system.ReleaseInstance()
        except Exception:
            pass
