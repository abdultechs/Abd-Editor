"""
Script Editor Dialog — matching target design screenshot.
Left side: Operations List (Trim, Speed, Flip, Audio, Text)
Right side: Form parameters for selected operation
"""

import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QCheckBox, QPushButton, QComboBox, QDoubleSpinBox,
    QSpinBox, QStackedWidget, QWidget, QFormLayout, QFileDialog, QMessageBox,
    QTextEdit, QRadioButton, QScrollArea, QFrame, QAbstractItemView
)
from PyQt5.QtCore import Qt


def _safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


class ScriptEditorDialog(QDialog):
    def __init__(self, script: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Script" if script else "Create New Script")
        self.setMinimumSize(950, 650)
        self.script_data = script or {
            "name": "New Script",
            "keepOriginal": True,
            "operations": []
        }
        self.script_result = None
        self._current_selected_row = None

        self._init_ui()
        self._load_script_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Details
        hdr_layout = QHBoxLayout()
        hdr_layout.addWidget(QLabel("Name:"))
        self.txt_name = QLineEdit()
        hdr_layout.addWidget(self.txt_name)

        self.chk_keep_original = QCheckBox("Keep Original Audio")
        hdr_layout.addWidget(self.chk_keep_original)

        main_layout.addLayout(hdr_layout)

        # Content Split: Left = Operations list, Right = Operation Settings
        body_layout = QHBoxLayout()

        # Left Column
        left_box = QVBoxLayout()
        left_box.addWidget(QLabel("Operations (Drag to reorder):"))

        self.lst_ops = QListWidget()
        self.lst_ops.setDragDropMode(QAbstractItemView.InternalMove)
        self.lst_ops.setDefaultDropAction(Qt.MoveAction)
        self.lst_ops.setAcceptDrops(True)
        self.lst_ops.currentRowChanged.connect(self._on_op_selected)
        left_box.addWidget(self.lst_ops)

        # Reorder buttons
        btn_reorder_layout = QHBoxLayout()
        btn_up = QPushButton("⬆ Move Up")
        btn_up.setProperty("class", "actionBtn")
        btn_up.clicked.connect(self._move_op_up)
        btn_down = QPushButton("⬇ Move Down")
        btn_down.setProperty("class", "actionBtn")
        btn_down.clicked.connect(self._move_op_down)
        btn_reorder_layout.addWidget(btn_up)
        btn_reorder_layout.addWidget(btn_down)
        left_box.addLayout(btn_reorder_layout)

        btn_op_layout = QHBoxLayout()
        self.cmb_add_op = QComboBox()
        self.cmb_add_op.addItems(["trim", "speed", "flip", "audio", "text", "fade", "merge", "border", "zoom", "image_overlay"])
        btn_op_layout.addWidget(self.cmb_add_op)

        btn_add = QPushButton("+ Add")
        btn_add.setProperty("class", "primaryBtn")
        btn_add.clicked.connect(self._add_op)
        btn_op_layout.addWidget(btn_add)

        btn_rem = QPushButton("🗑 Remove")
        btn_rem.setProperty("class", "dangerBtn")
        btn_rem.clicked.connect(self._remove_op)
        btn_op_layout.addWidget(btn_rem)

        left_box.addLayout(btn_op_layout)
        body_layout.addLayout(left_box, stretch=1)

        # Right Column — Stacked Settings Panel
        self.stack_settings = QStackedWidget()
        self.stack_settings.setProperty("class", "cardBox")

        # Page 0: Empty
        p0 = QWidget()
        p0_l = QVBoxLayout(p0)
        p0_l.addWidget(QLabel("Select an operation from the list to configure."))
        self.stack_settings.addWidget(p0)

        # Page 1: Trim
        self.p_trim = QWidget()
        f_trim = QFormLayout(self.p_trim)
        self.spn_trim_start = QDoubleSpinBox()
        self.spn_trim_start.setRange(0, 99999)
        self.spn_trim_end = QDoubleSpinBox()
        self.spn_trim_end.setRange(0, 99999)
        f_trim.addRow("Start Seconds:", self.spn_trim_start)
        f_trim.addRow("End Seconds:", self.spn_trim_end)
        self.stack_settings.addWidget(self.p_trim)

        # Page 2: Speed
        self.p_speed = QWidget()
        f_speed = QFormLayout(self.p_speed)
        self.spn_speed_val = QDoubleSpinBox()
        self.spn_speed_val.setRange(0.1, 10.0)
        self.spn_speed_val.setValue(1.0)
        self.spn_speed_val.setSingleStep(0.25)
        f_speed.addRow("Speed Multiplier (e.g. 1.25):", self.spn_speed_val)
        self.stack_settings.addWidget(self.p_speed)

        # Page 3: Flip
        self.p_flip = QWidget()
        f_flip = QFormLayout(self.p_flip)
        self.cmb_flip_dir = QComboBox()
        self.cmb_flip_dir.addItems(["horizontal", "vertical"])
        f_flip.addRow("Direction:", self.cmb_flip_dir)
        self.stack_settings.addWidget(self.p_flip)

        # Page 4: Audio
        self.p_audio = QWidget()
        f_audio = QFormLayout(self.p_audio)

        self.cmb_audio_mode = QComboBox()
        self.cmb_audio_mode.addItems(["keep-original", "remove", "replace-audio", "background-music"])
        self.cmb_audio_mode.currentIndexChanged.connect(self._update_audio_ui_visibility)

        self.cmb_audio_source_type = QComboBox()
        self.cmb_audio_source_type.addItems(["Single File", "Folder (Multiple Files)"])
        self.cmb_audio_source_type.currentIndexChanged.connect(self._update_audio_ui_visibility)

        self.cmb_audio_folder_mode = QComboBox()
        self.cmb_audio_folder_mode.addItems(["Pick Random Audio per Video", "Merge Audio Files (Sequential)"])

        self.txt_audio_path = QLineEdit()
        self.btn_browse_audio = QPushButton("Browse...")
        self.btn_browse_audio.clicked.connect(self._browse_audio)
        h_aud = QHBoxLayout()
        h_aud.addWidget(self.txt_audio_path)
        h_aud.addWidget(self.btn_browse_audio)

        self.spn_orig_vol = QSpinBox()
        self.spn_orig_vol.setRange(0, 500)
        self.spn_orig_vol.setValue(100)
        self.spn_orig_vol.setSuffix("%")

        self.spn_asset_vol = QSpinBox()
        self.spn_asset_vol.setRange(0, 500)
        self.spn_asset_vol.setValue(35)
        self.spn_asset_vol.setSuffix("%")

        self.chk_audio_segment = QCheckBox("Select Part of Audio / Custom Segment")
        self.chk_audio_segment.stateChanged.connect(self._update_audio_ui_visibility)

        self.spn_audio_seg_start = QDoubleSpinBox()
        self.spn_audio_seg_start.setRange(0.0, 99999.0)
        self.spn_audio_seg_start.setValue(0.0)
        self.spn_audio_seg_start.setSingleStep(0.5)

        self.spn_audio_seg_end = QDoubleSpinBox()
        self.spn_audio_seg_end.setRange(0.0, 99999.0)
        self.spn_audio_seg_end.setValue(0.0)
        self.spn_audio_seg_end.setSingleStep(0.5)

        f_audio.addRow("Mode:", self.cmb_audio_mode)

        self.lbl_audio_source_type = QLabel("Source Type:")
        f_audio.addRow(self.lbl_audio_source_type, self.cmb_audio_source_type)

        self.lbl_audio_folder_mode = QLabel("Folder Mode:")
        f_audio.addRow(self.lbl_audio_folder_mode, self.cmb_audio_folder_mode)

        self.lbl_audio_asset_path = QLabel("Asset File/Folder:")
        f_audio.addRow(self.lbl_audio_asset_path, h_aud)

        self.lbl_orig_vol = QLabel("Original Audio Volume:")
        f_audio.addRow(self.lbl_orig_vol, self.spn_orig_vol)

        self.lbl_asset_vol = QLabel("Background/Asset Volume:")
        f_audio.addRow(self.lbl_asset_vol, self.spn_asset_vol)

        f_audio.addRow("Cut Segment:", self.chk_audio_segment)

        self.lbl_audio_seg_start = QLabel("Segment Start (s):")
        f_audio.addRow(self.lbl_audio_seg_start, self.spn_audio_seg_start)

        self.lbl_audio_seg_end = QLabel("Segment End (s, 0 = End):")
        f_audio.addRow(self.lbl_audio_seg_end, self.spn_audio_seg_end)

        self.stack_settings.addWidget(self.p_audio)

        # Page 5: Text Overlay (Upgraded Text Settings)
        self.p_text_scroll = QScrollArea()
        self.p_text_scroll.setWidgetResizable(True)

        self.p_text = QWidget()
        f_text = QVBoxLayout(self.p_text)
        f_text.setSpacing(10)

        lbl_text_hdr = QLabel("<b>TEXT SETTINGS</b>")
        lbl_text_hdr.setStyleSheet("font-size: 14px; color: #0284C7;")
        f_text.addWidget(lbl_text_hdr)

        # Content
        f_text.addWidget(QLabel("Content:"))
        self.txt_text_content = QTextEdit()
        self.txt_text_content.setPlaceholderText("Enter text content...")
        self.txt_text_content.setMaximumHeight(80)
        self.txt_text_content.setText("When they return home\nafter honeymoon.....")
        f_text.addWidget(self.txt_text_content)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        f_text.addWidget(sep1)

        # Font & Typography
        f_font_form = QFormLayout()
        self.cmb_text_font = QComboBox()
        self.cmb_text_font.addItems([
            "Impact", "Arial", "Roboto", "Montserrat", "Comic Sans MS",
            "Courier New", "Times New Roman", "Verdana", "Segoe UI", "Calibri",
            "Trebuchet MS", "Georgia"
        ])
        self.spn_text_font_size = QSpinBox()
        self.spn_text_font_size.setRange(10, 300)
        self.spn_text_font_size.setValue(80)

        self.cmb_font_weight = QComboBox()
        self.cmb_font_weight.addItems(["Bold", "Normal", "Italic", "Bold Italic"])

        f_font_form.addRow("Font:", self.cmb_text_font)
        f_font_form.addRow("Font Size:", self.spn_text_font_size)
        f_font_form.addRow("Font Weight:", self.cmb_font_weight)
        f_text.addLayout(f_font_form)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        f_text.addWidget(sep2)

        # Text Color, Outline & Shadow
        f_color_form = QFormLayout()

        self.cmb_text_color = QComboBox()
        self.cmb_text_color.addItems([
            "Yellow", "White", "Black", "Red", "Green", "Blue",
            "Cyan", "Magenta", "Orange", "Purple"
        ])

        self.chk_enable_outline = QCheckBox("Enable Outline")
        self.chk_enable_outline.setChecked(True)
        self.cmb_outline_color = QComboBox()
        self.cmb_outline_color.addItems(["Black", "White", "Red", "Yellow", "Blue", "Green"])
        self.spn_outline_thick = QSpinBox()
        self.spn_outline_thick.setRange(0, 50)
        self.spn_outline_thick.setValue(5)

        self.chk_enable_shadow = QCheckBox("Enable Shadow")
        self.chk_enable_shadow.setChecked(True)
        self.spn_shadow_blur = QSpinBox()
        self.spn_shadow_blur.setRange(0, 50)
        self.spn_shadow_blur.setValue(2)

        self.spn_text_opacity = QSpinBox()
        self.spn_text_opacity.setRange(0, 100)
        self.spn_text_opacity.setValue(100)
        self.spn_text_opacity.setSuffix("%")

        f_color_form.addRow("Text Color:", self.cmb_text_color)
        f_color_form.addRow("Opacity / Transparency:", self.spn_text_opacity)
        f_color_form.addRow("Outline:", self.chk_enable_outline)
        f_color_form.addRow("Outline Color:", self.cmb_outline_color)
        f_color_form.addRow("Outline Thickness:", self.spn_outline_thick)
        f_color_form.addRow("Shadow:", self.chk_enable_shadow)
        f_color_form.addRow("Shadow Blur:", self.spn_shadow_blur)
        f_text.addLayout(f_color_form)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        f_text.addWidget(sep3)

        # Alignment
        f_text.addWidget(QLabel("Alignment:"))
        align_layout = QHBoxLayout()
        self.rdo_align_left = QRadioButton("Left")
        self.rdo_align_center = QRadioButton("Center")
        self.rdo_align_center.setChecked(True)
        self.rdo_align_right = QRadioButton("Right")
        align_layout.addWidget(self.rdo_align_left)
        align_layout.addWidget(self.rdo_align_center)
        align_layout.addWidget(self.rdo_align_right)
        f_text.addLayout(align_layout)

        sep4 = QFrame()
        sep4.setFrameShape(QFrame.HLine)
        f_text.addWidget(sep4)

        # Position
        f_pos_form = QFormLayout()

        self.cmb_pos_x = QComboBox()
        self.cmb_pos_x.addItems(["Center", "Margin 5%", "Margin 10%", "Margin 20%"])

        self.cmb_pos_y = QComboBox()
        self.cmb_pos_y.addItems(["Top 10%", "Top 20%", "Top 5%", "Center", "Bottom 10%", "Bottom 20%", "Bottom 5%"])

        f_pos_form.addRow("X Position:", self.cmb_pos_x)
        f_pos_form.addRow("Y Position:", self.cmb_pos_y)
        f_text.addLayout(f_pos_form)

        sep5 = QFrame()
        sep5.setFrameShape(QFrame.HLine)
        f_text.addWidget(sep5)

        # Wrapping
        f_wrap_form = QFormLayout()

        self.spn_max_width = QSpinBox()
        self.spn_max_width.setRange(10, 100)
        self.spn_max_width.setValue(90)
        self.spn_max_width.setSuffix("%")

        self.chk_auto_wrap = QCheckBox("Auto Wrap")
        self.chk_auto_wrap.setChecked(True)

        f_wrap_form.addRow("Maximum Width:", self.spn_max_width)
        f_wrap_form.addRow("Auto Wrap:", self.chk_auto_wrap)
        f_text.addLayout(f_wrap_form)

        sep6 = QFrame()
        sep6.setFrameShape(QFrame.HLine)
        f_text.addWidget(sep6)

        # Timestamp / Display Timing
        f_time_form = QFormLayout()

        self.cmb_text_display_mode = QComboBox()
        self.cmb_text_display_mode.addItems([
            "Full Video (Always Show)",
            "Display at Start",
            "Display at End",
            "Display at Start & End",
            "Custom Timestamps"
        ])
        self.cmb_text_display_mode.currentIndexChanged.connect(self._update_text_timing_visibility)

        self.spn_text_start_dur = QDoubleSpinBox()
        self.spn_text_start_dur.setRange(0.1, 99999.0)
        self.spn_text_start_dur.setValue(3.0)
        self.spn_text_start_dur.setSingleStep(0.5)

        self.spn_text_end_dur = QDoubleSpinBox()
        self.spn_text_end_dur.setRange(0.1, 99999.0)
        self.spn_text_end_dur.setValue(3.0)
        self.spn_text_end_dur.setSingleStep(0.5)

        self.spn_text_start_time = QDoubleSpinBox()
        self.spn_text_start_time.setRange(0.0, 99999.0)
        self.spn_text_start_time.setValue(0.0)
        self.spn_text_start_time.setSingleStep(0.5)

        self.spn_text_end_time = QDoubleSpinBox()
        self.spn_text_end_time.setRange(0.0, 99999.0)
        self.spn_text_end_time.setValue(0.0)
        self.spn_text_end_time.setSingleStep(0.5)

        f_time_form.addRow("Display Timing:", self.cmb_text_display_mode)

        self.lbl_text_start_dur = QLabel("Start Duration (s):")
        f_time_form.addRow(self.lbl_text_start_dur, self.spn_text_start_dur)

        self.lbl_text_end_dur = QLabel("End Duration (s):")
        f_time_form.addRow(self.lbl_text_end_dur, self.spn_text_end_dur)

        self.lbl_text_start_time = QLabel("Start Timestamp (s):")
        f_time_form.addRow(self.lbl_text_start_time, self.spn_text_start_time)

        self.lbl_text_end_time = QLabel("End Timestamp (s, 0=End):")
        f_time_form.addRow(self.lbl_text_end_time, self.spn_text_end_time)

        f_text.addLayout(f_time_form)

        self.p_text_scroll.setWidget(self.p_text)
        self.stack_settings.addWidget(self.p_text_scroll)

        # Page 6: Fade
        self.p_fade = QWidget()
        f_fade = QFormLayout(self.p_fade)

        self.cmb_fade_type = QComboBox()
        self.cmb_fade_type.addItems(["Fade In", "Fade Out", "Fade In & Out"])
        self.cmb_fade_type.currentIndexChanged.connect(self._update_fade_ui_visibility)

        self.cmb_fade_target = QComboBox()
        self.cmb_fade_target.addItems(["Both (Video & Audio)", "Video Only", "Audio Only"])

        self.spn_fade_in_dur = QDoubleSpinBox()
        self.spn_fade_in_dur.setRange(0.1, 300.0)
        self.spn_fade_in_dur.setValue(1.0)
        self.spn_fade_in_dur.setSingleStep(0.5)

        self.spn_fade_out_dur = QDoubleSpinBox()
        self.spn_fade_out_dur.setRange(0.1, 300.0)
        self.spn_fade_out_dur.setValue(1.0)
        self.spn_fade_out_dur.setSingleStep(0.5)

        self.cmb_fade_color = QComboBox()
        self.cmb_fade_color.addItems(["black", "white", "red", "blue", "green"])

        f_fade.addRow("Fade Type:", self.cmb_fade_type)
        f_fade.addRow("Apply To:", self.cmb_fade_target)
        self.lbl_fade_in_dur = QLabel("Fade In Duration (s):")
        f_fade.addRow(self.lbl_fade_in_dur, self.spn_fade_in_dur)
        self.lbl_fade_out_dur = QLabel("Fade Out Duration (s):")
        f_fade.addRow(self.lbl_fade_out_dur, self.spn_fade_out_dur)
        self.lbl_fade_color = QLabel("Video Color:")
        f_fade.addRow(self.lbl_fade_color, self.cmb_fade_color)

        self.stack_settings.addWidget(self.p_fade)

        # Page 7: Merge (Video Compilation & Intro/Outro)
        self.p_merge = QWidget()
        f_merge = QFormLayout(self.p_merge)

        self.cmb_merge_mode = QComboBox()
        self.cmb_merge_mode.addItems(["Intro / Outro Clip Attachment", "Folder Video Compilation (Single Job Output)"])
        self.cmb_merge_mode.currentIndexChanged.connect(self._update_merge_ui_visibility)

        # Intro Section
        self.chk_enable_intro = QCheckBox("Add Intro Video (Plays before primary video)")
        self.chk_enable_intro.stateChanged.connect(self._update_merge_ui_visibility)
        self.txt_intro_path = QLineEdit()
        self.btn_browse_intro = QPushButton("Browse Intro...")
        self.btn_browse_intro.clicked.connect(self._browse_intro)

        # Outro Section
        self.chk_enable_outro = QCheckBox("Add Outro Video (Plays after primary video)")
        self.chk_enable_outro.stateChanged.connect(self._update_merge_ui_visibility)
        self.txt_outro_path = QLineEdit()
        self.btn_browse_outro = QPushButton("Browse Outro...")
        self.btn_browse_outro.clicked.connect(self._browse_outro)

        # Resolution Mode
        self.cmb_merge_res_mode = QComboBox()
        self.cmb_merge_res_mode.addItems(["Pad (Letterbox/Pillarbox)", "Scale & Crop", "Match Primary Video"])

        f_merge.addRow("Merge Mode:", self.cmb_merge_mode)

        self.lbl_intro_header = QLabel("<b>INTRO SETTINGS:</b>")
        f_merge.addRow(self.lbl_intro_header, self.chk_enable_intro)
        self.lbl_intro_file = QLabel("Intro Video File/Folder:")
        self.w_intro_file = QWidget()
        w_intro_l = QHBoxLayout(self.w_intro_file)
        w_intro_l.setContentsMargins(0, 0, 0, 0)
        w_intro_l.addWidget(self.txt_intro_path)
        w_intro_l.addWidget(self.btn_browse_intro)
        f_merge.addRow(self.lbl_intro_file, self.w_intro_file)

        self.lbl_outro_header = QLabel("<b>OUTRO SETTINGS:</b>")
        f_merge.addRow(self.lbl_outro_header, self.chk_enable_outro)
        self.lbl_outro_file = QLabel("Outro Video File/Folder:")
        self.w_outro_file = QWidget()
        w_outro_l = QHBoxLayout(self.w_outro_file)
        w_outro_l.setContentsMargins(0, 0, 0, 0)
        w_outro_l.addWidget(self.txt_outro_path)
        w_outro_l.addWidget(self.btn_browse_outro)
        f_merge.addRow(self.lbl_outro_file, self.w_outro_file)

        self.stack_settings.addWidget(self.p_merge)

        # Page 7: Border Frame Settings
        self.p_border = QWidget()
        f_border = QFormLayout(self.p_border)
        self.cmb_border_mode = QComboBox()
        self.cmb_border_mode.addItems(["Left & Right Sides Only", "All 4 Sides"])

        self.spn_border_thick = QSpinBox()
        self.spn_border_thick.setRange(1, 200)
        self.spn_border_thick.setValue(20)
        self.spn_border_thick.setSuffix(" px")

        self.cmb_border_color = QComboBox()
        self.cmb_border_color.addItems([
            "Solid Violet",
            "Solid Magenta",
            "Solid Teal",
            "Solid Fuchsia",
            "Solid Deep Purple",
            "Solid Bright Cyan",
            "Solid Coral",
            "Solid Mustard Yellow",
            "Solid Tangerine",
            "Solid Mint Green",
            "Solid Electric Blue",
            "Solid Lavender",
            "Solid Navy Blue",
            "Solid Forest Green",
            "Solid Black",
            "Solid White"
        ])
        f_border.addRow("Border Placement:", self.cmb_border_mode)
        f_border.addRow("Border Thickness:", self.spn_border_thick)
        f_border.addRow("Solid Color:", self.cmb_border_color)

        self.chk_enable_inner_border = QCheckBox("Enable Inner Outline Line (Inside Colored Border)")
        self.chk_enable_inner_border.setChecked(True)

        self.spn_inner_border_thick = QSpinBox()
        self.spn_inner_border_thick.setRange(1, 30)
        self.spn_inner_border_thick.setValue(4)
        self.spn_inner_border_thick.setSuffix(" px")

        self.cmb_inner_border_color = QComboBox()
        self.cmb_inner_border_color.addItems(["Solid White", "Solid Black", "Solid Gold Yellow", "Solid Bright Cyan", "Solid Crimson Red"])

        f_border.addRow("Inner Line:", self.chk_enable_inner_border)
        f_border.addRow("Inner Line Thickness:", self.spn_inner_border_thick)
        f_border.addRow("Inner Line Color:", self.cmb_inner_border_color)
        self.stack_settings.addWidget(self.p_border)

        # Page 8: Video Crop-Zoom Settings
        self.p_zoom = QWidget()
        f_zoom = QFormLayout(self.p_zoom)
        self.cmb_zoom_mode = QComboBox()
        self.cmb_zoom_mode.addItems(["Cut Top & Bottom (Zoom Wider)", "Uniform Center Crop"])

        self.spn_zoom_factor = QSpinBox()
        self.spn_zoom_factor.setRange(105, 200)
        self.spn_zoom_factor.setValue(115)
        self.spn_zoom_factor.setSuffix("%")
        f_zoom.addRow("Zoom Mode:", self.cmb_zoom_mode)
        f_zoom.addRow("Crop-Zoom Scale (Entire Video):", self.spn_zoom_factor)
        self.stack_settings.addWidget(self.p_zoom)

        # Page 9: Image / Logo Overlay Settings
        self.p_image = QWidget()
        f_image = QFormLayout(self.p_image)
        self.txt_image_path = QLineEdit()
        self.btn_browse_image = QPushButton("Browse Image...")
        self.btn_browse_image.clicked.connect(self._browse_image)
        h_img = QHBoxLayout()
        h_img.addWidget(self.txt_image_path)
        h_img.addWidget(self.btn_browse_image)

        self.spn_image_scale = QSpinBox()
        self.spn_image_scale.setRange(5, 100)
        self.spn_image_scale.setValue(30)
        self.spn_image_scale.setSuffix("%")

        self.spn_image_opacity = QSpinBox()
        self.spn_image_opacity.setRange(0, 100)
        self.spn_image_opacity.setValue(100)
        self.spn_image_opacity.setSuffix("%")

        self.cmb_image_pos_x = QComboBox()
        self.cmb_image_pos_x.addItems(["Center", "Left (5%)", "Right (5%)", "Custom Position (%)"])
        self.cmb_image_pos_x.currentIndexChanged.connect(self._update_image_pos_ui_visibility)

        self.spn_image_pos_x_pct = QSpinBox()
        self.spn_image_pos_x_pct.setRange(0, 100)
        self.spn_image_pos_x_pct.setValue(50)
        self.spn_image_pos_x_pct.setSuffix("%")

        self.cmb_image_pos_y = QComboBox()
        self.cmb_image_pos_y.addItems(["Center", "Top (5%)", "Bottom (5%)", "Custom Position (%)"])
        self.cmb_image_pos_y.currentIndexChanged.connect(self._update_image_pos_ui_visibility)

        self.spn_image_pos_y_pct = QSpinBox()
        self.spn_image_pos_y_pct.setRange(0, 100)
        self.spn_image_pos_y_pct.setValue(50)
        self.spn_image_pos_y_pct.setSuffix("%")

        f_image.addRow("Image Asset File:", h_img)
        f_image.addRow("Image Screen Width Coverage (%):", self.spn_image_scale)
        f_image.addRow("Opacity / Transparency:", self.spn_image_opacity)
        f_image.addRow("Horizontal Position (X):", self.cmb_image_pos_x)
        self.lbl_image_pos_x_pct = QLabel("Custom X Location (%):")
        f_image.addRow(self.lbl_image_pos_x_pct, self.spn_image_pos_x_pct)

        f_image.addRow("Vertical Position (Y):", self.cmb_image_pos_y)
        self.lbl_image_pos_y_pct = QLabel("Custom Y Location (%):")
        f_image.addRow(self.lbl_image_pos_y_pct, self.spn_image_pos_y_pct)

        self.stack_settings.addWidget(self.p_image)

        body_layout.addWidget(self.stack_settings, stretch=2)
        main_layout.addLayout(body_layout)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_save = QPushButton("Save Script")
        btn_save.setProperty("class", "primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "actionBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)

        main_layout.addLayout(btn_box)

    def _update_fade_ui_visibility(self):
        txt = self.cmb_fade_type.currentText()
        show_in = "In" in txt
        show_out = "Out" in txt
        self.lbl_fade_in_dur.setVisible(show_in)
        self.spn_fade_in_dur.setVisible(show_in)
        self.lbl_fade_out_dur.setVisible(show_out)
        self.spn_fade_out_dur.setVisible(show_out)

    def _update_text_timing_visibility(self):
        txt = self.cmb_text_display_mode.currentText()
        is_start = "Start" in txt and "End" not in txt
        is_end = "End" in txt and "Start" not in txt
        is_both = "Start & End" in txt
        is_custom = "Custom" in txt

        show_start_dur = is_start or is_both
        show_end_dur = is_end or is_both

        self.lbl_text_start_dur.setVisible(show_start_dur)
        self.spn_text_start_dur.setVisible(show_start_dur)

        self.lbl_text_end_dur.setVisible(show_end_dur)
        self.spn_text_end_dur.setVisible(show_end_dur)

        self.lbl_text_start_time.setVisible(is_custom)
        self.spn_text_start_time.setVisible(is_custom)
        self.lbl_text_end_time.setVisible(is_custom)
        self.spn_text_end_time.setVisible(is_custom)

    def _update_audio_ui_visibility(self):
        mode = self.cmb_audio_mode.currentText()
        source_type = self.cmb_audio_source_type.currentText()
        is_folder = "Folder" in source_type
        use_seg = self.chk_audio_segment.isChecked()

        is_keep = mode == "keep-original"
        is_replace = mode == "replace-audio"
        is_bg = mode == "background-music"

        has_asset = is_replace or is_bg

        # Asset path & source type
        self.lbl_audio_source_type.setVisible(has_asset)
        self.cmb_audio_source_type.setVisible(has_asset)
        self.lbl_audio_folder_mode.setVisible(has_asset and is_folder)
        self.cmb_audio_folder_mode.setVisible(has_asset and is_folder)
        self.lbl_audio_asset_path.setVisible(has_asset)
        self.txt_audio_path.setVisible(has_asset)
        self.btn_browse_audio.setVisible(has_asset)

        # Volumes
        self.lbl_orig_vol.setVisible(is_keep or is_bg)
        self.spn_orig_vol.setVisible(is_keep or is_bg)
        self.lbl_asset_vol.setVisible(has_asset)
        self.spn_asset_vol.setVisible(has_asset)

        # Segment trimming
        self.chk_audio_segment.setVisible(has_asset)
        self.lbl_audio_seg_start.setVisible(has_asset and use_seg)
        self.spn_audio_seg_start.setVisible(has_asset and use_seg)
        self.lbl_audio_seg_end.setVisible(has_asset and use_seg)
        self.spn_audio_seg_end.setVisible(has_asset and use_seg)

    def _load_script_data(self):
        self.txt_name.setText(self.script_data.get("name", "New Script"))
        self.chk_keep_original.setChecked(self.script_data.get("keepOriginal", True))

        self.lst_ops.clear()
        for op in self.script_data.get("operations", []):
            item = QListWidgetItem(f"{op['type'].upper()}")
            item.setData(Qt.UserRole, op)
            self.lst_ops.addItem(item)

    def _save_op_data_for_row(self, row: int):
        if row is None or row < 0 or row >= self.lst_ops.count():
            return
        item = self.lst_ops.item(row)
        if not item:
            return
        op = item.data(Qt.UserRole)
        if not op or not isinstance(op, dict):
            return

        op_type = op.get("type")

        if op_type == "trim":
            op["start"] = self.spn_trim_start.value()
            op["end"] = self.spn_trim_end.value()
        elif op_type == "speed":
            op["value"] = self.spn_speed_val.value()
        elif op_type == "flip":
            op["direction"] = self.cmb_flip_dir.currentText()
        elif op_type == "audio":
            op["mode"] = self.cmb_audio_mode.currentText()
            op["source_type"] = "folder" if "Folder" in self.cmb_audio_source_type.currentText() else "file"
            op["folder_mode"] = "merge" if "Merge" in self.cmb_audio_folder_mode.currentText() else "random"
            op["assetPath"] = self.txt_audio_path.text()
            op["original_volume"] = round(self.spn_orig_vol.value() / 100.0, 2)
            op["background_volume"] = round(self.spn_asset_vol.value() / 100.0, 2)
            op["volume"] = op["background_volume"]
            op["use_segment"] = self.chk_audio_segment.isChecked()
            op["segment_start"] = self.spn_audio_seg_start.value()
            op["segment_end"] = self.spn_audio_seg_end.value()
        elif op_type == "text":
            op["text"] = self.txt_text_content.toPlainText()
            op["font"] = self.cmb_text_font.currentText()
            op["fontSize"] = self.spn_text_font_size.value()
            op["fontWeight"] = self.cmb_font_weight.currentText()
            op["color"] = self.cmb_text_color.currentText()
            op["opacity"] = round(self.spn_text_opacity.value() / 100.0, 2)

            op["enableOutline"] = self.chk_enable_outline.isChecked()
            op["outlineColor"] = self.cmb_outline_color.currentText()
            op["outlineThickness"] = self.spn_outline_thick.value()

            op["enableShadow"] = self.chk_enable_shadow.isChecked()
            op["shadowBlur"] = self.spn_shadow_blur.value()

            if self.rdo_align_left.isChecked(): align_val = "Left"
            elif self.rdo_align_right.isChecked(): align_val = "Right"
            else: align_val = "Center"
            op["align"] = align_val

            op["posX"] = self.cmb_pos_x.currentText()
            op["posY"] = self.cmb_pos_y.currentText()

            op["maxWidth"] = self.spn_max_width.value()
            op["autoWrap"] = self.chk_auto_wrap.isChecked()

            dtext = self.cmb_text_display_mode.currentText()
            if "Start & End" in dtext: dmode_val = "both"
            elif "Start" in dtext: dmode_val = "start"
            elif "End" in dtext: dmode_val = "end"
            elif "Custom" in dtext: dmode_val = "custom"
            else: dmode_val = "always"

            op["display_mode"] = dmode_val
            op["start_duration"] = self.spn_text_start_dur.value()
            op["end_duration"] = self.spn_text_end_dur.value()
            op["startTime"] = self.spn_text_start_time.value()
            op["endTime"] = self.spn_text_end_time.value()
        elif op_type == "fade":
            ftype_map = {"Fade In": "in", "Fade Out": "out", "Fade In & Out": "both"}
            target_map = {"Both (Video & Audio)": "both", "Video Only": "video", "Audio Only": "audio"}
            op["fade_type"] = ftype_map.get(self.cmb_fade_type.currentText(), "both")
            op["target"] = target_map.get(self.cmb_fade_target.currentText(), "both")
            op["fade_in_duration"] = self.spn_fade_in_dur.value()
            op["fade_out_duration"] = self.spn_fade_out_dur.value()
            op["color"] = self.cmb_fade_color.currentText()
        elif op_type == "merge":
            is_compilation = "Folder Video Compilation" in self.cmb_merge_mode.currentText()
            op["mode"] = "folder_compilation" if is_compilation else "intro_outro"
            op["enable_intro"] = self.chk_enable_intro.isChecked()
            op["intro_path"] = self.txt_intro_path.text().strip()
            op["enable_outro"] = self.chk_enable_outro.isChecked()
            op["outro_path"] = self.txt_outro_path.text().strip()

            res_txt = self.cmb_merge_res_mode.currentText()
            if "Crop" in res_txt:
                op["resolution_mode"] = "crop"
            elif "Match" in res_txt:
                op["resolution_mode"] = "match_primary"
            else:
                op["resolution_mode"] = "pad"
        elif op_type == "border":
            op["thickness"] = self.spn_border_thick.value()
            op["color"] = self.cmb_border_color.currentText()
            op["mode"] = "sides_only" if "Sides Only" in self.cmb_border_mode.currentText() else "all_sides"
            op["enable_inner_border"] = self.chk_enable_inner_border.isChecked()
            op["inner_thickness"] = self.spn_inner_border_thick.value()
            op["inner_color"] = self.cmb_inner_border_color.currentText()
        elif op_type == "zoom":
            op["zoom_factor"] = round(self.spn_zoom_factor.value() / 100.0, 2)
            op["mode"] = "crop_top_bottom" if "Top" in self.cmb_zoom_mode.currentText() else "proportional"
        elif op_type in ("image_overlay", "image"):
            op["image_path"] = self.txt_image_path.text().strip()
            op["opacity"] = round(self.spn_image_opacity.value() / 100.0, 2)
            op["scale_pct"] = self.spn_image_scale.value()
            op["posX"] = self.cmb_image_pos_x.currentText()
            op["posY"] = self.cmb_image_pos_y.currentText()
            op["posX_pct"] = self.spn_image_pos_x_pct.value()
            op["posY_pct"] = self.spn_image_pos_y_pct.value()

        item.setData(Qt.UserRole, op)

    def _on_op_selected(self, row: int):
        try:
            if hasattr(self, "_current_selected_row") and self._current_selected_row is not None and self._current_selected_row != row:
                self._save_op_data_for_row(self._current_selected_row)

            self._current_selected_row = row

            if row < 0 or row >= self.lst_ops.count():
                self.stack_settings.setCurrentIndex(0)
                return

            item = self.lst_ops.item(row)
            if not item:
                return
            op = item.data(Qt.UserRole)
            if not op or not isinstance(op, dict):
                return

            op_type = op.get("type")

            if op_type == "trim":
                self.spn_trim_start.setValue(_safe_float(op.get("start"), 0.0))
                self.spn_trim_end.setValue(_safe_float(op.get("end"), 30.0))
                self.stack_settings.setCurrentIndex(1)
            elif op_type == "speed":
                self.spn_speed_val.setValue(_safe_float(op.get("value"), 1.0))
                self.stack_settings.setCurrentIndex(2)
            elif op_type == "flip":
                self.cmb_flip_dir.setCurrentText(str(op.get("direction", "horizontal")))
                self.stack_settings.setCurrentIndex(3)
            elif op_type == "audio":
                mode = str(op.get("mode", "keep-original"))
                self.cmb_audio_mode.setCurrentText(mode)

                stype = str(op.get("source_type", op.get("sourceType", "file")))
                self.cmb_audio_source_type.setCurrentText("Folder (Multiple Files)" if stype == "folder" else "Single File")

                fmode = str(op.get("folder_mode", op.get("folderMode", "random")))
                self.cmb_audio_folder_mode.setCurrentText("Merge Audio Files (Sequential)" if fmode == "merge" else "Pick Random Audio per Video")

                self.txt_audio_path.setText(str(op.get("assetPath", op.get("asset_path", ""))))

                orig_vol_raw = op.get("original_volume", op.get("originalVolume", 1.0))
                orig_vol_pct = _safe_int(_safe_float(orig_vol_raw, 1.0) * 100, 100)
                self.spn_orig_vol.setValue(orig_vol_pct)

                default_asset_vol = 0.35 if mode == "background-music" else 1.0
                raw_vol = op.get("background_volume", op.get("bgVolume", op.get("volume", default_asset_vol)))
                asset_vol_pct = _safe_int(_safe_float(raw_vol, default_asset_vol) * 100, int(default_asset_vol * 100))
                self.spn_asset_vol.setValue(asset_vol_pct)

                use_seg = bool(op.get("use_segment", op.get("useSegment", False)))
                self.chk_audio_segment.setChecked(use_seg)
                self.spn_audio_seg_start.setValue(_safe_float(op.get("segment_start", op.get("segmentStart", 0.0)), 0.0))
                self.spn_audio_seg_end.setValue(_safe_float(op.get("segment_end", op.get("segmentEnd", 0.0)), 0.0))

                self._update_audio_ui_visibility()
                self.stack_settings.setCurrentIndex(4)
            elif op_type == "text":
                self.txt_text_content.setText(str(op.get("text", "")))
                self.cmb_text_font.setCurrentText(str(op.get("font", op.get("fontFamily", "Impact"))))
                self.spn_text_font_size.setValue(_safe_int(op.get("fontSize"), 80))
                self.cmb_font_weight.setCurrentText(str(op.get("fontWeight", "Bold")))

                raw_opac = op.get("opacity", 1.0)
                opac_pct = _safe_int(_safe_float(raw_opac, 1.0) * 100 if _safe_float(raw_opac, 1.0) <= 1.0 else raw_opac, 100)
                self.spn_text_opacity.setValue(opac_pct)

                self.cmb_text_color.setCurrentText(str(op.get("color", "Yellow")))
                self.chk_enable_outline.setChecked(bool(op.get("enableOutline", True)))
                self.cmb_outline_color.setCurrentText(str(op.get("outlineColor", "Black")))
                self.spn_outline_thick.setValue(_safe_int(op.get("outlineThickness"), 5))

                self.chk_enable_shadow.setChecked(bool(op.get("enableShadow", True)))
                self.spn_shadow_blur.setValue(_safe_int(op.get("shadowBlur"), 2))

                align = str(op.get("align", "Center"))
                if align == "Left": self.rdo_align_left.setChecked(True)
                elif align == "Right": self.rdo_align_right.setChecked(True)
                else: self.rdo_align_center.setChecked(True)

                raw_pos_x = str(op.get("posX", "Center"))
                if "5%" in raw_pos_x: pos_x_val = "Margin 5%"
                elif "10%" in raw_pos_x: pos_x_val = "Margin 10%"
                elif "20%" in raw_pos_x: pos_x_val = "Margin 20%"
                else: pos_x_val = "Center"
                self.cmb_pos_x.setCurrentText(pos_x_val)
                self.cmb_pos_y.setCurrentText(str(op.get("posY", "Top 10%")))

                self.spn_max_width.setValue(_safe_int(op.get("maxWidth"), 90))
                self.chk_auto_wrap.setChecked(bool(op.get("autoWrap", True)))

                dmode = str(op.get("display_mode", op.get("displayMode", "always")))
                dmode_map = {
                    "always": "Full Video (Always Show)",
                    "start": "Display at Start",
                    "end": "Display at End",
                    "both": "Display at Start & End",
                    "custom": "Custom Timestamps"
                }
                self.cmb_text_display_mode.setCurrentText(dmode_map.get(dmode, "Full Video (Always Show)"))

                self.spn_text_start_dur.setValue(_safe_float(op.get("start_duration", op.get("startDuration", 3.0)), 3.0))
                self.spn_text_end_dur.setValue(_safe_float(op.get("end_duration", op.get("endDuration", 3.0)), 3.0))

                self.spn_text_start_time.setValue(_safe_float(op.get("startTime", op.get("start_time", op.get("start", 0.0))), 0.0))
                self.spn_text_end_time.setValue(_safe_float(op.get("endTime", op.get("end_time", op.get("end", 0.0))), 0.0))

                self._update_text_timing_visibility()
                self.stack_settings.setCurrentIndex(5)
            elif op_type == "fade":
                ftype = str(op.get("fade_type", "both"))
                if ftype == "in": self.cmb_fade_type.setCurrentText("Fade In")
                elif ftype == "out": self.cmb_fade_type.setCurrentText("Fade Out")
                else: self.cmb_fade_type.setCurrentText("Fade In & Out")

                target = str(op.get("target", "both"))
                if target == "video": self.cmb_fade_target.setCurrentText("Video Only")
                elif target == "audio": self.cmb_fade_target.setCurrentText("Audio Only")
                else: self.cmb_fade_target.setCurrentText("Both (Video & Audio)")

                self.spn_fade_in_dur.setValue(_safe_float(op.get("fade_in_duration"), 1.0))
                self.spn_fade_out_dur.setValue(_safe_float(op.get("fade_out_duration"), 1.0))
                self.cmb_fade_color.setCurrentText(str(op.get("color", "black")))
                self._update_fade_ui_visibility()
                self.stack_settings.setCurrentIndex(6)
            elif op_type == "merge":
                mode = str(op.get("mode", "intro_outro"))
                self.cmb_merge_mode.setCurrentText("Folder Video Compilation (Single Job Output)" if mode == "folder_compilation" else "Intro / Outro Clip Attachment")

                self.chk_enable_intro.setChecked(bool(op.get("enable_intro", False)))
                self.txt_intro_path.setText(str(op.get("intro_path", op.get("assetPath", ""))))

                self.chk_enable_outro.setChecked(bool(op.get("enable_outro", False)))
                self.txt_outro_path.setText(str(op.get("outro_path", "")))

                res_mode = str(op.get("resolution_mode", "pad"))
                if res_mode == "crop":
                    self.cmb_merge_res_mode.setCurrentText("Scale & Crop")
                elif res_mode == "match_primary":
                    self.cmb_merge_res_mode.setCurrentText("Match Primary Video")
                else:
                    self.cmb_merge_res_mode.setCurrentText("Pad (Letterbox/Pillarbox)")

                self._update_merge_ui_visibility()
                self.stack_settings.setCurrentIndex(7)
            elif op_type == "border":
                self.spn_border_thick.setValue(_safe_int(op.get("thickness"), 20))
                self.cmb_border_color.setCurrentText(str(op.get("color", "Solid Violet")))
                bmode = str(op.get("mode", "sides_only"))
                self.cmb_border_mode.setCurrentText("All 4 Sides" if "all" in bmode else "Left & Right Sides Only")
                self.chk_enable_inner_border.setChecked(bool(op.get("enable_inner_border", op.get("enableInnerBorder", True))))
                self.spn_inner_border_thick.setValue(_safe_int(op.get("inner_thickness", op.get("innerThickness", 4)), 4))
                self.cmb_inner_border_color.setCurrentText(str(op.get("inner_color", op.get("innerColor", "Solid White"))))
                self.stack_settings.setCurrentIndex(8)
            elif op_type == "zoom":
                raw_z = _safe_float(op.get("zoom_factor", op.get("factor", 1.15)), 1.15)
                z_pct = _safe_int(raw_z * 100 if raw_z <= 2.0 else raw_z, 115)
                self.spn_zoom_factor.setValue(z_pct)
                zmode = str(op.get("mode", "crop_top_bottom"))
                self.cmb_zoom_mode.setCurrentText("Uniform Center Crop" if "prop" in zmode else "Cut Top & Bottom (Zoom Wider)")
                self.stack_settings.setCurrentIndex(9)
            elif op_type in ("image_overlay", "image"):
                self.txt_image_path.setText(str(op.get("image_path", op.get("imagePath", op.get("assetPath", "")))))
                raw_op = _safe_float(op.get("opacity", 1.0), 1.0)
                self.spn_image_opacity.setValue(_safe_int(raw_op * 100 if raw_op <= 1.0 else raw_op, 100))
                self.spn_image_scale.setValue(_safe_int(op.get("scale_pct", op.get("scale", 30)), 30))
                self.cmb_image_pos_x.setCurrentText(str(op.get("posX", "Center")))
                self.cmb_image_pos_y.setCurrentText(str(op.get("posY", "Center")))
                self.spn_image_pos_x_pct.setValue(_safe_int(op.get("posX_pct", op.get("pos_x_pct", 50)), 50))
                self.spn_image_pos_y_pct.setValue(_safe_int(op.get("posY_pct", op.get("pos_y_pct", 50)), 50))
                self._update_image_pos_ui_visibility()
                self.stack_settings.setCurrentIndex(10)
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _update_image_pos_ui_visibility(self):
        show_x = "Custom" in self.cmb_image_pos_x.currentText()
        show_y = "Custom" in self.cmb_image_pos_y.currentText()
        self.lbl_image_pos_x_pct.setVisible(show_x)
        self.spn_image_pos_x_pct.setVisible(show_x)
        self.lbl_image_pos_y_pct.setVisible(show_y)
        self.spn_image_pos_y_pct.setVisible(show_y)

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image / Logo Asset", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self.txt_image_path.setText(path)

    def _add_op(self):
        op_type = self.cmb_add_op.currentText()
        new_op = {"type": op_type}
        if op_type == "trim": new_op.update({"start": 0, "end": 30})
        elif op_type == "speed": new_op.update({"value": 1.25})
        elif op_type == "flip": new_op.update({"direction": "horizontal"})
        elif op_type == "border": new_op.update({"thickness": 20, "color": "Solid Violet", "mode": "sides_only", "enable_inner_border": True, "inner_thickness": 4, "inner_color": "Solid White"})
        elif op_type == "zoom": new_op.update({"zoom_factor": 1.15, "mode": "crop_top_bottom"})
        elif op_type in ("image_overlay", "image"):
            new_op.update({"image_path": "", "opacity": 1.0, "scale_pct": 30, "posX": "Center", "posY": "Center", "posX_pct": 50, "posY_pct": 50})
        elif op_type == "audio":
            new_op.update({
                "mode": "background-music",
                "source_type": "file",
                "folder_mode": "random",
                "assetPath": "",
                "original_volume": 1.0,
                "background_volume": 0.35,
                "use_segment": False,
                "segment_start": 0.0,
                "segment_end": 0.0
            })
        elif op_type == "text":
            new_op.update({
                "text": "When they return home\nafter honeymoon.....",
                "font": "Impact",
                "fontSize": 80,
                "fontWeight": "Bold",
                "color": "Yellow",
                "enableOutline": True,
                "outlineColor": "Black",
                "outlineThickness": 5,
                "enableShadow": True,
                "shadowBlur": 2,
                "align": "Center",
                "posX": "Center",
                "posY": "Top 10%",
                "maxWidth": 90,
                "autoWrap": True,
                "display_mode": "always",
                "start_duration": 3.0,
                "end_duration": 3.0,
                "startTime": 0.0,
                "endTime": 0.0
            })
        elif op_type == "fade":
            new_op.update({
                "fade_type": "both",
                "target": "both",
                "fade_in_duration": 1.0,
                "fade_out_duration": 1.0,
                "color": "black"
            })
        elif op_type == "merge":
            new_op.update({
                "mode": "intro_outro",
                "enable_intro": True,
                "intro_path": "",
                "enable_outro": False,
                "outro_path": "",
                "resolution_mode": "pad"
            })

        # Save current active row before adding new item
        if hasattr(self, "_current_selected_row") and self._current_selected_row is not None:
            self._save_op_data_for_row(self._current_selected_row)

        item = QListWidgetItem(op_type.upper())
        item.setData(Qt.UserRole, new_op)
        self.lst_ops.addItem(item)
        self.lst_ops.setCurrentItem(item)
        self._current_selected_row = self.lst_ops.currentRow()

    def _move_op_up(self):
        row = self.lst_ops.currentRow()
        if row > 0:
            self._save_op_data_for_row(row)
            item = self.lst_ops.takeItem(row)
            self.lst_ops.insertItem(row - 1, item)
            self.lst_ops.setCurrentRow(row - 1)
            self._current_selected_row = row - 1

    def _move_op_down(self):
        row = self.lst_ops.currentRow()
        if row >= 0 and row < self.lst_ops.count() - 1:
            self._save_op_data_for_row(row)
            item = self.lst_ops.takeItem(row)
            self.lst_ops.insertItem(row + 1, item)
            self.lst_ops.setCurrentRow(row + 1)
            self._current_selected_row = row + 1

    def _remove_op(self):
        row = self.lst_ops.currentRow()
        if row >= 0:
            self.lst_ops.takeItem(row)
            new_row = self.lst_ops.currentRow()
            self._current_selected_row = new_row
            if new_row < 0 or self.lst_ops.count() == 0:
                self.stack_settings.setCurrentIndex(0)

    def _browse_audio(self):
        source_type = self.cmb_audio_source_type.currentText()
        if "Folder" in source_type:
            path = QFileDialog.getExistingDirectory(self, "Select Audio Folder")
            if path:
                self.txt_audio_path.setText(path)
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.m4a *.aac *.flac *.ogg)"
            )
            if path:
                self.txt_audio_path.setText(path)

    def _update_merge_ui_visibility(self):
        mode_text = self.cmb_merge_mode.currentText()
        is_compilation = "Folder Video Compilation" in mode_text

        show_intro_file = self.chk_enable_intro.isChecked() and not is_compilation
        show_outro_file = self.chk_enable_outro.isChecked() and not is_compilation

        self.lbl_intro_header.setVisible(not is_compilation)
        self.chk_enable_intro.setVisible(not is_compilation)
        self.lbl_intro_file.setVisible(show_intro_file)
        self.w_intro_file.setVisible(show_intro_file)

        self.lbl_outro_header.setVisible(not is_compilation)
        self.chk_enable_outro.setVisible(not is_compilation)
        self.lbl_outro_file.setVisible(show_outro_file)
        self.w_outro_file.setVisible(show_outro_file)

    def _browse_intro(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Intro Video File", "", "Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.flv *.m4v)"
        )
        if path:
            self.txt_intro_path.setText(path)

    def _browse_outro(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Outro Video File", "", "Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.flv *.m4v)"
        )
        if path:
            self.txt_outro_path.setText(path)

    def _on_save(self):
        row = self.lst_ops.currentRow()
        if row >= 0:
            self._save_op_data_for_row(row)

        # Collect operations
        ops = []
        for i in range(self.lst_ops.count()):
            item = self.lst_ops.item(i)
            if item:
                op_data = item.data(Qt.UserRole)
                if isinstance(op_data, dict):
                    ops.append(op_data)

        self.script_result = {
            "name": self.txt_name.text().strip() or "Untitled Script",
            "keepOriginal": self.chk_keep_original.isChecked(),
            "operations": ops,
            "version": 1
        }

        self.accept()
