# gui.py
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QCheckBox, QHBoxLayout, QMessageBox, QProgressBar,
    QComboBox, QMenuBar, QAction, QDialog, QSpacerItem, QSizePolicy, QFormLayout,
    QFrame, QStyle, QGraphicsDropShadowEffect, QLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
import main # Uses main.py
import sys
import os # For os.path.basename in pick_dir

# Application identity used by QSettings
ORG_NAME = "YourOrgName"
APP_NAME = "RumbleTranscriber"

MODEL_DESCRIPTIONS = {
    "tiny":      "Tiny        | ~39M params  | Fastest, lowest accuracy, low VRAM",
    "base":      "Base        | ~74M params  | Fast, decent accuracy, moderate VRAM",
    "small":     "Small       | ~244M params | Good balance of speed/accuracy, more VRAM",
    "medium":    "Medium      | ~769M params | Slower, high accuracy, significant VRAM",
    "large-v1":  "Large v1    | ~1.55B params| Slowest, highest accuracy, very high VRAM",
    "large-v2":  "Large v2    | ~1.55B params| Updated large model, similar requirements",
    "large-v3":  "Large v3    | ~1.55B params| Latest large model, best official accuracy",
    "turbo":     "Turbo       | ~809M params | Fast model variant",
}
# Default to turbo per app docs
DEFAULT_MODEL_KEY = "turbo"

# Defaults
DEFAULT_OUTPUT_FORMATS = ["txt"]

DOWNLOAD_FORMAT_OPTIONS = {
    "Audio: MP3 (Best Quality)": {"format_id": "mp3_best", "postprocessor_needed": True, "preferredcodec": "mp3", "output_ext": "mp3"},
    "Audio: M4A (Best Quality, AAC)": {"format_id": "m4a_best", "postprocessor_needed": True, "preferredcodec": "m4a", "output_ext": "m4a"},
    "Video: MP4 (Best Quality H.264/AAC)": {"format_id": "mp4_best_video", "postprocessor_needed": False, "output_ext": "mp4"},
    "Video: MKV (Best Quality Original Codecs)": {"format_id": "mkv_best_video", "postprocessor_needed": False, "output_ext": "mkv"},
}
DEFAULT_DOWNLOAD_FORMAT_ID = "mp3_best"


