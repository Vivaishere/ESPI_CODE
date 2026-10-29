"""Shared application state for ESPI Control Center."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AppState:
    """In-memory state shared across GUI actions."""

    working_directory: str = ""
    shared_params: dict = field(default_factory=dict)
    operation_params: dict = field(default_factory=dict)
