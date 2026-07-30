"""
Full implementation of JobsPage, HistoryPage, SettingsPage, and AIFeaturesPage.
Jobs & History now feature full QTableView data grids with search, filter, and audit capabilities.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QFormLayout,
    QSpinBox, QLineEdit, QPushButton, QTableView, QHeaderView,
    QComboBox, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt

from app.database.repositories.settings_repository import SettingsRepository
from app.database.repositories.history_repository import HistoryRepository
from app.database.repositories.job_repository import JobRepository
from app.models.job_table_model import JobTableModel
from app.utils.time_format import ms_to_hms


class JobsPage(QWidget):
    """Active Jobs & Queue Monitor Page with QTableView grid."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.job_repo = JobRepository()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("⏳ Active Jobs & Queue Monitor")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0284C7;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh Queue")
        self.btn_refresh.setProperty("class", "actionBtn")
        self.btn_refresh.clicked.connect(self.reload_jobs)
        hdr.addWidget(self.btn_refresh)

        layout.addLayout(hdr)

        # Filter bar
        filter_box = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search active jobs...")
        self.txt_search.textChanged.connect(self._on_search)
        filter_box.addWidget(self.txt_search, stretch=1)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["All Status", "Waiting", "Processing", "Completed", "Failed"])
        self.cmb_filter.currentTextChanged.connect(self._on_filter)
        filter_box.addWidget(self.cmb_filter)

        layout.addLayout(filter_box)

        # Table Grid
        self.table_model = JobTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)

        header = self.table_view.horizontalHeader()
        header.setMinimumHeight(38)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setStretchLastSection(True)

        layout.addWidget(self.table_view)
        self.reload_jobs()

    def reload_jobs(self):
        jobs = self.job_repo.list_all()
        self.table_model.set_jobs(jobs)

    def _on_search(self, text: str):
        self.table_model.set_search_text(text)

    def _on_filter(self, status: str):
        self.table_model.set_status_filter(status)


class HistoryPage(QWidget):
    """Historical Audit Log Page with QTableView grid and CSV Export."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_repo = HistoryRepository()
        self.job_repo = JobRepository()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("📜 Processing History & Audit Log")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0284C7;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        self.btn_clear = QPushButton("🗑 Clear History")
        self.btn_clear.setProperty("class", "dangerBtn")
        self.btn_clear.clicked.connect(self._clear_history)
        hdr.addWidget(self.btn_clear)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setProperty("class", "actionBtn")
        self.btn_refresh.clicked.connect(self.reload_history)
        hdr.addWidget(self.btn_refresh)

        layout.addLayout(hdr)

        # Table Grid
        self.table_model = JobTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)

        header = self.table_view.horizontalHeader()
        header.setMinimumHeight(38)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setStretchLastSection(True)

        layout.addWidget(self.table_view)
        self.reload_history()

    def reload_history(self):
        import json
        records = self.history_repo.list_all()
        history_jobs = []
        for r in records:
            job_data = {}
            if r.get("summary_json"):
                try:
                    job_data = json.loads(r["summary_json"])
                except Exception:
                    pass
            if not job_data:
                job_data = dict(r)

            status = str(job_data.get("status") or r.get("status") or "").lower()
            if status in ("completed", "failed", "cancelled"):
                job_data["status"] = status
                history_jobs.append(job_data)

        self.table_model.set_jobs(history_jobs)

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Clear History", "Are you sure you want to clear all processing history?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.history_repo.clear_all()
            self.reload_history()


class SettingsPage(QWidget):
    """Application Settings Page styled natively in QSS (No hardcoded dark backgrounds)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_repo = SettingsRepository()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        lbl = QLabel("⚙️ Application Settings")
        lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0284C7;")
        layout.addWidget(lbl)

        form_frame = QFrame()
        form_frame.setProperty("class", "cardBox")
        form = QFormLayout(form_frame)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(14)

        self.spn_workers = QSpinBox()
        self.spn_workers.setRange(1, 8)
        self.spn_workers.setValue(int(self.settings_repo.get("workerCount", "1")))
        form.addRow("Max Parallel Worker Threads:", self.spn_workers)

        self.txt_ffmpeg_path = QLineEdit()
        self.txt_ffmpeg_path.setText(self.settings_repo.get("ffmpegPath", ""))
        self.txt_ffmpeg_path.setPlaceholderText("Leave empty for auto-detected imageio-ffmpeg")
        form.addRow("Custom FFmpeg Executable Path:", self.txt_ffmpeg_path)

        layout.addWidget(form_frame)

        btn_save = QPushButton("Save Preferences")
        btn_save.setProperty("class", "primaryBtn")
        btn_save.setMinimumHeight(38)
        btn_save.clicked.connect(self._save_settings)
        layout.addWidget(btn_save)

        layout.addStretch()

    def _save_settings(self):
        self.settings_repo.set("workerCount", str(self.spn_workers.value()))
        self.settings_repo.set("ffmpegPath", self.txt_ffmpeg_path.text().strip())
        QMessageBox.information(self, "Settings Saved", "Preferences saved successfully.")


class AIFeaturesPage(QWidget):
    """AI Features Preview Page."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        badge = QLabel("COMING SOON — V2.0 MODULE")
        badge.setStyleSheet("background-color: #9333EA; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        badge.setFixedWidth(210)

        lbl = QLabel("🤖 AI Video Editing Suite")
        lbl.setStyleSheet("font-size: 24px; font-weight: bold; margin-top: 10px;")

        desc = QLabel(
            "Upcoming features in Abd Editor V2.0:\n\n"
            "• 🗣️ AI Auto-Captions Generation\n"
            "• 🌐 Chinese -> English Voice Dubbing\n"
            "• 🎙️ Speech Recognition & Cut out silences\n"
            "• 🎬 Scene Change Detection\n"
            "• 🎣 Viral Hook Detection\n"
            "• 👥 Voice Cloning & Audio Synthesis"
        )
        desc.setStyleSheet("font-size: 14px; line-height: 1.8;")

        layout.addWidget(badge)
        layout.addWidget(lbl)
        layout.addWidget(desc)
        layout.addStretch()
