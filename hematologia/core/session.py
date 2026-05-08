"""Application session.

Holds the currently authenticated ``Operario`` for the duration of the run.
Implemented as a simple singleton so any window can call ``get_session()``
without prop-drilling the operario through constructors.
"""
from __future__ import annotations

from typing import Optional

from hematologia.database.models import Operario


class Session:
    """Singleton holding the currently authenticated operario."""

    _instance: Optional["Session"] = None

    def __new__(cls) -> "Session":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._operario = None
            cls._instance = instance
        return cls._instance

    @property
    def operario(self) -> Optional[Operario]:
        return self._operario

    @property
    def rol(self) -> Optional[str]:
        return self._operario.rol if self._operario else None

    def login(self, operario: Operario) -> None:
        """Record that ``operario`` has authenticated."""
        self._operario = operario

    def logout(self) -> None:
        """Clear the current session."""
        self._operario = None

    def is_authenticated(self) -> bool:
        return self._operario is not None


def get_session() -> Session:
    """Return the application session singleton."""
    return Session()
