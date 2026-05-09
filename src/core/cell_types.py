"""Catálogo de tipos de células reportadas por el modelo de IA.

The order in :data:`CELL_TYPES` is the order in which categories appear in the
pre-report table on the Captura screen — kept exactly as the lab specified
(maturation-aware sequence: blastos → granulocíticas inmaduras → maduras).

In Fase 1 there is no IA yet, so counts are always zero. When the model lands
in Fase 2, it will produce per-image classifications keyed by these labels.
At that point we'll likely add a `conteos` table; for now we keep the catalog
in code only to avoid premature schema changes.
"""
from __future__ import annotations


# Ordered list — preserve the exact sequence; the table renders rows in this order.
CELL_TYPES: tuple[str, ...] = (
    "Blastos",
    "Metamielocitos",
    "Mielocitos",
    "Promielocitos",
    "Basófilos",
    "Eosinófilos",
    "Linfocitos",
    "Monocitos",
    "Neutrófilos",
)


def empty_counts() -> dict[str, int]:
    """Return a zeroed-out count dict for every category, in catalog order."""
    return {name: 0 for name in CELL_TYPES}
