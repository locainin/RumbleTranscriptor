# gui.py
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QCheckBox, QHBoxLayout, QMessageBox, QProgressBar,
    QComboBox, QMenuBar, QAction, QDialog, QSpacerItem, QSizePolicy, QFormLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
import main # Uses main.py
import sys
import os # For os.path.basename in pick_dir

MODEL_DESCRIPTIONS = {
    "tiny":      "Tiny        | ~39M params  | Fastest, lowest accuracy, low VRAM",
    "base":      "Base        | ~74M params  | Fast, decent accuracy, moderate VRAM",
    "small":     "Small       | ~244M params | Good balance of speed/accuracy, more VRAM",
    "medium":    "Medium      | ~769M params | Slower, high accuracy, significant VRAM",
    "large-v1":  "Large v1    | ~1.55B params| Slowest, highest accuracy, very high VRAM",
    "large-v2":  "Large v2    | ~1.55B params| Updated large model, similar requirements",
    "large-v3":  "Large v3    | ~1.55B params| Latest large model, best official accuracy",
    "turbo":     "Turbo (User)| ~809M params | User-specified 'turbo' model"
}
DEFAULT_MODEL_KEY = "turbo"

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

    def __init__(self, url, outdir, formats, model_name, keep_video_setting, download_format_details):
        super().__init__()
        self.url = url
        self.outdir = outdir
        self.formats = formats
        self.model_name = model_name
        self.keep_video = keep_video_setting
        self.download_format_details = download_format_details

    def run(self):
        try:
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
            results = main.transcribe(video_file_path, model_name=self.model_name, formats=self.formats)
            self.transcription_progress.emit(4,5)
            QThread.msleep(200)
            self.transcription_progress.emit(5,5)

            self.finished.emit(results)
            
            if not self.keep_video:
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
        
        self.settings = QSettings("YourOrgName", "RumbleTranscriber")
        
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
        self.accept()

