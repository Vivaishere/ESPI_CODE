# ==============================================================
# image_processing_old.py
# Callable GUI for ESPI image analysis workflow (no hanging process)
# ==============================================================

import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
from filter_and_subtract import filter_and_subtract
from phase_unwrap import unwrap_all_filter_images
from displacement import get_displacement
from utils import validate_folder  # must exist


class ImageProcessingApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ESPI Image Processing")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        try:
            self.root.eval('tk::PlaceWindow . center')
        except Exception:
            pass

        self.exp_folder = None
        self._stop_unwrap = False
        self.unwrap_thread = None

        # -------------------------
        # Header
        # -------------------------
        tk.Label(
            self.root,
            text="ESPI Image Processing",
            font=("Arial", 14, "bold"),
            fg="blue",
        ).pack(pady=10)

        # -------------------------
        # Buttons row
        # -------------------------
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=20)

        self.select_button = tk.Button(
            btn_frame, text="Select Experiment Folder", command=self.select_experiment_folder
        )
        self.filter_button = tk.Button(
            btn_frame, text="Filter and Subtract", command=self.run_filter_and_subtract
        )
        self.unwrap_button = tk.Button(
            btn_frame, text="Phase Unwrap", command=self.run_phase_unwrap
        )
        self.displacement_button = tk.Button(
            btn_frame, text="Get Displacement", command=self.run_displacement
        )


        for btn in [
            self.select_button,
            self.filter_button,
            self.unwrap_button,
            self.displacement_button,
        ]:
            btn.pack(side=tk.LEFT, padx=8)

        # Run All Calculations button
        self.run_all_button = tk.Button(
            self.root,
            text="Run All Calculations",
            command=self.run_all_calculations
        )
        self.run_all_button.pack(pady=10)

        # -------------------------
        # Info label
        # -------------------------
        self.info_label = tk.Label(self.root, text="Select an experiment folder to start.", fg="gray")
        self.info_label.pack(pady=20)

        # -------------------------
        # Close button
        # -------------------------
        tk.Button(self.root, text="Close", command=self.on_close).pack(side=tk.BOTTOM, pady=15)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ==============================================================
    # Folder selection
    # ==============================================================
    def select_experiment_folder(self):
        folder = filedialog.askdirectory(title="Select Experiment Folder", initialdir="ESPI_Images")

        if folder:
            if validate_folder(folder):
                self.exp_folder = folder
                self.info_label.config(text=f"Experiment folder:\n{folder}", fg="blue")
            else:
                messagebox.showerror(
                    "Invalid Folder", "The selected folder is not accessible or does not exist."
                )

    # ==============================================================
    # Filter and Subtract
    # ==============================================================
    def run_filter_and_subtract(self):
        if not self.exp_folder:
            messagebox.showwarning("No Folder Selected", "Please select an experiment folder first.")
            return

        try:
            result_path = filter_and_subtract(folder=self.exp_folder)
            messagebox.showinfo(
                "Success",
                f"Filtered and subtracted phase saved to:\n{result_path}",
            )
            self.info_label.config(text=f"Filter complete:\n{result_path}", fg="green")

        except Exception as e:
            messagebox.showerror("Error", f"Error during filtering:\n{e}")
            self.info_label.config(text=f"Error during filtering:\n{e}", fg="red")

    # ==============================================================
    # Phase Unwrap
    # ==============================================================
    def run_phase_unwrap(self):
        if not self.exp_folder:
            messagebox.showwarning("No Folder Selected", "Please select an experiment folder first.")
            return

        self.info_label.config(
            text=f"Unwrapping all 'filter#' images in:\n{self.exp_folder} ...",
            fg="orange",
        )

        def unwrap_task():
            try:
                count = unwrap_all_filter_images(self.exp_folder) or 0

                if count == 0:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "No Images Found",
                        "⚠️ No matching '*_filter#.tiff' images found in this folder."
                    ))
                    self.info_label.config(
                        text="⚠️ No matching images found to unwrap.",
                        fg="red"
                    )
                else:
                    self.info_label.config(
                        text=f"✅ Phase unwrapping complete. ({count} images processed)",
                        fg="green",
                    )
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error During Unwrapping", f"❌ {e}"))
                self.info_label.config(text=f"❌ Error during unwrapping:\n{e}", fg="red")

        self.unwrap_thread = threading.Thread(target=unwrap_task, daemon=True)
        self.unwrap_thread.start()

    # ==============================================================
    # Batch Displacement
    # ==============================================================
    def run_displacement(self):
        if not self.exp_folder:
            messagebox.showwarning("No Folder Selected", "Please select an experiment folder first.")
            return

        self.info_label.config(
            text=f"Processing all '_UW.tiff' images in:\n{self.exp_folder} ...",
            fg="orange",
        )

        def displacement_task():
            try:
                count = get_displacement(self.exp_folder) or 0

                if count == 0:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "No Images Found",
                        "⚠️ No '_UW.tiff' images found in this folder."
                    ))
                    self.info_label.config(
                        text="⚠️ No matching images found to process.",
                        fg="red"
                    )
                else:
                    self.info_label.config(
                        text=f"✅ Displacement processing complete. ({count} images processed)",
                        fg="green",
                    )
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error During Displacement", f"❌ {e}"))
                self.info_label.config(text=f"❌ Error during displacement:\n{e}", fg="red")

        # Run in background thread to keep GUI responsive
        self.displacement_thread = threading.Thread(target=displacement_task, daemon=True)
        self.displacement_thread.start()

    def run_all_calculations(self):
        if not self.exp_folder:
            messagebox.showwarning("No Folder Selected", "Please select an experiment folder first.")
            return

        self.info_label.config(text="Running all steps...", fg="orange")

        def task():
            try:
                # --- Step 1: Filter (blocking) ---
                self.root.after(0, lambda: self.info_label.config(text="Filtering...", fg="orange"))
                filter_and_subtract(self.exp_folder)

                # --- Step 2: Unwrap (blocking) ---
                self.root.after(0, lambda: self.info_label.config(text="Unwrapping...", fg="orange"))
                unwrap_all_filter_images(self.exp_folder)

                # --- Step 3: Displacement (blocking) ---
                self.root.after(0, lambda: self.info_label.config(text="Calculating displacement...", fg="orange"))
                get_displacement(self.exp_folder)

                # Done
                self.root.after(0, lambda: self.info_label.config(
                    text="✅ All calculations complete.",
                    fg="green"
                ))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Run All Error", f"❌ {e}"
                ))
                self.root.after(0, lambda: self.info_label.config(text=f"❌ Error: {e}", fg="red"))

        # Run the entire pipeline in ONE background thread
        threading.Thread(target=task, daemon=True).start()


    # ==============================================================
    # Close
    # ==============================================================
    def on_close(self):
        self._stop_unwrap = True
        if self.unwrap_thread and self.unwrap_thread.is_alive():
            try:
                self.unwrap_thread.join(timeout=1)
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)  # ensure process ends fully

    # ==============================================================
    # Run GUI
    # ==============================================================
    def run(self):
        """Run this window without blocking other code."""
        self.root.after(100, lambda: None)
        self.root.mainloop()


# ==============================================================
# Callable wrapper function
# ==============================================================
def image_processing_gui():
    """
    Launch the Image Processing GUI.
    Can be imported and called from another script.
    """
    app = ImageProcessingApp()
    app.run()


# ==============================================================
# Standalone entry
# ==============================================================
if __name__ == "__main__":
    image_processing_gui()
