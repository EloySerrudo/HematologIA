"""Main window for the 'personal' role.

Wraps the reusable ``MainShell`` (sidebar + header) around a Personal-specific
content stack. In Fase 1 the only real content is the dashboard view; the
remaining nav items show a "Próximamente" notice.
"""
from __future__ import annotations

from src.core.session import get_session
from src.ui.personal.dashboard_view import DashboardView
from src.ui.shell.main_shell import MainShell
from src.ui.shell.sidebar import NavItem
from src.ui.widgets.coming_soon import show_coming_soon


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
    :class:`MainShell`; wires ``nav_clicked`` to swap the content widget,
    leaves ``logout_requested`` for the AppController to handle.
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

        self.nav_clicked.connect(self._on_nav_clicked)

        # Initial content: the dashboard.
        self._dashboard = DashboardView(operario)
        self.set_content(self._dashboard)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_nav_clicked(self, key: str) -> None:
        if key == "dashboard":
            self.sidebar.set_active("dashboard")
            new_view = DashboardView(get_session().operario)
            self._dashboard = new_view
            self.set_content(new_view)
            return
        # Any other entry is a stub for now — keep the active item unchanged.
        show_coming_soon(self, _NAV_LABELS.get(key, key.title()))