class RumbleTranscriber(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rumble Transcript Extractor")
        self.setMinimumWidth(750)
        self.setMinimumHeight(550)
        self.settings = QSettings("YourOrgName", "RumbleTranscriber")
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)

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

        self.main_layout.addWidget(QLabel("Rumble Video URL:"))
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Paste Rumble video URL here…")
        self.main_layout.addWidget(self.url_input)

        self.main_layout.addWidget(QLabel("Output Folder:"))
        self.outdir_btn = QPushButton("Select Output Folder")
        self.outdir_btn.clicked.connect(self.pick_dir)
        self.main_layout.addWidget(self.outdir_btn)
        self.selected_dir_label = QLabel("Output Folder: Not selected")
        self.main_layout.addWidget(self.selected_dir_label)

        self.main_layout.addWidget(QLabel("Whisper Model:"))
        self.model_combo = QComboBox(self)
        default_item_index = 0
        found_default = False
        for index, (key, full_description) in enumerate(MODEL_DESCRIPTIONS.items()):
            self.model_combo.addItem(full_description, key)
            if key == DEFAULT_MODEL_KEY:
                default_item_index = index
                found_default = True
        
        if found_default:
            self.model_combo.setCurrentIndex(default_item_index)
        elif self.model_combo.count() > 0:
            self.model_combo.setCurrentIndex(0)
            
        self.main_layout.addWidget(self.model_combo)

        self.main_layout.addWidget(QLabel("Output Formats:"))
        self.format_checkboxes = {}
        formats_to_show = ['txt', 'srt', 'vtt', 'tsv', 'json', 'all']
        checkbox_container = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_container)
        for fmt in formats_to_show:
            box = QCheckBox(fmt.upper())
            checkbox_layout.addWidget(box)
            self.format_checkboxes[fmt] = box
        self.main_layout.addWidget(checkbox_container)

        self.main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.go_btn = QPushButton("Extract & Transcribe")
        self.go_btn.setFixedHeight(45)
        self.go_btn.clicked.connect(self.run_job)
        self.main_layout.addWidget(self.go_btn)

        self.progress_status_label = QLabel('Status: Ready')
        self.main_layout.addWidget(self.progress_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(5)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat('%p% - %v/%m steps')
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        self.selected_dir = None

    def apply_styles(self):
        # Corrected QSS: Removed the line that caused the NameError.
        # The checkbox will rely on background color change and possibly native checkmark.
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #1E1E1E; color: #D4D4D4;
                font-size: 15px; font-family: 'Fira Mono', 'Consolas', 'DejaVu Sans Mono', monospace;
                border: none;
            }}
            QMenuBar {{ background-color: #2D2D2D; color: #00ACC1; border-bottom: 1px solid #007A8A; }}
            QMenuBar::item {{ background-color: #2D2D2D; color: #00ACC1; padding: 5px 10px; }}
            QMenuBar::item:selected {{ background-color: #00ACC1; color: #1E1E1E; }}
            QMenu {{ background-color: #2D2D2D; color: #00ACC1; border: 1px solid #007A8A; }}
            QMenu::item:selected {{ background-color: #00ACC1; color: #1E1E1E; }}
            QLabel {{ margin-top: 7px; margin-bottom: 3px; color: #4DB6AC; font-weight: normal; qproperty-alignment: 'AlignCenter';}}
            QLineEdit {{
                background: #252526; border: 1px solid #007A8A; color: #D4D4D4;
                padding: 7px; border-radius: 2px; font-size: 14px;
                selection-background-color: #007A8A; selection-color: #FFFFFF;
            }}
            QLineEdit:focus {{ border: 1px solid #4DB6AC; }}
            QPushButton {{
                background-color: #333333; color: #4DB6AC; border: 1px solid #4DB6AC;
                padding: 8px 18px; border-radius: 3px; font-weight: bold; text-transform: none;
            }}
            QPushButton:hover {{ background-color: #4DB6AC; color: #1E1E1E; border: 1px solid #1E1E1E; }}
            QPushButton:pressed {{ background-color: #007A8A; color: #FFFFFF; }}
            QCheckBox {{ spacing: 8px; color: #B0BEC5; font-size: 14px; margin-right: 12px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid #4DB6AC; border-radius: 2px; background-color: #252526; }}
            QCheckBox::indicator:checked {{
                background-color: #4DB6AC; /* Background color changes on check */
            }}
            QCheckBox::indicator:hover {{ border: 1px solid #00ACC1; }}
            QComboBox {{
                background: #252526; border: 1px solid #007A8A; padding: 7px;
                color: #D4D4D4; border-radius: 2px; selection-background-color: #007A8A;
            }}
            QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 22px; border-left: 1px solid #007A8A; }}
            QComboBox QAbstractItemView {{ background-color: #2D2D2D; border: 1px solid #007A8A; color: #D4D4D4; selection-background-color: #007A8A; selection-color: #FFFFFF; }}
            QProgressBar {{
                border: 1px solid #007A8A; border-radius: 2px; background-color: #252526;
                text-align: center; color: #D4D4D4; height: 22px;
            }}
            QProgressBar::chunk {{ background-color: #4DB6AC; margin: 1px; }}
            QDialog {{ background-color: #1E1E1E; border: 1px solid #007A8A; }}
            QFormLayout QLabel {{ qproperty-alignment: 'AlignLeft'; }}
        """)

    def pick_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Choose output directory")
        if dir_path:
            self.selected_dir = dir_path
            self.selected_dir_label.setText(f"Output Folder: {self.selected_dir}")
            try:
                self.outdir_btn.setText(f"Output: .../{os.path.basename(dir_path)}")
            except:
                self.outdir_btn.setText(f"Output: {self.selected_dir}")

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def run_job(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "URL is required.")
            return
        if not self.selected_dir:
            QMessageBox.warning(self, "Input Error", "Output folder is required.")
            return
        
        selected_model_key = self.model_combo.currentData()
        if not selected_model_key:
            QMessageBox.critical(self, "Error", "Model selection is invalid.")
            return

        formats = [fmt for fmt, cb in self.format_checkboxes.items() if cb.isChecked()]
        if not formats:
            QMessageBox.warning(self, "Input Error", "At least one output format is required.")
            return
        if 'all' in formats:
            formats = ['txt', 'srt', 'vtt', 'tsv', 'json']

        keep_video_setting = self.settings.value("keepVideo", True, type=bool)
        current_dl_format_id = self.settings.value("downloadFormatID", DEFAULT_DOWNLOAD_FORMAT_ID, type=str)
        
        download_format_details = None
        for k, v_details in DOWNLOAD_FORMAT_OPTIONS.items():
            if v_details["format_id"] == current_dl_format_id:
                download_format_details = v_details
                break
        if not download_format_details: 
             download_format_details = DOWNLOAD_FORMAT_OPTIONS[next(iter(DOWNLOAD_FORMAT_OPTIONS))]


        self.go_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_status_label.setText("Processing...")

        self.worker = WorkerThread(url, self.selected_dir, formats, selected_model_key, keep_video_setting, download_format_details)
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
    app.setOrganizationName("YourOrgName")
    app.setApplicationName("RumbleTranscriber")
    win = RumbleTranscriber()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run_gui_app()