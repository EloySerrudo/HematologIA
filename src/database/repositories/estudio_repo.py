"""Repository for the ``estudios`` table."""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.database.connection import get_connection
from src.database.models import Estudio


def _row_to_estudio(row: sqlite3.Row) -> Estudio:
    return Estudio(
        id_estudio=row["id_estudio"],
        id_paciente=row["id_paciente"],
        id_operario=row["id_operario"],
        id_muestra=row["id_muestra"],
        procedencia=row["procedencia"],
        fecha_creacion=row["fecha_creacion"],
        fecha_analisis=row["fecha_analisis"],
        duracion_segundos=row["duracion_segundos"],
        observaciones=row["observaciones"],
    )


def get_by_id(id_estudio: int) -> Optional[Estudio]:
    """Fetch an estudio by its primary key."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM estudios WHERE id_estudio = ?",
            (id_estudio,),
        ).fetchone()
    return _row_to_estudio(row) if row else None


def get_by_id_muestra(id_muestra: str) -> Optional[Estudio]:
    """Fetch an estudio by its (unique) id_muestra."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM estudios WHERE id_muestra = ?",
            (id_muestra,),
        ).fetchone()
    return _row_to_estudio(row) if row else None


def create(
    *,
    id_paciente: int,
    id_operario: int,
    id_muestra: str,
    procedencia: str,
    observaciones: Optional[str] = None,
) -> Estudio:
    """Insert a pending estudio (no analysis run yet). Returns the new dataclass."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO estudios
                (id_paciente, id_operario, id_muestra, procedencia, observaciones)
            VALUES (?, ?, ?, ?, ?)
            """,
            (id_paciente, id_operario, id_muestra, procedencia, observaciones),
        )
        new_id = cursor.lastrowid

    estudio = get_by_id(new_id)
    assert estudio is not None, "Just-inserted estudio disappeared from DB"
    return estudio
