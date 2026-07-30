"""
Script Manager Page matching target design screenshot.
Left side: Script list with search bar, Favorite star, and New/Duplicate/Import/Export buttons.
Right side: Script details, operations preview, and Edit Script action button.
"""

import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QPushButton, QFrame, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

from app.database.repositories.script_repository import ScriptRepository
from app.ui.dialogs.script_editor_dialog import ScriptEditorDialog


class ScriptsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.script_repo = ScriptRepository()
        self.selected_script = None

        self._init_ui()
        self.reload_scripts()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ── Left Column: List & Actions ───────────────────────────────────────
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search scripts...")
        self.txt_search.textChanged.connect(self._filter_list)
        left_layout.addWidget(self.txt_search)

        self.lst_scripts = QListWidget()
        self.lst_scripts.currentRowChanged.connect(self._on_script_selected)
        left_layout.addWidget(self.lst_scripts)

        # Action Buttons Grid
        btn_grid1 = QHBoxLayout()
        btn_new = QPushButton("+ New Script")
        btn_new.setProperty("class", "primaryBtn")
        btn_new.clicked.connect(self._create_script)
        btn_dup = QPushButton("📋 Duplicate")
        btn_dup.setProperty("class", "actionBtn")
        btn_dup.clicked.connect(self._duplicate_script)
        btn_grid1.addWidget(btn_new)
        btn_grid1.addWidget(btn_dup)
        left_layout.addLayout(btn_grid1)

        btn_grid2 = QHBoxLayout()
        btn_imp = QPushButton("📥 Import JSON")
        btn_imp.setProperty("class", "actionBtn")
        btn_imp.clicked.connect(self._import_json)
        btn_exp = QPushButton("📤 Export JSON")
        btn_exp.setProperty("class", "actionBtn")
        btn_exp.clicked.connect(self._export_json)
        btn_grid2.addWidget(btn_imp)
        btn_grid2.addWidget(btn_exp)
        left_layout.addLayout(btn_grid2)

        layout.addWidget(left_frame, stretch=1)

        # ── Right Column: Details & Operations Preview ─────────────────────────
        right_frame = QFrame()
        right_frame.setProperty("class", "cardBox")
        right_layout = QVBoxLayout(right_frame)

        self.lbl_details_title = QLabel("Script Details")
        self.lbl_details_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284C7;")
        right_layout.addWidget(self.lbl_details_title)

        self.lbl_name = QLabel("Name: -")
        self.lbl_keep_orig = QLabel("Keep Original Audio: -")
        self.lbl_created = QLabel("Created: -")
        self.lbl_ops_cnt = QLabel("Operations Count: -")

        for lbl in (self.lbl_name, self.lbl_keep_orig, self.lbl_created, self.lbl_ops_cnt):
            right_layout.addWidget(lbl)

        right_layout.addWidget(QLabel("<b>Operations Preview:</b>"))
        self.lst_ops_preview = QListWidget()
        right_layout.addWidget(self.lst_ops_preview)

        btn_right_actions = QHBoxLayout()
        self.btn_fav = QPushButton("⭐ Favorite")
        self.btn_fav.setProperty("class", "actionBtn")
        self.btn_fav.clicked.connect(self._toggle_favorite)

        self.btn_edit = QPushButton("✏️ Edit Script")
        self.btn_edit.setProperty("class", "primaryBtn")
        self.btn_edit.clicked.connect(self._edit_script)

        self.btn_del = QPushButton("🗑 Delete")
        self.btn_del.setProperty("class", "dangerBtn")
        self.btn_del.clicked.connect(self._delete_script)

        btn_right_actions.addWidget(self.btn_fav)
        btn_right_actions.addWidget(self.btn_edit)
        btn_right_actions.addWidget(self.btn_del)

        right_layout.addLayout(btn_right_actions)

        layout.addWidget(right_frame, stretch=2)

    def reload_scripts(self):
        self.all_scripts = self.script_repo.list_all()
        self._filter_list()

    def _filter_list(self):
        query = self.txt_search.text().lower()
        self.lst_scripts.clear()
        for s in self.all_scripts:
            if query and query not in s["name"].lower():
                continue
            star = "⭐ " if s.get("is_favorite") else ""
            item = QListWidgetItem(f"{star}{s['name']}")
            item.setData(Qt.UserRole, s)
            self.lst_scripts.addItem(item)

    def _on_script_selected(self, row: int):
        try:
            if row < 0 or row >= self.lst_scripts.count():
                self.selected_script = None
                self.lbl_name.setText("Name: -")
                self.lbl_keep_orig.setText("Keep Original Audio: -")
                self.lbl_created.setText("Created: -")
                self.lbl_ops_cnt.setText("Operations Count: -")
                self.lst_ops_preview.clear()
                return

            item = self.lst_scripts.item(row)
            if not item:
                return

            s = item.data(Qt.UserRole)
            if not s or not isinstance(s, dict):
                return

            self.selected_script = s

            s_json = s.get("script_json", {})
            if isinstance(s_json, str):
                try:
                    s_data = json.loads(s_json)
                except Exception:
                    s_data = {}
            elif isinstance(s_json, dict):
                s_data = s_json
            else:
                s_data = {}

            name = s.get("name", "Untitled")
            created_at = str(s.get("created_at", ""))
            created_str = created_at[:19] if created_at else "-"
            ops = s_data.get("operations", [])

            self.lbl_name.setText(f"Name: {name}")
            self.lbl_keep_orig.setText(f"Keep Original Audio: {'Yes' if s_data.get('keepOriginal', True) else 'No'}")
            self.lbl_created.setText(f"Created: {created_str}")
            self.lbl_ops_cnt.setText(f"Operations Count: {len(ops)}")

            self.lst_ops_preview.clear()
            for idx, op in enumerate(ops, start=1):
                if not isinstance(op, dict):
                    continue
                op_type = str(op.get("type", "")).upper()
                if op_type == "FADE":
                    ftype = str(op.get("fade_type", "both")).upper()
                    target = str(op.get("target", "both")).capitalize()
                    details = f"{op_type} ({ftype}) -> Target: {target}, In: {op.get('fade_in_duration', 1.0)}s, Out: {op.get('fade_out_duration', 1.0)}s"
                    self.lst_ops_preview.addItem(f"{idx}. {details}")
                elif op_type == "TEXT":
                    txt_sample = str(op.get("text", "")).replace("\n", " ")
                    if len(txt_sample) > 30:
                        txt_sample = txt_sample[:27] + "..."
                    font = op.get("font") or op.get("fontFamily", "Impact")
                    size = op.get("fontSize", 80)
                    color = op.get("color", "Yellow")
                    dmode = op.get("display_mode", op.get("displayMode", "always")).capitalize()
                    details = f"TEXT -> \"{txt_sample}\" ({font} {size}pt, {color}, Timing: {dmode})"
                    self.lst_ops_preview.addItem(f"{idx}. {details}")
                elif op_type == "AUDIO":
                    mode = op.get("mode", "keep-original")
                    stype = op.get("source_type", "file")
                    fmode = op.get("folder_mode", "random")
                    asset_p = op.get("assetPath") or op.get("asset_path", "")
                    path_basename = os.path.basename(asset_p) if asset_p else "-"
                    details = f"AUDIO ({mode}) -> Source: {stype} ({fmode}), Asset: '{path_basename}'"
                    self.lst_ops_preview.addItem(f"{idx}. {details}")
                else:
                    details = f"{op_type} -> {op}"
                    self.lst_ops_preview.addItem(f"{idx}. {details}")
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _create_script(self):
        try:
            dlg = ScriptEditorDialog(parent=self)
            if dlg.exec_() == ScriptEditorDialog.Accepted:
                data = dlg.script_result
                self.script_repo.create(name=data["name"], script_json=data)
                self.reload_scripts()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _edit_script(self):
        try:
            if not self.selected_script:
                return
            s_json = self.selected_script.get("script_json", {})
            if isinstance(s_json, str):
                try:
                    s_data = json.loads(s_json)
                except Exception:
                    s_data = {}
            elif isinstance(s_json, dict):
                s_data = s_json
            else:
                s_data = {}

            s_data["name"] = self.selected_script.get("name", "New Script")
            dlg = ScriptEditorDialog(script=s_data, parent=self)
            if dlg.exec_() == ScriptEditorDialog.Accepted:
                res = dlg.script_result
                self.script_repo.update(self.selected_script["id"], name=res["name"], script_json=res)
                self.reload_scripts()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error Editing Script", f"Failed to edit script: {e}")

    def _duplicate_script(self):
        if not self.selected_script: return
        self.script_repo.duplicate(self.selected_script["id"])
        self.reload_scripts()

    def _delete_script(self):
        if not self.selected_script: return
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete script '{self.selected_script['name']}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.script_repo.delete(self.selected_script["id"])
            self.reload_scripts()

    def _toggle_favorite(self):
        if not self.selected_script: return
        self.script_repo.toggle_favorite(self.selected_script["id"])
        self.reload_scripts()

    def _import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Script JSON", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.script_repo.import_from_json(data)
                self.reload_scripts()
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))

    def _export_json(self):
        if not self.selected_script: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Script JSON", f"{self.selected_script['name']}.json", "JSON Files (*.json)")
        if path:
            try:
                data = json.loads(self.selected_script["script_json"])
                data["name"] = self.selected_script["name"]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                QMessageBox.information(self, "Export Complete", f"Script exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
