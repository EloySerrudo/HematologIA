"""Stat card used in the dashboard's metrics row.

Each card shows a coloured icon on the left and a stack on the right with
a small "Hoy" caption, a big number, and a description. The accent colour
parameterises the icon background and the icon glyph itself.
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
)


class StatCard(QFrame):
    """Single metric card: icon + caption + value + description."""

    def __init__(
        self,
        *,
        icon_name: str,
        title: str,
        accent_color: str,
        caption: str = "Hoy",
        parent: Optional[QFrame] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._accent_color = accent_color
        self._build_ui(icon_name, title, caption)
        # Initial value is a placeholder — set_value() will replace it.
        self.set_value("—")

    def _build_ui(self, icon_name: str, title: str, caption: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # --- Icon (rounded square with translucent accent background) ---
        icon_box = QFrame()
        icon_box.setObjectName("statIconBox")
        icon_box.setFixedSize(44, 44)
        icon_box.setStyleSheet(
            f"""
            QFrame#statIconBox {{
                background-color: {self._accent_color}1F;  /* ~12% alpha */
                border-radius: 10px;
            }}
            """
        )
        icon_label = QLabel(icon_box)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setGeometry(0, 0, 44, 44)
        icon_label.setPixmap(qta.icon(icon_name, color=self._accent_color).pixmap(20, 20))

        # --- Right column: caption / value / title ---
        right = QVBoxLayout()
        right.setSpacing(0)
        right.setContentsMargins(0, 0, 0, 0)

        caption_label = QLabel(caption)
        caption_label.setObjectName("statCaption")

        self._value_label = QLabel("—")
        self._value_label.setObjectName("statValue")
        value_font = QFont()
        value_font.setPointSize(20)
        value_font.setBold(True)
        self._value_label.setFont(value_font)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        title_label.setWordWrap(True)

        right.addWidget(caption_label)
        right.addWidget(self._value_label)
        right.addWidget(title_label)

        layout.addWidget(icon_box)
        layout.addLayout(right, stretch=1)

    def set_value(self, value: str) -> None:
        """Update the big number / value displayed on the card."""
        self._value_label.setText(value)
