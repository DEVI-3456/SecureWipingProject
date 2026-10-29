import sys
import os
import hashlib
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QSpinBox, QTextEdit, QProgressBar, QFileDialog,
    QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from certificate_generator import generate_html_certificate


# ---------------- SECURITY HELPERS ----------------

def calculate_sha256(file_path):
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha.update(chunk)
    return sha.hexdigest()


def secure_wipe(file_path, passes, progress_cb, log_cb):
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError("File does not exist.")

        size = os.path.getsize(file_path)
        log_cb("Calculating SHA-256 hash...")
        original_hash = calculate_sha256(file_path)

        with open(file_path, "r+b") as f:
            for i in range(passes):
                log_cb(f"Overwrite pass {i + 1}/{passes}")
                f.seek(0)
                f.write(os.urandom(size))
                f.flush()
                os.fsync(f.fileno())
                progress_cb(int(((i + 1) / passes) * 100))

        try:
            os.remove(file_path)
        except Exception as e:
            log_cb(f"⚠ Could not delete file: {e}")

        log_cb("File securely destroyed.")
        return original_hash, "FILE_DESTROYED", size

    except Exception as e:
        log_cb(f"❌ Wipe failed: {e}")
        raise


# ---------------- WORKER THREAD ----------------

class WipeWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path, passes):
        super().__init__()
        self.file_path = file_path
        self.passes = passes

    def run(self):
        try:
            original_hash, final_hash, size = secure_wipe(
                self.file_path,
                self.passes,
                self.progress.emit,
                self.log.emit
            )

            self.finished.emit({
                "file_path": self.file_path,
                "original_hash": original_hash,
                "final_hash": final_hash,
                "size": size,
                "passes": self.passes
            })

        except Exception as e:
            self.error.emit(str(e))


# ---------------- MAIN WINDOW ----------------

class SecureWiperGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_path = None
        self.recent_files = []
        self.worker = None   # IMPORTANT: persistent thread reference
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("SecureWiper Pro — Enterprise Edition")
        self.resize(1200, 750)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # -------- LEFT SIDEBAR --------
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        side_layout = QVBoxLayout(sidebar)

        logo = QLabel("🛡 SecureWiper")
        logo.setFont(QFont("Segoe UI", 18, QFont.Bold))
        side_layout.addWidget(logo)

        side_layout.addWidget(QLabel("Recent Files"))
        self.recent_list = QListWidget()
        self.recent_list.itemClicked.connect(self.load_recent_file)
        side_layout.addWidget(self.recent_list)

        side_layout.addStretch()
        main_layout.addWidget(sidebar)

        # -------- MAIN PANEL --------
        panel = QFrame()
        panel_layout = QVBoxLayout(panel)

        title = QLabel("Secure Data Destruction")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        panel_layout.addWidget(title)

        file_row = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        browse_btn = QPushButton("Browse File")
        browse_btn.clicked.connect(self.select_file)
        file_row.addWidget(self.file_label, 1)
        file_row.addWidget(browse_btn)
        panel_layout.addLayout(file_row)

        settings_row = QHBoxLayout()
        settings_row.addWidget(QLabel("Overwrite Passes (NIST 800-88):"))
        self.passes_spin = QSpinBox()
        self.passes_spin.setRange(1, 35)
        self.passes_spin.setValue(3)
        settings_row.addWidget(self.passes_spin)
        panel_layout.addLayout(settings_row)

        self.progress_bar = QProgressBar()
        panel_layout.addWidget(self.progress_bar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        panel_layout.addWidget(self.log_text, 1)

        self.wipe_btn = QPushButton("EXECUTE SECURE WIPE")
        self.wipe_btn.setEnabled(False)
        self.wipe_btn.clicked.connect(self.start_wipe)
        panel_layout.addWidget(self.wipe_btn)

        main_layout.addWidget(panel, 1)

    # -------- FILE SELECTION --------

    def select_file(self):
        dialog = QFileDialog(self, "Select File")
        dialog.setFileMode(QFileDialog.ExistingFile)

        if dialog.exec_():
            self.file_path = dialog.selectedFiles()[0]
            self.file_label.setText(self.file_path)
            self.wipe_btn.setEnabled(True)
            self.add_recent_file(self.file_path)

    # -------- RECENT FILES --------

    def add_recent_file(self, file_path):
        if file_path not in self.recent_files:
            self.recent_files.insert(0, file_path)
            self.recent_files = self.recent_files[:10]
            self.refresh_recent_list()

    def refresh_recent_list(self):
        self.recent_list.clear()
        for path in self.recent_files:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            self.recent_list.addItem(item)

    def load_recent_file(self, item):
        index = self.recent_list.row(item)
        if 0 <= index < len(self.recent_files):
            self.file_path = self.recent_files[index]
            self.file_label.setText(self.file_path)
            self.wipe_btn.setEnabled(True)

    # -------- WIPE PROCESS --------

    def start_wipe(self):
        if not self.file_path or not os.path.exists(self.file_path):
            self.log_text.append("❌ Invalid file selected.")
            return

        self.wipe_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_text.clear()

        self.worker = WipeWorker(self.file_path, self.passes_spin.value())
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_text.append)
        self.worker.finished.connect(self.wipe_finished)
        self.worker.error.connect(self.wipe_error)
        self.worker.start()

    def wipe_finished(self, result):
        self.log_text.append("Generating compliance certificate...")

        pdf_path, err = generate_html_certificate(
            result["file_path"],
            result["original_hash"],
            result["final_hash"],
            result["size"],
            result["passes"],
            True
        )

        if err:
            self.log_text.append(f"❌ Certificate error: {err}")
        else:
            self.log_text.append(f"Certificate saved at:\n{pdf_path}")

        self.wipe_btn.setEnabled(True)

        if self.worker:
            self.worker.quit()
            self.worker.wait()
            self.worker = None

    def wipe_error(self, message):
        self.log_text.append(f"❌ ERROR: {message}")
        self.wipe_btn.setEnabled(True)

        if self.worker:
            self.worker.quit()
            self.worker.wait()
            self.worker = None


# ---------------- ENTRY ----------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SecureWiperGUI()
    window.show()
    sys.exit(app.exec_())
