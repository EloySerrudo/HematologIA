"""Login window.

Two-pane layout matching ``Login_window.jpeg``:
  * Left brand panel: gradient blue background with hex pattern, microscope
    image and feature highlights.
  * Right form panel: title, user/password inputs, remember-me checkbox,
    primary login button and footer.

Visual styles live in ``src/ui/styles/login.qss``. Icons are sourced
from qtawesome (Font Awesome). Image assets live in
``src/ui/styles/assets/``.
"""
from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QEvent, QSettings, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.config import (
    APP_DISPLAY_NAME,
    APP_ORGANIZATION,
    ASSET_CELLS,
    ASSET_HEXAGONS,
    ASSET_LOGO_HOSPITAL_WHITE,
    ASSET_MICROSCOPE,
    LOGIN_QSS_PATH,
    LOGIN_WINDOW_HEIGHT,
    LOGIN_WINDOW_WIDTH,
    SETTING_REMEMBER_USER,
)
from src.core.auth import authenticate
from src.core.logger import get_logger
from src.core.session import get_session

_logger = get_logger(__name__)

# --- Color palette (kept in sync with login.qss) ---
_COLOR_BLUE_DARK = "#1E3A8A"
_COLOR_BLUE_PRIMARY = "#1E40AF"
_COLOR_BLUE_LIGHT = "#BFDBFE"
_COLOR_TEXT_DARK = "#1F2937"
_COLOR_TEXT_MUTED = "#6B7280"
_COLOR_RED_LOGO = "#DC2626"


# Feature card data: (qta-icon, title, description)
_FEATURES: list[tuple[str, str, str]] = [
    ("fa5s.shield-alt",   "Seguro",      "Protección\nde datos"),
    ("fa5s.brain",        "Inteligente", "IA para análisis\npreciso"),
    ("fa5s.chart-bar",    "Confiable",   "Resultados\nconfiables"),
    ("fa5s.clock",        "Rápido",      "Procesamiento\neficiente"),
]


