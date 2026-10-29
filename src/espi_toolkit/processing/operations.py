"""Operation wrappers that connect GUI actions to existing ESPI functions."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class ParamDef:
    """Parameter definition used by the GUI."""

    key: str
    label: str
    dtype: str
    default: Any
    choices: list[Any] | None = None


@dataclass
class OperationDef:
    """Describes one GUI operation and its unique parameters."""

    key: str
    label: str
    category: str
    description: str
    runner: Callable[[str, dict[str, Any], dict[str, Any]], None]
    unique_params: list[ParamDef] = field(default_factory=list)


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: Any, name: str) -> float:
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"Invalid float for {name}: {value}") from exc


def _parse_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise ValueError(f"Invalid integer for {name}: {value}") from exc


def _run_crop(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.acquisition.a__crop_images_2 import crop_tiff_images_series

    crop_tiff_images_series(folder=workdir)


def _run_crackcrop(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.b_nancrop_expand_crack_espi import crackcrop_all_espi_sets

    crackcrop_all_espi_sets(
        folder=workdir,
        seed_threshold=_parse_int(shared["seed_threshold"], "seed_threshold"),
        grow_threshold=_parse_int(shared["grow_threshold"], "grow_threshold"),
        similarity_threshold=_parse_int(shared["similarity_threshold"], "similarity_threshold"),
        valley_radius=_parse_int(shared["valley_radius"], "valley_radius"),
        bridge_radius=_parse_int(shared["bridge_radius"], "bridge_radius"),
        dilation_radius=_parse_int(shared["dilation_radius"], "dilation_radius"),
        min_component_size=_parse_int(shared["min_component_size"], "min_component_size"),
    )


def _run_intensity_to_displacement(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.c_img_processing_main import filter_and_subtract_all_sets

    filter_and_subtract_all_sets(
        folder=workdir,
        do_displacement=True,
        filter3_version=str(unique["filter3_version"]),
        include_diagnostics=_parse_bool(unique["include_diagnostics"]),
        pixel_size_m=_parse_float(shared["pixel_size_m"], "pixel_size_m"),
        lv=_parse_int(unique["lv"], "lv"),
        lh=_parse_int(unique["lh"], "lh"),
        filter_num=_parse_int(unique["filter_num"], "filter_num"),
    )


def _run_displacement_plot(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plot_single_displacement_tiff import plot_single_displacement_tiffs

    plot_single_displacement_tiffs(
        colormap=str(unique["colormap"]),
        percentile=_parse_float(unique["percentile"], "percentile"),
        pixel_size_m=_parse_float(shared["pixel_size_m"], "pixel_size_m"),
        save_png=_parse_bool(unique["save_png"]),
    )


def _run_strain_calc(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.e_plot_espi_strain import compute_strain_xx

    gauge_size = _parse_int(unique["gauge_size"], "gauge_size")
    compute_strain_xx(
        save_plot=_parse_bool(unique["save_plot"]),
        save_tiff=_parse_bool(unique["save_tiff"]),
        pixel_size_um=_parse_float(shared["pixel_size_m"], "pixel_size_m") * 1e6,
        fit_order=_parse_int(unique["fit_order"], "fit_order"),
        gauge_sizes=(gauge_size,),
        white_band=_parse_int(unique["white_band"], "white_band"),
        edge_exclusion_pixels=_parse_int(unique["edge_exclusion_pixels"], "edge_exclusion_pixels"),
        dotsize=_parse_int(unique["dotsize"], "dotsize"),
    )


def _run_disp_line(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plotline_disp_espi import plot_ux_singleline_tiff

    x_lo = _parse_float(unique["x_min"], "x_min")
    x_hi = _parse_float(unique["x_max"], "x_max")
    plot_ux_singleline_tiff(
        height_mm=_parse_float(unique["height_mm"], "height_mm"),
        x_bounds=(x_lo, x_hi),
        fit_order=_parse_int(unique["fit_order"], "fit_order"),
        pixel_size_m=_parse_float(shared["pixel_size_m"], "pixel_size_m"),
        save_plot=_parse_bool(unique["save_plot"]),
    )


def _run_strain_line(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plotline_strain_espi import plot_strain_line_tiffs

    x_lo = _parse_float(unique["x_min"], "x_min")
    x_hi = _parse_float(unique["x_max"], "x_max")
    plot_strain_line_tiffs(
        pixel_size_m=_parse_float(shared["pixel_size_m"], "pixel_size_m"),
        height_mm=_parse_float(unique["height_mm"], "height_mm"),
        x_bounds=(x_lo, x_hi),
        fit_order=_parse_int(unique["fit_order"], "fit_order"),
        save_plot=_parse_bool(unique["save_plot"]),
    )


def _run_plot_3d(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plot_disp_3D_plot import plot_3D_from_tiff

    plot_3D_from_tiff(
        colormap=str(unique["colormap"]),
        Zangle=_parse_float(unique["z_angle"], "z_angle"),
        XYrot=_parse_float(unique["xy_rot"], "xy_rot"),
    )


def _run_disp_sim_compare(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plot_disp_lines_espi_and_sim import plot_ux_tiff_sim

    plot_ux_tiff_sim(
        sim_radius=_parse_float(unique["sim_radius"], "sim_radius"),
        dist_from_center_mm=_parse_float(unique["dist_from_center_mm"], "dist_from_center_mm"),
        center_adjust=_parse_bool(unique["center_adjust"]),
        include_sim=_parse_bool(unique["include_sim"]),
        include_sum=_parse_bool(unique["include_sum"]),
        save_plot=_parse_bool(unique["save_plot"]),
    )


def get_shared_param_defs() -> list[ParamDef]:
    """Parameters intentionally shared across multiple operations."""
    return [
        ParamDef("pixel_size_m", "Pixel Size (m)", "float", 8.4e-6),
        ParamDef("seed_threshold", "Crack Seed Threshold", "int", 5),
        ParamDef("grow_threshold", "Crack Grow Threshold", "int", 20),
        ParamDef("similarity_threshold", "Crack Similarity Threshold", "int", 15),
        ParamDef("valley_radius", "Valley Radius (px)", "int", 1),
        ParamDef("bridge_radius", "Bridge Radius (px)", "int", 1),
        ParamDef("dilation_radius", "Dilation Radius (px)", "int", 0),
        ParamDef("min_component_size", "Min Crack Component Size (px)", "int", 100),
    ]


def get_operation_defs() -> list[OperationDef]:
    """Return operation definitions and connect wrappers to workspace modules."""
    yn = ["True", "False"]
    filter_sizes = ["1", "3", "5", "7", "9", "11", "13", "15", "17", "19", "21", "23", "25", "27", "29", "31", "33", "35", "37", "39"]

    return [
        OperationDef(
            key="crop_images",
            label="Crop Images",
            category="Acquisition/Preprocessing",
            description="Interactive crop for selected intensity TIFF series.",
            runner=_run_crop,
            unique_params=[],
        ),
        OperationDef(
            key="crack_crop",
            label="Crack Crop All ESPI Sets",
            category="Preprocessing",
            description="Build and apply crack mask to selected ESPI set.",
            runner=_run_crackcrop,
            unique_params=[],
        ),
        OperationDef(
            key="intensity_to_displacement",
            label="Intensity to Displacement",
            category="Core Processing",
            description="Filter/subtract phase series, unwrap, then compute displacement.",
            runner=_run_intensity_to_displacement,
            unique_params=[
                ParamDef("lv", "Filter Vertical Size", "choice", "11", choices=filter_sizes),
                ParamDef("lh", "Filter Horizontal Size", "choice", "11", choices=filter_sizes),
                ParamDef("filter_num", "Filter Number", "choice", "3", choices=["1", "2", "3"]),
                ParamDef("filter3_version", "Filter 3 Version", "choice", "B", choices=["A", "B", "C"]),
                ParamDef("include_diagnostics", "Diagnostics", "choice", "False", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_displacement_map",
            label="Plot Single Displacement TIFF(s)",
            category="Visualization",
            description="Render displacement TIFF(s) with percentile color scaling.",
            runner=_run_displacement_plot,
            unique_params=[
                ParamDef("colormap", "Colormap", "choice", "jet", choices=["jet", "viridis", "plasma", "coolwarm", "turbo"]),
                ParamDef("percentile", "Percentile", "choice", "99.9", choices=["99.0", "99.5", "99.9", "99.99"]),
                ParamDef("save_png", "Save PNG", "choice", "True", choices=yn),
            ],
        ),
        OperationDef(
            key="compute_strain",
            label="Compute Strain XX",
            category="Strain",
            description="Compute ESPI strain map(s) from displacement TIFF(s).",
            runner=_run_strain_calc,
            unique_params=[
                ParamDef("fit_order", "Fit Order", "choice", "1", choices=["0", "1", "2"]),
                ParamDef("gauge_size", "Gauge Size (px)", "choice", "40", choices=["5", "10", "20", "30", "40", "50", "60"]),
                ParamDef("white_band", "White Band", "choice", "0", choices=["0", "25", "50", "75", "100"]),
                ParamDef("edge_exclusion_pixels", "Edge Exclusion (px)", "choice", "10", choices=["0", "5", "10", "15", "20"]),
                ParamDef("dotsize", "Dot Size", "choice", "2", choices=["1", "2", "3", "4"]),
                ParamDef("save_plot", "Save Plot", "choice", "True", choices=yn),
                ParamDef("save_tiff", "Save TIFF", "choice", "True", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_disp_line_noise",
            label="Plot Displacement Line / Noise",
            category="Line Plots",
            description="Plot displacement line and fitted residual-based noise metric.",
            runner=_run_disp_line,
            unique_params=[
                ParamDef("height_mm", "Height (mm)", "choice", "2", choices=["0", "1", "2", "4", "6", "8", "10"]),
                ParamDef("x_min", "X Min (mm)", "choice", "-4", choices=["-12", "-10", "-8", "-6", "-4", "-2"]),
                ParamDef("x_max", "X Max (mm)", "choice", "4", choices=["2", "4", "6", "8", "10", "12"]),
                ParamDef("fit_order", "Fit Order", "choice", "0", choices=["0", "1", "2"]),
                ParamDef("save_plot", "Save Plot", "choice", "True", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_strain_line",
            label="Plot Strain Line",
            category="Line Plots",
            description="Plot strain line and polynomial fit in selected x-range.",
            runner=_run_strain_line,
            unique_params=[
                ParamDef("height_mm", "Height (mm)", "choice", "2", choices=["0", "1", "2", "4", "6", "8", "10"]),
                ParamDef("x_min", "X Min (mm)", "choice", "-4", choices=["-12", "-10", "-8", "-6", "-4", "-2"]),
                ParamDef("x_max", "X Max (mm)", "choice", "4", choices=["2", "4", "6", "8", "10", "12"]),
                ParamDef("fit_order", "Fit Order", "choice", "0", choices=["0", "1", "2"]),
                ParamDef("save_plot", "Save Plot", "choice", "True", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_3d",
            label="Plot 3D Displacement",
            category="Visualization",
            description="Generate 3D surface plots from displacement TIFF(s).",
            runner=_run_plot_3d,
            unique_params=[
                ParamDef("colormap", "Colormap", "choice", "jet", choices=["jet", "viridis", "plasma", "coolwarm", "turbo"]),
                ParamDef("z_angle", "Z Angle", "choice", "10", choices=["10", "20", "30", "45", "60"]),
                ParamDef("xy_rot", "XY Rotation", "choice", "-60", choices=["-90", "-60", "-45", "-30", "0", "30"]),
            ],
        ),
        OperationDef(
            key="plot_disp_vs_sim",
            label="Plot ESPI vs FEA Line",
            category="Comparison",
            description="Compare ESPI displacement line(s) against simulation line.",
            runner=_run_disp_sim_compare,
            unique_params=[
                ParamDef("sim_radius", "Simulation Radius (mm)", "choice", "12", choices=["8", "10", "11.5", "12", "14"]),
                ParamDef("dist_from_center_mm", "Distance From Center (mm)", "choice", "-7", choices=["-10", "-8", "-7", "-5", "0", "5"]),
                ParamDef("center_adjust", "Center Adjust", "choice", "True", choices=yn),
                ParamDef("include_sim", "Include Simulation", "choice", "True", choices=yn),
                ParamDef("include_sum", "Include ESPI Sum", "choice", "True", choices=yn),
                ParamDef("save_plot", "Save Plot", "choice", "True", choices=yn),
            ],
        ),
    ]


def launch_acquisition_subprocess(working_dir: str) -> None:
    """Launch the existing acquisition GUI in a separate process."""
    env = os.environ.copy()
    if working_dir:
        env["ESPI_IMAGE_DATA_DIR"] = working_dir

    python_exe = sys.executable

    import subprocess

    subprocess.Popen(
        [python_exe, "-m", "espi_toolkit.acquisition.a_phase_series_acquisition"],
        cwd=working_dir or os.getcwd(),
        env=env,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
