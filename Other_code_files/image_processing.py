# ==============================================================
# image_processing.py
# Callable GUI for ESPI image analysis workflow
# ==============================================================

import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
from filter_and_subtract import filter_and_subtract
from phase_unwrap import unwrap_all_filter_images
from displacement import get_displacement


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

        self.unwrap_thread = None
        self.exp_folder = None  # remembered experiment folder

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

        self.filter_button = tk.Button(
            btn_frame, text="Filter and Subtract", command=self.run_filter_and_subtract
        )
        self.unwrap_button = tk.Button(
            btn_frame, text="Phase Unwrap", command=self.run_phase_unwrap
        )
        self.displacement_button = tk.Button(
            btn_frame, text="Get Displacement", command=self.run_displacement
        )

        for btn in (
            self.filter_button,
            self.unwrap_button,
            self.displacement_button,
        ):
            btn.pack(side=tk.LEFT, padx=8)

        # -------------------------
        # Info label
        # -------------------------
        self.info_label = tk.Label(
            self.root,
            text="Use 'Filter and Subtract' to begin, or run steps individually.",
            fg="gray"
        )
        self.info_label.pack(pady=20)

        # -------------------------
        # Close button
        # -------------------------
        tk.Button(self.root, text="Close", command=self.on_close).pack(
            side=tk.BOTTOM, pady=15
        )
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ==============================================================
    # Helper: Ask for experiment folder if needed
    # ==============================================================
    def ensure_experiment_folder(self):
        """
        Ensure self.exp_folder is set.
        If not, prompt the user to select a folder.
        Returns True if a folder is available, False otherwise.
        """
        if self.exp_folder and os.path.isdir(self.exp_folder):
            return True

        folder = filedialog.askdirectory(
            title="Select Experiment Folder",
            initialdir=os.getcwd()
        )

        if not folder:
            return False  # user cancelled

        self.exp_folder = folder
        self.info_label.config(
            text=f"Experiment folder:\n{self.exp_folder}",
            fg="blue"
        )
        return True

    # ==============================================================
    # Filter and Subtract (MAIN THREAD)
    # ==============================================================
    def run_filter_and_subtract(self):
        try:
            self.info_label.config(
                text="Filtering and subtracting...",
                fg="orange"
            )
            self.root.update_idletasks()

            result_path = filter_and_subtract()

            # Remember folder from result
            self.exp_folder = os.path.dirname(result_path)

            self.info_label.config(
                text=f"✅ Filtering and Subtracting Completed\n{self.exp_folder}",
                fg="green"
            )

            messagebox.showinfo(
                "Success",
                "Filtered and subtracted phase image created successfully."
            )

        except Exception as e:
            messagebox.showerror("Error", f"Error during filtering:\n{e}")
            self.info_label.config(
                text=f"❌ Error during filtering:\n{e}",
                fg="red"
            )

    # ==============================================================
    # Phase Unwrap
    # ==============================================================
    def run_phase_unwrap(self):
        if not self.ensure_experiment_folder():
            return

        self.info_label.config(
            text=f"Unwrapping all 'filter#' images in:\n{self.exp_folder}",
            fg="orange",
        )

        def unwrap_task():
            try:
                count = unwrap_all_filter_images(self.exp_folder) or 0

                if count == 0:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "No Images Found",
                        "⚠️ No matching '*_filter#.tiff' images found."
                    ))
                    self.root.after(0, lambda: self.info_label.config(
                        text="⚠️ No matching images found to unwrap.",
                        fg="red"
                    ))
                else:
                    self.root.after(0, lambda: self.info_label.config(
                        text=f"✅ Phase unwrapping complete. ({count} images processed)",
                        fg="green",
                    ))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error During Unwrapping", f"❌ {e}"
                ))
                self.root.after(0, lambda: self.info_label.config(
                    text=f"❌ Error during unwrapping:\n{e}",
                    fg="red"
                ))

        self.unwrap_thread = threading.Thread(target=unwrap_task, daemon=True)
        self.unwrap_thread.start()

    # ==============================================================
    # Displacement
    # ==============================================================
    def run_displacement(self):
        if not self.ensure_experiment_folder():
            return

        self.info_label.config(
            text=f"Processing all '_UW.tiff' images in:\n{self.exp_folder}",
            fg="orange",
        )

        def displacement_task():
            try:
                count = get_displacement(self.exp_folder) or 0

                if count == 0:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "No Images Found",
                        "⚠️ No '_UW.tiff' images found."
                    ))
                    self.root.after(0, lambda: self.info_label.config(
                        text="⚠️ No matching images found to process.",
                        fg="red"
                    ))
                else:
                    self.root.after(0, lambda: self.info_label.config(
                        text=f"✅ Displacement processing complete. ({count} images processed)",
                        fg="green",
                    ))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error During Displacement", f"❌ {e}"
                ))
                self.root.after(0, lambda: self.info_label.config(
                    text=f"❌ Error during displacement:\n{e}",
                    fg="red"
                ))

        threading.Thread(target=displacement_task, daemon=True).start()

    # ==============================================================
    # Close
    # ==============================================================
    def on_close(self):
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    # ==============================================================
    # Run GUI
    # ==============================================================
    def run(self):
        self.root.mainloop()


# ==============================================================
# Callable wrapper function
# ==============================================================
def image_processing_gui():
    app = ImageProcessingApp()
    app.run()


# ==============================================================
# Standalone entry
# ==============================================================
if __name__ == "__main__":
    image_processing_gui()
