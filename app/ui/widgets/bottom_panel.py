"""
Bottom panel console matching target screenshot layout.
Tabs: Logs | Errors | Current Job | FFmpeg Output
"""

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QTabWidget, QWidget, QPlainTextEdit,
    QHBoxLayout, QLabel, QProgressBar
)
from PyQt5.QtCore import Qt
from app.utils.constants import BOTTOM_PANEL_HEIGHT


class BottomPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bottomPanelFrame")
        self.setFixedHeight(BOTTOM_PANEL_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Logs
        self.txt_logs = QPlainTextEdit()
        self.txt_logs.setReadOnly(True)
        self.tabs.addTab(self.txt_logs, "Logs")

        # Tab 2: Errors
        self.txt_errors = QPlainTextEdit()
        self.txt_errors.setReadOnly(True)
        self.tabs.addTab(self.txt_errors, "Errors")

        # Tab 3: Current Job Details
        self.current_job_widget = QWidget()
        cj_layout = QVBoxLayout(self.current_job_widget)
        cj_layout.setContentsMargins(12, 12, 12, 12)
        cj_layout.setSpacing(8)

        self.lbl_cj_file = QLabel("Current File: None")
        self.lbl_cj_file.setStyleSheet("font-weight: bold; font-size: 13px; color: #38BDF8;")
        self.lbl_cj_op = QLabel("Operation: Idle")
        self.lbl_cj_op.setStyleSheet("color: #94A3B8;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 4px;
                text-align: center;
                background-color: #0F172A;
                color: #F8FAFC;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 3px;
            }
        """)

        cj_layout.addWidget(self.lbl_cj_file)
        cj_layout.addWidget(self.lbl_cj_op)
        cj_layout.addWidget(self.progress_bar)
        cj_layout.addStretch()

        self.tabs.addTab(self.current_job_widget, "Current Job")

        # Tab 4: FFmpeg Output
        self.txt_ffmpeg = QPlainTextEdit()
        self.txt_ffmpeg.setReadOnly(True)
        self.tabs.addTab(self.txt_ffmpeg, "FFmpeg Output")

    def append_log(self, level: str, scope: str, message: str, timestamp: str = ""):
        prefix = f"[{timestamp}] [{level.upper()}] [{scope}]" if timestamp else f"[{level.upper()}] [{scope}]"
        line = f"{prefix} {message}"
        self.txt_logs.appendPlainText(line)

        if level.lower() == "error":
            self.txt_errors.appendPlainText(line)

    def append_ffmpeg_output(self, line: str):
        self.txt_ffmpeg.appendPlainText(line)

    def update_current_job(self, file_name: str, operation: str, progress: int):
        self.lbl_cj_file.setText(f"Current File: {file_name}")
        self.lbl_cj_op.setText(f"Operation: {operation}")
        self.progress_bar.setValue(progress)

    def clear_all(self):
        self.txt_logs.clear()
        self.txt_errors.clear()
        self.txt_ffmpeg.clear()
        self.update_current_job("None", "Idle", 0)
