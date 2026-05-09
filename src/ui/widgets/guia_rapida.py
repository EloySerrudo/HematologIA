"""Footer strip with the four-step quick guide for the Captura screen.

Mirrors the «Guía Rápida» row from ``CapturaImagen.png``: four numbered
steps laid out horizontally with an icon, a title and a one-line description.
"""
from __future__ import annotations

from typing import Optional

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


_STEPS: list[tuple[str, str, str]] = [
    ("fa5s.vial",         "Prepara la muestra",  "Coloca la lámina en el portamuestras"),
    ("fa5s.crosshairs",   "Enfoca la imagen",    "Ajusta el enfoque del microscopio"),
    ("fa5s.camera",       "Captura o sube",      "Dispará una captura o subí una imagen"),
    ("fa5s.microscope",   "Analiza",             "El sistema cuenta las células automáticamente"),
]

_ACCENT = "#1E40AF"


class GuiaRapida(QFrame):
    """Bordered frame with the 4 capture-flow steps in a single row."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("guiaRapida")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(8)

        title = QLabel("Guía Rápida")
        title.setObjectName("sectionTitle")
        tfont = QFont()
        tfont.setPointSize(12)
        tfont.setBold(True)
        title.setFont(tfont)

        steps_row = QHBoxLayout()
        steps_row.setSpacing(8)
        for idx, (icon, t, desc) in enumerate(_STEPS, start=1):
            steps_row.addWidget(self._build_step(idx, icon, t, desc), stretch=1)

        outer.addWidget(title)
        outer.addLayout(steps_row)

    @staticmethod
    def _build_step(number: int, icon_name: str, title: str, description: str) -> QFrame:
        step = QFrame()
        step.setObjectName("guiaStep")
        step.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        h = QHBoxLayout(step)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(10)

        # Numbered circle
        badge = QLabel(str(number))
        badge.setObjectName("guiaBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(28, 28)
        badge.setStyleSheet(
            f"QLabel#guiaBadge {{ background-color: {_ACCENT}; "
            f"color: white; border-radius: 14px; font-weight: 700; font-size: 12px; }}"
        )

        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=_ACCENT).pixmap(16, 16))
        icon_label.setFixedSize(16, 16)

        # Text block
        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        text_box.setContentsMargins(0, 0, 0, 0)

        t_label = QLabel(title)
        t_label.setObjectName("guiaStepTitle")

        d_label = QLabel(description)
        d_label.setObjectName("guiaStepDesc")
        d_label.setWordWrap(True)

        text_box.addWidget(t_label)
        text_box.addWidget(d_label)

        h.addWidget(badge)
        h.addWidget(icon_label)
        h.addLayout(text_box, stretch=1)
        return step
