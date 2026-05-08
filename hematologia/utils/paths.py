"""Path resolution helpers.

Centralizes how the project root is located so no module has to compute paths
manually. Always use these helpers instead of hardcoding paths.
"""
from __future__ import annotations

from pathlib import Path


def get_project_root() -> Path:
    """Return the absolute path to the project root.

    The project root is the directory containing the ``hematologia`` package,
    ``main.py``, ``schema.sql``, etc.

    This file is at ``<root>/hematologia/utils/paths.py``, so the root is three
    levels up from this file.
    """
    return Path(__file__).resolve().parents[2]


def resolve_from_root(*parts: str) -> Path:
    """Join the given path components to the project root.

    Example:
        ``resolve_from_root("data", "hematologia.db")``
        → ``<root>/data/hematologia.db``
    """
    return get_project_root().joinpath(*parts)
