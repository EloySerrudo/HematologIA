"""Horizontal scrollable strip of capture thumbnails.

Each captured image is shown as a small bordered tile (``THUMB_W × THUMB_H``).
The strip is wrapped in a horizontal ``QScrollArea`` so older captures stay
visible to the left while new ones get appended to the right.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


THUMB_W = 96
THUMB_H = 72


class ThumbnailStrip(QWidget):
    """Scrollable horizontal row of small image thumbnails."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("thumbnailStrip")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("thumbnailScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setFixedHeight(THUMB_H + 26)  # leave room for the scrollbar

        self._inner = QWidget()
        self._inner.setObjectName("thumbnailStripInner")
        self._strip_layout = QHBoxLayout(self._inner)
        self._strip_layout.setContentsMargins(8, 8, 8, 8)
        self._strip_layout.setSpacing(8)
        self._strip_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Placeholder shown when there are no captures yet.
        self._placeholder = QLabel("Sin capturas todavía. Dispará «Capturar» para empezar.")
        self._placeholder.setObjectName("thumbnailPlaceholder")
        self._placeholder.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        self._strip_layout.addWidget(self._placeholder)
        self._strip_layout.addStretch()

        self._scroll.setWidget(self._inner)
        layout.addWidget(self._scroll)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def add_thumbnail(self, image_path: Path | str) -> None:
        """Append a thumbnail for ``image_path`` to the right end of the strip."""
        # Drop placeholder once we have at least one real thumbnail.
        if self._placeholder is not None:
            self._placeholder.setParent(None)
            self._placeholder.deleteLater()
            self._placeholder = None

        tile = self._make_tile(Path(image_path))
        # Insert before the trailing stretch so the row stays left-aligned.
        insert_at = max(0, self._strip_layout.count() - 1)
        self._strip_layout.insertWidget(insert_at, tile)

        # Auto-scroll to the right so the new tile is visible.
        bar = self._scroll.horizontalScrollBar()
        # Defer to the next event loop tick — geometry isn't valid yet.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    def add_pixmap(self, pix: QPixmap) -> None:
        """Append a thumbnail directly from an in-memory ``QPixmap``."""
        if self._placeholder is not None:
            self._placeholder.setParent(None)
            self._placeholder.deleteLater()
            self._placeholder = None
        tile = self._make_tile_from_pixmap(pix)
        insert_at = max(0, self._strip_layout.count() - 1)
        self._strip_layout.insertWidget(insert_at, tile)
        from PySide6.QtCore import QTimer
        bar = self._scroll.horizontalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    def clear(self) -> None:
        """Remove all thumbnails and restore the placeholder."""
        while self._strip_layout.count():
            item = self._strip_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._placeholder = QLabel("Sin capturas todavía. Dispará «Capturar» para empezar.")
        self._placeholder.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        self._strip_layout.addWidget(self._placeholder)
        self._strip_layout.addStretch()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _make_tile(self, image_path: Path) -> QFrame:
        pix = QPixmap(str(image_path))
        return self._make_tile_from_pixmap(pix)

    @staticmethod
    def _make_tile_from_pixmap(pix: QPixmap) -> QFrame:
        tile = QFrame()
        tile.setObjectName("thumbnailTile")
        tile.setFixedSize(THUMB_W, THUMB_H)
        tile.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        label = QLabel(tile)
        label.setGeometry(0, 0, THUMB_W, THUMB_H)
        label.setAlignment(Qt.AlignCenter)
        if not pix.isNull():
            label.setPixmap(pix.scaled(
                THUMB_W, THUMB_H,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            ))
        else:
            label.setText("?")
        return tile