class WorkerThread(QThread):
    progress = pyqtSignal(str)
    transcription_progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url, outdir, formats, model_name, keep_video_setting,
                 download_format_details, start_time=None, end_time=None, local_file=None):
        super().__init__()
        self.url = url
        self.outdir = outdir
        self.formats = formats
        self.model_name = model_name
        self.keep_video = keep_video_setting
        self.download_format_details = download_format_details
        self.start_time = start_time
        self.end_time = end_time
        self.local_file = local_file

    def run(self):
        try:
            if self.local_file:
                video_file_path = self.local_file
                self.progress.emit("Using provided local file...")
                self.transcription_progress.emit(1,5)
            else:
                self.progress.emit("Downloading media...")
                for i in range(1, 3):
                    self.transcription_progress.emit(i, 5)
                    QThread.msleep(100)
                video_file_path = main.download_video(self.url, self.outdir, self.download_format_details)
                self.transcription_progress.emit(2,5)

            self.progress.emit(f"Loading/verifying Whisper model: '{self.model_name}'...")
            QThread.msleep(200)
            self.transcription_progress.emit(3,5)

            self.progress.emit(f"Transcribing with '{self.model_name}' model...")
            results = main.transcribe(
                video_file_path,
                model_name=self.model_name,
                formats=self.formats,
                start_time=self.start_time,
                end_time=self.end_time,
            )
            self.transcription_progress.emit(4,5)
            QThread.msleep(200)
            self.transcription_progress.emit(5,5)

            self.finished.emit(results)
            
            if not self.keep_video and not self.local_file:
                self.progress.emit(f"Keep media setting is OFF. Attempting to delete: {video_file_path}")
                if os.path.exists(video_file_path):
                    try:
                        os.remove(video_file_path)
                        self.progress.emit(f"Media successfully deleted: {video_file_path}")
                    except OSError as e:
                        self.progress.emit(f"Warning: Could not delete media {video_file_path}: {e}")
                else:
                    self.progress.emit(f"Warning: Media file not found for deletion: {video_file_path}")
            else:
                self.progress.emit(f"Keep media setting is ON. Media preserved: {video_file_path}")

        except Exception as e:
            import traceback
            self.error.emit(f"Error: {str(e)}\n{traceback.format_exc()}")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setMinimumWidth(450)
        
        self.settings = QSettings(ORG_NAME, APP_NAME)
        
        form_layout = QFormLayout(self)

        self.keep_video_checkbox = QCheckBox("Keep downloaded file after transcription")
        self.keep_video_checkbox.setChecked(self.settings.value("keepVideo", True, type=bool))
        form_layout.addRow(self.keep_video_checkbox)

        self.download_format_label = QLabel("Download Format:")
        self.download_format_combo = QComboBox()
        current_dl_format_id = self.settings.value("downloadFormatID", DEFAULT_DOWNLOAD_FORMAT_ID, type=str)
        default_dl_idx = 0
        for idx, (display_name, details) in enumerate(DOWNLOAD_FORMAT_OPTIONS.items()):
            self.download_format_combo.addItem(display_name, details["format_id"])
            if details["format_id"] == current_dl_format_id:
                default_dl_idx = idx
        self.download_format_combo.setCurrentIndex(default_dl_idx)
        form_layout.addRow(self.download_format_label, self.download_format_combo)

        # Whisper model selection
        self.model_label = QLabel("Default Whisper Model:")
        self.model_combo = QComboBox()
        current_model_key = self.settings.value("modelKey", DEFAULT_MODEL_KEY, type=str)
        model_default_idx = 0
        for idx, (key, desc) in enumerate(MODEL_DESCRIPTIONS.items()):
            self.model_combo.addItem(desc, key)
            if key == current_model_key:
                model_default_idx = idx
        self.model_combo.setCurrentIndex(model_default_idx)
        form_layout.addRow(self.model_label, self.model_combo)

        # Output formats selection
        self.output_formats_label = QLabel("Transcript Formats:")
        self.output_formats_container = QWidget()
        of_layout = QHBoxLayout(self.output_formats_container)
        self.output_format_boxes = {}
        for fmt in ["txt", "srt", "vtt", "tsv", "json"]:
            cb = QCheckBox(fmt.upper())
            self.output_format_boxes[fmt] = cb
            of_layout.addWidget(cb)
        saved_formats = self._load_output_formats()
        for fmt, cb in self.output_format_boxes.items():
            cb.setChecked(fmt in saved_formats)
        form_layout.addRow(self.output_formats_label, self.output_formats_container)

        button_layout = QHBoxLayout()
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        button_layout.addSpacerItem(spacer)

        save_button = QPushButton("Save & Close")
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)
        
        form_layout.addRow(button_layout)

        if parent:
            self.setStyleSheet(parent.styleSheet())

    def save_settings(self):
        self.settings.setValue("keepVideo", self.keep_video_checkbox.isChecked())
        selected_dl_format_id = self.download_format_combo.currentData()
        self.settings.setValue("downloadFormatID", selected_dl_format_id)
        self.settings.setValue("modelKey", self.model_combo.currentData())
        selected_formats = [f for f, cb in self.output_format_boxes.items() if cb.isChecked()]
        if not selected_formats:
            selected_formats = DEFAULT_OUTPUT_FORMATS
        self._save_output_formats(selected_formats)
        self.accept()

    def _load_output_formats(self):
        value = self.settings.value("outputFormats", ",".join(DEFAULT_OUTPUT_FORMATS), type=str)
        if isinstance(value, str):
            items = [v.strip().lower() for v in value.split(",") if v.strip()]
        elif isinstance(value, (list, tuple)):
            items = [str(v).strip().lower() for v in value]
        else:
            items = list(DEFAULT_OUTPUT_FORMATS)
        if 'all' in items:
            return ["txt", "srt", "vtt", "tsv", "json"]
        return items or list(DEFAULT_OUTPUT_FORMATS)

    def _save_output_formats(self, formats_list):
        safe = [f for f in formats_list if f in ["txt", "srt", "vtt", "tsv", "json"]]
        self.settings.setValue("outputFormats", ",".join(safe))

