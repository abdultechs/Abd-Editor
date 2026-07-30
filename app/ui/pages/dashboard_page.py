"""
Dashboard Page matching target design.
Contains:
1. Overview Statistics Cards Grid (2 rows for high responsiveness)
2. Search / Status Filter bar
3. Main QTableView Job Table Grid
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QTableView, QHeaderView, QLineEdit, QComboBox, QPushButton, QMenu,
    QShortcut, QMessageBox
)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, pyqtSignal

from app.models.job_table_model import JobTableModel
from app.utils.time_format import ms_to_hms


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0", value_color: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("class", "statCard")
        self.setMinimumHeight(68)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setProperty("class", "statTitle")
        self.lbl_title.setWordWrap(True)

        self.lbl_val = QLabel(value)
        self.lbl_val.setProperty("class", "statValue")
        if value_color:
            self.lbl_val.setStyleSheet(f"color: {value_color}; font-size: 18px; font-weight: bold;")
        else:
            self.lbl_val.setStyleSheet("font-size: 18px; font-weight: bold;")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_val)

    def set_value(self, value: str):
        self.lbl_val.setText(value)


class DashboardPage(QWidget):
    export_requested = pyqtSignal()
    jobs_delete_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # ── 1. Responsive 2-Row Stats Grid (4 Cards Row 0, 3 Cards Row 1) ─────
        stats_grid = QGridLayout()
        stats_grid.setSpacing(10)

        self.card_total = StatCard("Videos Processed", "0")
        self.card_completed = StatCard("Completed", "0", "#16A34A")
        self.card_failed = StatCard("Failed", "0", "#DC2626")
        self.card_processing = StatCard("Processing", "0", "#2563EB")
        self.card_waiting = StatCard("Waiting", "0", "#D97706")
        self.card_avg_time = StatCard("Avg. Process Time", "00:00:00", "#0284C7")
        self.card_last_job = StatCard("Last Job", "-", "#9333EA")

        # Row 0
        stats_grid.addWidget(self.card_total, 0, 0)
        stats_grid.addWidget(self.card_completed, 0, 1)
        stats_grid.addWidget(self.card_failed, 0, 2)
        stats_grid.addWidget(self.card_processing, 0, 3)

        # Row 1
        stats_grid.addWidget(self.card_waiting, 1, 0)
        stats_grid.addWidget(self.card_avg_time, 1, 1)
        stats_grid.addWidget(self.card_last_job, 1, 2, 1, 2)  # Last Job spans 2 columns

        for c in range(4):
            stats_grid.setColumnStretch(c, 1)

        layout.addLayout(stats_grid)

        # ── 2. Filter / Search Bar ─────────────────────────────────────────────
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search by filename or path...")
        self.txt_search.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self.txt_search, stretch=1)

        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["All Status", "Waiting", "Processing", "Completed", "Failed", "Cancelled"])
        self.cmb_status.currentTextChanged.connect(self._on_status_changed)
        filter_layout.addWidget(self.cmb_status)

        self.btn_delete = QPushButton("🗑 Delete Selected")
        self.btn_delete.setProperty("class", "dangerBtn")
        self.btn_delete.clicked.connect(self._on_delete_selected)
        filter_layout.addWidget(self.btn_delete)

        self.btn_export = QPushButton("📥 Export CSV")
        self.btn_export.setProperty("class", "actionBtn")
        self.btn_export.clicked.connect(self.export_requested.emit)
        filter_layout.addWidget(self.btn_export)

        layout.addLayout(filter_layout)

        # ── 3. Main Job QTableView Grid ────────────────────────────────────────
        self.table_model = JobTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.ExtendedSelection)
        self.table_view.setSortingEnabled(True)

        header = self.table_view.horizontalHeader()
        header.setMinimumHeight(38)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # File Name stretches
        header.setStretchLastSection(True)

        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._on_context_menu)

        shortcut_del = QShortcut(QKeySequence.Delete, self.table_view)
        shortcut_del.activated.connect(self._on_delete_selected)

        layout.addWidget(self.table_view)

    def update_summary(self, summary: dict):
        self.card_total.set_value(str(summary.get("totalVideos", 0)))
        self.card_completed.set_value(str(summary.get("completed", 0)))
        self.card_failed.set_value(str(summary.get("failed", 0)))
        self.card_processing.set_value(str(summary.get("processing", 0)))
        self.card_waiting.set_value(str(summary.get("waiting", 0)))
        self.card_avg_time.set_value(ms_to_hms(summary.get("averageTimeMs", 0)))
        self.card_last_job.set_value(summary.get("lastJob") or "-")

    def update_jobs(self, jobs: list[dict]):
        self.table_model.set_jobs(jobs)

    def _on_search_changed(self, text: str):
        self.table_model.set_search_text(text)

    def _on_status_changed(self, status: str):
        self.table_model.set_status_filter(status)

    def _on_context_menu(self, pos):
        menu = QMenu(self)
        act_delete = menu.addAction("🗑 Delete Selected Video(s)")
        act_delete.triggered.connect(self._on_delete_selected)
        menu.exec_(self.table_view.viewport().mapToGlobal(pos))

    def _on_delete_selected(self):
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            return

        job_ids = []
        for index in selection:
            job = self.table_model.get_job_at(index.row())
            if job and "id" in job:
                job_ids.append(job["id"])

        if not job_ids:
            return

        reply = QMessageBox.question(
            self,
            "Remove Video(s)",
            f"Are you sure you want to delete {len(job_ids)} selected video(s) from the queue?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.jobs_delete_requested.emit(job_ids)
