# app/models/job_table_model.py
"""
QAbstractTableModel implementation for the main jobs QTableView grid.

Supports:
- Thousands of video jobs efficiently
- Sorting
- Filtering & searching
- Status badge coloring
- Live progress updates
"""

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QColor, QBrush

from app.utils.constants import STATUS_COLORS


class JobTableModel(QAbstractTableModel):
    HEADERS = [
        "File Name",
        "Status",
        "Progress",
        "Duration Before",
        "Duration After",
        "Resolution Before",
        "Resolution After",
        "Processing Time",
        "Script Used",
        "Output Path",
        "Error",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_jobs: list[dict] = []
        self._filtered_jobs: list[dict] = []
        self._search_text = ""
        self._status_filter = "All Status"

    def set_jobs(self, jobs: list[dict]):
        self.beginResetModel()
        self._all_jobs = jobs
        self._apply_filter()
        self.endResetModel()

    def set_search_text(self, text: str):
        self._search_text = text.lower().strip()
        self.beginResetModel()
        self._apply_filter()
        self.endResetModel()

    def set_status_filter(self, status: str):
        self._status_filter = status
        self.beginResetModel()
        self._apply_filter()
        self.endResetModel()

    def _apply_filter(self):
        result = []
        for job in self._all_jobs:
            if self._status_filter != "All Status" and job.get("status") != self._status_filter.lower():
                continue
            if self._search_text:
                fname = job.get("file_name", "").lower()
                spath = job.get("output_path", "").lower()
                if self._search_text not in fname and self._search_text not in spath:
                    continue
            result.append(job)
        self._filtered_jobs = result

    def rowCount(self, parent=QModelIndex()):
        return len(self._filtered_jobs)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return section + 1
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._filtered_jobs):
            return None

        job = self._filtered_jobs[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0: return job.get("file_name")
            if col == 1: return job.get("status", "").capitalize()
            if col == 2: return f"{job.get('progress', 0)}%"
            if col == 3: return job.get("duration_before") or "--:--:--"
            if col == 4: return job.get("duration_after") or "--:--:--"
            if col == 5: return job.get("resolution_before") or "-"
            if col == 6: return job.get("resolution_after") or "-"
            if col == 7:
                ms = job.get("processing_time_ms")
                return f"{ms / 1000.0:.2f}s" if ms else "-"
            if col == 8: return job.get("script_name") or "None"
            if col == 9: return job.get("output_path")
            if col == 10: return job.get("error_message") or "-"

        elif role == Qt.ForegroundRole:
            if col == 1:  # Status column color
                status = job.get("status", "waiting")
                hex_color = STATUS_COLORS.get(status, "#F8FAFC")
                return QBrush(QColor(hex_color))

        elif role == Qt.TextAlignmentRole:
            if col in (1, 2, 3, 4, 5, 6, 7):
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def get_job_at(self, row: int) -> dict | None:
        if 0 <= row < len(self._filtered_jobs):
            return self._filtered_jobs[row]
        return None
