"""HematologIA — application entry point.

Orchestrates the boot flow:

    Splash (~2s)  →  Login  →  PersonalMainWindow | JefeMainWindow
                       ↑                ↓
                       └── logout ──────┘

Run with: ``python main.py``.

If the database does not exist yet, run ``python scripts/init_db.py`` first.
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from hematologia.config import (
    APP_DISPLAY_NAME,
    APP_NAME,
    APP_ORGANIZATION,
    APP_VERSION,
    DB_PATH,
)
from hematologia.core.logger import get_logger, setup_logger
from hematologia.core.session import get_session
from hematologia.ui.jefe.main_window import JefeMainWindow
from hematologia.ui.login_window import LoginWindow
from hematologia.ui.personal.main_window import PersonalMainWindow
from hematologia.ui.splash_window import SplashWindow


class AppController:
    """Owns top-level windows and routes between them.

    Holds references to the live splash/login/main window so they don't get
    garbage-collected while shown.
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.splash: SplashWindow | None = None
        self.login: LoginWindow | None = None
        self.main_window: PersonalMainWindow | JefeMainWindow | None = None

    def start(self) -> None:
        """Kick off the boot flow."""
        self.logger.info("Application starting (%s v%s)", APP_NAME, APP_VERSION)
        self._verify_database()
        self.splash = SplashWindow()
        self.splash.finished.connect(self._show_login)
        self.splash.start()

    def _verify_database(self) -> None:
        if DB_PATH.exists():
            return
        self.logger.warning("Database not found at %s", DB_PATH)
        QMessageBox.warning(
            None,
            APP_DISPLAY_NAME,
            "No se encontró la base de datos.\n\n"
            "Antes de usar la aplicación ejecutá:\n\n"
            "    python scripts/init_db.py",
        )

    # --- Window transitions -------------------------------------------------

    def _show_login(self) -> None:
        if self.login is None:
            self.login = LoginWindow()
            self.login.login_succeeded.connect(self._on_login_succeeded)
        else:
            self.login.reset()
        self.login.show()
        self.login.raise_()
        self.login.activateWindow()

    def _on_login_succeeded(self) -> None:
        operario = get_session().operario
        if operario is None:
            self.logger.error("login_succeeded fired but session has no operario")
            return

        if self.login is not None:
            self.login.hide()

        if operario.rol == "jefe":
            self.main_window = JefeMainWindow()
        else:
            self.main_window = PersonalMainWindow()

        self.main_window.logout_requested.connect(self._on_logout_requested)
        self.main_window.show()

    def _on_logout_requested(self) -> None:
        operario = get_session().operario
        usuario = operario.usuario if operario else "<unknown>"
        self.logger.info("User '%s' logged out", usuario)

        get_session().logout()

        if self.main_window is not None:
            self.main_window.close()
            self.main_window = None

        self._show_login()


def main() -> int:
    setup_logger()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_ORGANIZATION)

    controller = AppController()
    controller.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
