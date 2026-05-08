"""Domain model dataclasses.

These are plain Python dataclasses that mirror the rows of the database tables.
Repositories convert ``sqlite3.Row`` instances into these dataclasses so the
rest of the app works with strongly-typed objects rather than dict-like rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


# Genders accepted across the schema. Defined here so UI/repos can reuse them.
GENERO_MASCULINO = "M"
GENERO_FEMENINO = "F"
VALID_GENEROS = (GENERO_MASCULINO, GENERO_FEMENINO)


@dataclass(frozen=True)
class Operario:
    """Represents a row of the ``operarios`` table."""

    id_operario: int
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    profesion: Optional[str]            # 'Bioq.', 'Dr.', 'Tec.', 'Enf.', etc.
    genero: Optional[str]               # 'M' | 'F' | None
    usuario: str
    password_hash: str
    rol: str                            # 'jefe' | 'personal'
    activo: bool
    fecha_creacion: Optional[datetime]
    ultimo_acceso: Optional[datetime]

    @property
    def nombre_completo(self) -> str:
        """Full name as ``"{nombre} {apellido_paterno} {apellido_materno}"``.

        ``apellido_materno`` is omitted if missing.
        """
        parts = [self.nombre, self.apellido_paterno]
        if self.apellido_materno:
            parts.append(self.apellido_materno)
        return " ".join(parts).strip()

    @property
    def nombre_con_titulo(self) -> str:
        """Display name with profession prefix, e.g. ``"Bioq. María López Vargas"``.

        Falls back to plain ``nombre_completo`` if no profession is set.
        """
        if self.profesion:
            return f"{self.profesion} {self.nombre_completo}".strip()
        return self.nombre_completo

    @property
    def saludo(self) -> str:
        """Gendered greeting word — "Bienvenido" / "Bienvenida" / neutral fallback."""
        if self.genero == GENERO_FEMENINO:
            return "Bienvenida"
        if self.genero == GENERO_MASCULINO:
            return "Bienvenido"
        return "Hola"

    @property
    def iniciales(self) -> str:
        """Two-letter initials for avatars (first letter of nombre + apellido_paterno)."""
        first = self.nombre[:1].upper() if self.nombre else ""
        second = self.apellido_paterno[:1].upper() if self.apellido_paterno else ""
        return f"{first}{second}" or "?"


@dataclass(frozen=True)
class Paciente:
    """Represents a row of the ``pacientes`` table."""

    id_paciente: int
    historia_clinica: str
    id_paciente_hospital: str
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    fecha_nacimiento: Optional[date]
    genero: Optional[str]               # 'M' | 'F' | None
    documento: Optional[str]
    fecha_creacion: Optional[datetime]

    @property
    def nombre_completo(self) -> str:
        parts = [self.nombre, self.apellido_paterno]
        if self.apellido_materno:
            parts.append(self.apellido_materno)
        return " ".join(parts).strip()


@dataclass(frozen=True)
class Estudio:
    """Represents a row of the ``estudios`` table."""

    id_estudio: int
    id_paciente: int
    id_operario: int
    id_muestra: str
    procedencia: str
    fecha_creacion: Optional[datetime]
    fecha_analisis: Optional[datetime]  # None while pending
    duracion_segundos: Optional[float]  # None while pending
    observaciones: Optional[str]

    @property
    def is_pendiente(self) -> bool:
        """True if the IA analysis has not been run yet."""
        return self.fecha_analisis is None


@dataclass(frozen=True)
class Captura:
    """Represents a row of the ``capturas`` table."""

    id_captura: int
    id_estudio: int
    path_imagen: str                    # relative to data/capturas/
    fecha_captura: Optional[datetime]
    notas: Optional[str]


@dataclass(frozen=True)
class Reporte:
    """Represents a row of the ``reportes`` table."""

    id_reporte: int
    id_estudio: int
    path_pdf: Optional[str]             # relative to data/reportes/, None if not generated yet
    fecha_generacion: Optional[datetime]


@dataclass(frozen=True)
class DashboardStats:
    """Aggregated daily metrics for the Personal dashboard.

    All counters are filtered by the current operator and limited to "today"
    in local time.
    """

    imagenes_capturadas_hoy: int
    analisis_realizados_hoy: int
    reportes_generados_hoy: int
    duracion_promedio_segundos: Optional[float]  # None if no analyses today
