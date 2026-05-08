"""Initialize the HematologIA SQLite database.

Reads `schema.sql` from the project root and applies it to `data/hematologia.db`,
then inserts seed data (operarios, pacientes, estudios, capturas, reportes)
with bcrypt-hashed passwords generated at runtime.

Usage:
    python scripts/init_db.py            # create DB if it doesn't exist
    python scripts/init_db.py --reset    # delete and recreate the DB

The script lives outside the `src` package because it's an operational
tool, not part of the runtime app. It still imports from the package to reuse
config and the connection helper.

Seed strategy:
  * 2 operarios (jefe + personal) — match the Login window credentials.
  * 4 pacientes with fake but plausible Bolivian data.
  * 8 estudios distributed: 6 today, 2 yesterday. Most have fecha_analisis
    set with a duration; one is left "pendiente" to exercise NULL handling.
  * Capturas associated to each estudio (1-3 per estudio).
  * Reportes for the studies that have already been analyzed.
This is enough for the Personal dashboard to show non-zero stats.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

# Make the project root importable when invoking the script directly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import bcrypt

from src.config import DATA_DIR, DB_PATH, SCHEMA_PATH
from src.database.connection import get_connection


# -----------------------------------------------------------------------------
# Seed data
# -----------------------------------------------------------------------------

# Seed operarios. Passwords are hashed at runtime — never commit hashes.
SEED_OPERARIOS: list[dict] = [
    {
        "usuario": "jefe",
        "password": "jefe123",
        "nombre": "Carlos",
        "apellido_paterno": "Mendoza",
        "apellido_materno": "Quispe",
        "profesion": "Dr.",
        "genero": "M",
        "rol": "jefe",
    },
    {
        "usuario": "personal",
        "password": "personal123",
        "nombre": "María",
        "apellido_paterno": "López",
        "apellido_materno": "Vargas",
        "profesion": "Bioq.",
        "genero": "F",
        "rol": "personal",
    },
]


SEED_PACIENTES: list[dict] = [
    {
        "historia_clinica": "HC-2024-0001",
        "id_paciente_hospital": "HSK/2024/0001",
        "nombre": "Juana",
        "apellido_paterno": "Pérez",
        "apellido_materno": "Mamani",
        "fecha_nacimiento": "1979-03-12",
        "genero": "F",
        "documento": "9123456",
    },
    {
        "historia_clinica": "HC-2024-0002",
        "id_paciente_hospital": "HSK/2024/0002",
        "nombre": "Luis",
        "apellido_paterno": "Quispe",
        "apellido_materno": "Tola",
        "fecha_nacimiento": "1992-07-04",
        "genero": "M",
        "documento": "9234567",
    },
    {
        "historia_clinica": "HC-2024-0003",
        "id_paciente_hospital": "HSK/2024/0003",
        "nombre": "Rosa",
        "apellido_paterno": "Choque",
        "apellido_materno": "Vargas",
        "fecha_nacimiento": "1957-11-23",
        "genero": "F",
        "documento": "9345678",
    },
    {
        "historia_clinica": "HC-2024-0004",
        "id_paciente_hospital": "HSK/2024/0004",
        "nombre": "Andrés",
        "apellido_paterno": "Flores",
        "apellido_materno": "Mendoza",
        "fecha_nacimiento": "1996-01-30",
        "genero": "M",
        "documento": "9456789",
    },
]


# Estudios are defined in terms of *offsets* from "now" so the seed always
# produces a mix of "today" and "yesterday" rows regardless of when it runs.
#   `hours_ago_*` is None to leave a column NULL (e.g. pending analysis).
#   `id_paciente_seed` and `id_operario_seed` are 1-based positions into the
#   seed lists above; we resolve them to actual DB ids after insert.
SEED_ESTUDIOS: list[dict] = [
    # --- Personal (María, op-seed #2) — today ---
    {
        "id_operario_seed": 2, "id_paciente_seed": 1,
        "id_muestra": "M-2024-001", "procedencia": "URG",
        "hours_ago_creacion": 4, "hours_ago_analisis": 3, "duracion_segundos": 45.2,
        "observaciones": "Frotis con leucocitosis evidente.",
        "n_capturas": 3, "report_hours_ago": 3,
    },
    {
        "id_operario_seed": 2, "id_paciente_seed": 2,
        "id_muestra": "M-2024-002", "procedencia": "CON-EXT",
        "hours_ago_creacion": 3, "hours_ago_analisis": 2, "duracion_segundos": 60.5,
        "observaciones": "Solicitado por consulta externa, paciente estable.",
        "n_capturas": 2, "report_hours_ago": 2,
    },
    {
        "id_operario_seed": 2, "id_paciente_seed": 3,
        "id_muestra": "M-2024-003", "procedencia": "INT-MED",
        "hours_ago_creacion": 2, "hours_ago_analisis": 1, "duracion_segundos": 30.8,
        "observaciones": "Paciente internada, control hematológico.",
        "n_capturas": 2, "report_hours_ago": None,  # análisis listo, reporte aún no
    },
    {
        "id_operario_seed": 2, "id_paciente_seed": 4,
        "id_muestra": "M-2024-004", "procedencia": "URG",
        "hours_ago_creacion": 1, "hours_ago_analisis": None, "duracion_segundos": None,
        "observaciones": "Recién ingresado, capturas tomadas, análisis pendiente.",
        "n_capturas": 1, "report_hours_ago": None,
    },
    # --- Personal — yesterday ---
    {
        "id_operario_seed": 2, "id_paciente_seed": 1,
        "id_muestra": "M-2024-005", "procedencia": "CON-EXT",
        "hours_ago_creacion": 27, "hours_ago_analisis": 26, "duracion_segundos": 55.0,
        "observaciones": "Seguimiento post-tratamiento.",
        "n_capturas": 2, "report_hours_ago": 26,
    },
    {
        "id_operario_seed": 2, "id_paciente_seed": 2,
        "id_muestra": "M-2024-006", "procedencia": "URG",
        "hours_ago_creacion": 30, "hours_ago_analisis": 29, "duracion_segundos": 42.3,
        "observaciones": None,
        "n_capturas": 2, "report_hours_ago": 29,
    },
    # --- Jefe (Carlos, op-seed #1) ---
    {
        "id_operario_seed": 1, "id_paciente_seed": 3,
        "id_muestra": "M-2024-007", "procedencia": "INT-PED",
        "hours_ago_creacion": 5, "hours_ago_analisis": 4, "duracion_segundos": 70.0,
        "observaciones": "Caso pediátrico, revisión por jefe.",
        "n_capturas": 2, "report_hours_ago": 4,
    },
    {
        "id_operario_seed": 1, "id_paciente_seed": 4,
        "id_muestra": "M-2024-008", "procedencia": "INT-MED",
        "hours_ago_creacion": 28, "hours_ago_analisis": 27, "duracion_segundos": 50.0,
        "observaciones": None,
        "n_capturas": 1, "report_hours_ago": 27,
    },
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize the HematologIA database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing database before recreating it.",
    )
    return parser.parse_args()


def hash_password(password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _ts(hours_ago: float | None) -> str | None:
    """Return an ISO-8601 local timestamp ``hours_ago`` hours before now, or None."""
    if hours_ago is None:
        return None
    return (datetime.now() - timedelta(hours=hours_ago)).isoformat(sep=" ", timespec="seconds")


def apply_schema() -> None:
    """Read schema.sql and execute it against the database."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(sql)


