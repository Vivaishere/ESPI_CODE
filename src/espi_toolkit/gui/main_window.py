"""Main Tkinter window for ESPI Control Center."""

from __future__ import annotations

import queue
import threading
import textwrap
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from espi_toolkit.core.config import load_config, save_config
from espi_toolkit.core.state import AppState
from espi_toolkit.processing.operations import (
    get_operation_defs,
    get_shared_param_defs,
    launch_acquisition_subprocess,
)


class ESPIControlCenterApp:
    """Single-window control center for ESPI acquisition and processing."""

    def __init__(self) -> None:
        self.project_root = Path.cwd()
        self.state = AppState()
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._worker_alive = False
        self._operation_buttons: list[ttk.Button] = []

        self.root = tk.Tk()
        self.root.title("ESPI Control Center")
        self.root.geometry("1220x800")
        self.root.minsize(1220, 800)

        # Custom style for section headings and borders
        self.style = ttk.Style(self.root)

        self.style.configure(
            "Black.TLabelframe.Label",
            foreground="black",
            font=("Segoe UI", 12, "bold")
        )

        self.shared_defs = get_shared_param_defs()
        self.operations = get_operation_defs()

        self.shared_vars: dict[str, tk.StringVar] = {}
        self.operation_unique_vars: dict[str, dict[str, tk.StringVar]] = {}

        self._build_scrollable_layout()
        self._build_header()
        self._build_acquisition_section()
        self._build_working_directory_section()
        self._build_shared_parameter_section()
        self._build_section_d_operations()
        self._build_section_e_operations()
        self._build_status_section()

        self._load_state_from_config()
        self._poll_worker_queue()

    def run(self) -> None:
        """Run Tkinter mainloop."""
        self.root.mainloop()

    def _build_scrollable_layout(self) -> None:
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.vbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)

        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_content_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_header(self) -> None:
        title = ttk.Label(self.content, text="ESPI Control Center", font=("Segoe UI", 20, "bold"))
        title.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 8))

    def _build_section_title(self, row: int, text: str) -> int:
        lbl = ttk.Label(self.content, text=text, font=("Segoe UI", 12, "bold"))
        lbl.grid(row=row, column=0, sticky="w", padx=14, pady=(10, 2))
        return row + 1

    def _build_acquisition_section(self) -> None:
        frame = ttk.LabelFrame(self.content, text="Section A: Image Acquisition", style="Black.TLabelframe")
        frame.grid(row=1, column=0, sticky="ew", padx=14, pady=8)
        frame.columnconfigure(0, weight=1) 

        self.launch_button = ttk.Button(
            frame,
            text="Launch Image Acquisition",
            command=self._launch_acquisition,
        )
        self.launch_button.grid(row=0, column=0, sticky="w", padx=10, pady=10)

    def _build_working_directory_section(self) -> None:
        frame = ttk.LabelFrame(self.content, text="Section B: Shared Working Directory", style="Black.TLabelframe")
        frame.grid(row=2, column=0, sticky="ew", padx=14, pady=8)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Working Directory:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.workdir_var = tk.StringVar(value="")
        self.workdir_entry = ttk.Entry(frame, textvariable=self.workdir_var)
        self.workdir_entry.grid(row=0, column=1, sticky="ew", padx=6, pady=10)

        browse_btn = ttk.Button(frame, text="Browse", command=self._browse_workdir)
        browse_btn.grid(row=1, column=0, sticky="w", padx=6, pady=(2, 10))

    
    def _build_shared_parameter_section(self) -> None:
        frame = ttk.LabelFrame(self.content, text="Section C: Shared Processing Parameters", style="Black.TLabelframe")
        frame.grid(row=3, column=0, sticky="ew", padx=14, pady=8)
        frame.columnconfigure(1, weight=1)

        for idx, pdef in enumerate(self.shared_defs):
            ttk.Label(frame, text=pdef.label).grid(
                row=idx * 2, column=0, sticky="w", padx=8, pady=4
            )

            var = tk.StringVar(value=str(pdef.default))
            self.shared_vars[pdef.key] = var

            ttk.Entry(frame, textvariable=var, width=24).grid(
                row=idx * 2, column=1, sticky="w", padx=6, pady=4
            )

            if pdef.help_text:
                ttk.Label(
                    frame,
                    text=pdef.help_text,
                    foreground="#555",
                    justify="left",
                    wraplength=700,
                ).grid(
                    row=idx * 2 + 1,
                    column=0,
                    columnspan=2,
                    sticky="w",
                    padx=8,
                    pady=(0, 6),
                )


    def _build_section_d_operations(self) -> None:
        frame = ttk.LabelFrame(self.content, text="Section D: Core Processing Functions", style="Black.TLabelframe")
        frame.grid(row=4, column=0, sticky="ew", padx=14, pady=8)
        self._build_operations_in_frame(frame, section_key="D")

    def _build_section_e_operations(self) -> None:
        frame = ttk.LabelFrame(self.content, text="Section E: Additional Plotting and Comparison Functions", style="Black.TLabelframe")
        frame.grid(row=5, column=0, sticky="ew", padx=14, pady=8)
        self._build_operations_in_frame(frame, section_key="E")

    def _build_operations_in_frame(self, frame: ttk.LabelFrame, section_key: str) -> None:
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        section_ops = [op for op in self.operations if op.section == section_key]

        grouped: dict[str, list] = {}
        for op in section_ops:
            grouped.setdefault(op.category, []).append(op)

        row_i = 0
        for category, ops in grouped.items():
            sep = ttk.Label(frame, text=category, font=("Segoe UI", 10, "bold"))
            sep.grid(row=row_i, column=0, columnspan=2, sticky="w", padx=8, pady=(10, 4))
            row_i += 1

            for op in ops:
                left = ttk.Frame(frame)
                left.grid(row=row_i, column=0, sticky="nw", padx=8, pady=6)

                btn = ttk.Button(left, text=op.label, command=lambda op_key=op.key: self._run_operation(op_key))
                btn.grid(row=0, column=0, sticky="w")
                self._operation_buttons.append(btn)

                desc = ttk.Label(
                    left,
                    text=self._wrap_text_by_line(op.description, width=100),
                    foreground="#444",
                    justify="left",
                    wraplength=520,
                )
                desc.grid(row=1, column=0, sticky="w", pady=(2, 0))

                right = ttk.Frame(frame)
                right.grid(row=row_i, column=1, sticky="ew", padx=8, pady=6)
                right.columnconfigure(1, weight=0)
                right.columnconfigure(2, weight=1)

                unique_vars: dict[str, tk.StringVar] = {}
                for up_idx, up in enumerate(op.unique_params):
                    ttk.Label(right, text=up.label).grid(row=up_idx, column=0, sticky="w", padx=(0, 6), pady=2)
                    v = tk.StringVar(value=str(up.default))
                    unique_vars[up.key] = v

                    if up.choices:
                        combo = ttk.Combobox(
                            right,
                            values=[str(c) for c in up.choices],
                            state="readonly",
                            textvariable=v,
                            width=20,
                        )
                        combo.grid(row=up_idx, column=1, sticky="w", pady=2)
                    else:
                        ttk.Entry(right, textvariable=v, width=22).grid(row=up_idx, column=1, sticky="w", pady=2)

                    ttk.Label(
                        right,
                        text=self._wrap_text_by_line(up.help_text, width=100),
                        foreground="#555",
                        justify="left",
                        wraplength=520,
                    ).grid(
                        row=up_idx,
                        column=2,
                        sticky="w",
                        padx=(8, 0),
                        pady=2,
                    )

                self.operation_unique_vars[op.key] = unique_vars
                row_i += 1

    def _build_status_section(self) -> None:
        frame = ttk.LabelFrame(self.content, text="Status / Progress / Errors")
        frame.grid(row=6, column=0, sticky="ew", padx=14, pady=(8, 14))
        frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(frame, textvariable=self.status_var).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))

        self.log_text = tk.Text(frame, height=10, wrap="word")
        self.log_text.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 10))

    def _load_state_from_config(self) -> None:
        cfg = load_config(self.project_root)

        workdir = cfg.get("working_directory", "")
        if workdir:
            self.workdir_var.set(workdir)
            self.state.working_directory = workdir

        shared_cfg = cfg.get("shared_params", {})
        for key, var in self.shared_vars.items():
            if key in shared_cfg:
                var.set(str(shared_cfg[key]))

        op_cfg = cfg.get("operation_params", {})
        for op_key, param_vars in self.operation_unique_vars.items():
            stored = op_cfg.get(op_key, {})
            for pkey, var in param_vars.items():
                if pkey in stored:
                    var.set(str(stored[pkey]))

    def _persist_state(self) -> None:
        cfg = {
            "working_directory": self.workdir_var.get().strip(),
            "shared_params": {k: v.get().strip() for k, v in self.shared_vars.items()},
            "operation_params": {
                op_key: {k: v.get().strip() for k, v in vars_map.items()}
                for op_key, vars_map in self.operation_unique_vars.items()
            },
        }
        save_config(self.project_root, cfg)

    def _browse_workdir(self) -> None:
        initial = self.workdir_var.get().strip() or str(self.project_root)
        folder = filedialog.askdirectory(title="Select ESPI working directory", initialdir=initial)
        if folder:
            self.workdir_var.set(folder)
            self.status_var.set("Working directory selected")
            self._persist_state()

    def _validate_workdir(self) -> str:
        wd = self.workdir_var.get().strip()
        if not wd:
            raise ValueError("No working directory selected.")
        p = Path(wd)
        if not p.exists() or not p.is_dir():
            raise ValueError(f"Working directory does not exist: {wd}")
        return str(p)

    def _collect_shared_values(self) -> dict[str, str]:
        return {k: v.get().strip() for k, v in self.shared_vars.items()}

    def _collect_unique_values(self, op_key: str) -> dict[str, str]:
        return {k: v.get().strip() for k, v in self.operation_unique_vars[op_key].items()}

    def _append_log(self, msg: str) -> None:
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for btn in self._operation_buttons:
            btn.configure(state=state)

    def _launch_acquisition(self) -> None:
        try:
            wd = self._validate_workdir()
        except ValueError as exc:
            messagebox.showerror("Invalid Working Directory", str(exc))
            return

        self._persist_state()
        try:
            launch_acquisition_subprocess(wd)
            self.status_var.set("Acquisition launched in separate process")
            self._append_log(f"[INFO] Launched acquisition with ESPI_IMAGE_DATA_DIR={wd}")
        except Exception as exc:
            self.status_var.set("Failed to launch acquisition")
            self._append_log(f"[ERROR] {exc}")
            messagebox.showerror("Acquisition Launch Failed", str(exc))

    def _run_operation(self, op_key: str) -> None:
        if self._worker_alive:
            messagebox.showwarning("Busy", "Another operation is already running.")
            return

        op = next((o for o in self.operations if o.key == op_key), None)
        if op is None:
            messagebox.showerror("Operation Error", f"Unknown operation: {op_key}")
            return

        try:
            wd = self._validate_workdir()
        except ValueError as exc:
            messagebox.showerror("Invalid Working Directory", str(exc))
            return

        shared = self._collect_shared_values()
        unique = self._collect_unique_values(op_key)

        self._persist_state()
        self.status_var.set(f"Running: {op.label}")
        self._append_log(f"[RUN] {op.label}")
        self._set_busy(True)

        t = threading.Thread(
            target=self._run_worker,
            args=(op, wd, shared, unique),
            daemon=True,
        )
        self._worker_alive = True
        t.start()

    def _run_worker(self, op, wd: str, shared: dict[str, str], unique: dict[str, str]) -> None:
        try:
            op.runner(wd, shared, unique)
            self._queue.put(("success", f"Completed: {op.label}"))
        except Exception as exc:
            tb = traceback.format_exc()
            self._queue.put(("error", f"{op.label} failed: {exc}\n{tb}"))

    def _poll_worker_queue(self) -> None:
        try:
            while True:
                level, msg = self._queue.get_nowait()
                if level == "success":
                    self.status_var.set(msg)
                    self._append_log(f"[OK] {msg}")
                else:
                    self.status_var.set("Operation failed")
                    self._append_log(f"[ERROR] {msg}")
                    messagebox.showerror("Operation Failed", msg.splitlines()[0])

                self._worker_alive = False
                self._set_busy(False)
        except queue.Empty:
            pass

        self.root.after(150, self._poll_worker_queue)

    def _wrap_text_by_line(self, text: str, width: int = 100) -> str:
        """Wrap each existing line to a maximum character width while preserving manual line breaks."""
        if not text:
            return ""

        wrapped_lines: list[str] = []
        for line in text.splitlines():
            if not line.strip():
                wrapped_lines.append("")
                continue

            wrapped_lines.extend(
                textwrap.wrap(
                    line,
                    width=width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )

        return "\n".join(wrapped_lines)
