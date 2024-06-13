import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QComboBox, QProgressBar, QPlainTextEdit, QMessageBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import subprocess
import re

# Initialize colorama
from colorama import init
init(autoreset=True)

# Function to strip ANSI escape codes
def strip_ansi_escape_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class LogicalBackupWorker(QThread):
    progress_updated = pyqtSignal(int)
    log_updated = pyqtSignal(str)
    backup_finished = pyqtSignal(str)

    def __init__(self, command, backup_directory=None):
        super().__init__()
        self.command = command
        self.backup_directory = backup_directory

    def run(self):
        try:
            # Execute the command based on user input
            self.execute_command(self.command)
        except Exception as e:
            self.log_updated.emit(f"Error: {e}")

    def execute_command(self, command):
        if command == 'backup':
            self.backup()
        elif command == 'list':
            self.list_files()
        elif command == 'info':
            self.backup_info()
        elif command == 'encryption':
            self.set_encryption()
        elif command == 'list-devices':
            self.list_connected_devices()

    def backup(self):
        if not self.backup_directory:
            self.log_updated.emit("Backup directory not selected.")
            return

        self.log_updated.emit(f"Starting backup to {self.backup_directory}...")
        try:
            process = subprocess.Popen(['pymobiledevice3', 'backup2', 'backup', '--full', self.backup_directory],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       universal_newlines=True, encoding='utf-8')

            total_lines = 100  # Assuming progress is reported in lines as in your example
            progress = 0

            for line in process.stdout:
                self.log_updated.emit(strip_ansi_escape_codes(line.strip()))
                # Example: Parsing progress from a line like "  5%|###      | 5.0/100.0 [00:05<02:10, 0.5/it]"
                if re.search(r'(\d+)%\|\s*.*\|\s*(\d+\.\d+)/(\d+\.\d+)', line):
                    progress = int(re.search(r'(\d+)%\|\s*.*\|\s*(\d+\.\d+)/(\d+\.\d+)', line).group(1))
                    self.progress_updated.emit(progress)
                # Check if progress has reached 100%
                if progress >= 100:
                    break  # Exit loop when progress reaches 100%

            process.communicate()
            if process.returncode != 0:
                self.log_updated.emit(f"Error executing backup command.")
            else:
                self.log_updated.emit("Backup completed successfully.")
                self.backup_finished.emit("Backup completed successfully.")  # Emit signal when backup is finished
        except KeyboardInterrupt:
            self.log_updated.emit("Backup process aborted by user.")
        except subprocess.CalledProcessError as e:
            self.log_updated.emit(f"Error executing backup command: {e}")

    def list_files(self):
        if not self.backup_directory:
            self.log_updated.emit("Backup directory not selected.")
            return
        
        self.log_updated.emit(f"Listing files in backup directory {self.backup_directory}...")
        try:
            subprocess.run(['pymobiledevice3', 'backup2', 'list', self.backup_directory], check=True)
        except KeyboardInterrupt:
            self.log_updated.emit("List process aborted by user.")
        except subprocess.CalledProcessError as e:
            self.log_updated.emit(f"Error listing files: {e}")

    def backup_info(self):
        if not self.backup_directory:
            self.log_updated.emit("Backup directory not selected.")
            return
        
        self.log_updated.emit(f"Printing information for backup directory {self.backup_directory}...")
        try:
            subprocess.run(['pymobiledevice3', 'backup2', 'info', self.backup_directory], check=True)
        except KeyboardInterrupt:
            self.log_updated.emit("Info process aborted by user.")
        except subprocess.CalledProcessError as e:
            self.log_updated.emit(f"Error printing backup info: {e}")

    def set_encryption(self):
        state = "on"  # Default to "on" for example
        password = "my_password"  # Default password for example
        self.log_updated.emit(f"Setting encryption {state} with password {password}...")
        try:
            subprocess.run(['pymobiledevice3', 'backup2', 'encryption', state, password], check=True)
        except KeyboardInterrupt:
            self.log_updated.emit("Encryption process aborted by user.")
        except subprocess.CalledProcessError as e:
            self.log_updated.emit(f"Error setting encryption: {e}")

    def list_connected_devices(self):
        self.log_updated.emit("Listing connected devices...")
        try:
            process = subprocess.Popen(['pymobiledevice3', 'usbmux', 'list'],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)

            for line in process.stdout:
                self.log_updated.emit(strip_ansi_escape_codes(line.strip()))

            _, stderr = process.communicate()
            if process.returncode != 0:
                self.log_updated.emit(f"Error listing connected devices: {stderr}")
        except subprocess.CalledProcessError as e:
            self.log_updated.emit(f"Error listing connected devices: {e}")

class LogicalBackupApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Logical Backup Tool")
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        self.command_label = QLabel("Command:")
        self.command_combo = QComboBox()
        self.command_combo.addItem("Select Command")
        self.command_combo.addItem("backup")
        self.command_combo.addItem("list")
        self.command_combo.addItem("info")
        self.command_combo.addItem("encryption")
        self.command_combo.addItem("list-devices")
        
        self.execute_button = QPushButton("Execute", self)
        self.execute_button.setObjectName("blueButton")
        self.execute_button.clicked.connect(self.execute_command)

        self.backup_label = QLabel("Backup Directory:")
        self.backup_path_edit = QLineEdit()
        self.browse_button = QPushButton("Browse", self)
        self.browse_button.setObjectName("browseButton")
        self.browse_button.clicked.connect(self.browse_backup_directory)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)

        layout.addWidget(self.command_label)
        layout.addWidget(self.command_combo)
        layout.addWidget(self.backup_label)
        layout.addWidget(self.backup_path_edit)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.execute_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_box)

        self.setLayout(layout)

        self.setStyleSheet("""
        QPushButton#blueButton, #browseButton {
            background-color: #3498db;
            border: none;
            color: white;
            padding: 10px 20px;
            font-size: 16px;
            border-radius: 4px;
        }
        QPushButton#blueButton:hover, #browseButton:hover {
            background-color: #2980b9;
        }
        """)

        self.worker = None

    def browse_backup_directory(self):
        backup_directory = QFileDialog.getExistingDirectory(self, "Select Backup Directory")
        if backup_directory:
            self.backup_path_edit.setText(backup_directory)

    def execute_command(self):
        command = self.command_combo.currentText()
        backup_directory = self.backup_path_edit.text()

        if command == "Select Command":
            self.show_message("Error", "Please select a command.")
            return

        if command == "backup" and not backup_directory:
            self.show_message("Error", "Please select a backup directory.")
            return

        self.worker = LogicalBackupWorker(command, backup_directory)
        self.worker.log_updated.connect(self.update_log)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.backup_finished.connect(self.show_backup_completed_popup)  # Connect to backup finished signal
        self.worker.start()

    def update_log(self, message):
        self.log_box.appendPlainText(message)
        
        # Check if the message contains progress information
        if re.search(r'\d+%.*', message):
            progress = int(re.search(r'\d+', message).group())
            self.progress_bar.setValue(progress)

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def show_backup_completed_popup(self, message):
        QMessageBox.information(self, "Backup Completed", message)

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LogicalBackupApp()
    window.show()
    sys.exit(app.exec())
