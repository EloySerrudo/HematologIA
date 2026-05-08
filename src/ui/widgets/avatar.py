"""Circular avatar widget showing two-letter initials.

Used in the header to identify the logged-in operario without needing a
photo. The background colour is derived deterministically from the
initials so the same user always gets the same colour.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


# Soft palette of distinct hues. Indexing into it by hashing the initials
# gives every user a stable, accessible colour.
_PALETTE: tuple[str, ...] = (
    "#1E40AF",  # blue
    "#0E7490",  # cyan
    "#047857",  # emerald
    "#B45309",  # amber
    "#BE185D",  # pink
    "#6D28D9",  # purple
    "#DC2626",  # red
    "#0F766E",  # teal
)


class InitialsAvatar(QWidget):
    """Filled circle with two letters centred on top.

    The background colour is derived from the initials so it stays stable
    across sessions for the same user.
    """

    def __init__(self, initials: str, size: int = 40, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._initials = (initials or "?").upper()[:2]
        self._size = size
        self.setFixedSize(size, size)
        self._color = QColor(_PALETTE[hash(self._initials) % len(_PALETTE)])

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Filled circle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(0, 0, self._size, self._size)

        # Centred initials
        painter.setPen(QPen(QColor("#FFFFFF")))
        font = QFont()
        font.setPointSize(max(8, int(self._size * 0.36)))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self._initials)
