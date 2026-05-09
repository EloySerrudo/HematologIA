"""Table that shows the per-cell-type count for the current capture session.

Two columns: ``Tipo de célula`` (wide) and ``Conteo`` (narrow). One row per
entry in :data:`CELL_TYPES`, plus a footer label with the total. The
counts column is intentionally narrow so the live-view panel gets more
horizontal real estate.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.cell_types import CELL_TYPES, empty_counts


class CellCountTable(QWidget):
    """Sticky table of cell-type counts for the active session."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cellCountTable")
        self._build_ui()
        self.set_counts(empty_counts())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._table = QTableWidget(len(CELL_TYPES), 2)
        self._table.setObjectName("cellCountQTable")
        self._table.setHorizontalHeaderLabels(["Tipo de célula", "Conteo"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Column sizing: name column stretches, count column is narrow & fixed.
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self._table.setColumnWidth(1, 70)
        header.setHighlightSections(False)

        # Pre-populate rows with zero counts.
        for row, name in enumerate(CELL_TYPES):
            name_item = QTableWidgetItem(name)
            count_item = QTableWidgetItem("0")
            count_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, count_item)
            self._table.setRowHeight(row, 28)

        # Slim the table vertically: total height = header + 9 rows.
        total_h = self._table.horizontalHeader().height() + 28 * len(CELL_TYPES) + 4
        self._table.setMinimumHeight(total_h)
        self._table.setMaximumHeight(total_h)

        # Total footer
        self._total_label = QLabel("Total: 0 células")
        self._total_label.setObjectName("cellCountTotal")
        self._total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        font = QFont()
        font.setBold(True)
        self._total_label.setFont(font)

        layout.addWidget(self._table)
        layout.addWidget(self._total_label)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def set_counts(self, counts: dict[str, int]) -> None:
        """Replace all counts. ``counts`` maps cell-type name → count."""
        total = 0
        for row, name in enumerate(CELL_TYPES):
            value = int(counts.get(name, 0))
            total += value
            item = self._table.item(row, 1)
            item.setText(str(value))
        self._total_label.setText(f"Total: {total} {'célula' if total == 1 else 'células'}")

    def reset(self) -> None:
        """Reset all counts back to zero."""
        self.set_counts(empty_counts())
