"""Application entrypoint for ESPI Control Center."""

from espi_toolkit.gui.main_window import ESPIControlCenterApp


def run() -> None:
    """Launch the ESPI Control Center GUI."""
    app = ESPIControlCenterApp()
    app.run()
