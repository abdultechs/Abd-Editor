"""
Sidebar navigation widget matching target design.
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel, QButtonGroup
from PyQt5.QtCore import pyqtSignal, Qt

from app.models.enums import AppView
from app.utils.constants import SIDEBAR_WIDTH


class Sidebar(QFrame):
    navigated = pyqtSignal(str)
    new_job_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarFrame")
        self.setFixedWidth(SIDEBAR_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(6)

        title = QLabel("🎬 Abd Editor")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        items = [
            ("📊 Dashboard", AppView.DASHBOARD.value),
            ("📜 Scripts", AppView.SCRIPTS.value),
            ("⏳ Jobs", AppView.JOBS.value),
            ("📜 History", AppView.HISTORY.value),
            ("⚙️ Settings", AppView.SETTINGS.value),
            ("🤖 AI Features (Soon)", AppView.AI_FEATURES.value),
        ]

        self.buttons = {}
        for label, view_key in items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("sidebarBtn")
            btn.setProperty("class", "sidebarBtn")
            btn.setCursor(Qt.PointingHandCursor)

            if view_key == AppView.AI_FEATURES.value:
                btn.setEnabled(True)  # clickable to see coming soon page

            self.btn_group.addButton(btn)
            layout.addWidget(btn)
            self.buttons[view_key] = btn

            btn.clicked.connect(lambda checked, vk=view_key: self.navigated.emit(vk))

        self.buttons[AppView.DASHBOARD.value].setChecked(True)

        layout.addStretch()

        # New Job Button at bottom
        self.btn_new_job = QPushButton("+ New Job")
        self.btn_new_job.setProperty("class", "primaryBtn")
        self.btn_new_job.setCursor(Qt.PointingHandCursor)
        self.btn_new_job.clicked.connect(self.new_job_clicked.emit)
        layout.addWidget(self.btn_new_job)

    def select_view(self, view_key: str):
        if view_key in self.buttons:
            self.buttons[view_key].setChecked(True)

    def update_queue_stats(self, proc: int, wait: int, comp: int, fail: int):
        pass
