"""Main window for the 'personal' role.

Wraps the reusable ``MainShell`` (sidebar + header) around a Personal-specific
content stack. In Fase 1 the implemented views are:

* ``Dashboard``  → :class:`DashboardView`
* ``Captura``    → :class:`CapturaView` (opens after :class:`PacientePickerDialog`)

The remaining nav items show a "Próximamente" notice.

While a capture session is active the window asks for confirmation before
navigating away (Opción C) so the operator doesn't lose track of the open
study by accident.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QMessageBox

from src.config import APP_DISPLAY_NAME
from src.core.logger import get_logger
from src.core.session import get_session
from src.ui.personal.captura_view import CapturaView
from src.ui.personal.dashboard_view import DashboardView
from src.ui.personal.paciente_picker_dialog import PacientePickerDialog
from src.ui.shell.main_shell import MainShell
from src.ui.shell.sidebar import NavItem
from src.ui.widgets.coming_soon import show_coming_soon

_logger = get_logger(__name__)


# Navigation items for the Personal sidebar. The order matches the design.
_PERSONAL_NAV: list[NavItem] = [
    NavItem(key="dashboard",  label="Dashboard",         icon_name="fa5s.th-large"),
    NavItem(key="captura",    label="Captura de Imagen", icon_name="fa5s.camera"),
    NavItem(key="analisis",   label="Análisis",          icon_name="fa5s.microscope"),
    NavItem(key="estudios",   label="Mis Estudios",      icon_name="fa5s.folder-open"),
    NavItem(key="reportes",   label="Reportes",          icon_name="fa5s.file-pdf"),
]

# Human-friendly labels for the "Próximamente" notice.
_NAV_LABELS: dict[str, str] = {
    "captura":  "Captura de Imagen",
    "analisis": "Análisis",
    "estudios": "Mis Estudios",
    "reportes": "Reportes",
}


class PersonalMainWindow(MainShell):
    """Main window for operarios with rol='personal'.

    Inherits ``nav_clicked`` and ``logout_requested`` signals from
    :class:`MainShell`. Wires ``nav_clicked`` to swap the content widget
    (with a confirmation prompt when there's an active capture session) and
    intercepts ``logout_requested`` for the same reason.
    """

    def __init__(self) -> None:
        operario = get_session().operario
        if operario is None:
            raise RuntimeError("PersonalMainWindow opened without an authenticated operario")

        super().__init__(
            operario=operario,
            nav_items=_PERSONAL_NAV,
            active_nav_key="dashboard",
            title_suffix="Personal",
        )

        # Open maximized — lab PCs typically run this app foreground on a single monitor.
        self.showMaximized()

        # Track the active view's nav key so we can compare against new clicks.
        self._active_nav_key: str = "dashboard"
        # When CapturaView is the current content, this holds the reference so
        # we can ask it whether there's an in-flight session before navigating.
        self._captura_view: Optional[CapturaView] = None

        # Wire shell signals
        self.nav_clicked.connect(self._on_nav_clicked)
        # Intercept logout from the parent's signal — re-emit only after the
        # confirmation passes. We disconnect & reconnect via a dedicated handler.
        # Easier: shadow it by handling sidebar.logout_requested ourselves.
        self.sidebar.logout_requested.disconnect(self.logout_requested)
        self.sidebar.logout_requested.connect(self._on_logout_requested)

        # Initial content: dashboard.
        self._show_dashboard()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_nav_clicked(self, key: str) -> None:
        if key == self._active_nav_key:
            # Already on this section — clicking the active item just refreshes.
            if key == "dashboard":
                self._show_dashboard()
            return

        if not self._confirm_leaving_session(reason="cambiar de pantalla"):
            return

        if key == "dashboard":
            self._show_dashboard()
        elif key == "captura":
            self._open_captura_flow()
        else:
            # Other nav items are stubs in Fase 1 — keep the active view as is.
            show_coming_soon(self, _NAV_LABELS.get(key, key.title()))

    def _on_logout_requested(self) -> None:
        if not self._confirm_leaving_session(reason="cerrar sesión"):
            return
        self._teardown_captura()
        # Forward to the AppController.
        self.logout_requested.emit()

    # ------------------------------------------------------------------
    # View transitions
    # ------------------------------------------------------------------

    def _show_dashboard(self) -> None:
        self._teardown_captura()
        self._active_nav_key = "dashboard"
        self.sidebar.set_active("dashboard")
        view = DashboardView(get_session().operario)
        # Quick-action cards on the dashboard route through the same handler
        # as the sidebar so "Ir a Captura" actually opens the picker dialog.
        view.quick_action_triggered.connect(self._on_nav_clicked)
        self.set_content(view)

    def _open_captura_flow(self) -> None:
        """Run the patient picker dialog, then enter the capture view if confirmed."""
        dialog = PacientePickerDialog(parent=self)
        if dialog.exec() != PacientePickerDialog.Accepted:
            # User cancelled — keep the previous view + active nav item.
            return

        paciente = dialog.paciente
        estudio = dialog.estudio
        assert paciente is not None and estudio is not None, \
            "PacientePickerDialog accepted but didn't expose paciente/estudio"

        _logger.info(
            "Opening capture session for estudio id=%s muestra=%s paciente=%s",
            estudio.id_estudio, estudio.id_muestra, paciente.historia_clinica,
        )

        self._teardown_captura()
        self._captura_view = CapturaView(paciente, estudio, parent=self)
        self._active_nav_key = "captura"
        self.sidebar.set_active("captura")
        self.set_content(self._captura_view)

    def _teardown_captura(self) -> None:
        """Stop the session timer and drop the captura view if any."""
        if self._captura_view is not None:
            self._captura_view.stop_session()
            self._captura_view = None

    # ------------------------------------------------------------------
    # Session protection (Opción C)
    # ------------------------------------------------------------------

    def _confirm_leaving_session(self, *, reason: str) -> bool:
        """Show the confirmation dialog when there's an active session.

        Returns True if the user accepts to leave (or there was no session
        to protect), False if they cancel.
        """
        if self._captura_view is None:
            return True

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle(APP_DISPLAY_NAME)
        msg.setText("<b>¿Salir de la sesión de captura?</b>")
        msg.setInformativeText(
            f"El estudio <b>{self._captura_view.estudio.id_muestra}</b> "
            f"({self._captura_view.paciente.nombre_completo}) quedará guardado "
            f"y podrás retomarlo desde <b>Mis Estudios</b>."
            f"<br><br>Acción: {reason}."
        )
        leave_btn = msg.addButton("Salir", QMessageBox.AcceptRole)
        msg.addButton("Continuar capturando", QMessageBox.RejectRole)
        msg.setDefaultButton(leave_btn)
        msg.exec()
        return msg.clickedButton() is leave_btn
