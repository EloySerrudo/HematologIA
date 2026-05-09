"""Camera selection panel.

Lists every video input reported by Qt, lets the operator pick one, optionally
shows a "Probar" preview, and confirms the choice. The selected camera's
description is persisted in :data:`SETTING_LAST_CAMERA` so future sessions
restore it automatically.

Notes on device identity (Windows/UVC):
  * ``QCameraDevice.id()`` is opaque bytes that often include the OS device
    path; it can change across reboots or USB hub re-enumerations.
  * ``QCameraDevice.description()`` is a human-readable string that tends to
    stay stable for a given model. We persist *that* and re-resolve to the
    current ``QCameraDevice`` on startup.
"""
from __future__ import annotations

from typing import Optional

import qtawesome as qta
from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import (
    QCamera,
    QCameraDevice,
    QMediaCaptureSession,
    QMediaDevices,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config import SETTING_LAST_CAMERA
from src.core.logger import get_logger

_logger = get_logger(__name__)

_PRIMARY = "#1E40AF"
_TEXT_MUTED = "#6B7280"


class CameraPicker(QWidget):
    """Camera selection page shown inside the live-view stack."""

    camera_selected = Signal(QCameraDevice)
    cancelled = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraPicker")
        self._test_camera: Optional[QCamera] = None
        self._test_session: Optional[QMediaCaptureSession] = None

        # `videoInputsChanged` is an *instance* signal — keep a QMediaDevices
        # instance alive so we get device hot-plug notifications.
        self._media_devices = QMediaDevices(self)
        self._media_devices.videoInputsChanged.connect(self._refresh_camera_list)

        self._build_ui()
        self._refresh_camera_list()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Seleccioná la cámara del microscopio")
        title.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 700;")

        instruction = QLabel(
            "Elegí en la lista la cámara que corresponde al microscopio.\n"
            "Probá el preview antes de confirmar para asegurarte que es la correcta."
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

        self._test_btn = QPushButton(" Probar")
        self._test_btn.setIcon(qta.icon("fa5s.eye", color=_PRIMARY))
        self._test_btn.setObjectName("captureSecondaryButton")
        self._test_btn.setMinimumHeight(34)
        self._test_btn.setCursor(Qt.PointingHandCursor)
        self._test_btn.clicked.connect(self._on_test_clicked)

        controls.addWidget(self._combo, stretch=1)
        controls.addWidget(self._test_btn)

        # --- Preview area ---
        self._preview = QVideoWidget()
        self._preview.setObjectName("cameraPreview")
        self._preview.setMinimumHeight(220)
        self._preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._preview.setStyleSheet(
            "background-color: #0F172A; border-radius: 6px;"
        )

        # --- Status / error message ---
        self._status_label = QLabel("Tocá «Probar» para ver el preview de la cámara seleccionada.")
        self._status_label.setStyleSheet("color: #BFDBFE; font-size: 11px;")
        self._status_label.setWordWrap(True)

        # --- Confirm + cancel ---
        actions = QHBoxLayout()
        actions.setSpacing(10)

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

        actions.addStretch()
        actions.addWidget(self._cancel_btn)
        actions.addWidget(self._confirm_btn)

        layout.addWidget(title)
        layout.addWidget(instruction)
        layout.addLayout(controls)
        layout.addWidget(self._preview, stretch=1)
        layout.addWidget(self._status_label)
        layout.addLayout(actions)

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
        previous = self._combo.currentData() if self._combo.count() > 0 else None
        self._combo.clear()

        devices = QMediaDevices.videoInputs()
        if not devices:
            self._combo.addItem("No se detectaron cámaras", None)
            self._combo.setEnabled(False)
            self._test_btn.setEnabled(False)
            self._confirm_btn.setEnabled(False)
            self._status_label.setText(
                "No se detectaron cámaras conectadas. Verificá que la cámara del "
                "microscopio esté enchufada y que el sistema operativo permita "
                "el acceso a cámaras."
            )
            return

        self._combo.setEnabled(True)
        self._test_btn.setEnabled(True)
        self._confirm_btn.setEnabled(True)

        # Persisted choice from a previous session (description string).
        remembered_desc = QSettings().value(SETTING_LAST_CAMERA, "", type=str)
        preferred_index = -1

        for idx, dev in enumerate(devices):
            label = dev.description() or "Cámara sin nombre"
            if dev.isDefault():
                label += "  (predeterminada)"
            self._combo.addItem(label, dev)

            # Prefer the remembered camera, then the same instance as before.
            if preferred_index < 0 and remembered_desc and dev.description() == remembered_desc:
                preferred_index = idx

        if preferred_index < 0 and isinstance(previous, QCameraDevice):
            for idx in range(self._combo.count()):
                cd = self._combo.itemData(idx)
                if isinstance(cd, QCameraDevice) and cd.id() == previous.id():
                    preferred_index = idx
                    break

        if preferred_index >= 0:
            self._combo.setCurrentIndex(preferred_index)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _on_test_clicked(self) -> None:
        device = self._combo.currentData()
        if not isinstance(device, QCameraDevice):
            return
        self._stop_test()

        try:
            self._test_camera = QCamera(device)
            self._test_session = QMediaCaptureSession()
            self._test_session.setCamera(self._test_camera)
            self._test_session.setVideoOutput(self._preview)
            self._test_camera.errorOccurred.connect(self._on_camera_error)
            self._test_camera.start()
        except Exception as exc:  # noqa: BLE001
            _logger.error("Failed to start preview camera: %s", exc)
            self._status_label.setText(f"No se pudo iniciar el preview: {exc}")
            return

        self._status_label.setText(
            f"Mostrando preview de «{device.description()}». "
            "Si la imagen no es del microscopio, elegí otra cámara y volvé a probar."
        )

    def _stop_test(self) -> None:
        if self._test_camera is not None:
            try:
                self._test_camera.stop()
            except Exception:  # noqa: BLE001
                pass
            self._test_camera.deleteLater()
            self._test_camera = None
        if self._test_session is not None:
            self._test_session.deleteLater()
            self._test_session = None

    def _on_camera_error(self, error, error_string: str) -> None:  # noqa: ARG002
        _logger.warning("Preview camera error: %s", error_string)
        self._status_label.setText(
            f"Error al acceder a la cámara: {error_string or 'desconocido'}. "
            "Probá con otro dispositivo."
        )

    # ------------------------------------------------------------------
    # Confirm / cancel
    # ------------------------------------------------------------------

    def _on_confirm(self) -> None:
        device = self._combo.currentData()
        if not isinstance(device, QCameraDevice):
            return
        # Persist the description so next session restores the same camera.
        QSettings().setValue(SETTING_LAST_CAMERA, device.description())
        _logger.info("Camera selected and persisted: %s", device.description())
        self._stop_test()
        self.camera_selected.emit(device)

    def _on_cancel(self) -> None:
        self._stop_test()
        self.cancelled.emit()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Release the preview camera. Safe to call from the parent's teardown."""
        self._stop_test()

    @staticmethod
    def resolve_remembered_camera() -> Optional[QCameraDevice]:
        """If a camera was persisted in QSettings and is still connected, return it."""
        desc = QSettings().value(SETTING_LAST_CAMERA, "", type=str)
        if not desc:
            return None
        for dev in QMediaDevices.videoInputs():
            if dev.description() == desc:
                return dev
        return None
