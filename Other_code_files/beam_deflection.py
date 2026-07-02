"""
3-POINT BENDING: MASS vs CENTRAL DEFLECTION (THEORETICAL)
---------------------------------------------------------

This script computes and plots the small-deflection prediction
for a 3-point bending specimen under a central load.

Geometry uses ASTM D5045 values:
- width b  = 1.2 cm  (0.012 m)
- height h = 2.4 cm  (0.024 m)
- support span L = 9.6 cm (0.096 m)

The formula used is the classical small-deflection expression:

        δ = F * L^3 / (48 * E * I)

where:
    δ = central deflection (m)
    F = applied force (N)
    L = support span (m)
    E = Young's modulus (Pa)
    I = second moment of area (m^4), I = b h^3 / 12
"""

# ------------------------------ Imports ------------------------------
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

# --------------------------- Constants -------------------------------
L = 0.096           # support span (m)
b = 0.012           # width (m)
h = 0.024           # height (m)

E_GPa = 1.42        # Young's modulus (GPa)
E = E_GPa * 1e9     # Pa

# -------------------- Second Moment of Area --------------------------
I = b * h**3 / 12.0

# -------------------- Force Range ------------------------------------
F_max = 500.0                       # N
forces = np.linspace(0, F_max, 201)

# -------------------- Deflection Calculation -------------------------
def deflection_from_force(F):
    """Return deflection in micrometres for a given force (N)."""
    delta_m = F * L**3 / (48 * E * I)
    return delta_m * 1e6  # µm

delta_um = deflection_from_force(forces)

# -------------------- Tkinter Window ---------------------------------
root = tk.Tk()
root.title("3-Point Bending – Force vs Deflection (PETG)")
root.geometry("1100x750")

def on_close():
    plt.close("all")
    root.quit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

root.columnconfigure(0, weight=0)
root.columnconfigure(1, weight=0)
root.columnconfigure(2, weight=1)
root.rowconfigure(0, weight=1)

# -------------------- Plot Figure ------------------------------------
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(forces, delta_um, linewidth=2)

# Initial marker force
F0 = 50.0  # N
marker_point, = ax.plot(F0, deflection_from_force(F0), "ro", markersize=8)

ax.set_xlabel("Force (N)", fontsize=12)
ax.set_ylabel("Central Deflection (µm)", fontsize=12)
ax.set_title("3-Point Bending: Force vs Deflection (PETG)", fontsize=14)
ax.grid(True)
ax.set_xlim(0, F_max)
ax.set_ylim(0, deflection_from_force(F_max))

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()
canvas.get_tk_widget().grid(
    row=0, column=0, columnspan=3,
    padx=20, pady=20, sticky="nsew"
)

root.rowconfigure(0, weight=10)

# -------------------- Force Input & Display ---------------------------
def compute_deflection():
    try:
        F = float(entry_force.get())
        F = max(0, min(F_max, F))
        delta_val = deflection_from_force(F)
        result_label.config(text=f"Deflection: {delta_val:.3f} µm")
        marker_point.set_data([F], [delta_val])
        canvas.draw()
    except ValueError:
        result_label.config(text="Enter a valid number.")

ttk.Label(root, text="Force (N):", font=("Arial", 14)).grid(
    row=1, column=0, padx=5, pady=15, sticky="e"
)

entry_force_var = tk.StringVar()
entry_force = ttk.Entry(root, width=10, font=("Arial", 14),
                        textvariable=entry_force_var)
entry_force.grid(row=1, column=1, padx=5, pady=15, sticky="w")

result_label = ttk.Label(
    root, text="Deflection: --- µm", font=("Arial", 14)
)
result_label.grid(row=1, column=2, padx=10, pady=15, sticky="w")

def on_entry_change(*args):
    compute_deflection()

entry_force_var.trace_add("write", on_entry_change)

# -------------------- Mouse Drag Logic --------------------------------
dragging = False

def on_plot_press(event):
    global dragging
    if event.inaxes != ax:
        return
    dragging = True

def on_plot_release(event):
    global dragging
    dragging = False

def on_plot_motion(event):
    if not dragging or event.inaxes != ax:
        return
    F = max(0, min(F_max, event.xdata))
    entry_force_var.set(f"{F:.2f}")
    delta_val = deflection_from_force(F)
    marker_point.set_data([F], [delta_val])
    result_label.config(text=f"Deflection: {delta_val:.3f} µm")
    canvas.draw()

fig.canvas.mpl_connect("button_press_event", on_plot_press)
fig.canvas.mpl_connect("button_release_event", on_plot_release)
fig.canvas.mpl_connect("motion_notify_event", on_plot_motion)

# -------------------- Initialize -------------------------------------
entry_force_var.set(f"{F0:.2f}")
compute_deflection()

# -------------------- Run --------------------------------------------
root.mainloop()
