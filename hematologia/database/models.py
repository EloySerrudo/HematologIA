"""Domain model dataclasses.

These are plain Python dataclasses that mirror the rows of the database tables.
Repositories convert ``sqlite3.Row`` instances into these dataclasses so the
rest of the app works with strongly-typed objects rather than dict-like rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Operario:
    """Represents a row of the ``operarios`` table."""

    id_operario: int
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    usuario: str
    password_hash: str
    rol: str  # 'jefe' | 'personal'
    activo: bool
    fecha_creacion: Optional[datetime]
    ultimo_acceso: Optional[datetime]

    @property
    def nombre_completo(self) -> str:
        """Full name as ``"{nombre} {apellido_paterno} {apellido_materno}"``.

        ``apellido_materno`` is omitted if missing, and the result is stripped
        to avoid trailing whitespace.
        """
        parts = [self.nombre, self.apellido_paterno]
        if self.apellido_materno:
            parts.append(self.apellido_materno)
        return " ".join(parts).strip()
