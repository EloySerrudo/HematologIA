"""Repository for the ``operarios`` table.

Encapsulates SQL access for the ``Operario`` model. Other layers must go
through this module instead of issuing SQL directly.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from src.database.connection import get_connection
from src.database.models import Operario


def _row_to_operario(row: sqlite3.Row) -> Operario:
    """Convert a SQLite row into an ``Operario`` dataclass."""
    return Operario(
        id_operario=row["id_operario"],
        nombre=row["nombre"],
        apellido_paterno=row["apellido_paterno"],
        apellido_materno=row["apellido_materno"],
        usuario=row["usuario"],
        password_hash=row["password_hash"],
        rol=row["rol"],
        activo=bool(row["activo"]),
        fecha_creacion=row["fecha_creacion"],
        ultimo_acceso=row["ultimo_acceso"],
    )


def get_by_usuario(usuario: str) -> Optional[Operario]:
    """Fetch an operario by ``usuario``. Returns None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM operarios WHERE usuario = ?",
            (usuario,),
        ).fetchone()
    return _row_to_operario(row) if row else None


def update_ultimo_acceso(id_operario: int) -> None:
    """Set ``ultimo_acceso`` to the current timestamp for the given operario."""
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            "UPDATE operarios SET ultimo_acceso = ? WHERE id_operario = ?",
            (now, id_operario),
        )
