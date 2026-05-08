"""Main window for the 'jefe' role.

Placeholder for Fase 1 — only displays a welcome message and a logout button.
The actual functionality (gestión de operarios, todos los estudios, etc.)
will be built later, after the Personal flow is validated.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hematologia.config import APP_DISPLAY_NAME
from hematologia.core.session import get_session


class JefeMainWindow(QMainWindow):
    """Placeholder main window for operarios with rol='jefe'."""

    logout_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_DISPLAY_NAME} — Jefe")
        self.resize(900, 600)

        self._build_ui()

    def _build_ui(self) -> None:
        operario = get_session().operario
        nombre = operario.nombre_completo if operario else "Jefe"

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 40, 40, 40)

        welcome = QLabel(f"Bienvenido, {nombre}")
        welcome_font = QFont()
        welcome_font.setPointSize(20)
        welcome_font.setBold(True)
        welcome.setFont(welcome_font)
        welcome.setAlignment(Qt.AlignCenter)

        rol_label = QLabel("Rol: Jefe de Laboratorio")
        rol_label.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(welcome)
        layout.addWidget(rol_label)
        layout.addStretch()

        bottom = QHBoxLayout()
        bottom.addStretch()
        logout_btn = QPushButton("Cerrar sesión")
        logout_btn.setFixedWidth(160)
        logout_btn.clicked.connect(self._on_logout_clicked)
        bottom.addWidget(logout_btn)
        layout.addLayout(bottom)

        self.setCentralWidget(central)

    def _on_logout_clicked(self) -> None:
        self.logout_requested.emit()
