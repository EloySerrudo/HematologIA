"""Repository for the ``capturas`` table."""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.database.connection import get_connection
from src.database.models import Captura


def _row_to_captura(row: sqlite3.Row) -> Captura:
    return Captura(
        id_captura=row["id_captura"],
        id_estudio=row["id_estudio"],
        path_imagen=row["path_imagen"],
        fecha_captura=row["fecha_captura"],
        notas=row["notas"],
    )


def list_by_estudio(id_estudio: int) -> list[Captura]:
    """Return all capturas for an estudio, ordered by capture date (oldest first)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM capturas WHERE id_estudio = ? ORDER BY fecha_captura ASC",
            (id_estudio,),
        ).fetchall()
    return [_row_to_captura(r) for r in rows]


def count_by_estudio(id_estudio: int) -> int:
    """Return how many capturas an estudio has."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM capturas WHERE id_estudio = ?",
            (id_estudio,),
        ).fetchone()
    return int(row["n"] or 0)


def create(
    *,
    id_estudio: int,
    path_imagen: str,                # relative to data/capturas/
    notas: Optional[str] = None,
) -> Captura:
    """Insert a new captura row. Returns the freshly created dataclass."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO capturas (id_estudio, path_imagen, notas)
            VALUES (?, ?, ?)
            """,
            (id_estudio, path_imagen, notas),
        )
        new_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM capturas WHERE id_captura = ?",
            (new_id,),
        ).fetchone()
    return _row_to_captura(row)
