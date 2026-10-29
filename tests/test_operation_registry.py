from espi_toolkit.processing.operations import get_operation_defs, get_shared_param_defs


def test_shared_params_present() -> None:
    shared = get_shared_param_defs()
    keys = {p.key for p in shared}
    assert "pixel_size_m" in keys
    assert "grow_threshold" in keys


def test_operation_registry_has_core_workflow() -> None:
    ops = get_operation_defs()
    op_keys = {op.key for op in ops}
    assert "intensity_to_displacement" in op_keys
    assert "crack_crop" in op_keys
    assert "crop_images" in op_keys
