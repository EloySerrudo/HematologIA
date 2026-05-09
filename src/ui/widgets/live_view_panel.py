"""Live preview + still-image capture for the Captura screen.

Wraps a :class:`QCamera` + :class:`QMediaCaptureSession` + :class:`QImageCapture`
into a single widget. Exposes:

* :attr:`status_changed` — fires when the camera connects/disconnects so the
  parent view can update the status indicators.
* :meth:`capture_to` — kicks off an async still capture; the resulting
  :class:`QImage` arrives through the :attr:`captured` signal once Qt finishes
  decoding the frame.
* :meth:`stop` — releases the camera; safe to call multiple times.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import (
    QCamera,
    QCameraDevice,
    QImageCapture,
    QMediaCaptureSession,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from src.core.logger import get_logger

_logger = get_logger(__name__)


class LiveViewPanel(QWidget):
    """Shows a continuously-running camera preview and supports still capture.

    Signals:
        status_changed(active: bool, message: str): emitted when the camera
            transitions between active and inactive (or on errors). The parent
            uses this to update the «Cámara conectada» / «Formato OK» dots.
        captured(image: QImage, request_id: int): a still capture decoded
            successfully. The parent decides where to save it.
        capture_failed(error: str): the still capture failed.
    """

    status_changed = Signal(bool, str)
    captured = Signal(QImage, int)
    capture_failed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveViewPanel")
        self._camera: Optional[QCamera] = None
        self._session: Optional[QMediaCaptureSession] = None
        self._image_capture: Optional[QImageCapture] = None
        self._device: Optional[QCameraDevice] = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._video = QVideoWidget()
        self._video.setObjectName("liveViewVideo")
        self._video.setMinimumHeight(280)
        self._video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._video.setStyleSheet(
            "background-color: #111827; border-radius: 6px;"
        )
        layout.addWidget(self._video)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, device: QCameraDevice) -> None:
        """Start streaming from ``device``. Stops any previous stream first."""
        self.stop()
        self._device = device

        self._camera = QCamera(device)
        self._session = QMediaCaptureSession()
        self._session.setCamera(self._camera)
        self._session.setVideoOutput(self._video)

        self._image_capture = QImageCapture()
        # NOTE: QImageCapture defaults to "save to file" mode. We override that
        # to ask for the in-memory QImage so we can re-encode (PNG + thumb)
        # ourselves with a single decoded buffer.
        self._image_capture.setFileFormat(QImageCapture.FileFormat.PNG)
        self._session.setImageCapture(self._image_capture)

        self._camera.errorOccurred.connect(self._on_camera_error)
        self._camera.activeChanged.connect(self._on_active_changed)
        self._image_capture.imageCaptured.connect(self._on_image_captured)
        self._image_capture.errorOccurred.connect(self._on_image_capture_error)

        try:
            self._camera.start()
        except Exception as exc:  # noqa: BLE001
            _logger.error("Camera start raised: %s", exc)
            self.status_changed.emit(False, str(exc))
            return

        _logger.info("Camera started: %s", device.description())

    def stop(self) -> None:
        """Stop the camera and release Qt resources. Safe to call repeatedly."""
        if self._camera is not None:
            try:
                self._camera.stop()
            except Exception:  # noqa: BLE001
                pass
            self._camera.deleteLater()
            self._camera = None
        if self._image_capture is not None:
            self._image_capture.deleteLater()
            self._image_capture = None
        if self._session is not None:
            self._session.deleteLater()
            self._session = None
        self._device = None

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def capture(self) -> int:
        """Trigger an asynchronous still capture.

        Returns the request id assigned by Qt (-1 if the capture cannot be
        scheduled because the camera is not ready). The decoded QImage will
        arrive through :attr:`captured`.
        """
        if self._image_capture is None or self._camera is None or not self._camera.isActive():
            self.capture_failed.emit("La cámara no está activa.")
            return -1
        if not self._image_capture.isReadyForCapture():
            self.capture_failed.emit("La cámara está procesando una captura previa.")
            return -1
        return self._image_capture.capture()

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_active_changed(self, active: bool) -> None:
        if active:
            desc = self._device.description() if self._device else "cámara"
            self.status_changed.emit(True, f"Conectada a «{desc}»")
        else:
            self.status_changed.emit(False, "Cámara inactiva")

    def _on_camera_error(self, error, error_string: str) -> None:  # noqa: ARG002
        _logger.warning("Live camera error: %s", error_string)
        self.status_changed.emit(False, error_string or "Error desconocido")

    def _on_image_captured(self, request_id: int, preview: QImage) -> None:
        # `preview` IS the decoded image (full resolution on most platforms).
        self.captured.emit(preview, request_id)

    def _on_image_capture_error(self, request_id: int, error, error_string: str) -> None:  # noqa: ARG002
        _logger.error("ImageCapture error (req=%s): %s", request_id, error_string)
        self.capture_failed.emit(error_string or "Error al capturar la imagen.")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def device(self) -> Optional[QCameraDevice]:
        return self._device

    def is_active(self) -> bool:
        return self._camera is not None and self._camera.isActive()
