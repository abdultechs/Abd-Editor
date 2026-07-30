"""
Application bootstrap and launcher.
Sets up database migrations, applies QSS stylesheet, instantiates QApplication and MainWindow.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from app.database.migrations import run_migrations
from app.ui.main_window import MainWindow
from app.utils.constants import STYLES_DIR


def create_application():
    """Bootstrap database and launch PyQt5 QApplication."""
    # Enable High DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy") and hasattr(QApplication, "setHighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("Abd Editor V1.0")
    app.setOrganizationName("AbdEditor")

    from PyQt5.QtGui import QFont
    default_font = QFont("Segoe UI", 11)
    app.setFont(default_font)

    # Run database migrations
    run_migrations()

    # Load default QSS theme (Light Theme)
    qss_path = os.path.join(STYLES_DIR, "light_theme.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
