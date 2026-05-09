"""Top header strip shown above the dashboard content.

Layout: app title on the left, user identity block on the right (avatar,
display name with profession prefix, role caption underneath).
"""
from __future__ import annotations

from typing import Optional

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config import APP_DISPLAY_NAME
from src.database.models import Operario
from src.ui.widgets.avatar import InitialsAvatar


HEADER_HEIGHT = 64
_HELP_ICON_COLOR = "#1E40AF"


class Header(QFrame):
    """White header strip with app title (left) and user identity (right).

    Exposes :attr:`help_requested` so the surrounding shell can react to a
    click on the contextual help button (rendered just before the user block).
    """

    help_requested = Signal()

    def __init__(self, operario: Operario, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("appHeader")
        self.setFixedHeight(HEADER_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._build_ui(operario)

    def _build_ui(self, operario: Operario) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 8, 24, 8)
        layout.setSpacing(16)

        # --- Left: app title ---
        title = QLabel(APP_DISPLAY_NAME)
        title.setObjectName("headerTitle")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)

        layout.addWidget(title, alignment=Qt.AlignVCenter)
        layout.addStretch()

        # --- Right: help button + user info ---
        self._help_button = self._build_help_button()
        layout.addWidget(self._help_button, alignment=Qt.AlignVCenter)
        layout.addLayout(self._build_user_block(operario))

    def _build_help_button(self) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("headerHelpButton")
        btn.setIcon(qta.icon("fa5s.question-circle", color=_HELP_ICON_COLOR))
        btn.setIconSize(qta.icon("fa5s.question-circle").pixmap(20, 20).size())
        btn.setFixedSize(34, 34)
        btn.setFlat(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Ayuda sobre esta pantalla")
        btn.clicked.connect(self.help_requested)
        return btn

    def _build_user_block(self, operario: Operario) -> QHBoxLayout:
        block = QHBoxLayout()
        block.setSpacing(12)

        text = QVBoxLayout()
        text.setSpacing(0)
        text.setAlignment(Qt.AlignVCenter)

        name = QLabel(operario.nombre_con_titulo)
        name.setObjectName("headerUserName")
        name.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        rol_caption = self._format_role_caption(operario)
        rol = QLabel(rol_caption)
        rol.setObjectName("headerUserRole")
        rol.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        text.addWidget(name)
        text.addWidget(rol)

        avatar = InitialsAvatar(operario.iniciales, size=42)

        block.addLayout(text)
        block.addWidget(avatar, alignment=Qt.AlignVCenter)
        return block

    @staticmethod
    def _format_role_caption(operario: Operario) -> str:
        """Build the small grey caption: role + (optional) profession."""
        rol_human = "Jefe de Laboratorio" if operario.rol == "jefe" else "Personal"
        if operario.profesion:
            # "Personal · Bioq." reads cleaner than glueing prefix + role
            # ('Bioq. Personal') in the line directly below the name.
            prof_word = _profesion_long(operario.profesion)
            return f"{rol_human} · {prof_word}"
        return rol_human


def _profesion_long(prefix: str) -> str:
    """Expand a profession abbreviation for display in the role caption."""
    table = {
        "Bioq.": "Bioquímica",
        "Dr.": "Médico",
        "Dra.": "Médica",
        "Tec.": "Técnico",
        "Téc.": "Técnico",
        "Enf.": "Enfermería",
    }
    return table.get(prefix, prefix.rstrip("."))