# -----------------------------------------------------------------------------
# Seed insertion
# -----------------------------------------------------------------------------

def insert_operarios() -> dict[int, int]:
    """Insert seed operarios. Returns a mapping seed_index (1-based) → id_operario."""
    seed_to_id: dict[int, int] = {}
    with get_connection() as conn:
        for idx, user in enumerate(SEED_OPERARIOS, start=1):
            existing = conn.execute(
                "SELECT id_operario FROM operarios WHERE usuario = ?",
                (user["usuario"],),
            ).fetchone()
            if existing:
                seed_to_id[idx] = existing["id_operario"]
                continue

            cursor = conn.execute(
                """
                INSERT INTO operarios
                    (nombre, apellido_paterno, apellido_materno,
                     profesion, genero, usuario, password_hash, rol)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["nombre"],
                    user["apellido_paterno"],
                    user["apellido_materno"],
                    user["profesion"],
                    user["genero"],
                    user["usuario"],
                    hash_password(user["password"]),
                    user["rol"],
                ),
            )
            seed_to_id[idx] = cursor.lastrowid
    return seed_to_id


def insert_pacientes() -> dict[int, int]:
    """Insert seed pacientes. Returns mapping seed_index (1-based) → id_paciente."""
    seed_to_id: dict[int, int] = {}
    with get_connection() as conn:
        for idx, pac in enumerate(SEED_PACIENTES, start=1):
            existing = conn.execute(
                "SELECT id_paciente FROM pacientes WHERE historia_clinica = ?",
                (pac["historia_clinica"],),
            ).fetchone()
            if existing:
                seed_to_id[idx] = existing["id_paciente"]
                continue

            cursor = conn.execute(
                """
                INSERT INTO pacientes
                    (historia_clinica, id_paciente_hospital,
                     nombre, apellido_paterno, apellido_materno,
                     fecha_nacimiento, genero, documento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pac["historia_clinica"],
                    pac["id_paciente_hospital"],
                    pac["nombre"],
                    pac["apellido_paterno"],
                    pac["apellido_materno"],
                    pac["fecha_nacimiento"],
                    pac["genero"],
                    pac["documento"],
                ),
            )
            seed_to_id[idx] = cursor.lastrowid
    return seed_to_id


