"""Sidebar widget for the role main windows.

Layout (top → bottom):
  * Hospital logo (white-on-blue) + app subtitle
  * Vertical navigation buttons (one active, others "próximamente" stubs)
  * Spacer
  * Logout button
  * Smaller hospital logo at the very bottom

The sidebar is role-agnostic: the caller passes the list of nav items it
wants to expose, and the sidebar takes care of selection state, signals
and styling. This way Personal and Jefe can reuse the same widget with
different menus.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config import APP_DISPLAY_NAME, ASSET_LOGO_HOSPITAL_WHITE


SIDEBAR_WIDTH = 240


@dataclass(frozen=True)
class NavItem:
    """Definition of a single navigation entry in the sidebar."""

    key: str                # stable id, used to track the active item
    label: str              # text shown in the button
    icon_name: str          # qtawesome icon name
    enabled: bool = True    # if False, the click triggers a "Próximamente" notice


class Sidebar(QFrame):
    """Vertical navigation bar shown on the left of role main windows."""

    nav_clicked = Signal(str)       # emits the NavItem.key that was clicked
    logout_requested = Signal()

    def __init__(
        self,
        items: list[NavItem],
        *,
        active_key: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self._items = items
        self._buttons: dict[str, QPushButton] = {}
        self._active_key = active_key or (items[0].key if items else None)

        self._build_ui()
        if self._active_key:
            self._update_active_state()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 24, 0, 18)
        layout.setSpacing(0)

        # --- Top: hospital logo + app subtitle ---
        layout.addWidget(self._build_brand_block())
        layout.addSpacing(28)

        # --- Nav items ---
        for item in self._items:
            btn = self._build_nav_button(item)
            self._buttons[item.key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # --- Logout ---
        logout_btn = QPushButton("Cerrar Sesión")
        logout_btn.setObjectName("logoutButton")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setIcon(qta.icon("fa5s.sign-out-alt", color="#FFFFFF"))
        logout_btn.setMinimumHeight(40)
        logout_btn.clicked.connect(self.logout_requested)
        wrap = QHBoxLayout()
        wrap.setContentsMargins(16, 0, 16, 0)
        wrap.addWidget(logout_btn)
        layout.addLayout(wrap)

        layout.addSpacing(18)

        # --- Footer logo ---
        layout.addWidget(self._build_footer_logo(), alignment=Qt.AlignHCenter)

    def _build_brand_block(self) -> QFrame:
        block = QFrame()
        block.setObjectName("sidebarBrand")
        v = QVBoxLayout(block)
        v.setContentsMargins(20, 0, 20, 0)
        v.setSpacing(6)
        v.setAlignment(Qt.AlignHCenter)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        pix = QPixmap(str(ASSET_LOGO_HOSPITAL_WHITE))
        if not pix.isNull():
            logo.setPixmap(pix.scaledToWidth(180, Qt.SmoothTransformation))

        subtitle = QLabel(APP_DISPLAY_NAME)
        subtitle.setObjectName("sidebarSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        v.addWidget(logo)
        v.addWidget(subtitle)
        return block

    def _build_nav_button(self, item: NavItem) -> QPushButton:
        btn = QPushButton(f"  {item.label}")
        btn.setObjectName("sidebarNavButton")
        btn.setProperty("active", False)
        btn.setProperty("nav_key", item.key)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(44)
        btn.setIcon(qta.icon(item.icon_name, color="#BFDBFE"))
        btn.setLayoutDirection(Qt.LeftToRight)
        btn.setIconSize(qta.icon(item.icon_name).pixmap(18, 18).size())
        btn.clicked.connect(lambda _checked=False, k=item.key: self.nav_clicked.emit(k))

        # Wrap in a horizontal layout so we can give the button its own L/R margin
        # without affecting the rest of the sidebar.
        return btn

    def _build_footer_logo(self) -> QLabel:
        logo = QLabel()
        logo.setObjectName("sidebarFooterLogo")
        logo.setAlignment(Qt.AlignCenter)
        pix = QPixmap(str(ASSET_LOGO_HOSPITAL_WHITE))
        if not pix.isNull():
            logo.setPixmap(pix.scaledToWidth(110, Qt.SmoothTransformation))
        return logo

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def set_active(self, key: str) -> None:
        """Mark ``key`` as the currently active nav item."""
        self._active_key = key
        self._update_active_state()

    def _update_active_state(self) -> None:
        for key, btn in self._buttons.items():
            is_active = key == self._active_key
            btn.setProperty("active", is_active)
            # Re-tint icon to match active state.
            for item in self._items:
                if item.key != key:
                    continue
                color = "#FFFFFF" if is_active else "#BFDBFE"
                btn.setIcon(qta.icon(item.icon_name, color=color))
            btn.style().unpolish(btn)
            btn.style().polish(btn)
