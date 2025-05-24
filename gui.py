# gui.py
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QCheckBox, QHBoxLayout, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import main
import sys

class WorkerThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url, outdir, formats):
        super().__init__()
        self.url = url
        self.outdir = outdir
        self.formats = formats

    def run(self):
        try:
            self.progress.emit("Downloading video...")
            video_file = main.download_video(self.url, self.outdir)
            self.progress.emit("Transcribing...")
            results = main.transcribe(video_file, formats=self.formats)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class RumbleTranscriber(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rumble Transcript Extractor")
        self.setMinimumWidth(450)
        self.setStyleSheet("""
            QWidget { background: #191919; color: #f8f8f2; font-size: 15px; font-family: 'Fira Mono', 'Consolas', monospace; }
            QPushButton { background: #333; border: 1px solid #666; padding: 6px 18px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background: #222; border: 1px solid #00ffc3; color: #00ffc3; }
            QLineEdit { background: #222; border: 1px solid #444; color: #fff; padding: 6px; border-radius: 3px; }
            QCheckBox { margin-right: 12px; }
            QLabel { margin-top: 5px; }
            QProgressBar { background: #222; border: 1px solid #444; height: 12px; border-radius: 6px; }
        """)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Paste Rumble video URL here…")
        layout.addWidget(self.url_input)

        self.outdir_btn = QPushButton("Select Output Folder")
        self.outdir_btn.clicked.connect(self.pick_dir)
        layout.addWidget(self.outdir_btn)

        self.format_checkboxes = {}
        formats = ['txt', 'srt', 'vtt', 'tsv', 'json', 'all']
        box_row = QHBoxLayout()
        for fmt in formats:
            box = QCheckBox(fmt.upper())
            box_row.addWidget(box)
            self.format_checkboxes[fmt] = box
        layout.addLayout(box_row)

        self.go_btn = QPushButton("GO! Extract and Transcribe")
        self.go_btn.clicked.connect(self.run_job)
        layout.addWidget(self.go_btn)

        self.progress = QLabel('')
        layout.addWidget(self.progress)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0) # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.selected_dir = None

    def pick_dir(self):
        self.selected_dir = QFileDialog.getExistingDirectory(self, "Choose output directory")
        self.outdir_btn.setText(f"Output: {self.selected_dir or 'Not set'}")

    def run_job(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Fuckup", "Enter a goddamn URL.")
            return
        if not self.selected_dir:
            QMessageBox.warning(self, "Fuckup", "Pick a folder, genius.")
            return
        # Which boxes checked?
        formats = [fmt for fmt, cb in self.format_checkboxes.items() if cb.isChecked()]
        if not formats:
            QMessageBox.warning(self, "Seriously?", "Pick at least one format.")
            return
        if 'all' in formats:
            formats = ['txt', 'srt', 'vtt', 'tsv', 'json']

        # Launch worker thread so GUI doesn't freeze
        self.progress_bar.setVisible(True)
        self.worker = WorkerThread(url, self.selected_dir, formats)
        self.worker.progress.connect(self.progress.setText)
        self.worker.finished.connect(self.done)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def done(self, files):
        self.progress_bar.setVisible(False)
        self.progress.setText("DONE! Files:\n" + "\n".join(files))
        QMessageBox.information(self, "All Done", "Everything’s finished. Go look in your folder.")

    def handle_error(self, msg):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Shit broke", msg)

def run_gui():
    app = QApplication(sys.argv)
    win = RumbleTranscriber()
    win.show()
    sys.exit(app.exec_())