class LoginWindow(QWidget):
    """Login screen. Emits ``login_succeeded`` after a valid login."""

    login_succeeded = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_DISPLAY_NAME} — Iniciar Sesión")
        self.setFixedSize(LOGIN_WINDOW_WIDTH, LOGIN_WINDOW_HEIGHT)
        self.setObjectName("loginWindow")

        # Maps id(QLineEdit) → its visual wrapper QFrame, so the focus event
        # filter can update the wrapper's border via a dynamic property.
        self._wrapper_for_input: dict[int, QFrame] = {}

        self._build_ui()
        self._load_stylesheet()
        self._restore_remembered_user()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_brand_panel(), stretch=1)
        root.addWidget(self._build_form_panel(), stretch=1)

    def _build_brand_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("brandPanel")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Hexagons backdrop — child QLabel with opacity effect, lowered behind
        # everything else. Stretched to cover the panel via resizeEvent.
        hex_label = QLabel(panel)
        hex_label.setObjectName("hexBackdrop")
        hex_pix = QPixmap(str(ASSET_HEXAGONS))
        if not hex_pix.isNull():
            hex_label.setPixmap(hex_pix)
            hex_label.setScaledContents(True)
            hex_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            opacity = QGraphicsOpacityEffect(hex_label)
            opacity.setOpacity(0.18)
            hex_label.setGraphicsEffect(opacity)
        self._hex_backdrop = hex_label

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(36, 36, 36, 28)
        layout.setSpacing(0)

        # Header: logo + title + subtitle
        header = QHBoxLayout()
        header.setSpacing(12)

        logo = QLabel()
        logo.setObjectName("brandLogo")
        logo_icon = qta.icon("fa5s.tint", color=_COLOR_RED_LOGO)
        logo.setPixmap(logo_icon.pixmap(48, 48))
        logo.setFixedSize(48, 48)
        logo.setAlignment(Qt.AlignCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        brand_title = QLabel(APP_DISPLAY_NAME)
        brand_title.setObjectName("brandTitle")
        brand_subtitle = QLabel("Análisis inteligente de células sanguíneas")
        brand_subtitle.setObjectName("brandSubtitle")
        title_box.addWidget(brand_title)
        title_box.addWidget(brand_subtitle)

        header.addWidget(logo, alignment=Qt.AlignTop)
        header.addLayout(title_box, stretch=1)

        layout.addLayout(header)
        layout.addSpacing(20)

        # Microscope image
        microscope = QLabel()
        microscope.setObjectName("microscopeImage")
        pix = QPixmap(str(ASSET_MICROSCOPE))
        if not pix.isNull():
            # Reduced from 320 → 280 to make room for the hospital logo at the
            # bottom of the panel without squashing the layout.
            scaled = pix.scaledToHeight(280, Qt.SmoothTransformation)
            microscope.setPixmap(scaled)
        microscope.setAlignment(Qt.AlignCenter)
        layout.addWidget(microscope, stretch=1, alignment=Qt.AlignCenter)

        # Features row
        features = QGridLayout()
        features.setHorizontalSpacing(8)
        features.setVerticalSpacing(4)
        for col, (icon_name, title, desc) in enumerate(_FEATURES):
            features.addLayout(self._build_feature_card(icon_name, title, desc), 0, col)
        layout.addLayout(features)

        # Hospital institutional branding (footer of the brand panel).
        layout.addSpacing(16)
        divider = QFrame()
        divider.setObjectName("brandDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(12)

        hospital_logo = QLabel()
        hospital_logo.setObjectName("hospitalLogo")
        hosp_pix = QPixmap(str(ASSET_LOGO_HOSPITAL_WHITE))
        if not hosp_pix.isNull():
            hospital_logo.setPixmap(
                hosp_pix.scaledToWidth(180, Qt.SmoothTransformation)
            )
        hospital_logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(hospital_logo, alignment=Qt.AlignHCenter)

        return panel

    def _build_feature_card(self, icon_name: str, title: str, desc: str) -> QVBoxLayout:
        card = QVBoxLayout()
        card.setSpacing(4)
        card.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon = qta.icon(icon_name, color="#FFFFFF")
        icon_label.setPixmap(icon.pixmap(22, 22))

        title_label = QLabel(title)
        title_label.setObjectName("featureTitle")
        title_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel(desc)
        desc_label.setObjectName("featureDesc")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)

        card.addWidget(icon_label)
        card.addWidget(title_label)
        card.addWidget(desc_label)
        return card

    def _build_form_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("formPanel")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Decorative cells image at the bottom-right corner.
        # It's a child of the panel so it doesn't push the form layout around.
        cells = QLabel(panel)
        cells.setObjectName("cellsDeco")
        cells_pix = QPixmap(str(ASSET_CELLS))
        if not cells_pix.isNull():
            cells.setPixmap(cells_pix.scaledToWidth(200, Qt.SmoothTransformation))
            cells.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            cells.adjustSize()
        self._cells_deco = cells

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(60, 50, 60, 24)
        layout.setSpacing(0)

        # Title
        title = QLabel("Iniciar Sesión")
        title.setObjectName("formTitle")
        title.setAlignment(Qt.AlignCenter)

        underline = QFrame()
        underline.setObjectName("formTitleUnderline")
        underline.setFixedSize(56, 3)
        underline_wrap = QHBoxLayout()
        underline_wrap.addStretch()
        underline_wrap.addWidget(underline)
        underline_wrap.addStretch()

        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addLayout(underline_wrap)
        layout.addSpacing(28)

        # Usuario field
        layout.addWidget(self._field_label("Usuario"))
        layout.addSpacing(6)
        layout.addLayout(self._build_usuario_input())
        layout.addSpacing(18)

        # Contraseña field
        layout.addWidget(self._field_label("Contraseña"))
        layout.addSpacing(6)
        layout.addLayout(self._build_password_input())
        layout.addSpacing(10)

        # Remember-me checkbox
        self.remember_checkbox = QCheckBox("Recordar sesión")
        self.remember_checkbox.setObjectName("rememberCheckbox")
        layout.addWidget(self.remember_checkbox)
        layout.addSpacing(16)

        # Error message slot (hidden until needed)
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        layout.addSpacing(4)

        # Primary login button
        self.login_button = QPushButton("Iniciar Sesión")
        self.login_button.setObjectName("loginButton")
        self.login_button.setIcon(qta.icon("fa5s.sign-in-alt", color="#FFFFFF"))
        self.login_button.setMinimumHeight(48)
        self.login_button.setDefault(True)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.clicked.connect(self._on_login_clicked)
        layout.addWidget(self.login_button)

        layout.addStretch()

        # Footer
        footer = QLabel(f"© 2025 - {APP_ORGANIZATION}")
        footer.setObjectName("formFooter")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        # Wire Enter key navigation
        self.usuario_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self._on_login_clicked)

        return panel

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _build_usuario_input(self) -> QHBoxLayout:
        wrapper = QFrame()
        wrapper.setObjectName("inputWrapper")
        wrapper.setProperty("focused", False)
        inner = QHBoxLayout(wrapper)
        inner.setContentsMargins(12, 0, 12, 0)
        inner.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa5s.user", color=_COLOR_TEXT_MUTED).pixmap(16, 16))

        self.usuario_input = QLineEdit()
        self.usuario_input.setObjectName("usuarioInput")
        self.usuario_input.setPlaceholderText("Ingrese su usuario")
        self.usuario_input.setFrame(False)
        self.usuario_input.installEventFilter(self)
        self._wrapper_for_input[id(self.usuario_input)] = wrapper

        inner.addWidget(icon_label)
        inner.addWidget(self.usuario_input, stretch=1)

        wrapper.setMinimumHeight(46)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(wrapper)
        return layout

    def _build_password_input(self) -> QHBoxLayout:
        wrapper = QFrame()
        wrapper.setObjectName("inputWrapper")
        wrapper.setProperty("focused", False)
        inner = QHBoxLayout(wrapper)
        inner.setContentsMargins(12, 0, 12, 0)
        inner.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa5s.lock", color=_COLOR_TEXT_MUTED).pixmap(16, 16))

        self.password_input = QLineEdit()
        self.password_input.setObjectName("passwordInput")
        self.password_input.setPlaceholderText("Ingrese su contraseña")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFrame(False)
        self.password_input.installEventFilter(self)
        self._wrapper_for_input[id(self.password_input)] = wrapper

        self.toggle_password_button = QToolButton()
        self.toggle_password_button.setObjectName("togglePasswordButton")
        self.toggle_password_button.setCursor(Qt.PointingHandCursor)
        self.toggle_password_button.setCheckable(True)
        self.toggle_password_button.setIcon(qta.icon("fa5s.eye", color=_COLOR_TEXT_MUTED))
        self.toggle_password_button.setAutoRaise(True)
        self.toggle_password_button.toggled.connect(self._on_toggle_password_visibility)

        inner.addWidget(icon_label)
        inner.addWidget(self.password_input, stretch=1)
        inner.addWidget(self.toggle_password_button)

        wrapper.setMinimumHeight(46)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(wrapper)
        return layout

    # ------------------------------------------------------------------
    # Stylesheet & layout
    # ------------------------------------------------------------------

    def _load_stylesheet(self) -> None:
        try:
            self.setStyleSheet(LOGIN_QSS_PATH.read_text(encoding="utf-8"))
        except OSError as exc:
            _logger.warning("Could not load login.qss: %s", exc)

    def eventFilter(self, obj, event):  # noqa: N802 (Qt naming)
        # Toggle the `focused` dynamic property on the input wrapper so the
        # QSS rule `QFrame#inputWrapper[focused="true"]` kicks in.
        wrapper = self._wrapper_for_input.get(id(obj))
        if wrapper is not None:
            if event.type() == QEvent.FocusIn:
                self._set_wrapper_focused(wrapper, True)
            elif event.type() == QEvent.FocusOut:
                self._set_wrapper_focused(wrapper, False)
        return super().eventFilter(obj, event)

    @staticmethod
    def _set_wrapper_focused(wrapper: QFrame, focused: bool) -> None:
        wrapper.setProperty("focused", focused)
        wrapper.style().unpolish(wrapper)
        wrapper.style().polish(wrapper)

    def resizeEvent(self, event):  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        # Stretch the hexagons backdrop to fully cover the brand panel.
        if hasattr(self, "_hex_backdrop") and self._hex_backdrop.parent() is not None:
            parent = self._hex_backdrop.parent()
            self._hex_backdrop.setGeometry(0, 0, parent.width(), parent.height())
            self._hex_backdrop.lower()
        # Pin the cells decoration to the bottom-right of the form panel.
        if hasattr(self, "_cells_deco") and self._cells_deco.parent() is not None:
            parent = self._cells_deco.parent()
            x = parent.width() - self._cells_deco.width() + 20
            y = parent.height() - self._cells_deco.height() + 20
            self._cells_deco.move(x, y)
            self._cells_deco.lower()

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def _on_toggle_password_visibility(self, checked: bool) -> None:
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_password_button.setIcon(
                qta.icon("fa5s.eye-slash", color=_COLOR_TEXT_MUTED)
            )
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_password_button.setIcon(
                qta.icon("fa5s.eye", color=_COLOR_TEXT_MUTED)
            )

    def _on_login_clicked(self) -> None:
        usuario = self.usuario_input.text().strip()
        password = self.password_input.text()

        if not usuario or not password:
            self._show_error("Ingrese usuario y contraseña.")
            return

        operario = authenticate(usuario, password)
        if operario is None:
            self._show_error("Usuario o contraseña incorrectos.")
            self.password_input.clear()
            self.password_input.setFocus()
            return

        self._clear_error()
        self._persist_remember_choice(usuario)
        get_session().login(operario)
        self.login_succeeded.emit()

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _clear_error(self) -> None:
        self.error_label.setText("")
        self.error_label.setVisible(False)

    def reset(self) -> None:
        """Clear sensitive fields and re-apply remembered user. Called after logout."""
        self.password_input.clear()
        self.toggle_password_button.setChecked(False)
        self._clear_error()
        self._restore_remembered_user()
        if self.usuario_input.text():
            self.password_input.setFocus()
        else:
            self.usuario_input.setFocus()

    # ------------------------------------------------------------------
    # Persistence (Recordar sesión)
    # ------------------------------------------------------------------

    def _restore_remembered_user(self) -> None:
        remembered = QSettings().value(SETTING_REMEMBER_USER, "", type=str)
        if remembered:
            self.usuario_input.setText(remembered)
            self.remember_checkbox.setChecked(True)
            self.password_input.setFocus()
        else:
            self.usuario_input.setFocus()

    def _persist_remember_choice(self, usuario: str) -> None:
        settings = QSettings()
        if self.remember_checkbox.isChecked():
            settings.setValue(SETTING_REMEMBER_USER, usuario)
        else:
            settings.remove(SETTING_REMEMBER_USER)
