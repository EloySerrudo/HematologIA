"""Camera selection panel.

Enumerates DirectShow video devices via
:func:`src.ui.widgets.camera_info.list_video_devices`, lets the operator
pick one, optionally previews the stream and confirms the choice. The
selected device's name is persisted in :data:`SETTING_LAST_CAMERA` so the
next session restores it automatically.

The "Probar" preview reuses :class:`OpenCVCaptureThread` so what you see
here is *exactly* what the live view will display once you confirm — no
backend switching between picker and main view.
"""
from __future__ import annotations

from typing import Optional

import qtawesome as qta
from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config import SETTING_LAST_CAMERA
from src.core.logger import get_logger
from src.ui.widgets.camera_info import (
    CameraInfo,
    list_video_devices,
    resolve_remembered,
)
from src.ui.widgets.opencv_capture_thread import OpenCVCaptureThread

_logger = get_logger(__name__)

_PRIMARY = "#1E40AF"


class CameraPicker(QWidget):
    """Camera selection page shown inside the live-view stack."""

    camera_selected = Signal(CameraInfo)
    cancelled = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraPicker")
        self._test_thread: Optional[OpenCVCaptureThread] = None
        self._devices: list[CameraInfo] = []

        self._build_ui()
        self._refresh_camera_list()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 1, 20, 1)
        layout.setSpacing(1)

        instruction = QLabel(
            "Elegí en la lista la cámara que corresponde al microscopio. "
            "Si no aparece, conectá la cámara y tocá «Actualizar lista»."
        )
        instruction.setStyleSheet("color: #BFDBFE; font-size: 11px;")
        instruction.setWordWrap(True)

        # --- Dropdown + buttons ---
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self._combo = QComboBox()
        self._combo.setObjectName("cameraCombo")
        self._combo.setMinimumHeight(34)
        self._combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._refresh_btn = QPushButton(" Actualizar lista")
        self._refresh_btn.setIcon(qta.icon("fa5s.sync", color=_PRIMARY))
        self._refresh_btn.setObjectName("captureSecondaryButton")
        self._refresh_btn.setMinimumHeight(34)
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.clicked.connect(self._refresh_camera_list)

        self._test_btn = QPushButton(" Probar")
        self._test_btn.setIcon(qta.icon("fa5s.eye", color=_PRIMARY))
        self._test_btn.setObjectName("captureSecondaryButton")
        self._test_btn.setMinimumHeight(34)
        self._test_btn.setCursor(Qt.PointingHandCursor)
        self._test_btn.clicked.connect(self._on_test_clicked)

        # --- Confirm + cancel ---
        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setObjectName("captureSecondaryButton")
        self._cancel_btn.setMinimumHeight(38)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel)

        self._confirm_btn = QPushButton(" Usar esta cámara")
        self._confirm_btn.setIcon(qta.icon("fa5s.check", color="#FFFFFF"))
        self._confirm_btn.setObjectName("capturePrimaryButton")
        self._confirm_btn.setMinimumHeight(38)
        self._confirm_btn.setCursor(Qt.PointingHandCursor)
        self._confirm_btn.setDefault(True)
        self._confirm_btn.clicked.connect(self._on_confirm)

        controls.addWidget(self._combo, stretch=1)
        controls.addWidget(self._refresh_btn)
        controls.addWidget(self._test_btn)
        controls.addWidget(self._cancel_btn)
        controls.addWidget(self._confirm_btn)

        # --- Preview area ---
        self._preview = QLabel()
        self._preview.setObjectName("cameraPreview")
        self._preview.setMinimumHeight(220)
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._preview.setStyleSheet(
            "background-color: #0F172A; color: #94A3B8; border-radius: 6px;"
            "font-size: 11px;"
        )
        self._preview.setText("Tocá «Probar» para ver el preview.")

        # --- Status / error message ---
        self._status_label = QLabel("Tocá «Probar» para ver el preview de la cámara seleccionada.")
        self._status_label.setStyleSheet("color: #BFDBFE; font-size: 11px;")
        self._status_label.setWordWrap(True)

        layout.addWidget(instruction)
        layout.addLayout(controls)
        layout.addWidget(self._preview, stretch=1)
        layout.addWidget(self._status_label)

        self.setStyleSheet(
            "QWidget#cameraPicker { background-color: #1E3A8A; border-radius: 6px; }"
            "QComboBox#cameraCombo { background-color: #FFFFFF; color: #111827; "
            "  border: 1px solid #BFDBFE; border-radius: 6px; padding: 4px 8px; }"
            "QComboBox#cameraCombo QAbstractItemView { background-color: #FFFFFF; "
            "  color: #111827; selection-background-color: #EFF6FF; }"
        )

    # ------------------------------------------------------------------
    # Camera list management
    # ------------------------------------------------------------------

    def _refresh_camera_list(self) -> None:
        """Re-populate the combo with the current set of available cameras."""
        # Stop any preview before re-enumerating — we may invalidate the
        # currently-selected device.
        self._stop_test()

        previous_name = None
        if self._combo.count() > 0:
            prev = self._combo.currentData()
            if isinstance(prev, CameraInfo):
                previous_name = prev.name

        self._combo.clear()
        self._devices = list_video_devices()

        if not self._devices:
            self._combo.addItem("No se detectaron cámaras", None)
            self._combo.setEnabled(False)
            self._test_btn.setEnabled(False)
            self._confirm_btn.setEnabled(False)
            self._status_label.setText(
                "No se detectaron cámaras conectadas. Verificá que la cámara del "
                "microscopio esté enchufada y que no la esté usando otro programa."
            )
            return

        self._combo.setEnabled(True)
        self._test_btn.setEnabled(True)
        self._confirm_btn.setEnabled(True)

        remembered_name = QSettings().value(SETTING_LAST_CAMERA, "", type=str)
        preferred_index = -1

        for i, dev in enumerate(self._devices):
            self._combo.addItem(dev.name, dev)
            if preferred_index < 0 and remembered_name and dev.name == remembered_name:
                preferred_index = i

        if preferred_index < 0 and previous_name is not None:
            for i, dev in enumerate(self._devices):
                if dev.name == previous_name:
                    preferred_index = i
                    break

        if preferred_index >= 0:
            self._combo.setCurrentIndex(preferred_index)

        self._status_label.setText(
            f"{len(self._devices)} cámara(s) detectada(s). "
            "Seleccioná una y tocá «Probar» para verificar."
        )

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _on_test_clicked(self) -> None:
        device = self._combo.currentData()
        if not isinstance(device, CameraInfo):
            return
        self._stop_test()

        thread = OpenCVCaptureThread(device.index, parent=self)
        thread.frame_ready.connect(self._on_preview_frame)
        thread.started_ok.connect(self._on_preview_started)
        thread.failed.connect(self._on_preview_failed)
        self._test_thread = thread
        thread.start()

        self._status_label.setText(
            f"Abriendo «{device.name}»… esperá el primer frame."
        )

    def _stop_test(self) -> None:
        if self._test_thread is not None:
            try:
                self._test_thread.stop()
            except Exception:  # noqa: BLE001
                pass
            self._test_thread.deleteLater()
            self._test_thread = None

    def _on_preview_frame(self, image: QImage) -> None:
        if image.isNull():
            return
        pix = QPixmap.fromImage(image)
        scaled = pix.scaled(
            self._preview.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._preview.setPixmap(scaled)

    def _on_preview_started(self, w: int, h: int, fourcc: str) -> None:
        device = self._combo.currentData()
        name = device.name if isinstance(device, CameraInfo) else "cámara"
        self._status_label.setText(
            f"Mostrando preview de «{name}» — {w}x{h} {fourcc}. "
            "Si no es la cámara del microscopio, elegí otra y volvé a probar."
        )

    def _on_preview_failed(self, message: str) -> None:
        _logger.warning("Preview camera failed: %s", message)
        self._preview.setPixmap(QPixmap())
        self._preview.setText("Sin señal")
        self._status_label.setText(
            f"Error al acceder a la cámara: {message}. Probá con otro dispositivo."
        )

    # ------------------------------------------------------------------
    # Confirm / cancel
    # ------------------------------------------------------------------

    def _on_confirm(self) -> None:
        device = self._combo.currentData()
        if not isinstance(device, CameraInfo):
            return
        QSettings().setValue(SETTING_LAST_CAMERA, device.name)
        _logger.info("Camera selected and persisted: %s (#%s)", device.name, device.index)
        self._stop_test()
        self.camera_selected.emit(device)

    def _on_cancel(self) -> None:
        self._stop_test()
        self.cancelled.emit()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Release the preview thread. Safe to call from the parent's teardown."""
        self._stop_test()

    @staticmethod
    def resolve_remembered_camera() -> Optional[CameraInfo]:
        """If a camera was persisted in QSettings and is still connected, return it."""
        name = QSettings().value(SETTING_LAST_CAMERA, "", type=str)
        return resolve_remembered(name)
