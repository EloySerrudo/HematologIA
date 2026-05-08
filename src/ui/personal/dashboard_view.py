"""Dashboard content for the Personal main window.

Composes the greeting, the four stat cards, and the four quick-action
cards. All numeric values come from ``dashboard_repo.get_personal_stats``.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.logger import get_logger
from src.database.models import DashboardStats, Operario
from src.database.repositories.dashboard_repo import get_personal_stats
from src.ui.widgets.coming_soon import show_coming_soon
from src.ui.widgets.quick_action_card import QuickActionCard
from src.ui.widgets.stat_card import StatCard

_logger = get_logger(__name__)


# Accent colours, kept in sync with the design reference (DashboardPersonal.png)
_COLOR_BLUE = "#2563EB"
_COLOR_GREEN = "#059669"
_COLOR_ORANGE = "#EA580C"
_COLOR_PURPLE = "#7C3AED"


class DashboardView(QWidget):
    """Scrollable main view: greeting + stat cards + quick actions."""

    quick_action_triggered = Signal(str)  # emits the action key, mostly for logging

    def __init__(self, operario: Operario, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardView")
        self._operario = operario
        self._build_ui()
        self.refresh_stats()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # The whole dashboard is wrapped in a scroll area so it stays usable
        # on smaller screens.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("dashboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("dashboardContent")
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        layout.addLayout(self._build_greeting())
        layout.addWidget(self._build_stats_grid())
        layout.addWidget(self._build_quick_actions_section())
        layout.addStretch()

    def _build_greeting(self) -> QVBoxLayout:
        block = QVBoxLayout()
        block.setSpacing(2)

        greeting = QLabel(
            f"¡{self._operario.saludo}, {self._operario.nombre_con_titulo}!"
        )
        greeting.setObjectName("dashboardGreeting")
        greeting_font = QFont()
        greeting_font.setPointSize(20)
        greeting_font.setBold(True)
        greeting.setFont(greeting_font)

        subtitle = QLabel("¿Qué deseas hacer hoy?")
        subtitle.setObjectName("dashboardSubtitle")

        block.addWidget(greeting)
        block.addWidget(subtitle)
        return block

    def _build_stats_grid(self) -> QFrame:
        wrap = QFrame()
        wrap.setObjectName("statsRowWrapper")

        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        self._card_imagenes = StatCard(
            icon_name="fa5s.camera",
            title="Imágenes Capturadas",
            accent_color=_COLOR_BLUE,
        )
        self._card_analisis = StatCard(
            icon_name="fa5s.microscope",
            title="Análisis Realizados",
            accent_color=_COLOR_GREEN,
        )
        self._card_reportes = StatCard(
            icon_name="fa5s.file-alt",
            title="Reportes Generados",
            accent_color=_COLOR_ORANGE,
        )
        self._card_tiempo = StatCard(
            icon_name="fa5s.clock",
            title="Tiempo de Análisis",
            accent_color=_COLOR_PURPLE,
        )

        grid.addWidget(self._card_imagenes, 0, 0)
        grid.addWidget(self._card_analisis, 0, 1)
        grid.addWidget(self._card_reportes, 0, 2)
        grid.addWidget(self._card_tiempo,   0, 3)

        for col in range(4):
            grid.setColumnStretch(col, 1)

        return wrap

    def _build_quick_actions_section(self) -> QFrame:
        wrap = QFrame()
        wrap.setObjectName("quickActionsSection")

        v = QVBoxLayout(wrap)
        v.setContentsMargins(20, 18, 20, 20)
        v.setSpacing(14)

        title = QLabel("Mis Accesos Rápidos")
        title.setObjectName("sectionTitle")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        actions = [
            ("captura", "fa5s.camera",      "Captura de Imagen", "Capturar nueva imagen para análisis", "Ir a Captura",   _COLOR_BLUE),
            ("analisis","fa5s.microscope",  "Realizar Análisis", "Analizar imágenes y obtener resultados", "Ir a Análisis",  _COLOR_GREEN),
            ("estudios","fa5s.folder-open", "Mis Estudios",      "Consulta tus estudios realizados",       "Ver Estudios",   _COLOR_ORANGE),
            ("reportes","fa5s.file-pdf",    "Generar Reporte",   "Genera y descarga reportes de resultados", "Ir a Reportes", _COLOR_PURPLE),
        ]

        for col, (key, icon, t, desc, btn_label, color) in enumerate(actions):
            card = QuickActionCard(
                icon_name=icon,
                title=t,
                description=desc,
                button_label=btn_label,
                accent_color=color,
            )
            card.clicked.connect(lambda _checked=False, k=key, name=t: self._on_quick_action(k, name))
            grid.addWidget(card, 0, col)
            grid.setColumnStretch(col, 1)

        v.addWidget(title)
        v.addLayout(grid)
        return wrap

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def _on_quick_action(self, key: str, label: str) -> None:
        _logger.info("Quick action triggered: %s", key)
        self.quick_action_triggered.emit(key)
        show_coming_soon(self, label)

    def refresh_stats(self) -> None:
        """Re-fetch dashboard stats from the DB and update the cards."""
        try:
            stats: DashboardStats = get_personal_stats(self._operario.id_operario)
        except Exception as exc:
            _logger.error("Failed to fetch dashboard stats: %s", exc)
            return

        self._card_imagenes.set_value(str(stats.imagenes_capturadas_hoy))
        self._card_analisis.set_value(str(stats.analisis_realizados_hoy))
        self._card_reportes.set_value(str(stats.reportes_generados_hoy))
        self._card_tiempo.set_value(_format_duration(stats.duracion_promedio_segundos))


def _format_duration(seconds: Optional[float]) -> str:
    """Format a duration in seconds for display in the stat card.

    Examples:
        None  -> "—"
        45.5  -> "45 s"
        72.0  -> "1 m 12 s"
        3700  -> "1 h 1 m"
    """
    if seconds is None:
        return "—"
    s = int(round(seconds))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        minutes, secs = divmod(s, 60)
        if secs == 0:
            return f"{minutes} m"
        return f"{minutes} m {secs} s"
    hours, rem = divmod(s, 3600)
    minutes = rem // 60
    if minutes == 0:
        return f"{hours} h"
    return f"{hours} h {minutes} m"
