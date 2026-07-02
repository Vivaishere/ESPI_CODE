import os
import tkinter as tk
from tkinter import filedialog

# -----------------------------
# FILE PICKER
# -----------------------------
root = tk.Tk()
root.withdraw()

input_file = filedialog.askopenfilename(
    title="Select G-code file",
    filetypes=[("G-code files", "*.gcode"), ("All files", "*.*")]
)

if not input_file:
    raise Exception("No file selected")

output_file = os.path.join(
    os.path.dirname(input_file),
    "modified_" + os.path.basename(input_file)
)

# -----------------------------
# READ FILE
# -----------------------------
with open(input_file, "r") as f:
    content = f.read()

# -----------------------------
# REPLACE
# -----------------------------
content = content.replace("E165", "E170")

# -----------------------------
# WRITE OUTPUT
# -----------------------------
with open(output_file, "w") as f:
    f.write(content)

print("Modified file saved to:", output_file)