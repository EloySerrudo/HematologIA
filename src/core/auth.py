"""Authentication logic.

The single public entry point is :func:`authenticate`. It returns the
``Operario`` on success and ``None`` on any failure (unknown user, inactive
account, or bad password). The caller cannot distinguish *why* it failed —
this prevents user enumeration attacks.

All login attempts are logged. Passwords are NEVER logged, not even hashed.
"""
from __future__ import annotations

from typing import Optional

import bcrypt

from src.core.logger import get_logger
from src.database.models import Operario
from src.database.repositories import operario_repo

_logger = get_logger(__name__)


def authenticate(usuario: str, password: str) -> Optional[Operario]:
    """Verify credentials against the ``operarios`` table.

    Args:
        usuario: Username entered in the UI.
        password: Plaintext password entered in the UI.

    Returns:
        The matching ``Operario`` on success, or ``None`` if the user does not
        exist, is inactive, or the password is incorrect.
    """
    if not usuario or not password:
        _logger.warning("Login attempt failed: empty usuario or password")
        return None

    operario = operario_repo.get_by_usuario(usuario)

    if operario is None:
        _logger.warning("Login attempt failed: unknown user '%s'", usuario)
        return None

    if not operario.activo:
        _logger.warning("Login attempt failed: inactive user '%s'", usuario)
        return None

    try:
        password_ok = bcrypt.checkpw(
            password.encode("utf-8"),
            operario.password_hash.encode("utf-8"),
        )
    except ValueError as exc:
        # Malformed hash in the DB — should not happen if init_db.py was used.
        _logger.error("Malformed password hash for user '%s': %s", usuario, exc)
        return None

    if not password_ok:
        _logger.warning("Login attempt failed: bad password for user '%s'", usuario)
        return None

    operario_repo.update_ultimo_acceso(operario.id_operario)
    _logger.info("Login successful: user '%s' (rol=%s)", usuario, operario.rol)
    return operario