class RumbleTranscriber(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rumble Transcript Extractor")
        # Cap minimum size so layout never crushes
        self.setMinimumSize(900, 620)
        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        # Prevent resizing below minimum effective layout hint
        self.main_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.main_layout.setContentsMargins(24, 18, 24, 18)
        self.main_layout.setSpacing(16)

        menubar = QMenuBar(self)
        self.main_layout.setMenuBar(menubar)

        settings_menu = menubar.addMenu('&Settings')
        configure_action = QAction('&Configure Application...', self)
        configure_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(configure_action)
        settings_menu.addSeparator()
        exit_action = QAction('&Exit', self)
        exit_action.triggered.connect(self.close)
        settings_menu.addAction(exit_action)

        # Shortcuts
        act_open_file = QAction('Choose Local File', self)
        act_open_file.setShortcut('Ctrl+O')
        act_open_file.triggered.connect(self.pick_file)
        self.addAction(act_open_file)
        act_open_dir = QAction('Select Output Folder', self)
        act_open_dir.setShortcut('Ctrl+Shift+O')
        act_open_dir.triggered.connect(self.pick_dir)
        self.addAction(act_open_dir)

        # Header
        header = QLabel("Transcribe Rumble videos with Whisper")
        header.setAlignment(Qt.AlignHCenter)
        header.setObjectName('headerTitle')
        header.setWordWrap(True)
        self.main_layout.addWidget(header)

        # Input card
        input_card, input_layout = self._make_card()
        title1 = QLabel("Rumble Video URL")
        title1.setWordWrap(True)
        input_layout.addWidget(title1)
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Paste Rumble video URL here…")
        self.url_input.returnPressed.connect(self.run_job)
        input_layout.addWidget(self.url_input)

        file_row = QHBoxLayout()
        self.file_btn = QPushButton("Choose Local File")
        self.file_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.file_btn.clicked.connect(self.pick_file)
        file_row.addWidget(self.file_btn)
        self.selected_file_label = QLabel("Local File: None")
        self.selected_file_label.setObjectName('mutedLabel')
        self.selected_file_label.setWordWrap(True)
        file_row.addWidget(self.selected_file_label, 1)
        input_layout.addLayout(file_row)

        # Advanced options (collapsed)
        self.advanced_toggle = QPushButton("Advanced Options ▸")
        self.advanced_toggle.setObjectName('toggleButton')
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setChecked(False)
        self.advanced_toggle.toggled.connect(self._update_advanced_toggle_label)

        adv_card, adv_layout = self._make_card()
        lbl_start = QLabel("Start Time (HH:MM:SS or seconds)")
        lbl_start.setWordWrap(True)
        adv_layout.addWidget(lbl_start)
        self.start_time_input = QLineEdit(self)
        self.start_time_input.setPlaceholderText("e.g., 00:01:30 or 90")
        adv_layout.addWidget(self.start_time_input)
        lbl_end = QLabel("End Time (HH:MM:SS or seconds)")
        lbl_end.setWordWrap(True)
        adv_layout.addWidget(lbl_end)
        self.end_time_input = QLineEdit(self)
        self.end_time_input.setPlaceholderText("e.g., 00:03:00 or 180")
        adv_layout.addWidget(self.end_time_input)
        adv_card.setVisible(False)
        self.advanced_toggle.toggled.connect(adv_card.setVisible)

        # Output card
        out_card, out_layout = self._make_card()
        self.out_title_label = QLabel("Output Folder")
        self.out_title_label.setWordWrap(True)
        out_layout.addWidget(self.out_title_label)
        out_row = QHBoxLayout()
        self.outdir_btn = QPushButton("Select Output Folder")
        self.outdir_btn.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
        self.outdir_btn.clicked.connect(self.pick_dir)
        out_row.addWidget(self.outdir_btn)
        out_layout.addLayout(out_row)

        # Arrange input and output cards side-by-side for a more horizontal feel
        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        content_row.addWidget(input_card, 1)
        content_row.addWidget(out_card, 1)
        self.main_layout.addLayout(content_row)

        # Now add Advanced toggle and card beneath the row
        self.main_layout.addWidget(self.advanced_toggle)
        self.main_layout.addWidget(adv_card)

        # Spacer and primary action
        self.main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.go_btn = QPushButton("Extract & Transcribe")
        self.go_btn.setObjectName('primaryButton')
        self.go_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.go_btn.setFixedHeight(48)
        self.go_btn.clicked.connect(self.run_job)
        self.main_layout.addWidget(self.go_btn)

        # Status and progress
        self.progress_status_label = QLabel('Status: Ready')
        self.progress_status_label.setObjectName('mutedLabel')
        self.progress_status_label.setWordWrap(True)
        self.main_layout.addWidget(self.progress_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(5)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        self.selected_dir = None
        self.local_file_path = None

    def _make_card(self):
        container = QWidget()
        container.setProperty('card', True)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        # Subtle shadow
        shadow = QGraphicsDropShadowEffect(container)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(Qt.black)
        container.setGraphicsEffect(shadow)
        # Make cards expand horizontally but keep minimal vertical height
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        return container, layout

    def apply_styles(self):
        # App-wide stylesheet: dark, clean, modern
        self.setStyleSheet("""
            QWidget {
                background-color: #111315; color: #E6E6E6;
                font-size: 15px; font-family: 'Inter', 'SF Pro Text', 'Segoe UI', 'Roboto', 'DejaVu Sans', sans-serif;
                border: none;
            }
            QLabel#headerTitle {
                font-size: 20px; font-weight: 600; color: #F2F2F2; margin: 6px 0 2px 0;
            }
            QLabel { color: #B6C2CF; }
            QLabel#mutedLabel { color: #94A3B8; }

            QWidget[card="true"] {
                background-color: #171A1D; border: 1px solid #262B31; border-radius: 10px;
            }

            QMenuBar { background-color: #0F1113; color: #9AD7FF; border: none; }
            QMenuBar::item { padding: 6px 10px; background: transparent; border-radius: 6px; }
            QMenuBar::item:selected { background-color: #3B82F6; color: #0B1220; }
            QMenu { background-color: #171A1D; color: #D9E3EA; border: 1px solid #262B31; }
            QMenu::item { padding: 6px 10px; }
            QMenu::item:selected { background-color: #253349; color: #DDF3FF; }

            QLineEdit {
                background: #0F1113; border: 1px solid #2B323A; color: #E6E6E6;
                padding: 9px 10px; border-radius: 8px; font-size: 14px;
                selection-background-color: #2B5CFF; selection-color: #FFFFFF;
            }
            QLineEdit:focus { border: 1px solid #3B82F6; }

            QPushButton {
                background-color: #161A1E; color: #D9E3EA; border: 1px solid #2B323A;
                padding: 10px 16px; border-radius: 8px; font-weight: 600;
            }
            QPushButton:hover { background-color: #1F242A; border-color: #3B82F6; }
            QPushButton:pressed { background-color: #1A2027; }
            QPushButton#primaryButton {
                background-color: #3B82F6; border: 1px solid #3B82F6; color: #0B1220;
            }
            QPushButton#primaryButton:hover { background-color: #5B9CF8; border-color: #5B9CF8; }
            QPushButton#primaryButton:pressed { background-color: #2F6BD6; }

            QPushButton#toggleButton {
                background: transparent; border: none; color: #9AD7FF; text-align: left;
                padding: 4px 2px; font-weight: 600;
            }
            QPushButton#toggleButton:hover { color: #DDF3FF; }

            /* Improve hover/selection cues in Settings dialog */
            QCheckBox {
                spacing: 8px; color: #D9E3EA; font-size: 14px; margin-right: 12px;
                padding: 6px 10px; border-radius: 8px;
            }
            /* Hover state: strong blue like menu */
            QCheckBox:hover { background-color: #3B82F6; color: #0B1220; }
            /* Checked state: blue pill, but keep indicator dark with visible tick */
            QCheckBox:checked { background-color: #3B82F6; color: #0B1220; }
            QCheckBox::indicator {
                width: 18px; height: 18px; border: 1px solid #2B323A; border-radius: 4px; background-color: #0F1113;
            }
            QCheckBox::indicator:hover { border-color: #3B82F6; }
            QCheckBox::indicator:checked { background-color: #0F1113; border-color: #3B82F6; }
            QComboBox:hover { border-color: #3B82F6; }
            QComboBox::drop-down { width: 26px; border-left: 1px solid #2B323A; }
            QComboBox QAbstractItemView {
                background-color: #171A1D; color: #D9E3EA; border: 1px solid #2B323A;
                selection-background-color: #3B82F6; selection-color: #0B1220;
                outline: none;
            }
            QComboBox QAbstractItemView::item { padding: 6px 10px; }
            /* Strong blue hover/selection to replace faint grey */
            QComboBox QAbstractItemView::item:hover { background-color: #3B82F6; color: #0B1220; }
            QComboBox QAbstractItemView::item:selected { background-color: #3B82F6; color: #0B1220; }
            QComboBox::drop-down { width: 26px; border-left: 1px solid #2B323A; }
            QComboBox QAbstractItemView {
                background-color: #171A1D; color: #D9E3EA; border: 1px solid #2B323A;
                selection-background-color: #253349; selection-color: #DDF3FF;
                outline: none;
            }
            QComboBox QAbstractItemView::item { padding: 6px 10px; }
            QComboBox QAbstractItemView::item:hover { background-color: #1F2937; }

            QProgressBar {
                border: 1px solid #262B31; border-radius: 6px; background-color: #0F1113;
                height: 10px;
            }
            QProgressBar::chunk { background-color: #3B82F6; border-radius: 6px; }

            QDialog { background-color: #111315; border: 1px solid #262B31; }
        """)

    def _update_advanced_toggle_label(self, checked):
        self.advanced_toggle.setText("Advanced Options ▾" if checked else "Advanced Options ▸")

    def pick_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Choose output directory")
        if dir_path:
            self.selected_dir = dir_path
            # Show concise path in the title area and switch button label to Change
            shown = self._shorten_path(dir_path)
            self.out_title_label.setText(shown)
            self.outdir_btn.setText("Change Output Folder")

    def pick_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select media file")
        if file_path:
            self.local_file_path = file_path
            self.selected_file_label.setText(f"Local File: {os.path.basename(file_path)}")
            try:
                self.file_btn.setText(f"File: .../{os.path.basename(file_path)}")
            except Exception:
                self.file_btn.setText(f"File: {self.local_file_path}")
        else:
            self.local_file_path = None
            self.selected_file_label.setText("Local File: None")
            self.file_btn.setText("Choose Local File")

    def _shorten_path(self, path_str, max_len=60):
        if not path_str:
            return ""
        # If path is short, return as is
        if len(path_str) <= max_len:
            return path_str
        # Otherwise, keep start and end segments
        base = os.path.basename(path_str)
        prefix = path_str[:max(0, max_len - len(base) - 5)]
        return f"{prefix}…/{base}"

    def parse_time(self, text):
        if not text:
            return None
        try:
            parts = [float(p) for p in text.split(":")]
            if len(parts) == 1:
                return parts[0]
            elif len(parts) == 2:
                return parts[0]*60 + parts[1]
            elif len(parts) == 3:
                return parts[0]*3600 + parts[1]*60 + parts[2]
        except ValueError:
            return None
        return None

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def run_job(self):
        url = self.url_input.text().strip()
        local_file = getattr(self, 'local_file_path', None)
        if not url and not local_file:
            QMessageBox.warning(self, "Input Error", "Provide a URL or select a local file.")
            return
        if not self.selected_dir:
            QMessageBox.warning(self, "Input Error", "Output folder is required.")
            return
        
        # Read model and formats from Settings
        selected_model_key = self.settings.value("modelKey", DEFAULT_MODEL_KEY, type=str)
        formats_value = self.settings.value("outputFormats", ",".join(DEFAULT_OUTPUT_FORMATS), type=str)
        if isinstance(formats_value, str):
            formats = [v.strip().lower() for v in formats_value.split(',') if v.strip()]
        else:
            formats = [str(v).strip().lower() for v in (formats_value or [])]
        if 'all' in formats:
            formats = ['txt', 'srt', 'vtt', 'tsv', 'json']
        if not formats:
            formats = list(DEFAULT_OUTPUT_FORMATS)

        keep_video_setting = self.settings.value("keepVideo", True, type=bool)
        current_dl_format_id = self.settings.value("downloadFormatID", DEFAULT_DOWNLOAD_FORMAT_ID, type=str)
        
        download_format_details = None
        for k, v_details in DOWNLOAD_FORMAT_OPTIONS.items():
            if v_details["format_id"] == current_dl_format_id:
                download_format_details = v_details
                break
        if not download_format_details: 
             download_format_details = DOWNLOAD_FORMAT_OPTIONS[next(iter(DOWNLOAD_FORMAT_OPTIONS))]


        start_time = self.parse_time(self.start_time_input.text().strip())
        end_time = self.parse_time(self.end_time_input.text().strip())
        if start_time is not None and end_time is not None and end_time <= start_time:
            QMessageBox.warning(self, "Input Error", "End time must be greater than start time.")
            return

        self.go_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_status_label.setText("Processing...")

        self.worker = WorkerThread(
            url,
            self.selected_dir,
            formats,
            selected_model_key,
            keep_video_setting,
            download_format_details,
            start_time=start_time,
            end_time=end_time,
            local_file=local_file,
        )
        self.worker.progress.connect(self.update_status_message)
        self.worker.transcription_progress.connect(self.update_progress_bar)
        self.worker.finished.connect(self.done)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def update_status_message(self, msg):
        self.progress_status_label.setText(f"Status: {msg}")

    def update_progress_bar(self, current_step, total_steps):
        self.progress_bar.setMaximum(total_steps)
        self.progress_bar.setValue(current_step)

    def done(self, files):
        self.progress_bar.setVisible(False)
        self.progress_status_label.setText("Status: DONE!")
        self.go_btn.setEnabled(True)
        QMessageBox.information(self, "Completed", "Processing finished.\nFiles:\n" + "\n".join(files))

    def handle_error(self, msg):
        self.progress_bar.setVisible(False)
        self.progress_status_label.setText("Status: Error Occurred.")
        self.go_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"An error occurred:\n{msg}")

def run_gui_app():
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)
    win = RumbleTranscriber()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run_gui_app()
