import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np


def crop_multiple_tiffs():

    # --- Select files ---
    filepaths = filedialog.askopenfilenames(
        title="Select TIFF images",
        filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
    )

    if not filepaths:
        return

    # --- Verify all images same size ---
    first_img = Image.open(filepaths[0])
    orig_w, orig_h = first_img.size

    for fp in filepaths[1:]:
        test_img = Image.open(fp)

        if test_img.size != (orig_w, orig_h):
            messagebox.showerror(
                "Size Mismatch",
                f"Image has different size:\n{os.path.basename(fp)}"
            )
            return

    # --- Display image = first image ---
    img_np = np.array(first_img).astype(np.float32)

    # --- CONTRAST ENHANCEMENT ---
    p_low, p_high = np.percentile(img_np, (1, 99))

    img_np = np.clip(img_np, p_low, p_high)
    img_np = (img_np - p_low) / (p_high - p_low + 1e-8)
    img_np = (img_np * 255).astype(np.uint8)

    img = Image.fromarray(img_np).convert("L")

    # --- Window ---
    root = tk.Tk()
    root.title("TIFF Crop Tool (Batch Crop)")

    screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
    max_w, max_h = int(screen_w * 0.8), int(screen_h * 0.8)

    scale = min(max_w / orig_w, max_h / orig_h)
    min_scale, max_scale = 0.2, 10.0

    offset_x = 0
    offset_y = 0

    canvas_w, canvas_h = int(orig_w * scale), int(orig_h * scale)

    canvas = tk.Canvas(
        root,
        width=canvas_w,
        height=canvas_h,
        cursor="cross"
    )

    canvas.pack(expand=True, fill="both")

    # --- Initial rectangle ---
    rect = [
        orig_w * 0.25,
        orig_h * 0.25,
        orig_w * 0.75,
        orig_h * 0.75
    ]

    side_drag = None

    # =========================
    # DRAW
    # =========================
    def draw():

        canvas.delete("all")

        disp = img.resize(
            (int(orig_w * scale), int(orig_h * scale)),
            Image.Resampling.NEAREST
        )

        tk_img = ImageTk.PhotoImage(disp)
        canvas.tk_img = tk_img

        canvas.create_image(
            offset_x,
            offset_y,
            anchor="nw",
            image=tk_img
        )

        x1, y1, x2, y2 = rect

        x1 = x1 * scale + offset_x
        y1 = y1 * scale + offset_y
        x2 = x2 * scale + offset_x
        y2 = y2 * scale + offset_y

        canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="red",
            width=2
        )

        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

        canvas.create_line(x1, cy, x2, cy, fill="red")
        canvas.create_line(cx, y1, cx, y2, fill="red")

    draw()

    # =========================
    # DETECT SIDE
    # =========================
    def get_side(event):

        x = (event.x - offset_x) / scale
        y = (event.y - offset_y) / scale

        tol = 5 / scale

        x1, y1, x2, y2 = rect

        if abs(x - x1) < tol:
            return "left"

        if abs(x - x2) < tol:
            return "right"

        if abs(y - y1) < tol:
            return "top"

        if abs(y - y2) < tol:
            return "bottom"

        return None

    # =========================
    # MOUSE EVENTS
    # =========================
    def press(event):
        nonlocal side_drag
        side_drag = get_side(event)

    def move(event):

        nonlocal rect

        if not side_drag:
            return

        x = (event.x - offset_x) / scale
        y = (event.y - offset_y) / scale

        x1, y1, x2, y2 = rect

        min_size = 5

        if side_drag == "left":
            x1 = min(x, x2 - min_size)

        elif side_drag == "right":
            x2 = max(x, x1 + min_size)

        elif side_drag == "top":
            y1 = min(y, y2 - min_size)

        elif side_drag == "bottom":
            y2 = max(y, y1 + min_size)

        rect = [x1, y1, x2, y2]

        draw()

    def release(event):
        nonlocal side_drag
        side_drag = None

    # =========================
    # ZOOM
    # =========================
    def zoom(event):

        nonlocal scale, offset_x, offset_y

        factor = 1.1 if event.delta > 0 else 0.9
        new_scale = scale * factor

        if min_scale <= new_scale <= max_scale:

            mx = canvas.canvasx(event.x)
            my = canvas.canvasy(event.y)

            offset_x = mx - ((mx - offset_x) / scale) * new_scale
            offset_y = my - ((my - offset_y) / scale) * new_scale

            scale = new_scale

            draw()

    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", move)
    canvas.bind("<ButtonRelease-1>", release)
    canvas.bind("<MouseWheel>", zoom)

    # =========================
    # SAVE CROPPED IMAGES
    # =========================
    def save():

        x1, y1, x2, y2 = map(int, rect)

        saved_count = 0

        try:

            for filepath in filepaths:

                folder, name = os.path.split(filepath)
                name_no_ext, ext = os.path.splitext(name)

                im = Image.open(filepath)

                cropped = im.crop((x1, y1, x2, y2))

                save_path = os.path.join(
                    folder,
                    f"crop_{name_no_ext}{ext}"
                )

                i = 1

                while os.path.exists(save_path):

                    save_path = os.path.join(
                        folder,
                        f"crop{i}_{name_no_ext}{ext}"
                    )

                    i += 1

                cropped.save(save_path)

                print("Saved:", save_path)

                saved_count += 1

            messagebox.showinfo(
                "Saved",
                f"Cropped and saved {saved_count} images."
            )

        except Exception as e:

            messagebox.showerror("Error", str(e))

    btn = tk.Button(
        root,
        text="Crop & Save All",
        command=save
    )

    btn.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    crop_multiple_tiffs()