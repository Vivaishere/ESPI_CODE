"""Session/local configuration helpers for ESPI Control Center."""

from __future__ import annotations

import json
from pathlib import Path


CONFIG_FILE_NAME = ".espi_control_center_config.json"


def load_config(project_root: Path) -> dict:
    """Load persisted control-center config from workspace root."""
    config_path = project_root / CONFIG_FILE_NAME
    if not config_path.exists():
        return {}

    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(project_root: Path, config_data: dict) -> None:
    """Persist control-center config to workspace root."""
    config_path = project_root / CONFIG_FILE_NAME
    config_path.write_text(
        json.dumps(config_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )
