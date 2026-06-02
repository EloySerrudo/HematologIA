"""Video device descriptor and DirectShow enumeration helper.

Why DirectShow (and not Qt's ``QMediaDevices``):
    Qt Multimedia on Windows uses Windows Media Foundation. Some microscope
    cameras (notably the SwiftCam SC503) only ship a DirectShow filter and are
    invisible to WMF — and therefore to ``QMediaDevices``. DirectShow is the
    older Windows API and surfaces virtually every camera, including UVC
    webcams, so a single DirectShow code path covers both worlds.

Enumeration uses ``pygrabber`` (which wraps the DirectShow ``ICreateDevEnum``
COM interface) to retrieve human-readable names. If pygrabber is not
installed or fails, we fall back to probing numeric indices ``0..N-1`` so the
picker is at least usable with generic labels.

The DirectShow device *index* (the position in the enumerated list) is what
``cv2.VideoCapture(idx, cv2.CAP_DSHOW)`` expects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.config import CAMERA_FALLBACK_PROBE_INDICES
from src.core.logger import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True)
class CameraInfo:
    """Descriptor for a video input device.

    Attributes:
        index: Position in the DirectShow enumeration. Pass this directly to
            ``cv2.VideoCapture(index, cv2.CAP_DSHOW)``.
        name: Human-readable name (e.g. ``"Swift Cam SC503"``). Used both for
            the UI and as the QSettings key to restore the device next run.
    """
    index: int
    name: str


def list_video_devices() -> List[CameraInfo]:
    """Return every DirectShow video input on this system.

    Tries pygrabber first (so we get real names), then falls back to a numeric
    probe by opening each index up to ``CAMERA_FALLBACK_PROBE_INDICES`` and
    keeping the ones that report at least one frame.
    """
    devices = _enumerate_with_pygrabber()
    if devices:
        return devices

    _logger.warning(
        "pygrabber enumeration returned no devices; falling back to numeric probe."
    )
    return _enumerate_by_probing()


def resolve_remembered(name: str) -> CameraInfo | None:
    """Look up a previously-used camera by its persisted name.

    Returns the live descriptor if a device with the same name is still
    connected. ``None`` otherwise.
    """
    if not name:
        return None
    for dev in list_video_devices():
        if dev.name == name:
            return dev
    return None


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _enumerate_with_pygrabber() -> List[CameraInfo]:
    try:
        from pygrabber.dshow_graph import FilterGraph
    except Exception as exc:  # noqa: BLE001 — pygrabber/COM init can fail many ways
        _logger.warning("pygrabber import failed: %s", exc)
        return []

    try:
        names = FilterGraph().get_input_devices()
    except Exception as exc:  # noqa: BLE001
        _logger.warning("pygrabber get_input_devices() failed: %s", exc)
        return []

    return [CameraInfo(index=i, name=name or f"Cámara {i}") for i, name in enumerate(names)]


def _enumerate_by_probing() -> List[CameraInfo]:
    # Import locally so cv2 isn't required at module import time.
    import cv2

    found: List[CameraInfo] = []
    for idx in range(CAMERA_FALLBACK_PROBE_INDICES):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        try:
            if not cap.isOpened():
                continue
            ok, _ = cap.read()
            if ok:
                found.append(CameraInfo(index=idx, name=f"Cámara DirectShow #{idx}"))
        finally:
            cap.release()
    return found
