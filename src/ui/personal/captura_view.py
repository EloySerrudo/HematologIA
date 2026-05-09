"""Capture screen content for the Personal role.

Composes the patient banner, thumbnail strip, live-view panel (real
:class:`QCamera`-backed widget), pre-report cell count table and the
quick guide footer.

The view is *bound to a single estudio* — every capture (camera or upload)
goes to ``data/capturas/{id_muestra}/`` as ``img_NN.png`` plus a JPEG
thumbnail (``img_NN_thumb.jpg``) and gets persisted via :mod:`captura_repo`.

The live-view area is a :class:`QStackedWidget` with two pages:

* :class:`CameraPicker` — shown when no camera is selected yet (or the
  user clicked «Cambiar cámara»).
* :class:`LiveViewPanel` — shown once a camera is active.

A previously-chosen camera (persisted in :data:`SETTING_LAST_CAMERA`) is
auto-restored on startup; if it isn't connected anymore we fall back to
the picker.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import qtawesome as qta
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QImage, QImageReader, QPixmap
from PySide6.QtMultimedia import QCameraDevice
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.config import (
    APP_DISPLAY_NAME,
    CAPTURAS_DIR,
    CAPTURA_THUMBNAIL_MAX_PX,
    CAPTURA_THUMBNAIL_QUALITY,
)
from src.core.cell_types import empty_counts
from src.core.logger import get_logger
from src.database.models import Estudio, Paciente
from src.database.repositories import captura_repo
from src.ui.widgets.camera_picker import CameraPicker
from src.ui.widgets.cell_count_table import CellCountTable
from src.ui.widgets.coming_soon import show_coming_soon
from src.ui.widgets.guia_rapida import GuiaRapida
from src.ui.widgets.live_view_panel import LiveViewPanel
from src.ui.widgets.thumbnail_strip import ThumbnailStrip

_logger = get_logger(__name__)


_PRIMARY = "#1E40AF"
_TEXT_DARK = "#111827"
_TEXT_MUTED = "#6B7280"
_OK_GREEN = "#059669"
_NEUTRAL_GRAY = "#9CA3AF"

_LIVE_PAGE = 0
_PICKER_PAGE = 1


class CapturaView(QWidget):
    """The full Captura screen, bound to a (paciente, estudio) pair."""

    # Emitted whenever a new capture is added (image_path_relative, total_in_session).
    captura_added = Signal(str, int)

    def __init__(
        self,
        paciente: Paciente,
        estudio: Estudio,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("capturaView")
        self._paciente = paciente
        self._estudio = estudio
        self._captura_count: int = 0
        self._session_seconds: int = 0

        # Directory for this study's captures (data/capturas/{id_muestra}/).
        # We sanitize the id_muestra so it can never contain path separators.
        self._study_dir: Path = CAPTURAS_DIR / _safe_dirname(estudio.id_muestra)
        self._study_dir.mkdir(parents=True, exist_ok=True)

        self._build_ui()

        # Session timer ticks every second.
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

        # Pick the page to show: live view if a camera was remembered, picker otherwise.
        QTimer.singleShot(0, self._restore_or_pick_camera)

    # ------------------------------------------------------------------
    # Public API used by PersonalMainWindow
    # ------------------------------------------------------------------

    @property
    def estudio(self) -> Estudio:
        return self._estudio

    @property
    def paciente(self) -> Paciente:
        return self._paciente

    @property
    def has_captures(self) -> bool:
        return self._captura_count > 0

    def stop_session(self) -> None:
        """Stop the timer and release the camera. Called when the view is disposed."""
        if self._timer.isActive():
            self._timer.stop()
        self._live_view.stop()
        self._picker.stop()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        outer.addLayout(self._build_header_block())

        middle = QGridLayout()
        middle.setHorizontalSpacing(16)
        middle.setVerticalSpacing(16)
        middle.addWidget(self._build_thumbnails_section(), 0, 0)
        middle.addWidget(self._build_live_view_section(), 1, 0)
        middle.addWidget(self._build_pre_report_section(), 0, 1, 2, 1)
        middle.setColumnStretch(0, 7)
        middle.setColumnStretch(1, 3)
        middle.setRowStretch(0, 0)
        middle.setRowStretch(1, 1)
        outer.addLayout(middle, stretch=1)

        outer.addWidget(GuiaRapida())

    # ----- Header (title + paciente banner) -----

    def _build_header_block(self) -> QVBoxLayout:
        block = QVBoxLayout()
        block.setSpacing(4)

        title = QLabel("Captura de Imagen")
        title.setObjectName("dashboardGreeting")
        tfont = QFont()
        tfont.setPointSize(18)
        tfont.setBold(True)
        title.setFont(tfont)

        banner = QFrame()
        banner.setObjectName("pacienteBanner")
        banner.setStyleSheet(
            "QFrame#pacienteBanner { background-color: #EFF6FF; "
            "border: 1px solid #BFDBFE; border-radius: 8px; padding: 10px 14px; }"
        )
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(10)

        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.user-injured", color=_PRIMARY).pixmap(18, 18))

        info = QLabel(
            f"<b>Paciente:</b> {self._paciente.nombre_completo}  "
            f"·  <b>HC:</b> {self._paciente.historia_clinica}  "
            f"·  <b>Muestra:</b> {self._estudio.id_muestra}  "
            f"·  <b>Procedencia:</b> {self._estudio.procedencia}"
        )
        info.setTextFormat(Qt.RichText)
        info.setStyleSheet(f"color: {_TEXT_DARK}; font-size: 12px;")

        change_btn = QPushButton(" Cambiar paciente")
        change_btn.setObjectName("inlineLinkButton")
        change_btn.setCursor(Qt.PointingHandCursor)
        change_btn.setIcon(qta.icon("fa5s.exchange-alt", color=_PRIMARY))
        change_btn.clicked.connect(lambda: show_coming_soon(self, "Cambiar paciente"))

        bl.addWidget(icon)
        bl.addWidget(info, stretch=1)
        bl.addWidget(change_btn)

        block.addWidget(title)
        block.addWidget(banner)
        return block

    # ----- Thumbnails strip -----

    def _build_thumbnails_section(self) -> QFrame:
        section = QFrame()
        section.setObjectName("captureSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        title = QLabel("Capturas de esta sesión")
        title.setObjectName("sectionTitle")
        tfont = QFont()
        tfont.setPointSize(12)
        tfont.setBold(True)
        title.setFont(tfont)

        self._strip_counter_label = QLabel("0 imágenes capturadas")
        self._strip_counter_label.setObjectName("stripCounter")
        self._strip_counter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self._strip_counter_label)

        self._thumbnail_strip = ThumbnailStrip()

        layout.addLayout(header_row)
        layout.addWidget(self._thumbnail_strip)
        return section

    # ----- Live view section (real camera) -----

    def _build_live_view_section(self) -> QFrame:
        section = QFrame()
        section.setObjectName("captureSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Title row + change-camera button
        header_row = QHBoxLayout()
        title = QLabel("Cámara en Vivo")
        title.setObjectName("sectionTitle")
        tfont = QFont()
        tfont.setPointSize(12)
        tfont.setBold(True)
        title.setFont(tfont)

        change_cam = QPushButton(" Cambiar cámara")
        change_cam.setObjectName("changeCameraButton")
        change_cam.setIcon(qta.icon("fa5s.cog", color=_PRIMARY))
        change_cam.setCursor(Qt.PointingHandCursor)
        change_cam.clicked.connect(self._open_camera_picker)

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(change_cam)

        # Status indicators (updated by LiveViewPanel.status_changed)
        status_row = QHBoxLayout()
        status_row.setSpacing(14)
        self._status_camera = QLabel()
        self._status_format = QLabel()
        self._set_camera_status(False, "Cámara desconectada")
        self._set_format_status(False, "Formato pendiente")
        status_row.addWidget(self._status_camera)
        status_row.addWidget(self._status_format)
        status_row.addStretch()

        # --- Stack: live view (page 0) | camera picker (page 1) ---
        self._live_stack = QStackedWidget()
        self._live_stack.setMinimumHeight(280)
        self._live_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._live_view = LiveViewPanel()
        self._live_view.status_changed.connect(self._on_camera_status_changed)
        self._live_view.captured.connect(self._on_image_captured)
        self._live_view.capture_failed.connect(self._on_capture_failed)
        self._live_stack.insertWidget(_LIVE_PAGE, self._live_view)

        self._picker = CameraPicker()
        self._picker.camera_selected.connect(self._on_camera_selected)
        self._picker.cancelled.connect(self._on_picker_cancelled)
        self._live_stack.insertWidget(_PICKER_PAGE, self._picker)

        # Status bar with timer + counter (white background so labels are visible).
        info_bar = QFrame()
        info_bar.setObjectName("captureInfoBar")
        info_row = QHBoxLayout(info_bar)
        info_row.setContentsMargins(2, 4, 2, 4)
        info_row.setSpacing(6)

        timer_icon = QLabel()
        timer_icon.setPixmap(qta.icon("fa5s.clock", color=_PRIMARY).pixmap(14, 14))
        timer_icon.setFixedSize(14, 14)

        self._timer_label = QLabel("Sesión: 00:00:00")
        self._timer_label.setObjectName("sessionTimer")

        counter_icon = QLabel()
        counter_icon.setPixmap(qta.icon("fa5s.camera", color=_PRIMARY).pixmap(14, 14))
        counter_icon.setFixedSize(14, 14)

        self._counter_label = QLabel("0 capturas")
        self._counter_label.setObjectName("captureCounter")

        info_row.addWidget(timer_icon)
        info_row.addWidget(self._timer_label)
        info_row.addSpacing(24)
        info_row.addWidget(counter_icon)
        info_row.addWidget(self._counter_label)
        info_row.addStretch()

        # Action buttons
        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)

        self._upload_btn = QPushButton(" Subir imagen")
        self._upload_btn.setObjectName("captureSecondaryButton")
        self._upload_btn.setIcon(qta.icon("fa5s.folder-open", color=_PRIMARY))
        self._upload_btn.setMinimumHeight(42)
        self._upload_btn.setCursor(Qt.PointingHandCursor)
        self._upload_btn.clicked.connect(self._on_upload_clicked)

        self._capture_btn = QPushButton(" Capturar")
        self._capture_btn.setObjectName("capturePrimaryButton")
        self._capture_btn.setIcon(qta.icon("fa5s.camera", color="#FFFFFF"))
        self._capture_btn.setMinimumHeight(42)
        self._capture_btn.setCursor(Qt.PointingHandCursor)
        self._capture_btn.setEnabled(False)  # enabled once the camera is active
        self._capture_btn.clicked.connect(self._on_capture_clicked)

        actions_row.addWidget(self._upload_btn, stretch=1)
        actions_row.addWidget(self._capture_btn, stretch=2)

        layout.addLayout(header_row)
        layout.addLayout(status_row)
        layout.addWidget(self._live_stack, stretch=1)
        layout.addWidget(info_bar)
        layout.addLayout(actions_row)
        return section

    # ----- Pre-report section -----

    def _build_pre_report_section(self) -> QFrame:
        section = QFrame()
        section.setObjectName("captureSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        title = QLabel("Pre-reporte")
        title.setObjectName("sectionTitle")
        tfont = QFont()
        tfont.setPointSize(12)
        tfont.setBold(True)
        title.setFont(tfont)

        subtitle = QLabel("Conteo de células detectadas en la sesión")
        subtitle.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 11px;")

        self._cell_table = CellCountTable()
        self._cell_table.set_counts(empty_counts())

        report_btn = QPushButton(" Generar Reporte")
        report_btn.setObjectName("generateReportButton")
        report_btn.setIcon(qta.icon("fa5s.file-pdf", color="#FFFFFF"))
        report_btn.setMinimumHeight(40)
        report_btn.setCursor(Qt.PointingHandCursor)
        report_btn.setStyleSheet(
            "QPushButton#generateReportButton {"
            "  background-color: #EA580C; color: white; border: none;"
            "  border-radius: 8px; font-size: 12px; font-weight: 600; padding: 0 12px;"
            "}"
            "QPushButton#generateReportButton:hover { background-color: #C2410C; }"
        )
        report_btn.clicked.connect(lambda: show_coming_soon(self, "Generar Reporte"))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._cell_table)
        layout.addStretch()
        layout.addWidget(report_btn)
        return section

    # ------------------------------------------------------------------
    # Camera lifecycle
    # ------------------------------------------------------------------

    def _restore_or_pick_camera(self) -> None:
        """Try to start the remembered camera; if missing, show the picker."""
        device = CameraPicker.resolve_remembered_camera()
        if device is None:
            self._open_camera_picker()
            return
        self._start_camera(device)

    def _open_camera_picker(self) -> None:
        # Stop any active live preview before showing the picker.
        self._live_view.stop()
        self._capture_btn.setEnabled(False)
        self._set_camera_status(False, "Selección de cámara…")
        self._set_format_status(False, "Formato pendiente")
        self._live_stack.setCurrentIndex(_PICKER_PAGE)

    def _on_camera_selected(self, device: QCameraDevice) -> None:
        self._start_camera(device)

    def _on_picker_cancelled(self) -> None:
        # If we have a running camera already, fall back to it. Otherwise stay
        # on the picker page so the user can try again.
        if self._live_view.is_active():
            self._live_stack.setCurrentIndex(_LIVE_PAGE)

    def _start_camera(self, device: QCameraDevice) -> None:
        self._live_stack.setCurrentIndex(_LIVE_PAGE)
        self._live_view.start(device)
        # `status_changed` will flip the dot to green once the camera is actually streaming.

    def _on_camera_status_changed(self, active: bool, message: str) -> None:
        self._set_camera_status(active, message if active else f"Cámara: {message}")
        # We trust the camera's reported pixel format on UVC devices.
        self._set_format_status(active, "Formato OK" if active else "Formato pendiente")
        self._capture_btn.setEnabled(active)

    def _set_camera_status(self, ok: bool, text: str) -> None:
        color = _OK_GREEN if ok else _NEUTRAL_GRAY
        self._status_camera.setText(f"●  {text}")
        self._status_camera.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 600;"
        )

    def _set_format_status(self, ok: bool, text: str) -> None:
        color = _OK_GREEN if ok else _NEUTRAL_GRAY
        self._status_format.setText(f"●  {text}")
        self._status_format.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 600;"
        )

    # ------------------------------------------------------------------
    # Capture handlers
    # ------------------------------------------------------------------

    def _on_capture_clicked(self) -> None:
        self._capture_btn.setEnabled(False)  # prevent double-click; re-enabled on result
        request_id = self._live_view.capture()
        if request_id < 0:
            # Capture refused; re-enable so user can try again.
            self._capture_btn.setEnabled(True)

    def _on_image_captured(self, image: QImage, request_id: int) -> None:  # noqa: ARG002
        try:
            rel_path = self._persist_image(image)
        except Exception as exc:  # noqa: BLE001
            _logger.error("Failed to persist captured image: %s", exc)
            QMessageBox.warning(
                self, APP_DISPLAY_NAME,
                f"No se pudo guardar la captura:\n{exc}",
            )
            self._capture_btn.setEnabled(self._live_view.is_active())
            return

        self._register_new_capture(rel_path)
        self._capture_btn.setEnabled(self._live_view.is_active())

    def _on_capture_failed(self, error: str) -> None:
        QMessageBox.warning(self, APP_DISPLAY_NAME, f"Error al capturar: {error}")
        self._capture_btn.setEnabled(self._live_view.is_active())

    # ------------------------------------------------------------------
    # Upload handler
    # ------------------------------------------------------------------

    def _on_upload_clicked(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccioná una imagen para subir",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        if not path_str:
            return

        src = Path(path_str)
        try:
            image = self._load_image_from_disk(src)
            rel_path = self._persist_image(image, source_for_log=src)
        except Exception as exc:  # noqa: BLE001
            _logger.error("Failed to upload image %s: %s", src, exc)
            QMessageBox.warning(
                self, APP_DISPLAY_NAME,
                f"No se pudo subir la imagen:\n{exc}",
            )
            return

        self._register_new_capture(rel_path)

    @staticmethod
    def _load_image_from_disk(path: Path) -> QImage:
        """Load ``path`` as a QImage with auto-orientation. Raises on failure."""
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise OSError(reader.errorString() or f"No se pudo leer {path.name}")
        return image

    # ------------------------------------------------------------------
    # Persistence (disk + DB)
    # ------------------------------------------------------------------

    def _persist_image(self, image: QImage, *, source_for_log: Optional[Path] = None) -> str:
        """Save ``image`` as PNG + JPEG thumbnail to the study directory.

        Returns the path of the PNG *relative to* ``data/capturas/`` — i.e.
        what gets stored in ``capturas.path_imagen``.
        """
        idx = self._next_capture_index()
        png_name = f"img_{idx:02d}.png"
        thumb_name = f"img_{idx:02d}_thumb.jpg"
        png_path = self._study_dir / png_name
        thumb_path = self._study_dir / thumb_name

        # Original PNG (lossless).
        if not image.save(str(png_path), "PNG"):
            raise OSError(f"No se pudo escribir {png_path}")

        # JPEG thumbnail for the strip.
        thumb = image.scaled(
            CAPTURA_THUMBNAIL_MAX_PX, CAPTURA_THUMBNAIL_MAX_PX,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        if not thumb.save(str(thumb_path), "JPEG", CAPTURA_THUMBNAIL_QUALITY):
            # PNG still saved; remove it to keep things consistent.
            png_path.unlink(missing_ok=True)
            raise OSError(f"No se pudo escribir el thumbnail {thumb_path}")

        rel_path = f"{self._study_dir.name}/{png_name}"

        captura_repo.create(id_estudio=self._estudio.id_estudio, path_imagen=rel_path)
        if source_for_log is not None:
            _logger.info(
                "Uploaded image '%s' -> %s (estudio=%s)",
                source_for_log.name, rel_path, self._estudio.id_estudio,
            )
        else:
            _logger.info(
                "Captured image -> %s (estudio=%s)",
                rel_path, self._estudio.id_estudio,
            )
        return rel_path

    def _next_capture_index(self) -> int:
        """Return the next ``NN`` for ``img_NN.png`` based on what's on disk.

        Counting on disk (rather than on the in-memory counter) is robust to
        crashes mid-session: re-opening the same estudio resumes numbering
        without colliding.
        """
        existing = sorted(self._study_dir.glob("img_*.png"))
        if not existing:
            return 1
        last = existing[-1].stem  # e.g. "img_05"
        try:
            n = int(last.split("_")[1])
            return n + 1
        except (IndexError, ValueError):
            return len(existing) + 1

    def _register_new_capture(self, rel_path: str) -> None:
        """Update the strip + counters after a successful capture/upload."""
        self._captura_count += 1

        # Build the absolute path for the thumbnail and feed it to the strip.
        png_filename = Path(rel_path).name
        thumb_filename = png_filename.replace(".png", "_thumb.jpg")
        thumb_path = self._study_dir / thumb_filename
        if thumb_path.exists():
            self._thumbnail_strip.add_thumbnail(thumb_path)
        else:
            # Fallback: scale the PNG live (slow but functional).
            png_path = self._study_dir / png_filename
            pix = QPixmap(str(png_path))
            self._thumbnail_strip.add_pixmap(pix)

        # Update header counter and footer.
        self._strip_counter_label.setText(
            f"{self._captura_count} {'imagen capturada' if self._captura_count == 1 else 'imágenes capturadas'}"
        )
        self._counter_label.setText(
            f"{self._captura_count} {'captura' if self._captura_count == 1 else 'capturas'}"
        )
        self.captura_added.emit(rel_path, self._captura_count)

    # ------------------------------------------------------------------
    # Session timer
    # ------------------------------------------------------------------

    def _on_tick(self) -> None:
        self._session_seconds += 1
        h, rem = divmod(self._session_seconds, 3600)
        m, s = divmod(rem, 60)
        self._timer_label.setText(f"Sesión: {h:02d}:{m:02d}:{s:02d}")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _safe_dirname(name: str) -> str:
    """Sanitize an id_muestra so it can be used as a directory name on Windows.

    Replaces ``/``, ``\\`` and anything that's not alphanumeric, dash, dot or
    underscore with an underscore. The id_muestra is alphanumeric in our
    schema, but we never want a path-traversal surprise from a future
    "MUESTRAS/2024/A".
    """
    import re
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return cleaned or "estudio"
