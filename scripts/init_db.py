"""Initialize the HematologIA SQLite database.

Reads `schema.sql` from the project root and applies it to `data/hematologia.db`,
then inserts seed users with bcrypt-hashed passwords generated at runtime.

Usage:
    python scripts/init_db.py            # create DB if it doesn't exist
    python scripts/init_db.py --reset    # delete and recreate the DB

The script lives outside the `src` package because it's an operational
tool, not part of the runtime app. It still imports from the package to reuse
config and the connection helper.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the project root importable when invoking the script directly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import bcrypt

from src.config import DATA_DIR, DB_PATH, SCHEMA_PATH
from src.database.connection import get_connection


# Seed users for development. Passwords are hashed at runtime — never commit hashes.
SEED_USERS: list[dict] = [
    {
        "usuario": "jefe",
        "password": "jefe123",
        "nombre": "Carlos",
        "apellido_paterno": "Mendoza",
        "apellido_materno": "Quispe",
        "rol": "jefe",
    },
    {
        "usuario": "personal",
        "password": "personal123",
        "nombre": "María",
        "apellido_paterno": "López",
        "apellido_materno": "Vargas",
        "rol": "personal",
    },
]


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


def apply_schema() -> None:
    """Read schema.sql and execute it against the database."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(sql)


def insert_seed_users() -> int:
    """Insert seed users with hashed passwords. Returns the number of users inserted."""
    inserted = 0
    with get_connection() as conn:
        for user in SEED_USERS:
            existing = conn.execute(
                "SELECT 1 FROM operarios WHERE usuario = ?",
                (user["usuario"],),
            ).fetchone()
            if existing:
                continue

            conn.execute(
                """
                INSERT INTO operarios
                    (nombre, apellido_paterno, apellido_materno, usuario, password_hash, rol)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user["nombre"],
                    user["apellido_paterno"],
                    user["apellido_materno"],
                    user["usuario"],
                    hash_password(user["password"]),
                    user["rol"],
                ),
            )
            inserted += 1
    return inserted


def main() -> int:
    args = parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.reset and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[reset] Deleted existing database at {DB_PATH}")

    db_existed = DB_PATH.exists()

    print(f"[schema] Applying schema from {SCHEMA_PATH.name}...")
    apply_schema()

    print("[seed]   Inserting seed users (skipping existing)...")
    inserted = insert_seed_users()

    print()
    print("=" * 60)
    print(f"  DB path        : {DB_PATH}")
    print(f"  DB existed     : {db_existed}")
    print(f"  Users inserted : {inserted}")
    print(f"  Seed users     : {', '.join(u['usuario'] for u in SEED_USERS)}")
    print("=" * 60)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
