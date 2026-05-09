"""Modal help popup with the contextual quick-guide for the current view.

Triggered from the help button on the app header. Each entry in
:data:`HELP_TOPICS` describes one topic with a title and an ordered list of
``(icon_name, step_title, step_description)`` tuples.

The popup applies an explicit light theme so it ignores the system's dark
mode (same approach as :class:`PacientePickerDialog`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config import APP_DISPLAY_NAME

_PRIMARY = "#1E40AF"


@dataclass(frozen=True)
class HelpStep:
    """One numbered entry inside a help topic."""

    icon_name: str
    title: str
    description: str


@dataclass(frozen=True)
class HelpTopic:
    """A complete help topic: title + ordered steps."""

    title: str
    intro: str
    steps: tuple[HelpStep, ...]


# --- Topics by view key (matches the sidebar nav keys) ---
HELP_TOPICS: dict[str, HelpTopic] = {
    "captura": HelpTopic(
        title="Cómo capturar imágenes",
        intro=(
            "Seguí estos pasos para capturar campos del frotis sanguíneo. "
            "Mientras vas capturando, el sistema cuenta automáticamente las células "
            "encontradas y arma el pre-reporte."
        ),
        steps=(
            HelpStep("fa5s.vial",       "Prepará la muestra",
                    "Colocá la lámina del frotis en el portamuestras del microscopio."),
            HelpStep("fa5s.crosshairs", "Enfocá la imagen",
                    "Ajustá el enfoque del microscopio hasta ver las células nítidas en el preview."),
            HelpStep("fa5s.camera",     "Capturá o subí",
                    "Disparás «Capturar» para tomar el campo en vivo, o «Subir imagen» para cargar una existente."),
            HelpStep("fa5s.microscope", "Análisis automático",
                    "Cada captura se analiza y suma a la tabla de pre-reporte. Cuando termines, generá el reporte final."),
        ),
    ),
    "dashboard": HelpTopic(
        title="Sobre el Dashboard",
        intro=(
            "El dashboard muestra un resumen de tu actividad del día y atajos a las "
            "tareas más comunes."
        ),
        steps=(
            HelpStep("fa5s.chart-bar", "Métricas de hoy",
                    "Las cuatro tarjetas superiores muestran cuántas imágenes capturaste, "
                    "análisis hiciste, reportes generaste y el tiempo promedio por análisis."),
            HelpStep("fa5s.bolt",      "Accesos rápidos",
                    "Las cuatro tarjetas inferiores te llevan directo a las funciones principales."),
        ),
    ),
}


class HelpDialog(QDialog):
    """Modal popup that renders one :class:`HelpTopic`."""

    def __init__(self, topic: HelpTopic, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} — Ayuda")
        self.setModal(True)
        self.setMinimumWidth(520)
        self._apply_light_theme()
        self._build_ui(topic)

    @classmethod
    def show_for_key(cls, key: str, parent: Optional[QWidget] = None) -> None:
        """Show the topic associated with ``key``. Falls back to the dashboard topic."""
        topic = HELP_TOPICS.get(key) or HELP_TOPICS["dashboard"]
        cls(topic, parent=parent).exec()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_light_theme(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #FFFFFF;
                color: #111827;
            }
            QLabel {
                color: #111827;
                background: transparent;
                font-family: "Segoe UI", "Inter", "Arial", sans-serif;
                font-size: 12px;
            }
            QFrame#helpStep {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
            QPushButton#helpCloseButton {
                background-color: #1E40AF;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 12px;
                min-width: 110px;
            }
            QPushButton#helpCloseButton:hover { background-color: #1D4ED8; }
            """
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self, topic: HelpTopic) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(12)

        # Header: icon + title
        head = QHBoxLayout()
        head.setSpacing(10)
        head_icon = QLabel()
        head_icon.setPixmap(qta.icon("fa5s.question-circle", color=_PRIMARY).pixmap(22, 22))
        head_icon.setFixedSize(22, 22)
        title = QLabel(topic.title)
        tfont = QFont()
        tfont.setPointSize(14)
        tfont.setBold(True)
        title.setFont(tfont)
        head.addWidget(head_icon)
        head.addWidget(title, stretch=1)
        outer.addLayout(head)

        # Intro paragraph
        intro = QLabel(topic.intro)
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #6B7280; font-size: 12px;")
        outer.addWidget(intro)

        # Steps stack
        for idx, step in enumerate(topic.steps, start=1):
            outer.addWidget(self._build_step(idx, step))

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Entendido")
        close_btn.setObjectName("helpCloseButton")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        outer.addLayout(btn_row)

    @staticmethod
    def _build_step(number: int, step: HelpStep) -> QFrame:
        frame = QFrame()
        frame.setObjectName("helpStep")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        h = QHBoxLayout(frame)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(12)

        # Numbered circle
        badge = QLabel(str(number))
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(28, 28)
        badge.setStyleSheet(
            f"background-color: {_PRIMARY}; color: white; "
            "border-radius: 14px; font-weight: 700; font-size: 12px;"
        )

        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(step.icon_name, color=_PRIMARY).pixmap(18, 18))
        icon_label.setFixedSize(18, 18)

        # Text block
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        text_box.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(step.title)
        title_label.setStyleSheet("color: #111827; font-size: 12px; font-weight: 700;")
        desc_label = QLabel(step.description)
        desc_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        desc_label.setWordWrap(True)
        text_box.addWidget(title_label)
        text_box.addWidget(desc_label)

        h.addWidget(badge)
        h.addWidget(icon_label)
        h.addLayout(text_box, stretch=1)
        return frame
