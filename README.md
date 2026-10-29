# ESPI Control Center

This workspace now includes a packaged desktop application, ESPI Control Center, that integrates your existing ESPI acquisition and processing scripts into one primary window.

## What It Integrates

The control center reuses your existing code directly:

- Acquisition launcher: [src/espi_toolkit/acquisition/a_phase_series_acquisition.py](src/espi_toolkit/acquisition/a_phase_series_acquisition.py)
- Cropping: [src/espi_toolkit/acquisition/a__crop_images_2.py](src/espi_toolkit/acquisition/a__crop_images_2.py)
- Crack crop preprocessing: [src/espi_toolkit/processing/b_nancrop_expand_crack_espi.py](src/espi_toolkit/processing/b_nancrop_expand_crack_espi.py)
- Intensity-to-displacement pipeline: [src/espi_toolkit/processing/c_img_processing_main.py](src/espi_toolkit/processing/c_img_processing_main.py)
  - This includes filter_and_subtract_all_sets and downstream unwrap/displacement behavior.
- Displacement plotting and analysis:
  - [src/espi_toolkit/processing/plot_single_displacement_tiff.py](src/espi_toolkit/processing/plot_single_displacement_tiff.py)
  - [src/espi_toolkit/processing/plotline_disp_espi.py](src/espi_toolkit/processing/plotline_disp_espi.py)
  - [src/espi_toolkit/processing/plot_disp_3D_plot.py](src/espi_toolkit/processing/plot_disp_3D_plot.py)
  - [src/espi_toolkit/processing/plot_disp_lines_espi_and_sim.py](src/espi_toolkit/processing/plot_disp_lines_espi_and_sim.py)
- Strain processing and plotting:
  - [src/espi_toolkit/processing/e_plot_espi_strain.py](src/espi_toolkit/processing/e_plot_espi_strain.py)
  - [src/espi_toolkit/processing/plotline_strain_espi.py](src/espi_toolkit/processing/plotline_strain_espi.py)

## Package Structure

```text
ESPI_CODE/
|-- pyproject.toml
|-- README.md
|-- src/
|   `-- espi_toolkit/
|       |-- __init__.py
|       |-- __main__.py
|       |-- main.py
|       |-- gui/
|       |   |-- __init__.py
|       |   `-- main_window.py
|       |-- acquisition/
|       |   |-- __init__.py
|       |   |-- a__crop_images_2.py
|       |   |-- a__liq_crystal_retarder_control.py
|       |   |-- a_image_acquisition.py
|       |   `-- a_phase_series_acquisition.py
|       |-- core/
|       |   |-- __init__.py
|       |   |-- a__utils.py
|       |   |-- config.py
|       |   `-- state.py
|       `-- processing/
|           |-- __init__.py
|           |-- operations.py
|           |-- b_nancrop_espi.py
|           |-- b_nancrop_expand_crack_espi.py
|           |-- c_img_processing_main.py
|           |-- c_img_processing_support_functions.py
|           |-- c_phase_unwrap.py
|           |-- d_displacement_calc.py
|           |-- d_displacement_support_functions.py
|           |-- e_displacement_animation.py
|           |-- e_displacement_animation_prep.py
|           |-- e_plot_espi_strain.py
|           |-- plot_single_displacement_tiff.py
|           |-- plotline_disp_espi.py
|           |-- plotline_strain_espi.py
|           `-- additional plotting/comparison modules
`-- tests/
    `-- test_operation_registry.py
```

### Module Roles

- [src/espi_toolkit/main.py](src/espi_toolkit/main.py)
  - Application entrypoint that starts the ESPI Control Center GUI.
- [src/espi_toolkit/gui/main_window.py](src/espi_toolkit/gui/main_window.py)
  - Main single-window control center with acquisition launch, working directory, shared parameters, function list, and status.
- [src/espi_toolkit/acquisition/a_phase_series_acquisition.py](src/espi_toolkit/acquisition/a_phase_series_acquisition.py)
  - Existing camera and LC-retarder acquisition interface.
- [src/espi_toolkit/processing/operations.py](src/espi_toolkit/processing/operations.py)
  - Explicit operation registry and GUI-to-function parameter mapping.
- [src/espi_toolkit/core/config.py](src/espi_toolkit/core/config.py)
  - Session-local persistence for selected directory and parameters.
- [src/espi_toolkit/core/state.py](src/espi_toolkit/core/state.py)
  - Shared in-memory app state.

## GUI Workflow

The main window uses this order:

1. ESPI Control Center title
2. Launch Image Acquisition button
3. Shared working-directory selector
4. Shared processing parameters section
5. Processing functions list with each function's unique parameters shown inline beside it
6. Status/progress/error area

### Parameter Grouping Model

- Shared parameters (used across multiple operations) appear once in Section C.
- Unique parameters are shown next to each operation in Section D using dropdowns (or entries where needed).
- Each operation only receives mapped parameters relevant to that operation.

## Acquisition Integration

The acquisition GUI is launched in a separate process to avoid Tkinter root/event-loop conflicts with the control-center window.

- The control center sets ESPI_IMAGE_DATA_DIR for the acquisition subprocess when a working directory is selected.
- [src/espi_toolkit/core/a__utils.py](src/espi_toolkit/core/a__utils.py) checks this environment variable in get_image_data_dir().

If camera SDK/hardware is unavailable, acquisition launch may still open but camera actions will depend on your installed drivers/SDK.

## Working Directory Behavior

- The selected directory is validated before operations run.
- The directory is persisted in [.espi_control_center_config.json](.espi_control_center_config.json) at workspace root.
- Processing wrappers pass this folder to existing functions where supported.
- Some legacy operations still open file dialogs as designed by original scripts.

## Installation

Use a virtual environment, then install editable package:

```bash
pip install -e .
```

## Launch

Use either:

```bash
espi-toolkit
```

or:

```bash
python -m espi_toolkit
```

## Dependencies

Python dependencies are declared in [pyproject.toml](pyproject.toml) and aligned with [requirements.txt](requirements.txt).

Hardware/external dependencies:

- FLIR/Spinnaker SDK plus PySpin for camera control
- LC retarder serial device support (pyserial)

These are not redistributed by this project.

## Notes and Limitations

- Acquisition and processing scientific algorithms were not rewritten; wrappers call existing functions.
- Some source modules still use internal file dialogs and legacy defaults.
- Operations that require physical hardware cannot be fully validated without your device setup.
