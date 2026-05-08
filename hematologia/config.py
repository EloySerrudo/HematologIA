"""Global configuration constants.

All hardcoded values used across the app live here. Modules must import from
this file rather than defining their own constants.
"""
from __future__ import annotations

from hematologia.utils.paths import resolve_from_root

# --- Application metadata ---------------------------------------------------
APP_NAME: str = "HematologIA"
APP_DISPLAY_NAME: str = "Sistema Hematológico IA"
APP_VERSION: str = "0.1.0"
APP_ORGANIZATION: str = "Laboratorio de Análisis Clínicos"

# --- Filesystem paths -------------------------------------------------------
ROOT_DIR = resolve_from_root()
DATA_DIR = resolve_from_root("data")
LOGS_DIR = resolve_from_root("logs")
CAPTURAS_DIR = resolve_from_root("data", "capturas")
SCHEMA_PATH = resolve_from_root("schema.sql")
DB_PATH = resolve_from_root("data", "hematologia.db")
LOG_PATH = resolve_from_root("logs", "hematologia.log")

# UI assets
STYLES_DIR = resolve_from_root("hematologia", "ui", "styles")
ASSETS_DIR = resolve_from_root("hematologia", "ui", "styles", "assets")
LOGIN_QSS_PATH = resolve_from_root("hematologia", "ui", "styles", "login.qss")
LOGIN_REFERENCE_IMAGE = resolve_from_root("Login_window.jpeg")
ASSET_MICROSCOPE = resolve_from_root("hematologia", "ui", "styles", "assets", "microscope.png")
ASSET_CELLS = resolve_from_root("hematologia", "ui", "styles", "assets", "cells.png")
ASSET_HEXAGONS = resolve_from_root("hematologia", "ui", "styles", "assets", "hexagons.png")

# --- Settings persistence ---------------------------------------------------
# Used by QSettings (e.g. for "Recordar sesión").
SETTINGS_ORG: str = "HematologIA"
SETTINGS_APP: str = "HematologIA"
SETTING_REMEMBER_USER: str = "login/remembered_user"

# --- UI dimensions ----------------------------------------------------------
LOGIN_WINDOW_WIDTH: int = 940
LOGIN_WINDOW_HEIGHT: int = 620
SPLASH_WIDTH: int = 440
SPLASH_HEIGHT: int = 260
SPLASH_DURATION_MS: int = 2000

# --- Logging ----------------------------------------------------------------
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT: int = 3

# --- Roles ------------------------------------------------------------------
ROL_JEFE: str = "jefe"
ROL_PERSONAL: str = "personal"
VALID_ROLES: tuple[str, ...] = (ROL_JEFE, ROL_PERSONAL)
