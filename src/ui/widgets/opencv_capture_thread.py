"""Background capture thread for OpenCV + DirectShow video sources.

Why a thread:
    ``cv2.VideoCapture.read()`` is blocking and (at 2592x1944 MJPEG) takes
    tens of milliseconds. Running it in the GUI thread would freeze the UI
    between frames. A ``QThread`` decouples grabbing from rendering and lets
    Qt's signal/slot machinery marshal each :class:`QImage` back into the
    main thread for display.

Why MJPEG at high resolution:
    The SwiftCam SC503 sensor is 2592x1944. Uncompressed YUV at that
    resolution exceeds USB 2.0 bandwidth and the camera silently refuses
    to stream. Forcing ``MJPG`` makes the camera compress frames on-chip;
    OpenCV decodes them per ``read()``. Other cameras that don't support
    those exact settings simply negotiate their native maximum — the
    ``set()`` calls are best-effort and never raise.

The thread keeps the latest decoded frame around so :meth:`capture_latest`
can return a still without having to wait for the next ``read()``.
"""
from __future__ import annotations

from threading import Lock
from typing import Any, Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from src.config import (
    CAMERA_PREFERRED_FOURCC,
    CAMERA_PREFERRED_HEIGHT,
    CAMERA_PREFERRED_WIDTH,
)
from src.core.logger import get_logger

_logger = get_logger(__name__)


class OpenCVCaptureThread(QThread):
    """Continuously grab frames from a DirectShow camera and emit them.

    Signals:
        frame_ready(QImage): a fresh frame, ready to draw. The QImage is a
            deep copy and outlives the underlying numpy buffer.
        started_ok(int, int, str): emitted once the first frame arrives —
            actual ``(width, height, fourcc)`` reported by the camera after
            negotiation. Useful to show "Conectada a ... 2592x1944 MJPG".
        failed(str): the capture loop could not start or died unrecoverably.
    """

    frame_ready = Signal(QImage)
    started_ok = Signal(int, int, str)
    failed = Signal(str)

    def __init__(self, device_index: int, parent=None) -> None:
        super().__init__(parent)
        self._index = device_index
        self._running = False
        self._latest: Optional[QImage] = None
        self._latest_lock = Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Ask the loop to exit and block until the thread has joined."""
        self._running = False
        # `wait` blocks the caller (typically the GUI thread). The loop
        # iteration is short (one frame's worth) so this is bounded.
        self.wait(2000)

    def capture_latest(self) -> Optional[QImage]:
        """Return a copy of the most recent frame, or ``None`` if none yet."""
        with self._latest_lock:
            if self._latest is None:
                return None
            # Detach from any shared buffer — the caller may keep this around.
            return self._latest.copy()

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------

    def run(self) -> None:  # noqa: D401 — Qt convention
        # Import cv2 lazily so a missing OpenCV install doesn't break module load.
        import cv2

        cap = cv2.VideoCapture(self._index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            msg = f"No se pudo abrir el dispositivo DirectShow #{self._index}."
            _logger.error(msg)
            self.failed.emit(msg)
            return

        # Best-effort negotiation. None of these raise on failure; OpenCV
        # silently keeps the previous value when the camera rejects them.
        fourcc = cv2.VideoWriter_fourcc(*CAMERA_PREFERRED_FOURCC)
        cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_PREFERRED_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_PREFERRED_HEIGHT)

        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        actual_fourcc = _fourcc_to_str(int(cap.get(cv2.CAP_PROP_FOURCC) or 0))
        _logger.info(
            "OpenCV camera #%s opened — negotiated %sx%s @ %s",
            self._index, actual_w, actual_h, actual_fourcc,
        )

        self._running = True
        first_frame_signaled = False

        try:
            while self._running:
                ok, frame = cap.read()
                if not ok or frame is None:
                    # Single bad read can happen during USB hiccups. The old
                    # project reopens the device; we do the same.
                    _logger.warning("read() failed on camera #%s — reopening.", self._index)
                    cap.release()
                    cap = cv2.VideoCapture(self._index, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        msg = f"La cámara #{self._index} dejó de responder."
                        _logger.error(msg)
                        self.failed.emit(msg)
                        return
                    continue

                image = _bgr_frame_to_qimage(frame)

                with self._latest_lock:
                    self._latest = image

                self.frame_ready.emit(image)

                if not first_frame_signaled:
                    first_frame_signaled = True
                    self.started_ok.emit(actual_w, actual_h, actual_fourcc)
        finally:
            cap.release()
            _logger.info("OpenCV camera #%s released.", self._index)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bgr_frame_to_qimage(frame: Any) -> QImage:
    """Convert a BGR OpenCV frame to a deep-copied RGB ``QImage``.

    ``QImage(buffer, ...)`` does not own its memory; calling ``.copy()`` is
    what detaches the image from the numpy buffer (which is overwritten on
    the next ``read()``).
    """
    import numpy as np
    # Ensure contiguous memory; OpenCV usually returns contiguous buffers,
    # but np.ascontiguousarray is a cheap no-op when already contiguous.
    rgb = frame[..., ::-1]  # BGR -> RGB (view)
    rgb = np.ascontiguousarray(rgb)
    h, w, ch = rgb.shape
    bytes_per_line = ch * w
    qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return qimg.copy()


def _fourcc_to_str(fourcc_int: int) -> str:
    """Decode the 4-char FourCC integer that OpenCV returns."""
    if fourcc_int <= 0:
        return "?"
    try:
        return "".join(chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)).strip()
    except Exception:  # noqa: BLE001
        return "?"
