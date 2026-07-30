"""
Toolbar widget matching target screenshot design.
"""

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QPushButton, QComboBox, QLabel
from PyQt5.QtCore import pyqtSignal, Qt


class Toolbar(QFrame):
    add_folder_clicked = pyqtSignal()
    output_folder_clicked = pyqtSignal()
    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    theme_toggled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolbarFrame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Left controls
        self.btn_input = QPushButton("+ Add Folder")
        self.btn_input.setProperty("class", "actionBtn")
        self.btn_input.setCursor(Qt.PointingHandCursor)
        self.btn_input.clicked.connect(self.add_folder_clicked.emit)
        layout.addWidget(self.btn_input)

        self.btn_output = QPushButton("📁 Output Folder")
        self.btn_output.setProperty("class", "actionBtn")
        self.btn_output.setCursor(Qt.PointingHandCursor)
        self.btn_output.clicked.connect(self.output_folder_clicked.emit)
        layout.addWidget(self.btn_output)

        lbl_script = QLabel("Script:")
        lbl_script.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_script)

        self.cmb_script = QComboBox()
        self.cmb_script.setMaximumWidth(180)
        layout.addWidget(self.cmb_script)

        self.btn_start = QPushButton("▶ Start Processing")
        self.btn_start.setProperty("class", "primaryBtn")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_clicked.emit)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setProperty("class", "dangerBtn")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setVisible(False)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.btn_stop)

        layout.addStretch(1)

        # Right controls
        self.btn_theme = QPushButton("☀️ Light Theme")
        self.btn_theme.setProperty("class", "actionBtn")
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.clicked.connect(self.theme_toggled.emit)
        layout.addWidget(self.btn_theme)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setProperty("class", "actionBtn")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.btn_refresh)

    def populate_scripts(self, scripts: list[dict]):
        prev_id = self.cmb_script.currentData()
        self.cmb_script.clear()
        self.cmb_script.addItem("No Script (Pass through)", None)
        select_idx = 0
        for idx, s in enumerate(scripts, start=1):
            name = f"⭐ {s['name']}" if s.get("is_favorite") else s['name']
            self.cmb_script.addItem(name, s["id"])
            if prev_id and s["id"] == prev_id:
                select_idx = idx

        if select_idx > 0:
            self.cmb_script.setCurrentIndex(select_idx)
        elif len(scripts) > 0:
            self.cmb_script.setCurrentIndex(1)

    def get_selected_script_id(self) -> str | None:
        return self.cmb_script.currentData()

    def set_running_state(self, running: bool):
        self.btn_start.setVisible(not running)
        self.btn_stop.setVisible(running)
        self.btn_input.setEnabled(not running)
        self.cmb_script.setEnabled(not running)
