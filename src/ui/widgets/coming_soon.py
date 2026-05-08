"""Helper for "Próximamente" notifications.

Most navigation actions in Fase 1 don't have a destination window yet.
Calling :func:`show_coming_soon` from any handler shows a friendly modal
saying that feature isn't ready, without polluting the call sites with the
same QMessageBox boilerplate everywhere.
"""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from src.config import APP_DISPLAY_NAME


def show_coming_soon(parent: QWidget | None, feature_name: str) -> None:
    """Show a modal informing the user that ``feature_name`` is not implemented yet."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(APP_DISPLAY_NAME)
    msg.setText(f"<b>{feature_name}</b>")
    msg.setInformativeText(
        "Esta funcionalidad estará disponible próximamente.\n"
        "La vamos a habilitar en una próxima actualización."
    )
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec()
