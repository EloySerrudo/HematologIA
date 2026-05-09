"""QMainWindow scaffold shared by Personal and Jefe.

Composes a left sidebar + a top header + a swappable content area in the
centre. Subclasses (or callers) inject the nav items and the initial
content widget; the shell takes care of the framing and surfaces the
sidebar signals (``nav_clicked`` / ``logout_requested``).
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.config import APP_DISPLAY_NAME, APP_VERSION, DASHBOARD_QSS_PATH
from src.core.logger import get_logger
from src.database.models import Operario
from src.ui.shell.header import Header
from src.ui.shell.sidebar import NavItem, Sidebar

_logger = get_logger(__name__)


FOOTER_HEIGHT = 32


class MainShell(QMainWindow):
    """Sidebar + header + content shell, generic over the role.

    Signals:
        nav_clicked(str): forwarded from the sidebar.
        logout_requested(): emitted when the user clicks "Cerrar Sesión".
    """

    nav_clicked = Signal(str)
    logout_requested = Signal()
    help_requested = Signal()

    def __init__(
        self,
        *,
        operario: Operario,
        nav_items: list[NavItem],
        active_nav_key: str,
        title_suffix: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} — {title_suffix}")
        self.setMinimumSize(1100, 700)

        self._operario = operario
        self._build_ui(nav_items, active_nav_key)
        self._load_stylesheet()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, nav_items: list[NavItem], active_nav_key: str) -> None:
        central = QWidget()
        central.setObjectName("shellRoot")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = Sidebar(nav_items, active_key=active_nav_key)
        self.sidebar.nav_clicked.connect(self.nav_clicked)
        self.sidebar.logout_requested.connect(self.logout_requested)
        root.addWidget(self.sidebar)

        # --- Right column: header + content + footer ---
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)

        self.header = Header(self._operario)
        self.header.help_requested.connect(self.help_requested)
        right_col.addWidget(self.header)

        self.content_area = QStackedWidget()
        self.content_area.setObjectName("contentArea")
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_col.addWidget(self.content_area, stretch=1)

        right_col.addWidget(self._build_footer())

        right_wrapper = QWidget()
        right_wrapper.setLayout(right_col)
        root.addWidget(right_wrapper, stretch=1)

        self.setCentralWidget(central)

    def _build_footer(self) -> QFrame:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QLabel

        footer = QFrame()
        footer.setObjectName("appFooter")
        footer.setFixedHeight(FOOTER_HEIGHT)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(28, 0, 28, 0)

        copyright_label = QLabel(
            "© 2025 Hospital Solomon Klein - Laboratorio de Análisis Clínicos"
        )
        copyright_label.setObjectName("footerCopyright")

        version_label = QLabel(f"Versión {APP_VERSION}")
        version_label.setObjectName("footerVersion")

        layout.addWidget(copyright_label, alignment=Qt.AlignVCenter)
        layout.addStretch()
        layout.addWidget(version_label, alignment=Qt.AlignVCenter)
        return footer

    def _load_stylesheet(self) -> None:
        try:
            self.setStyleSheet(DASHBOARD_QSS_PATH.read_text(encoding="utf-8"))
        except OSError as exc:
            _logger.warning("Could not load dashboard.qss: %s", exc)

    # ------------------------------------------------------------------
    # Content management
    # ------------------------------------------------------------------

    def set_content(self, widget: QWidget) -> None:
        """Replace the current content widget with ``widget``."""
        # Drop previous widgets to avoid leaking memory across role switches.
        while self.content_area.count():
            old = self.content_area.widget(0)
            self.content_area.removeWidget(old)
            old.deleteLater()
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)
