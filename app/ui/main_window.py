"""
Main Window Shell for Abd Editor V1.0.

Integrates:
- Toolbar (top)
- Sidebar (left)
- Stacked Pages (center)
- Bottom Console (bottom)
- QueueManager signal connections
"""

import os
import csv
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

from app.ui.widgets.sidebar import Sidebar
from app.ui.widgets.toolbar import Toolbar
from app.ui.widgets.bottom_panel import BottomPanel
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.scripts_page import ScriptsPage
from app.ui.pages.auxiliary_pages import JobsPage, HistoryPage, SettingsPage, AIFeaturesPage
from app.workers.queue_manager import QueueManager
from app.database.repositories.script_repository import ScriptRepository
from app.models.enums import AppView
from app.utils.constants import WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, EXPORTS_DIR


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Abd Editor V1.0")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self.queue_mgr = QueueManager()
        self.script_repo = ScriptRepository()

        self.input_folder = ""
        self.output_folder = ""

        self._init_ui()
        self._connect_signals()
        self._reload_scripts()

        # Initial queue snapshot load
        self.queue_mgr.emit_snapshot()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # 1. Top Toolbar
        self.toolbar = Toolbar()
        main_vbox.addWidget(self.toolbar)

        # 2. Middle Row: Sidebar + Stacked Content Pages
        middle_hbox = QHBoxLayout()
        middle_hbox.setContentsMargins(0, 0, 0, 0)
        middle_hbox.setSpacing(0)

        self.sidebar = Sidebar()
        middle_hbox.addWidget(self.sidebar)

        self.pages_stack = QStackedWidget()
        self.page_dashboard = DashboardPage()
        self.page_scripts = ScriptsPage()
        self.page_jobs = JobsPage()
        self.page_history = HistoryPage()
        self.page_settings = SettingsPage()
        self.page_ai = AIFeaturesPage()

        self.pages_stack.addWidget(self.page_dashboard)  # Index 0
        self.pages_stack.addWidget(self.page_scripts)    # Index 1
        self.pages_stack.addWidget(self.page_jobs)       # Index 2
        self.pages_stack.addWidget(self.page_history)    # Index 3
        self.pages_stack.addWidget(self.page_settings)   # Index 4
        self.pages_stack.addWidget(self.page_ai)         # Index 5

        from PyQt5.QtWidgets import QScrollArea, QFrame

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidget(self.pages_stack)

        middle_hbox.addWidget(self.scroll_area, stretch=1)
        main_vbox.addLayout(middle_hbox, stretch=1)

        # 3. Bottom Log Console
        self.bottom_panel = BottomPanel()
        main_vbox.addWidget(self.bottom_panel)

    def _connect_signals(self):
        # Sidebar Navigation
        self.sidebar.navigated.connect(self._on_navigate)
        self.sidebar.new_job_clicked.connect(self._on_select_input_folder)

        self.current_theme = "light"

        # Toolbar Actions
        self.toolbar.add_folder_clicked.connect(self._on_select_input_folder)
        self.toolbar.output_folder_clicked.connect(self._on_select_output_folder)
        self.toolbar.cmb_script.currentIndexChanged.connect(self._on_script_changed)
        self.toolbar.start_clicked.connect(self._on_start_processing)
        self.toolbar.stop_clicked.connect(self._on_stop_processing)
        self.toolbar.refresh_clicked.connect(self._on_refresh)
        self.toolbar.theme_toggled.connect(self._on_toggle_theme)

        # Page Actions
        self.page_dashboard.export_requested.connect(self._on_export_csv)
        self.page_dashboard.jobs_delete_requested.connect(self.queue_mgr.delete_jobs)

        # QueueManager Signals -> UI
        self.queue_mgr.queue_snapshot_updated.connect(self._on_snapshot_updated)
        self.queue_mgr.log_emitted.connect(self._on_log_emitted)
        self.queue_mgr.ffmpeg_output_emitted.connect(self._on_ffmpeg_output)
        self.queue_mgr.progress_updated.connect(self._on_progress_updated)
        self.queue_mgr.current_job_changed.connect(self._on_current_job_changed)
        self.queue_mgr.queue_idle.connect(self._on_queue_idle)

    def _reload_scripts(self):
        scripts = self.script_repo.list_all()
        self.toolbar.populate_scripts(scripts)

    def _on_navigate(self, view_key: str):
        views_map = {
            AppView.DASHBOARD.value: 0,
            AppView.SCRIPTS.value: 1,
            AppView.JOBS.value: 2,
            AppView.HISTORY.value: 3,
            AppView.SETTINGS.value: 4,
            AppView.AI_FEATURES.value: 5,
        }
        idx = views_map.get(view_key, 0)
        self.pages_stack.setCurrentIndex(idx)
        if view_key == AppView.SCRIPTS.value:
            self.page_scripts.reload_scripts()

    def _on_select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video Input Folder")
        if folder:
            self.input_folder = folder
            if not self.output_folder:
                self.output_folder = os.path.join(folder, "Output")
            self._scan_folder()

    def _on_select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video Output Folder")
        if folder:
            self.output_folder = folder
            if self.input_folder:
                self._scan_folder()

    def _on_script_changed(self):
        if self.input_folder and self.output_folder:
            self._scan_folder()

    def _scan_folder(self):
        if not self.input_folder or not self.output_folder:
            return
        script_id = self.toolbar.get_selected_script_id()
        res = self.queue_mgr.scan_folder(self.input_folder, self.output_folder, script_id)
        self.bottom_panel.append_log("info", "app", f"Scanned {res['created']} videos into queue.")

    def _on_start_processing(self):
        if not self.input_folder:
            self._on_select_input_folder()
            if not self.input_folder:
                return

        script_id = self.toolbar.get_selected_script_id()
        self._scan_folder()

        self.queue_mgr.start()
        self.toolbar.set_running_state(True)

    def _on_stop_processing(self):
        self.queue_mgr.stop()
        self.toolbar.set_running_state(False)

    def _on_refresh(self):
        self.queue_mgr.emit_snapshot()
        self._reload_scripts()

    def _on_snapshot_updated(self, summary: dict, jobs: list):
        self.page_dashboard.update_summary(summary)
        self.page_dashboard.update_jobs(jobs)

        self.sidebar.update_queue_stats(
            proc=summary.get("processing", 0),
            wait=summary.get("waiting", 0),
            comp=summary.get("completed", 0),
            fail=summary.get("failed", 0),
        )

        running = summary.get("running", False)
        self.toolbar.set_running_state(running)

    def _on_log_emitted(self, level: str, scope: str, message: str):
        self.bottom_panel.append_log(level, scope, message)

    def _on_ffmpeg_output(self, job_id: str, line: str):
        self.bottom_panel.append_ffmpeg_output(line)

    def _on_progress_updated(self, job_id: str, progress: int, operation: str):
        job = self.queue_mgr.job_repo.find_by_id(job_id)
        file_name = job["file_name"] if job else job_id
        self.bottom_panel.update_current_job(file_name, operation, progress)

    def _on_current_job_changed(self, job: dict, script: dict | None):
        self.bottom_panel.update_current_job(job.get("file_name", ""), "Processing", job.get("progress", 0))

    def _on_queue_idle(self, summary: dict):
        last_file = summary.get("lastJob") or "None"
        self.bottom_panel.update_current_job(last_file, "Completed", 100)

    def _on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Jobs to CSV", os.path.join(EXPORTS_DIR, "jobs_export.csv"), "CSV Files (*.csv)")
        if path:
            try:
                jobs = self.queue_mgr.job_repo.list_all()
                if not jobs:
                    QMessageBox.warning(self, "Export", "No jobs to export.")
                    return
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
                QMessageBox.information(self, "Export Complete", f"Exported {len(jobs)} rows to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))

    def _on_toggle_theme(self):
        from PyQt5.QtWidgets import QApplication
        from app.utils.constants import STYLES_DIR

        app = QApplication.instance()
        if not app:
            return

        if self.current_theme == "light":
            self.current_theme = "dark"
            self.toolbar.btn_theme.setText("🌙 Dark Theme")
            qss_file = "dark_theme.qss"
        else:
            self.current_theme = "light"
            self.toolbar.btn_theme.setText("☀️ Light Theme")
            qss_file = "light_theme.qss"

        qss_path = os.path.join(STYLES_DIR, qss_file)
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
