import os
import glob
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

def crop_tiff_images_series(folder=None, series_prefix="", show_message=True):
    """
    Interactive square-crop tool.

    - Preview always uses the first *_000.tiff image.
    - "Crop Intensity" crops files like *_[0-9][0-9][0-9].tiff.
    - "Crop Combined" crops files like *_combined.tiff.
    - "Crop All" crops both patterns.
    Returns crop_coords in original image pixels [x1, y1, x2, y2] or None.
    """
    # --- Ask user for folder if not provided ---
    if folder is None:
        base_dir = os.path.join(os.getcwd(), "ESPI_Images")

        filepath = filedialog.askopenfilename(
            title="Select any TIFF image from the target folder",
            initialdir=base_dir,
            filetypes=[("TIFF files", "*.tiff"), ("All files", "*.*")]
        )

        if not filepath:
            return

        folder = os.path.dirname(filepath)


    # --- Patterns ---
    pattern_000 = os.path.join(folder, f"{series_prefix}*_000.tiff") if series_prefix else os.path.join(folder, "*_000.tiff")
    pattern_intensity = os.path.join(folder, f"{series_prefix}*_[0-9][0-9][0-9].tiff") if series_prefix else os.path.join(folder, "*_[0-9][0-9][0-9].tiff")

    intensity_paths = sorted(glob.glob(pattern_intensity))

    # --- Always use the _000 image for preview ---
    zero_paths = sorted(glob.glob(pattern_000))
    if not zero_paths:
        messagebox.showerror("Error", f"No '_000.tiff' image found in:\n{folder}")
        return None

    first_image_path = zero_paths[0]

    # --- Load preview image and get original size ---
    img = Image.open(first_image_path)
    orig_w, orig_h = img.size

    # --- Prepare Tk window ---
    root = tk.Toplevel() if tk._default_root else tk.Tk()
    root.title("Draw, Move, or Resize Square Crop Area — Preview (_000 image)")
    root.geometry("")

    # --- Normalize 16-bit to 8-bit if needed ---
    if img.mode in ("I;16", "I"):
        img_np = np.array(img)
        img_np = (255 * (img_np - img_np.min()) / (img_np.ptp() + 1e-5)).astype("uint8")
        img = Image.fromarray(img_np)
    img = img.convert("L")

    # --- Compute display size ---
    root.update_idletasks()
    screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
    max_w, max_h = int(screen_w * 0.8), int(screen_h * 0.8)

    downsample_factor = 2
    small_w, small_h = max(1, orig_w // downsample_factor), max(1, orig_h // downsample_factor)
    img_small = img.resize((small_w, small_h), Image.Resampling.LANCZOS)

    scale_factor = min(max_w / small_w, max_h / small_h)
    disp_w, disp_h = max(1, int(small_w * scale_factor)), max(1, int(small_h * scale_factor))
    disp_img = img_small.resize((disp_w, disp_h), Image.Resampling.NEAREST)

    # --- Canvas and image ---
    tk_img = ImageTk.PhotoImage(disp_img)
    canvas = tk.Canvas(root, width=disp_w, height=disp_h, cursor="cross")
    canvas.pack()
    canvas.create_image(0, 0, anchor="nw", image=tk_img)
    canvas.image = tk_img
    root.tk_img = tk_img

    # --- Crop rectangle state ---
    rect = None
    handles = []
    start_x = start_y = 0
    active_handle = None
    move_start = None
    handle_size = 6

    # --- Helper functions ---
    def create_handles(x1, y1, x2, y2):
        nonlocal handles
        for h in handles:
            canvas.delete(h)
        handles = []
        coords = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        for cx, cy in coords:
            h = canvas.create_rectangle(cx - handle_size, cy - handle_size, cx + handle_size, cy + handle_size,
                                       fill="red", outline="black")
            handles.append(h)

    def point_in_rect(x, y, x1, y1, x2, y2):
        return x1 <= x <= x2 and y1 <= y <= y2

    def detect_handle(event):
        for i, h in enumerate(handles):
            hx1, hy1, hx2, hy2 = canvas.coords(h)
            if point_in_rect(event.x, event.y, hx1, hy1, hx2, hy2):
                return i
        return None

    # --- Mouse events ---
    def on_button_press(event):
        nonlocal rect, start_x, start_y, active_handle, move_start
        start_x, start_y = event.x, event.y
        active_handle = detect_handle(event)

        if rect:
            x1, y1, x2, y2 = canvas.coords(rect)
            if active_handle is None and point_in_rect(event.x, event.y, x1, y1, x2, y2):
                move_start = (event.x, event.y)
                return
            if not point_in_rect(event.x, event.y, x1, y1, x2, y2):
                canvas.delete(rect)
                for h in handles:
                    canvas.delete(h)
                handles.clear()
                rect = None

        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

    def on_move_press(event):
        nonlocal rect, move_start, active_handle
        if not rect:
            return
        x1, y1, x2, y2 = canvas.coords(rect)

        if active_handle is not None:
            hi = active_handle
            if hi == 0:
                x1, y1 = event.x, event.y
            elif hi == 1:
                x2, y1 = event.x, event.y
            elif hi == 2:
                x2, y2 = event.x, event.y
            elif hi == 3:
                x1, y2 = event.x, event.y

            side = min(abs(x2 - x1), abs(y2 - y1))
            if (x2 >= x1) and (y2 >= y1):
                x2 = x1 + side
                y2 = y1 + side
            elif (x2 < x1) and (y2 >= y1):
                x1 = x2 + side
                y2 = y1 + side
            elif (x2 >= x1) and (y2 < y1):
                x2 = x1 + side
                y1 = y2 + side
            else:
                x1 = x2 + side
                y1 = y2 + side

            canvas.coords(rect, x1, y1, x2, y2)
            create_handles(x1, y1, x2, y2)

        elif move_start:
            dx = event.x - move_start[0]
            dy = event.y - move_start[1]
            canvas.move(rect, dx, dy)
            for h in handles:
                canvas.move(h, dx, dy)
            move_start = (event.x, event.y)
        else:
            side = min(abs(event.x - start_x), abs(event.y - start_y))
            x2 = start_x + side if event.x >= start_x else start_x - side
            y2 = start_y + side if event.y >= start_y else start_y - side
            canvas.coords(rect, start_x, start_y, x2, y2)
            create_handles(start_x, start_y, x2, y2)

    def on_button_release(event):
        nonlocal active_handle, move_start
        active_handle = None
        move_start = None

    # --- Crop/save helpers ---
    def crop_and_save(paths, crop_coords_local):
        saved_paths = []
        for path in paths:
            try:
                image = Image.open(path)
                cropped = image.crop(tuple(crop_coords_local))
                folder_name, name = os.path.split(path)
                name_no_ext, ext = os.path.splitext(name)

                if name_no_ext.endswith("_combined"):
                    base_name = name_no_ext[:-9]
                else:
                    base_name = name_no_ext

                crop_num = 1
                save_path = os.path.join(folder_name, f"crop{crop_num}_{base_name}{ext}")
                while os.path.exists(save_path):
                    crop_num += 1
                    save_path = os.path.join(folder_name, f"crop{crop_num}_{base_name}{ext}")

                cropped.save(save_path)
                saved_paths.append(save_path)
                print(f"✅ Saved: {save_path}")
            except Exception as e:
                print(f"[WARN] Failed to crop {path}: {e}")
        return saved_paths

    def perform_crop_for_pattern(pattern_glob):
        if rect is None:
            messagebox.showwarning("No Selection", "Please draw a square crop area first.", parent=root)
            return
        x1, y1, x2, y2 = canvas.coords(rect)
        crop_coords_local = [
            int(min(x1, x2) / scale_factor * downsample_factor),
            int(min(y1, y2) / scale_factor * downsample_factor),
            int(max(x1, x2) / scale_factor * downsample_factor),
            int(max(y1, y2) / scale_factor * downsample_factor),
        ]
        paths = sorted(glob.glob(os.path.join(folder, pattern_glob)))
        if not paths:
            messagebox.showwarning("No Images Found", f"No images found for pattern '{pattern_glob}' in folder.", parent=root)
            return
        saved = crop_and_save(paths, crop_coords_local)
        if show_message:
            messagebox.showinfo("Crop Complete", f"Cropped {len(saved)} images.", parent=root)
        return saved


    def crop_all():
        patterns = []
        patterns.append(f"{series_prefix}*_[0-9][0-9][0-9].tiff" if series_prefix else "*_[0-9][0-9][0-9].tiff")
        all_paths = []
        for p in patterns:
            all_paths.extend(sorted(glob.glob(os.path.join(folder, p))))
        if not all_paths:
            messagebox.showwarning("No Images Found", "No intensity images found to crop.", parent=root)
            return
        if rect is None:
            messagebox.showwarning("No Selection", "Please draw a square crop area first.", parent=root)
            return
        x1, y1, x2, y2 = canvas.coords(rect)
        crop_coords_local = [
            int(min(x1, x2) / scale_factor * downsample_factor),
            int(min(y1, y2) / scale_factor * downsample_factor),
            int(max(x1, x2) / scale_factor * downsample_factor),
            int(max(y1, y2) / scale_factor * downsample_factor),
        ]
        saved = crop_and_save(all_paths, crop_coords_local)
        if show_message:
            messagebox.showinfo("Crop Complete", f"Cropped {len(saved)} images.", parent=root)
        return saved

    # --- Buttons ---
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    btn_all = tk.Button(btn_frame, text="Crop All", command=crop_all)
    btn_all.pack(side="left", padx=5)


    # --- Bind events ---
    canvas.bind("<ButtonPress-1>", on_button_press)
    canvas.bind("<B1-Motion>", on_move_press)
    canvas.bind("<ButtonRelease-1>", on_button_release)

    # --- Main loop ---
    root.mainloop()

    if rect:
        x1, y1, x2, y2 = canvas.coords(rect)
        crop_coords = [
            int(min(x1, x2) / scale_factor * downsample_factor),
            int(min(y1, y2) / scale_factor * downsample_factor),
            int(max(x1, x2) / scale_factor * downsample_factor),
            int(max(y1, y2) / scale_factor * downsample_factor),
        ]
        return crop_coords
    return None


if __name__ == "__main__":
    crop_tiff_images_series()