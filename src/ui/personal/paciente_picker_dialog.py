"""Modal dialog to pick (or register) the paciente that owns a new estudio.

Shown when the operario clicks "Captura de Imagen" in the sidebar. The
dialog has two tabs:

* **Buscar paciente existente** — lookup by historia clínica or hospital ID;
  if found, displays the paciente's data (read-only) and lets the user
  confirm or cancel.
* **Registrar nuevo paciente** — form with all schema fields; required ones
  are marked with ``*``.

Both tabs share a bottom block that asks for the *estudio*'s ``id_muestra``
and ``procedencia`` (also required).

On accept, the dialog creates (or reuses) the paciente, creates the estudio,
and exposes both via the :attr:`paciente` and :attr:`estudio` properties.
The caller can then enter the live capture view with a valid ``id_estudio``.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDate

from src.config import APP_DISPLAY_NAME
from src.core.logger import get_logger
from src.core.session import get_session
from src.database.models import Estudio, Paciente
from src.database.repositories import estudio_repo, paciente_repo

_logger = get_logger(__name__)


class PacientePickerDialog(QDialog):
    """Modal that resolves a (paciente, estudio) pair for a new capture session."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} — Iniciar sesión de captura")
        self.setModal(True)
        self.setMinimumSize(560, 580)

        self._paciente: Optional[Paciente] = None
        self._estudio: Optional[Estudio] = None
        self._found_paciente: Optional[Paciente] = None  # set by the search tab

        self._apply_light_theme()
        self._build_ui()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_light_theme(self) -> None:
        """Force a light theme so the dialog ignores the system's dark mode."""
        self.setStyleSheet(
            """
            QDialog {
                background-color: #FFFFFF;
                color: #111827;
            }
            QLabel {
                color: #111827;
                background: transparent;
                font-family: "Segoe UI", "Inter", "Arial", sans-serif;
                font-size: 12px;
            }
            QLineEdit, QComboBox, QDateEdit, QAbstractSpinBox {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 6px 10px;
                font-family: "Segoe UI", "Inter", "Arial", sans-serif;
                font-size: 12px;
                selection-background-color: #BFDBFE;
                min-height: 22px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #1E40AF;
            }
            QLineEdit::placeholder {
                color: #9CA3AF;
            }
            QComboBox::drop-down, QDateEdit::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #E5E7EB;
                selection-background-color: #EFF6FF;
                selection-color: #111827;
                outline: 0;
            }
            QTabWidget::pane {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #F3F4F6;
                color: #6B7280;
                padding: 8px 18px;
                border: 1px solid #E5E7EB;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-family: "Segoe UI", "Inter", "Arial", sans-serif;
                font-size: 12px;
                font-weight: 600;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #1E40AF;
                border-bottom: 2px solid #1E40AF;
            }
            QTabBar::tab:hover:!selected {
                background-color: #FFFFFF;
                color: #1F2937;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #1E40AF;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 6px 14px;
                font-family: "Segoe UI", "Inter", "Arial", sans-serif;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #EFF6FF;
            }
            QPushButton:default {
                background-color: #1E40AF;
                color: #FFFFFF;
                border: 1px solid #1E40AF;
            }
            QPushButton:default:hover {
                background-color: #1D4ED8;
            }
            QFrame {
                background: transparent;
            }
            """
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def paciente(self) -> Optional[Paciente]:
        """The paciente that was found or just created. None until the dialog is accepted."""
        return self._paciente

    @property
    def estudio(self) -> Optional[Estudio]:
        """The estudio just created in the DB. None until the dialog is accepted."""
        return self._estudio

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(14)

        title = QLabel("Iniciar sesión de captura")
        title.setObjectName("dialogTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")

        subtitle = QLabel(
            "Seleccioná el paciente y completá los datos de la muestra "
            "antes de capturar imágenes."
        )
        subtitle.setStyleSheet("color: #6B7280; font-size: 11px;")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # --- Tabs (search vs new patient) ---
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.addTab(self._build_search_tab(), "Buscar paciente existente")
        self._tabs.addTab(self._build_new_tab(), "Registrar nuevo paciente")
        layout.addWidget(self._tabs, stretch=1)

        # --- Estudio data block (shared) ---
        layout.addWidget(self._build_estudio_block())

        # --- Buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self._accept_btn = QPushButton("Iniciar captura")
        self._accept_btn.setDefault(True)
        self._accept_btn.setMinimumHeight(36)
        buttons.addButton(self._accept_btn, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        self._accept_btn.clicked.connect(self._on_accept)
        layout.addWidget(buttons)

    # ----- Search tab -----

    def _build_search_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(10)

        instructions = QLabel(
            "Buscá un paciente ya registrado por su historia clínica o ID del hospital."
        )
        instructions.setStyleSheet("color: #6B7280; font-size: 11px;")
        instructions.setWordWrap(True)

        # Search field + selector
        search_row = QHBoxLayout()
        self._search_field = QComboBox()
        self._search_field.addItems(["Historia clínica", "ID del hospital"])
        self._search_field.setFixedWidth(160)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Ej.: HC-2024-0001")
        self._search_input.returnPressed.connect(self._on_search)
        search_btn = QPushButton("Buscar")
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.clicked.connect(self._on_search)

        search_row.addWidget(self._search_field)
        search_row.addWidget(self._search_input, stretch=1)
        search_row.addWidget(search_btn)

        # Result panel
        self._result_panel = QFrame()
        self._result_panel.setObjectName("pacienteResult")
        self._result_panel.setStyleSheet(
            "QFrame#pacienteResult { background-color: #F9FAFB; "
            "border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; }"
        )
        result_layout = QVBoxLayout(self._result_panel)
        result_layout.setContentsMargins(0, 0, 0, 0)
        self._result_label = QLabel("Realizá una búsqueda para ver los datos del paciente.")
        self._result_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        self._result_label.setWordWrap(True)
        result_layout.addWidget(self._result_label)

        layout.addWidget(instructions)
        layout.addLayout(search_row)
        layout.addWidget(self._result_panel, stretch=1)
        return page

    # ----- New patient tab -----

    def _build_new_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(8, 12, 8, 8)
        outer.setSpacing(10)

        info = QLabel("Los campos marcados con * son obligatorios.")
        info.setStyleSheet("color: #6B7280; font-size: 11px;")

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        self._new_hc = QLineEdit()
        self._new_hc.setPlaceholderText("Ej.: HC-2024-0010")
        self._new_id_hosp = QLineEdit()
        self._new_id_hosp.setPlaceholderText("Ej.: HSK/2024/0010")
        self._new_nombre = QLineEdit()
        self._new_ape_pat = QLineEdit()
        self._new_ape_mat = QLineEdit()

        self._new_genero = QComboBox()
        self._new_genero.addItem("(no especificado)", None)
        self._new_genero.addItem("Femenino", "F")
        self._new_genero.addItem("Masculino", "M")

        self._new_fecha_nac = QDateEdit()
        self._new_fecha_nac.setCalendarPopup(True)
        self._new_fecha_nac.setDisplayFormat("dd/MM/yyyy")
        self._new_fecha_nac.setSpecialValueText("(sin especificar)")
        # Allow "no date" by setting min/special value below the real range.
        self._new_fecha_nac.setMinimumDate(QDate(1900, 1, 1))
        self._new_fecha_nac.setDate(self._new_fecha_nac.minimumDate())

        self._new_documento = QLineEdit()
        self._new_documento.setPlaceholderText("CI / DNI (opcional)")

        form.addRow(QLabel("Historia clínica *"), self._new_hc)
        form.addRow(QLabel("ID hospital *"), self._new_id_hosp)
        form.addRow(QLabel("Nombre *"), self._new_nombre)
        form.addRow(QLabel("Apellido paterno *"), self._new_ape_pat)
        form.addRow(QLabel("Apellido materno"), self._new_ape_mat)
        form.addRow(QLabel("Género"), self._new_genero)
        form.addRow(QLabel("Fecha de nacimiento"), self._new_fecha_nac)
        form.addRow(QLabel("Documento"), self._new_documento)

        outer.addWidget(info)
        outer.addLayout(form)
        outer.addStretch()
        return page

    # ----- Estudio data block -----

    def _build_estudio_block(self) -> QFrame:
        block = QFrame()
        block.setObjectName("estudioBlock")
        block.setStyleSheet(
            "QFrame#estudioBlock { background-color: #EFF6FF; "
            "border: 1px solid #BFDBFE; border-radius: 8px; padding: 12px; }"
        )
        layout = QFormLayout(block)
        layout.setSpacing(8)
        layout.setLabelAlignment(Qt.AlignRight)

        self._id_muestra = QLineEdit()
        self._id_muestra.setPlaceholderText("Ej.: M-2024-009")
        self._procedencia = QComboBox()
        self._procedencia.setEditable(True)
        for code in ("URG", "CON-EXT", "INT-MED", "INT-PED"):
            self._procedencia.addItem(code)
        self._procedencia.setCurrentText("")
        self._procedencia.lineEdit().setPlaceholderText("Código de procedencia (ej.: URG)")

        header = QLabel("Datos del estudio")
        header.setStyleSheet("font-weight: 600; color: #1E3A8A;")
        layout.addRow(header)
        layout.addRow(QLabel("ID de muestra *"), self._id_muestra)
        layout.addRow(QLabel("Procedencia *"), self._procedencia)
        return block

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def _on_search(self) -> None:
        query = self._search_input.text().strip()
        if not query:
            self._set_result_message("Ingresá un valor para buscar.", warning=True)
            self._found_paciente = None
            return

        if self._search_field.currentIndex() == 0:
            paciente = paciente_repo.get_by_historia_clinica(query)
        else:
            paciente = paciente_repo.get_by_id_hospital(query)

        if paciente is None:
            self._set_result_message(
                "No se encontró ningún paciente con ese identificador. "
                "Podés registrarlo desde la pestaña «Registrar nuevo paciente».",
                warning=True,
            )
            self._found_paciente = None
            return

        self._found_paciente = paciente
        self._render_paciente_card(paciente)

    def _render_paciente_card(self, p: Paciente) -> None:
        # Replace the result panel content with a structured card.
        for child in self._result_panel.findChildren(QWidget):
            child.deleteLater()
        layout = self._result_panel.layout()
        # Wipe layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        name = QLabel(p.nombre_completo)
        name.setStyleSheet("font-size: 14px; font-weight: 700; color: #111827;")

        details = QLabel(
            f"<b>Historia clínica:</b> {p.historia_clinica} &nbsp; "
            f"<b>ID hospital:</b> {p.id_paciente_hospital}<br>"
            f"<b>Género:</b> {p.genero or '—'} &nbsp; "
            f"<b>Documento:</b> {p.documento or '—'}<br>"
            f"<b>Fecha de nacimiento:</b> {p.fecha_nacimiento or '—'}"
        )
        details.setStyleSheet("color: #374151; font-size: 11px;")
        details.setTextFormat(Qt.RichText)
        details.setWordWrap(True)

        layout.addWidget(name)
        layout.addWidget(details)
        layout.addStretch()

    def _set_result_message(self, msg: str, *, warning: bool = False) -> None:
        # Wipe existing widgets and put a single label.
        layout = self._result_panel.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        label = QLabel(msg)
        label.setWordWrap(True)
        color = "#B91C1C" if warning else "#6B7280"
        label.setStyleSheet(f"color: {color}; font-size: 11px;")
        layout.addWidget(label)

    # ------------------------------------------------------------------
    # Accept handler
    # ------------------------------------------------------------------

    def _on_accept(self) -> None:
        # Validate the estudio fields first (always required).
        id_muestra = self._id_muestra.text().strip()
        procedencia = self._procedencia.currentText().strip()
        if not id_muestra or not procedencia:
            self._show_error("Completá los campos del estudio (ID de muestra y procedencia).")
            return

        # Resolve paciente based on the active tab.
        if self._tabs.currentIndex() == 0:
            paciente = self._found_paciente
            if paciente is None:
                self._show_error(
                    "Buscá un paciente existente o registrá uno nuevo en la otra pestaña."
                )
                return
        else:
            paciente = self._try_create_paciente()
            if paciente is None:
                return  # error already shown

        # Create the estudio.
        op = get_session().operario
        if op is None:
            self._show_error("Sesión inválida — volvé a iniciar sesión.")
            return

        try:
            estudio = estudio_repo.create(
                id_paciente=paciente.id_paciente,
                id_operario=op.id_operario,
                id_muestra=id_muestra,
                procedencia=procedencia,
            )
        except sqlite3.IntegrityError as exc:
            _logger.warning("Failed to create estudio: %s", exc)
            self._show_error(
                f"Ya existe un estudio con ID de muestra «{id_muestra}». "
                "Usá un identificador distinto."
            )
            return
        except Exception as exc:  # noqa: BLE001
            _logger.error("Unexpected error creating estudio: %s", exc)
            self._show_error("No se pudo crear el estudio. Revisá los logs.")
            return

        _logger.info(
            "Created estudio id=%s for paciente %s by operario %s",
            estudio.id_estudio, paciente.historia_clinica, op.usuario,
        )
        self._paciente = paciente
        self._estudio = estudio
        self.accept()

    def _try_create_paciente(self) -> Optional[Paciente]:
        hc = self._new_hc.text().strip()
        id_hosp = self._new_id_hosp.text().strip()
        nombre = self._new_nombre.text().strip()
        ape_pat = self._new_ape_pat.text().strip()
        if not hc or not id_hosp or not nombre or not ape_pat:
            self._show_error(
                "Faltan campos obligatorios del paciente (historia clínica, "
                "ID hospital, nombre, apellido paterno)."
            )
            return None

        ape_mat = self._new_ape_mat.text().strip() or None
        documento = self._new_documento.text().strip() or None
        genero = self._new_genero.currentData()
        fecha = self._new_fecha_nac.date()
        fecha_iso: Optional[str] = None
        if fecha != self._new_fecha_nac.minimumDate():
            fecha_iso = fecha.toString("yyyy-MM-dd")

        try:
            return paciente_repo.create(
                historia_clinica=hc,
                id_paciente_hospital=id_hosp,
                nombre=nombre,
                apellido_paterno=ape_pat,
                apellido_materno=ape_mat,
                fecha_nacimiento=fecha_iso,
                genero=genero,
                documento=documento,
            )
        except sqlite3.IntegrityError as exc:
            _logger.warning("Failed to create paciente: %s", exc)
            msg = str(exc).lower()
            if "historia_clinica" in msg:
                hint = "Ya existe un paciente con esa historia clínica."
            elif "id_paciente_hospital" in msg:
                hint = "Ya existe un paciente con ese ID del hospital."
            elif "documento" in msg:
                hint = "Ya existe un paciente con ese documento."
            else:
                hint = "Datos duplicados."
            self._show_error(hint)
            return None
        except Exception as exc:  # noqa: BLE001
            _logger.error("Unexpected error creating paciente: %s", exc)
            self._show_error("No se pudo registrar el paciente. Revisá los logs.")
            return None

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, APP_DISPLAY_NAME, message)
