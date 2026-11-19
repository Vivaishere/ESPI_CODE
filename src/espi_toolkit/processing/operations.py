"""Operation wrappers that connect GUI actions to existing ESPI functions."""

from __future__ import annotations

import importlib.util
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
    help_text: str = ""
    choices: list[Any] | None = None


@dataclass
class OperationDef:
    """Describes one GUI operation and its unique parameters."""

    key: str
    label: str
    section: str
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
        seed_threshold=_parse_int(unique["seed_threshold"], "seed_threshold"),
        grow_threshold=_parse_int(unique["grow_threshold"], "grow_threshold"),
        similarity_threshold=_parse_int(unique["similarity_threshold"], "similarity_threshold"),
        valley_radius=_parse_int(unique["valley_radius"], "valley_radius"),
        bridge_radius=_parse_int(unique["bridge_radius"], "bridge_radius"),
        dilation_radius=_parse_int(unique["dilation_radius"], "dilation_radius"),
        min_component_size=_parse_int(unique["min_component_size"], "min_component_size"),
    )


def _run_intensity_to_displacement(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.c_img_processing_main import filter_and_subtract_all_sets

    filter_and_subtract_all_sets(
        folder=workdir,
        do_displacement=_parse_bool(unique["do_displacement"]),
        filter3_version=str(unique["filter3_version"]),
        include_diagnostics=_parse_bool(unique["include_diagnostics"]),
        pixel_size_m=_parse_float(shared["pixel_size_m"], "pixel_size_m"),
        lv=_parse_int(unique["lv"], "lv"),
        lh=_parse_int(unique["lh"], "lh"),
        filter_num=_parse_int(unique["filter_num"], "filter_num"),
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
        dotsize=_parse_int(unique["dotsize"], "dotsize"),
        ssig=_parse_float(unique["ssig"], "ssig"),
        flip_displacement_sign=_parse_bool(unique["flip_displacement_sign"]),
        edge_exclusion_pixels=_parse_int(unique["edge_exclusion_pixels"], "edge_exclusion_pixels"),
    )


def _run_displacement_plot(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plot_single_displacement_tiff import plot_single_displacement_tiffs

    plot_single_displacement_tiffs(
        filepath=None,
        colormap=str(unique["colormap"]),
        percentile=_parse_float(unique["percentile"], "percentile"),
        pixel_size_m=_parse_float(shared["pixel_size_m"], "pixel_size_m"),
        save_png=_parse_bool(unique["save_png"]),
    )


def _run_plot_ux_combined(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plotline_disp_espi import plot_ux_combined_tiff

    plot_ux_combined_tiff(
        height_mm=_parse_float(unique["height_mm"], "height_mm"),
        pixel_size_m=_parse_float(shared["pixel_size_m"], "pixel_size_m"),
        save_plot=_parse_bool(unique["save_plot"]),
    )


def _run_plot_ux_sum(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plotline_disp_espi import plot_ux_sum_tiff

    plot_ux_sum_tiff(
        height_mm=_parse_float(unique["height_mm"], "height_mm"),
        save_plot=_parse_bool(unique["save_plot"]),
        pixel_size_m=_parse_float(shared["pixel_size_m"], "pixel_size_m"),
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
        sim_filename=str(unique["sim_filename"]),
        sim_radius=_parse_float(unique["sim_radius"], "sim_radius"),
        dist_from_center_mm=_parse_float(unique["dist_from_center_mm"], "dist_from_center_mm"),
        center_adjust=_parse_bool(unique["center_adjust"]),
        include_sim=_parse_bool(unique["include_sim"]),
        include_sum=_parse_bool(unique["include_sum"]),
        save_plot=_parse_bool(unique["save_plot"]),
    )


def _run_sim_uy_line(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plot_disp_lines_espi_and_sim import plot_simulation_uy_line

    plot_simulation_uy_line(
        filename=str(unique["filename"]),
        y_height=_parse_float(unique["y_height"], "y_height"),
        radius=_parse_float(unique["radius"], "radius"),
        mirror=_parse_bool(unique["mirror"]),
        save_plot=_parse_bool(unique["save_plot"]),
    )


def _run_dic_dx(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plot_DICe_strain_and_disp import plot_dic_dx_color

    plot_dic_dx_color(
        center_adjust=_parse_bool(unique["center_adjust"]),
        save_plot=_parse_bool(unique["save_plot"]),
        save_tiff=_parse_bool(unique["save_tiff"]),
    )


def _run_dic_dy(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plot_DICe_strain_and_disp import plot_dic_dy_color

    plot_dic_dy_color(save_plot=_parse_bool(unique["save_plot"]))


def _run_dic_strain(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plot_DICe_strain_and_disp import plot_dic_strainxx

    plot_dic_strainxx(
        save_plot=_parse_bool(unique["save_plot"]),
        save_tiff=_parse_bool(unique["save_tiff"]),
    )


def _run_espi_dic_profile_compare(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plot_espi_vs_dic import compare_espi_dic_profiles

    compare_espi_dic_profiles(save_plot=_parse_bool(unique["save_plot"]))


def _run_intensity_analysis(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing import plot_intensity_analysis

    plot_intensity_analysis.main()


def _run_noise_sd(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    from espi_toolkit.processing.plotSDvalue_zerodisp import calculate_sd_multiple_tiffs

    calculate_sd_multiple_tiffs(
        outer_pixels=_parse_int(unique["outer_pixels"], "outer_pixels"),
        save_png=_parse_bool(unique["save_png"]),
        grid_size=_parse_int(unique["grid_size"], "grid_size"),
    )


def _run_espi_dic_disp_diff(workdir: str, shared: dict[str, Any], unique: dict[str, Any]) -> None:
    """Import module with non-standard filename and run its main comparison function."""
    mod_path = Path(__file__).resolve().parent / "plot_espi--dic_disp_diff.py"
    spec = importlib.util.spec_from_file_location("plot_espi_dic_disp_diff", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.compute_difference_and_plot(
        save_fig=_parse_bool(unique["save_fig"]),
        save_tiff=_parse_bool(unique["save_tiff"]),
        plot_lines=_parse_bool(unique["plot_lines"]),
    )


def get_shared_param_defs() -> list[ParamDef]:
    """Parameters intentionally shared across multiple operations."""
    return [
        ParamDef(
            "pixel_size_m",
            "Pixel Size (m)",
            "float",
            8.4e-6,
            "Sets image scale for operations that convert pixels to physical dimensions.",
        )
    ]


def _yn() -> list[str]:
    return ["True", "False"]


def get_operation_defs() -> list[OperationDef]:
    """Return operation definitions and connect wrappers to packaged modules."""
    yn = _yn()
    filter_sizes = ["1", "3", "5", "7", "9", "11", "13", "15", "17", "19", "21", "23", "25", "27", "29", "31", "33", "35", "37", "39"]

    return [
        OperationDef(
            key="crop_images",
            label="Crop Images",
            section="D",
            category="Intensity Image Cropping",
            description=(
                "Input: Select one or more intensity TIFF files from the target set.\n"
                "Output: Saves cropped TIFF files in the same folder using cropN_ filename prefixes."
            ),
            runner=_run_crop,
            unique_params=[],
        ),
        OperationDef(
            key="crack_crop",
            label="Crack Crop All ESPI Sets",
            section="D",
            category="Non Sample Pixel Mask Application",
            description=(
                "Input: Select ESPI intensity TIFF set(s) for one specimen/load sequence.\n"
                "Output: Saves crack-mask-applied intensity TIFF images in the same set folder."
            ),
            runner=_run_crackcrop,
            unique_params=[
                ParamDef("seed_threshold", "Seed Threshold", "int", "5", "Initial crack seed brightness threshold for region seeding."),
                ParamDef("grow_threshold", "Grow Threshold", "int", "20", "Brightness threshold used while region-growing crack areas."),
                ParamDef("similarity_threshold", "Similarity Threshold", "int", "15", "Controls similarity tolerance during crack expansion."),
                ParamDef("valley_radius", "Valley Radius", "choice", "1", "Neighborhood radius used for valley detection/stability.", choices=["0", "1", "2", "3", "4"]),
                ParamDef("bridge_radius", "Bridge Radius", "choice", "1", "Radius used for morphological bridge connection in masks.", choices=["0", "1", "2", "3", "4"]),
                ParamDef("dilation_radius", "Dilation Radius", "choice", "0", "Extra dilation radius applied to final invalid region mask.", choices=["0", "1", "2", "3", "4"]),
                ParamDef("min_component_size", "Min Component Size", "int", "100", "Removes tiny mask components smaller than this pixel area."),
            ],
        ),
        OperationDef(
            key="intensity_to_displacement",
            label="Intensity to Displacement",
            section="D",
            category="Core Processing: Displacement Output",
            description=(
                "Input: Select one reference intensity TIFF from a 4-phase force series.\n"
                "Output 1 (filter_and_subtract_all_sets): Saves filter*-str* phase-difference TIFF files.\n"
                "Output 2 (unwrap_all_filter_images): Saves UW_*.tiff unwrapped phase files.\n"
                "Output 3 (get_displacement): Saves COMBINED-Disp_RBM-adj_*.tiff and optional PNGs.\n"
                "Output 4 (get_displacement nested): Creates Disp-RBM-adjusted_<set_name>/ with Disp files.\n"
                "Output 5 (create_displacement_gif nested): Creates gif-set_<folder_name>/ with GIF data.\n"
            ),
            runner=_run_intensity_to_displacement,
            unique_params=[
                ParamDef("do_displacement", "Do Displacement", "choice", "True", "Computes displacement from unwrapped phase images after filtering.", choices=yn),
                ParamDef("lv", "Filter Vertical Size", "choice", "11", "Vertical kernel size used by selected phase filter.", choices=filter_sizes),
                ParamDef("lh", "Filter Horizontal Size", "choice", "11", "Horizontal kernel size used by selected phase filter.", choices=filter_sizes),
                ParamDef("filter_num", "Filter Number", "choice", "3", "Selects filter implementation (1, 2, or 3 family).", choices=["1", "2", "3"]),
                ParamDef("filter3_version", "Filter 3 Version", "choice", "B", "Selects implementation variant when Filter Number = 3.", choices=["A", "B", "C"]),
                ParamDef("include_diagnostics", "Include Diagnostics", "choice", "False", "Saves phase-quality diagnostic images during processing.", choices=yn),
            ],
        ),
        OperationDef(
            key="compute_strain",
            label="Compute Strain XX",
            section="D",
            category="Core Processing: Strain Output",
            description=(
                "Input: Select displacement TIFF file(s) for ESPI strain computation.\n"
                "Output: Saves strain TIFF files and strain plot PNG files in the same folder."
            ),
            runner=_run_strain_calc,
            unique_params=[
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves strain map figures as image files.", choices=yn),
                ParamDef("save_tiff", "Save TIFF", "choice", "True", "Saves computed strain values as float TIFF files.", choices=yn),
                ParamDef("fit_order", "Fit Order", "choice", "1", "Polynomial order for local displacement fit before strain extraction.", choices=["0", "1", "2"]),
                ParamDef("gauge_size", "Gauge Size (px)", "choice", "40", "Window size used for local strain estimation.", choices=["5", "10", "20", "30", "40", "50", "60"]),
                ParamDef("white_band", "White Band", "choice", "0", "White center band width for strain color mapping.", choices=["0", "25", "50", "75", "100"]),
                ParamDef("dotsize", "Dot Size", "choice", "2", "Scatter marker size used in saved strain plots.", choices=["1", "2", "3", "4"]),
                ParamDef("ssig", "Gaussian Sigma", "choice", "0", "Gaussian weighting sigma for fitting window; 0 disables weighting.", choices=["0", "1", "2", "3", "4", "5"]),
                ParamDef("flip_displacement_sign", "Flip Displacement Sign", "choice", "False", "Flips displacement sign before strain computation if needed.", choices=yn),
                ParamDef("edge_exclusion_pixels", "Edge Exclusion (px)", "choice", "10", "Ignored border width where strain is not computed.", choices=["0", "5", "10", "15", "20"]),
            ],
        ),
        OperationDef(
            key="plot_displacement_map",
            label="Plot Single Displacement TIFF(s)",
            section="E",
            category="Displacement Plotting",
            description=(
                "Input: Select displacement TIFF file(s).\n"
                "Output: Saves color-mapped displacement PNG files in the same folder."
            ),
            runner=_run_displacement_plot,
            unique_params=[
                ParamDef("colormap", "Colormap", "choice", "jet", "Changes the colormap used for displacement visualization.", choices=["jet", "viridis", "plasma", "coolwarm", "turbo"]),
                ParamDef("percentile", "Percentile", "choice", "99.9", "Controls saturation limits using percentile clipping.", choices=["99.0", "99.5", "99.9", "99.99"]),
                ParamDef("save_png", "Save PNG", "choice", "True", "When True, exports plotted displacement maps as PNG.", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_disp_line_combined",
            label="Plot Combined Displacement Line",
            section="E",
            category="Displacement Plotting",
            description=(
                "Input: Select one combined displacement TIFF file.\n"
                "Output: Saves one horizontal displacement line plot PNG in the same folder."
            ),
            runner=_run_plot_ux_combined,
            unique_params=[
                ParamDef("height_mm", "Height (mm)", "choice", "0", "Line height extracted from displacement map (physical mm).", choices=["-5", "-2", "0", "2", "4", "8", "12"]),
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves generated displacement line plot.", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_disp_line_sum",
            label="Plot Summed Displacement Line",
            section="E",
            category="Displacement Plotting",
            description=(
                "Input: Select multiple displacement TIFF files.\n"
                "Output: Saves individual and summed displacement line plots as PNG files."
            ),
            runner=_run_plot_ux_sum,
            unique_params=[
                ParamDef("height_mm", "Height (mm)", "choice", "0", "Line height extracted from each selected displacement map.", choices=["-5", "-2", "0", "2", "4", "8", "12"]),
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves generated summed displacement line plot.", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_disp_line_noise",
            label="Plot Displacement Line / Noise",
            section="E",
            category="Displacement Plotting",
            description=(
                "Input: Select one combined displacement TIFF file.\n"
                "Output: Saves a profile plot with polynomial fit and residual noise metrics."
            ),
            runner=_run_disp_line,
            unique_params=[
                ParamDef("height_mm", "Height (mm)", "choice", "2", "Line height used for displacement/noise evaluation.", choices=["0", "1", "2", "4", "6", "8", "10"]),
                ParamDef("x_min", "X Min (mm)", "choice", "-4", "Lower X bound for polynomial fitting region.", choices=["-12", "-10", "-8", "-6", "-4", "-2"]),
                ParamDef("x_max", "X Max (mm)", "choice", "4", "Upper X bound for polynomial fitting region.", choices=["2", "4", "6", "8", "10", "12"]),
                ParamDef("fit_order", "Fit Order", "choice", "0", "Polynomial order used to estimate trend/noise residuals.", choices=["0", "1", "2"]),
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves displacement line/noise plot as PNG.", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_strain_line",
            label="Plot Strain Line",
            section="E",
            category="Strain Plotting",
            description=(
                "Input: Select strain TIFF file(s).\n"
                "Output: Saves horizontal strain-line plots with polynomial fit overlays."
            ),
            runner=_run_strain_line,
            unique_params=[
                ParamDef("height_mm", "Height (mm)", "choice", "2", "Line height used for strain profile extraction.", choices=["0", "1", "2", "4", "6", "8", "10"]),
                ParamDef("x_min", "X Min (mm)", "choice", "-4", "Lower X bound used for strain fit window.", choices=["-12", "-10", "-8", "-6", "-4", "-2"]),
                ParamDef("x_max", "X Max (mm)", "choice", "4", "Upper X bound used for strain fit window.", choices=["2", "4", "6", "8", "10", "12"]),
                ParamDef("fit_order", "Fit Order", "choice", "0", "Polynomial order for strain-line trend fitting.", choices=["0", "1", "2"]),
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves strain line plot as PNG.", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_3d",
            label="Plot 3D Displacement",
            section="E",
            category="Displacement Plotting",
            description=(
                "Input: Select displacement TIFF files or UW unwrapped phase TIFF files.\n"
                "Output: Saves 3D displacement surface PNG files in the selected file folder."
            ),
            runner=_run_plot_3d,
            unique_params=[
                ParamDef("colormap", "Colormap", "choice", "jet", "Changes 3D surface colormap.", choices=["jet", "viridis", "plasma", "coolwarm", "turbo"]),
                ParamDef("z_angle", "Z Angle", "choice", "10", "Camera elevation angle for 3D view.", choices=["10", "20", "30", "45", "60"]),
                ParamDef("xy_rot", "XY Rotation", "choice", "-60", "Azimuth rotation of 3D viewpoint.", choices=["-90", "-60", "-45", "-30", "0", "30"]),
            ],
        ),
        OperationDef(
            key="plot_disp_vs_sim",
            label="Plot ESPI vs FEA Line",
            section="E",
            category="ESPI-DIC/FEA Comparison",
            description=(
                "Input: Select ESPI displacement TIFF files and use FEA text file in FEA_comparison.\n"
                "Output: Saves ESPI-vs-FEA line comparison plots in the selected TIFF folder."
            ),
            runner=_run_disp_sim_compare,
            unique_params=[
                ParamDef("sim_filename", "Simulation File", "choice", "nodes_disp.txt", "FEA text file name read from processing/FEA_comparison.", choices=["nodes_disp.txt"]),
                ParamDef("sim_radius", "Simulation Radius (mm)", "choice", "12", "Radius window used for simulation line extraction.", choices=["8", "10", "11.5", "12", "14"]),
                ParamDef("dist_from_center_mm", "Distance From Center (mm)", "choice", "-7", "Vertical line location in specimen coordinates.", choices=["-10", "-8", "-7", "-5", "0", "5"]),
                ParamDef("center_adjust", "Center Adjust", "choice", "True", "Applies center-offset correction to ESPI lines.", choices=yn),
                ParamDef("include_sim", "Include Simulation", "choice", "True", "Adds FEA line to the ESPI plot.", choices=yn),
                ParamDef("include_sum", "Include ESPI Sum", "choice", "True", "Adds summed ESPI displacement profile.", choices=yn),
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves ESPI/FEA comparison figure as PNG.", choices=yn),
            ],
        ),
        OperationDef(
            key="plot_sim_uy",
            label="Plot Simulation UY Line",
            section="E",
            category="ESPI-DIC/FEA Comparison",
            description=(
                "Input: Use one FEA displacement text file.\n"
                "Output: Saves one simulation-only UY line plot PNG file."
            ),
            runner=_run_sim_uy_line,
            unique_params=[
                ParamDef("filename", "Simulation File", "choice", "nodes_disp.txt", "FEA text file used for vertical displacement profile.", choices=["nodes_disp.txt"]),
                ParamDef("y_height", "Y Height", "choice", "12", "Y-location sampled in simulation data.", choices=["8", "10", "12", "14"]),
                ParamDef("radius", "Radius", "choice", "12", "Half-width extraction radius in simulation coordinates.", choices=["8", "10", "12", "14"]),
                ParamDef("mirror", "Mirror Symmetry", "choice", "True", "Mirrors line profile to generate symmetric full-span curve.", choices=yn),
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves UY simulation plot as PNG.", choices=yn),
            ],
        ),
        OperationDef(
            key="dic_dx",
            label="Plot DIC DX",
            section="E",
            category="ESPI-DIC/FEA Comparison",
            description=(
                "Input: Select one DIC text displacement file.\n"
                "Output: Saves DIC DX plot PNG and optional interpolated DX TIFF output."
            ),
            runner=_run_dic_dx,
            unique_params=[
                ParamDef("center_adjust", "Center Adjust", "choice", "True", "Removes rigid horizontal shift from DIC displacement field.", choices=yn),
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves DIC DX color plot.", choices=yn),
                ParamDef("save_tiff", "Save TIFF", "choice", "True", "Exports interpolated DX displacement map as TIFF.", choices=yn),
            ],
        ),
        OperationDef(
            key="dic_dy",
            label="Plot DIC DY",
            section="E",
            category="ESPI-DIC/FEA Comparison",
            description=(
                "Input: Select one DIC text displacement file.\n"
                "Output: Saves one DIC DY color plot PNG file."
            ),
            runner=_run_dic_dy,
            unique_params=[
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves DIC DY color plot.", choices=yn),
            ],
        ),
        OperationDef(
            key="dic_strain_xx",
            label="Plot DIC Strain XX",
            section="E",
            category="ESPI-DIC/FEA Comparison",
            description=(
                "Input: Select one DIC strain text or CSV file.\n"
                "Output: Saves DIC strain plot PNG and optional interpolated strain TIFF."
            ),
            runner=_run_dic_strain,
            unique_params=[
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves DIC strain color plot.", choices=yn),
                ParamDef("save_tiff", "Save TIFF", "choice", "True", "Exports interpolated DIC strain field as TIFF.", choices=yn),
            ],
        ),
        OperationDef(
            key="espi_dic_profiles",
            label="Compare ESPI vs DIC Profiles",
            section="E",
            category="ESPI-DIC/FEA Comparison",
            description=(
                "Input: Select ESPI and DIC profile files via file dialogs.\n"
                "Output: Saves comparison plot and prints profile difference/error summary."
            ),
            runner=_run_espi_dic_profile_compare,
            unique_params=[
                ParamDef("save_plot", "Save Plot", "choice", "True", "Saves ESPI-vs-DIC profile comparison plot.", choices=yn),
            ],
        ),
        OperationDef(
            key="espi_dic_disp_diff",
            label="Compute ESPI-DIC Displacement Difference",
            section="E",
            category="ESPI-DIC/FEA Comparison",
            description=(
                "Input: Select ESPI and DIC displacement TIFF files.\n"
                "Output: Saves difference TIFF, figure PNG, and optional line-profile diagnostics."
            ),
            runner=_run_espi_dic_disp_diff,
            unique_params=[
                ParamDef("save_fig", "Save Figure", "choice", "True", "Saves displacement-difference color map figure.", choices=yn),
                ParamDef("save_tiff", "Save TIFF", "choice", "True", "Saves displacement-difference field as TIFF.", choices=yn),
                ParamDef("plot_lines", "Plot Line Profiles", "choice", "True", "Generates additional line-profile diagnostics.", choices=yn),
            ],
        ),
        OperationDef(
            key="intensity_metrics",
            label="Intensity Analysis",
            section="E",
            category="Noise and Intensity Analysis",
            description=(
                "Input: Select one intensity TIFF file.\n"
                "Output: Saves intensity histogram/statistics plot and prints image metrics."
            ),
            runner=_run_intensity_analysis,
            unique_params=[],
        ),
        OperationDef(
            key="noise_sd_map",
            label="Displacement Noise SD Map",
            section="E",
            category="Noise and Intensity Analysis",
            description=(
                "Input: Select displacement TIFF file(s).\n"
                "Output: Prints SD statistics and saves optional SD grid/noise-map PNG files."
            ),
            runner=_run_noise_sd,
            unique_params=[
                ParamDef("outer_pixels", "Outer Pixels", "choice", "40", "Excludes edge band before SD statistics are computed.", choices=["0", "10", "20", "40", "60"]),
                ParamDef("save_png", "Save PNG", "choice", "True", "Saves generated SD plots/maps to image files.", choices=yn),
                ParamDef("grid_size", "Grid Size", "choice", "8", "Grid resolution used for local SD/noise map computations.", choices=["4", "6", "8", "10", "12"]),
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
