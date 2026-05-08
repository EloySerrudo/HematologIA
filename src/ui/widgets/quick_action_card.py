"""Quick-action card used in the "Mis Accesos Rápidos" section.

Bigger and richer than ``StatCard``: shows a coloured icon, a title, a
description, and a primary button at the bottom that emits ``clicked``
when pressed.
"""
from __future__ import annotations

from typing import Optional

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class QuickActionCard(QFrame):
    """Tile with icon, title, description and a coloured CTA button."""

    clicked = Signal()

    def __init__(
        self,
        *,
        icon_name: str,
        title: str,
        description: str,
        button_label: str,
        accent_color: str,
        parent: Optional[QFrame] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("quickActionCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._accent_color = accent_color
        self._build_ui(icon_name, title, description, button_label)

    def _build_ui(self, icon_name: str, title: str, description: str, button_label: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # --- Top: icon + title row ---
        top = QHBoxLayout()
        top.setSpacing(12)

        icon_box = QFrame()
        icon_box.setObjectName("quickIconBox")
        icon_box.setFixedSize(48, 48)
        icon_box.setStyleSheet(
            f"""
            QFrame#quickIconBox {{
                background-color: {self._accent_color}1F;
                border-radius: 12px;
            }}
            """
        )
        icon_label = QLabel(icon_box)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setGeometry(0, 0, 48, 48)
        icon_label.setPixmap(qta.icon(icon_name, color=self._accent_color).pixmap(24, 24))

        title_label = QLabel(title)
        title_label.setObjectName("quickTitle")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_label.setFont(title_font)

        top.addWidget(icon_box)
        top.addWidget(title_label, stretch=1)

        # --- Description ---
        desc_label = QLabel(description)
        desc_label.setObjectName("quickDescription")
        desc_label.setWordWrap(True)

        # --- CTA button ---
        button = QPushButton(button_label)
        button.setObjectName("quickButton")
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(38)
        button.setStyleSheet(
            f"""
            QPushButton#quickButton {{
                background-color: {self._accent_color};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 12px;
            }}
            QPushButton#quickButton:hover {{
                background-color: {self._accent_color}E0;
            }}
            QPushButton#quickButton:pressed {{
                background-color: {self._accent_color}C0;
            }}
            """
        )
        button.clicked.connect(self.clicked)

        layout.addLayout(top)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addWidget(button)
