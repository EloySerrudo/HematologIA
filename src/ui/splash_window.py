"""Splash screen shown while the app boots.

Displays the app name, a short tagline, and an indeterminate progress bar for
``SPLASH_DURATION_MS`` milliseconds, then fires the ``finished`` signal.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from src.config import (
    APP_DISPLAY_NAME,
    APP_VERSION,
    SPLASH_DURATION_MS,
    SPLASH_HEIGHT,
    SPLASH_WIDTH,
)


class SplashWindow(QWidget):
    """Frameless splash window shown for ``SPLASH_DURATION_MS`` ms."""

    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedSize(SPLASH_WIDTH, SPLASH_HEIGHT)

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 30)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        # Logo placeholder — a circle of text. Replace with an image later.
        logo = QLabel("⬢")
        logo.setAlignment(Qt.AlignCenter)
        logo_font = QFont()
        logo_font.setPointSize(48)
        logo.setFont(logo_font)
        logo.setObjectName("splashLogo")

        title = QLabel(APP_DISPLAY_NAME)
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setObjectName("splashTitle")

        subtitle = QLabel("Análisis inteligente de células sanguíneas")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("splashSubtitle")

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)

        version = QLabel(f"v{APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        version.setObjectName("splashVersion")

        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addWidget(self.progress)
        layout.addSpacing(4)
        layout.addWidget(version)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background-color: #1E3A8A;
            }
            QLabel {
                color: #FFFFFF;
                background-color: transparent;
            }
            QLabel#splashLogo {
                color: #DC2626;
            }
            QLabel#splashSubtitle {
                color: #BFDBFE;
            }
            QLabel#splashVersion {
                color: #93C5FD;
                font-size: 10px;
            }
            QProgressBar {
                background-color: #1E40AF;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #60A5FA;
                border-radius: 2px;
            }
            """
        )

    def start(self) -> None:
        """Show the splash and emit ``finished`` after the configured delay."""
        self.show()
        QTimer.singleShot(SPLASH_DURATION_MS, self._on_timeout)

    def _on_timeout(self) -> None:
        self.close()
        self.finished.emit()
