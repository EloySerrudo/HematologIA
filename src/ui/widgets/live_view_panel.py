"""Live preview + still-image capture for the Captura screen.

OpenCV/DirectShow-backed live view. See
:mod:`src.ui.widgets.opencv_capture_thread` for the rationale behind not
using ``QCamera``.

Public surface (kept stable so :class:`CapturaView` doesn't need to know
which backend is running):

* :meth:`start(CameraInfo)` — open the device and begin streaming.
* :meth:`stop()` — release the device; safe to call repeatedly.
* :meth:`capture()` — grab the latest frame synchronously and emit it
  through :attr:`captured`.
* :meth:`is_active()` — whether a capture thread is currently running.

Signals:
    status_changed(bool, str): emitted when the camera transitions between
        active/inactive (or on errors).
    captured(QImage, int): a still capture decoded successfully. The integer
        is a monotonically increasing request id so callers can correlate
        captures with their UI feedback.
    capture_failed(str): the still capture failed.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.core.logger import get_logger
from src.ui.widgets.camera_info import CameraInfo
from src.ui.widgets.opencv_capture_thread import OpenCVCaptureThread

_logger = get_logger(__name__)


class LiveViewPanel(QWidget):
    """Shows a continuously-running camera preview and supports still capture."""

    status_changed = Signal(bool, str)
    captured = Signal(QImage, int)
    capture_failed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveViewPanel")
        self._thread: Optional[OpenCVCaptureThread] = None
        self._device: Optional[CameraInfo] = None
        self._capture_request_seq: int = 0
        self._active: bool = False

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._video = QLabel()
        self._video.setObjectName("liveViewVideo")
        self._video.setMinimumHeight(280)
        self._video.setAlignment(Qt.AlignCenter)
        self._video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._video.setStyleSheet(
            "background-color: #111827; color: #6B7280; border-radius: 6px;"
            "font-size: 12px;"
        )
        self._video.setText("Esperando cámara…")
        # Allow the label to shrink below the natural pixmap size — otherwise
        # a 2592x1944 frame would force the window wider than the screen.
        self._video.setScaledContents(False)
        layout.addWidget(self._video)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, device: CameraInfo) -> None:
        """Open ``device`` and begin streaming. Stops any previous stream first."""
        self.stop()
        self._device = device

        thread = OpenCVCaptureThread(device.index, parent=self)
        thread.frame_ready.connect(self._on_frame)
        thread.started_ok.connect(self._on_started_ok)
        thread.failed.connect(self._on_thread_failed)
        thread.finished.connect(self._on_thread_finished)

        self._thread = thread
        _logger.info("Starting OpenCV camera: index=%s name=%s", device.index, device.name)
        thread.start()

    def stop(self) -> None:
        """Stop the capture thread and clear the preview. Safe to call repeatedly."""
        if self._thread is not None:
            try:
                self._thread.stop()
            except Exception as exc:  # noqa: BLE001
                _logger.warning("Error stopping capture thread: %s", exc)
            self._thread.deleteLater()
            self._thread = None
        self._device = None
        self._active = False
        self._video.setPixmap(QPixmap())  # clear any leftover frame
        self._video.setText("Esperando cámara…")

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def capture(self) -> int:
        """Grab the latest frame as a still and emit it through :attr:`captured`.

        Returns the request id, or ``-1`` if no frame is available yet.
        """
        if self._thread is None or not self._active:
            self.capture_failed.emit("La cámara no está activa.")
            return -1

        image = self._thread.capture_latest()
        if image is None:
            self.capture_failed.emit("Todavía no llegó el primer frame.")
            return -1

        self._capture_request_seq += 1
        rid = self._capture_request_seq
        self.captured.emit(image, rid)
        return rid

    # ------------------------------------------------------------------
    # Thread signal handlers
    # ------------------------------------------------------------------

    def _on_frame(self, image: QImage) -> None:
        # Scale on display only — the underlying QImage stays full-res so
        # capture() returns the sensor's native resolution.
        if image.isNull():
            return
        pix = QPixmap.fromImage(image)
        scaled = pix.scaled(
            self._video.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._video.setPixmap(scaled)

    def _on_started_ok(self, w: int, h: int, fourcc: str) -> None:
        self._active = True
        name = self._device.name if self._device else "cámara"
        self.status_changed.emit(True, f"Conectada a «{name}» — {w}x{h} {fourcc}")

    def _on_thread_failed(self, message: str) -> None:
        self._active = False
        _logger.warning("Capture thread reported failure: %s", message)
        self.status_changed.emit(False, message)

    def _on_thread_finished(self) -> None:
        # The thread either was stopped voluntarily or died after a failure.
        # We don't flip status_changed here when there was no failure, because
        # the explicit stop() path is already silent. After a `failed` signal
        # the status was already updated to inactive.
        self._active = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def device(self) -> Optional[CameraInfo]:
        return self._device

    def is_active(self) -> bool:
        return self._active and self._thread is not None
