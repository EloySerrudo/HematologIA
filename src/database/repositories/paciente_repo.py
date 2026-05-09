"""Repository for the ``pacientes`` table.

Encapsulates SQL access for the ``Paciente`` model. Other layers must go
through this module instead of issuing SQL directly.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.database.connection import get_connection
from src.database.models import Paciente


def _row_to_paciente(row: sqlite3.Row) -> Paciente:
    """Convert a SQLite row into a ``Paciente`` dataclass."""
    return Paciente(
        id_paciente=row["id_paciente"],
        historia_clinica=row["historia_clinica"],
        id_paciente_hospital=row["id_paciente_hospital"],
        nombre=row["nombre"],
        apellido_paterno=row["apellido_paterno"],
        apellido_materno=row["apellido_materno"],
        fecha_nacimiento=row["fecha_nacimiento"],
        genero=row["genero"],
        documento=row["documento"],
        fecha_creacion=row["fecha_creacion"],
    )


def get_by_id(id_paciente: int) -> Optional[Paciente]:
    """Fetch a paciente by its primary key. Returns None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM pacientes WHERE id_paciente = ?",
            (id_paciente,),
        ).fetchone()
    return _row_to_paciente(row) if row else None


def get_by_historia_clinica(historia_clinica: str) -> Optional[Paciente]:
    """Fetch a paciente by its (unique) historia_clinica code."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM pacientes WHERE historia_clinica = ?",
            (historia_clinica,),
        ).fetchone()
    return _row_to_paciente(row) if row else None


def get_by_id_hospital(id_paciente_hospital: str) -> Optional[Paciente]:
    """Fetch a paciente by its (unique) hospital file system id."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM pacientes WHERE id_paciente_hospital = ?",
            (id_paciente_hospital,),
        ).fetchone()
    return _row_to_paciente(row) if row else None


def create(
    *,
    historia_clinica: str,
    id_paciente_hospital: str,
    nombre: str,
    apellido_paterno: str,
    apellido_materno: Optional[str] = None,
    fecha_nacimiento: Optional[str] = None,  # ISO 'YYYY-MM-DD'
    genero: Optional[str] = None,             # 'M' | 'F' | None
    documento: Optional[str] = None,
) -> Paciente:
    """Insert a new paciente. Returns the freshly created dataclass.

    Raises:
        sqlite3.IntegrityError if any UNIQUE constraint is violated
        (historia_clinica / id_paciente_hospital / documento already in DB).
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO pacientes
                (historia_clinica, id_paciente_hospital,
                 nombre, apellido_paterno, apellido_materno,
                 fecha_nacimiento, genero, documento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                historia_clinica,
                id_paciente_hospital,
                nombre,
                apellido_paterno,
                apellido_materno,
                fecha_nacimiento,
                genero,
                documento,
            ),
        )
        new_id = cursor.lastrowid

    # Re-fetch so we get the auto-generated fecha_creacion in a single shape.
    paciente = get_by_id(new_id)
    assert paciente is not None, "Just-inserted paciente disappeared from DB"
    return paciente
