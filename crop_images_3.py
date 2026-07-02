# crop_images_3.py

import os
import glob
import numpy as np
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk

def crop_tiff_img_series_rect(folder=None, series_prefix="", show_message=True, squareboolean=True):
    # --- File selection: single or multiple ---
    filepaths = filedialog.askopenfilenames(
        title="Select TIFF image(s) from the target folder",
        initialdir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ESPI_Images", "1_RAW_new_images")),
        filetypes=[("TIFF files", "*.tiff"), ("All files", "*.*")]
    )
    if not filepaths:
        return

    folder = os.path.dirname(filepaths[0])
    first_image_path = filepaths[0]  # preview image

    # --- Determine which images to crop ---
    if len(filepaths) == 1:
        first_image_name = os.path.basename(first_image_path)
        exp_name = first_image_name.split("_")[0]
        all_files = glob.glob(os.path.join(folder, "*.tiff"))
        crop_paths = [
            f for f in all_files
            if len(os.path.basename(f).split("_")) == 3
               and os.path.basename(f).split("_")[0] == exp_name
        ]
    else:
        crop_paths = list(filepaths)

    if not crop_paths:
        messagebox.showwarning("No Images Found", "No intensity images found.", parent=None)
        return

    # --- Load preview image ---
    img = Image.open(first_image_path)
    orig_w, orig_h = img.size

    # --- 🔥 Contrast enhancement (better for displacement maps) ---
    img_np = np.array(img).astype(np.float32)
    p_low, p_high = np.percentile(img_np, (1, 99))
    img_np = np.clip(img_np, p_low, p_high)
    img_np = (img_np - p_low) / (p_high - p_low + 1e-8)
    img_np = (img_np * 255).astype("uint8")
    img = Image.fromarray(img_np).convert("L")

    # --- Tkinter window ---
    root = tk.Toplevel() if tk._default_root else tk.Tk()
    root.title(f"{'Square' if squareboolean else 'Rectangle'} Crop Tool")

    screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
    max_w, max_h = int(screen_w * 0.8), int(screen_h * 0.8)

    scale = min(max_w / orig_w, max_h / orig_h)
    min_scale, max_scale = 0.2, 10.0
    offset_x = 0
    offset_y = 0

    # --- Canvas ---
    canvas_w, canvas_h = int(orig_w * scale), int(orig_h * scale)
    canvas = tk.Canvas(root, width=canvas_w, height=canvas_h, cursor="cross")
    canvas.pack(expand=True, fill="both")

    # --- Initial selection ---
    if squareboolean:
        side_len = min(orig_w, orig_h) // 2
        cx, cy = orig_w // 2, orig_h // 2
        rect = [cx - side_len // 2, cy - side_len // 2, cx + side_len // 2, cy + side_len // 2]
    else:
        rect = [orig_w * 0.25, orig_h * 0.25, orig_w * 0.75, orig_h * 0.75]

    side_being_dragged = None

    # --- Draw everything ---
    def draw_canvas():
        canvas.delete("all")
        disp_img = img.resize((int(orig_w * scale), int(orig_h * scale)), Image.Resampling.NEAREST)
        tk_img = ImageTk.PhotoImage(disp_img)
        canvas.tk_img = tk_img
        canvas.create_image(offset_x, offset_y, anchor="nw", image=tk_img)

        x1, y1, x2, y2 = [coord * scale + offset for coord, offset in zip(rect, [offset_x, offset_y, offset_x, offset_y])]
        canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)

        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        canvas.create_line(x1, cy, x2, cy, fill="red", width=1)
        canvas.create_line(cx, y1, cx, y2, fill="red", width=1)

    draw_canvas()

    # --- Detect side ---
    def get_side_under_cursor(event):
        x = (event.x - offset_x) / scale
        y = (event.y - offset_y) / scale
        threshold = 5 / scale
        x1, y1, x2, y2 = rect
        if abs(x - x1) <= threshold: return "left"
        if abs(x - x2) <= threshold: return "right"
        if abs(y - y1) <= threshold: return "top"
        if abs(y - y2) <= threshold: return "bottom"
        return None

    # --- Mouse events ---
    def on_button_press(event):
        nonlocal side_being_dragged
        side_being_dragged = get_side_under_cursor(event)

    def on_move(event):
        nonlocal rect
        if not side_being_dragged:
            return

        x = (event.x - offset_x) / scale
        y = (event.y - offset_y) / scale
        x1, y1, x2, y2 = rect
        min_size = 5

        if squareboolean:
            # --- ORIGINAL square behavior ---
            if side_being_dragged == "left":
                cy = (y1 + y2) / 2
                size = x2 - x
                rect = [x2 - size, cy - size / 2, x2, cy + size / 2]

            elif side_being_dragged == "right":
                cy = (y1 + y2) / 2
                size = x - x1
                rect = [x1, cy - size / 2, x1 + size, cy + size / 2]

            elif side_being_dragged == "top":
                cx = (x1 + x2) / 2
                size = y2 - y
                rect = [cx - size / 2, y2 - size, cx + size / 2, y2]

            elif side_being_dragged == "bottom":
                cx = (x1 + x2) / 2
                size = y - y1
                rect = [cx - size / 2, y1, cx + size / 2, y1 + size]

        else:
            # --- RECTANGLE mode ---
            if side_being_dragged == "left":
                x1 = min(x, x2 - min_size)
            elif side_being_dragged == "right":
                x2 = max(x, x1 + min_size)
            elif side_being_dragged == "top":
                y1 = min(y, y2 - min_size)
            elif side_being_dragged == "bottom":
                y2 = max(y, y1 + min_size)

            rect = [x1, y1, x2, y2]

        draw_canvas()

    def on_release(event):
        nonlocal side_being_dragged
        side_being_dragged = None

    def on_mouse_wheel(event):
        nonlocal scale, offset_x, offset_y
        factor = 1.1 if event.delta > 0 else 0.9
        new_scale = scale * factor
        if min_scale <= new_scale <= max_scale:
            mouse_x = canvas.canvasx(event.x)
            mouse_y = canvas.canvasy(event.y)
            offset_x = mouse_x - ((mouse_x - offset_x) / scale) * new_scale
            offset_y = mouse_y - ((mouse_y - offset_y) / scale) * new_scale
            scale = new_scale
            draw_canvas()

    canvas.bind("<ButtonPress-1>", on_button_press)
    canvas.bind("<B1-Motion>", on_move)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<MouseWheel>", on_mouse_wheel)

    # --- Crop button ---
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    def crop_and_save():
        crop_coords = [int(c) for c in rect]

        for path in crop_paths:
            try:
                image = Image.open(path)
                cropped = image.crop(tuple(crop_coords))

                folder_name, name = os.path.split(path)
                name_no_ext, ext = os.path.splitext(name)
                base_name = name_no_ext.replace("_combined", "")

                crop_num = 1
                save_path = os.path.join(folder_name, f"crop{crop_num}_{base_name}{ext}")

                while os.path.exists(save_path):
                    crop_num += 1
                    save_path = os.path.join(folder_name, f"crop{crop_num}_{base_name}{ext}")

                cropped.save(save_path)
                print("Saved:", save_path)

            except Exception as e:
                print("Crop failed:", path, e)

        if show_message:
            messagebox.showinfo("Crop Complete", f"Cropped {len(crop_paths)} images.", parent=root)

    tk.Button(btn_frame, text="Crop All", command=crop_and_save).pack(side="left", padx=5)

    root.mainloop()
    return rect


if __name__ == "__main__":
    # 🔁 Toggle here:
    crop_box = crop_tiff_img_series_rect(squareboolean=False)
    print("Selected crop region:", crop_box)