def insert_estudios_capturas_reportes(
    op_ids: dict[int, int],
    pac_ids: dict[int, int],
) -> tuple[int, int, int]:
    """Insert seed estudios + their capturas + reportes.

    Returns:
        Tuple ``(n_estudios, n_capturas, n_reportes)`` actually inserted.
    """
    n_estudios = n_capturas = n_reportes = 0
    with get_connection() as conn:
        for est in SEED_ESTUDIOS:
            existing = conn.execute(
                "SELECT id_estudio FROM estudios WHERE id_muestra = ?",
                (est["id_muestra"],),
            ).fetchone()
            if existing:
                continue

            cursor = conn.execute(
                """
                INSERT INTO estudios
                    (id_paciente, id_operario, id_muestra, procedencia,
                     fecha_creacion, fecha_analisis, duracion_segundos, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pac_ids[est["id_paciente_seed"]],
                    op_ids[est["id_operario_seed"]],
                    est["id_muestra"],
                    est["procedencia"],
                    _ts(est["hours_ago_creacion"]),
                    _ts(est["hours_ago_analisis"]),
                    est["duracion_segundos"],
                    est["observaciones"],
                ),
            )
            id_estudio = cursor.lastrowid
            n_estudios += 1

            # Capturas: distribute them around fecha_creacion (one minute apart).
            for i in range(est["n_capturas"]):
                # path is fictitious but follows a stable layout
                rel_path = f"{est['id_muestra']}/img_{i + 1:02d}.jpg"
                fecha_cap = _ts(est["hours_ago_creacion"] - i * (1 / 60))  # ~1 min apart
                conn.execute(
                    """
                    INSERT INTO capturas (id_estudio, path_imagen, fecha_captura, notas)
                    VALUES (?, ?, ?, ?)
                    """,
                    (id_estudio, rel_path, fecha_cap, None),
                )
                n_capturas += 1

            # Reporte (opcional)
            if est["report_hours_ago"] is not None:
                rel_pdf = f"{est['id_muestra']}.pdf"
                conn.execute(
                    """
                    INSERT INTO reportes (id_estudio, path_pdf, fecha_generacion)
                    VALUES (?, ?, ?)
                    """,
                    (id_estudio, rel_pdf, _ts(est["report_hours_ago"])),
                )
                n_reportes += 1

    return n_estudios, n_capturas, n_reportes


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.reset and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[reset] Deleted existing database at {DB_PATH}")

    db_existed = DB_PATH.exists()

    print(f"[schema]    Applying schema from {SCHEMA_PATH.name}...")
    apply_schema()

    print("[operarios] Inserting seed operarios (skipping existing)...")
    op_ids = insert_operarios()

    print("[pacientes] Inserting seed pacientes (skipping existing)...")
    pac_ids = insert_pacientes()

    print("[estudios]  Inserting seed estudios + capturas + reportes...")
    n_est, n_cap, n_rep = insert_estudios_capturas_reportes(op_ids, pac_ids)

    print()
    print("=" * 64)
    print(f"  DB path                : {DB_PATH}")
    print(f"  DB existed before run  : {db_existed}")
    print(f"  Operarios in DB        : {len(op_ids)} ({', '.join(u['usuario'] for u in SEED_OPERARIOS)})")
    print(f"  Pacientes in DB        : {len(pac_ids)}")
    print(f"  Estudios inserted      : {n_est}")
    print(f"  Capturas inserted      : {n_cap}")
    print(f"  Reportes inserted      : {n_rep}")
    print("=" * 64)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
