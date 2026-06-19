from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.device.adb import AdbBackend
from ui.i18n import tr

PLATFORM_TOOLS_URL = "https://developer.android.com/tools/releases/platform-tools"
ADB_EXECUTABLE = "adb.exe"


class SetupWizard(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.selected_adb_dir: Path | None = None
        self.setWindowTitle(tr("adb_setup_title"))
        self.resize(560, 360)

        self.pages = QStackedWidget(self)
        self.pages.addWidget(self._build_download_page())
        self.pages.addWidget(self._build_locate_page())
        self.pages.addWidget(self._build_verify_page())

        layout = QVBoxLayout(self)
        layout.addWidget(self.pages)

    def _build_download_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        explanation = QLabel(tr("wizard_intro"))
        explanation.setWordWrap(True)
        download_button = QPushButton(tr("download_platform_tools"))
        download_button.clicked.connect(self._open_download_page)
        next_button = QPushButton(tr("next"))
        next_button.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        layout.addWidget(explanation)
        layout.addWidget(download_button)
        layout.addStretch()
        layout.addWidget(next_button)
        return page

    def _build_locate_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(tr("locate_label"))
        label.setWordWrap(True)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        browse_button = QPushButton(tr("browse"))
        browse_button.clicked.connect(self._browse_for_adb_dir)
        path_row.addWidget(self.path_edit)
        path_row.addWidget(browse_button)

        self.locate_status = QLabel("")
        self.locate_status.setWordWrap(True)
        next_button = QPushButton(tr("next"))
        next_button.clicked.connect(self._validate_adb_dir)

        layout.addWidget(label)
        layout.addLayout(path_row)
        layout.addWidget(self.locate_status)
        layout.addStretch()
        layout.addWidget(next_button)
        return page

    def _build_verify_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        instruction = QLabel(tr("wizard_instruction"))
        instruction.setWordWrap(True)
        check_button = QPushButton(tr("check_connection"))
        check_button.clicked.connect(self._check_connection)
        self.verify_status = QLabel("")
        self.verify_status.setWordWrap(True)
        layout.addWidget(instruction)
        layout.addWidget(check_button)
        layout.addWidget(self.verify_status)
        layout.addStretch()
        return page

    def _open_download_page(self) -> None:
        QDesktopServices.openUrl(QUrl(PLATFORM_TOOLS_URL))

    def _browse_for_adb_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("adb_folder_dialog"))
        if directory:
            self.path_edit.setText(directory)

    def _validate_adb_dir(self) -> None:
        directory = self.path_edit.text().strip()
        if not directory:
            self.locate_status.setText(tr("specify_folder"))
            return
        if not (Path(directory) / ADB_EXECUTABLE).is_file():
            self.locate_status.setText(tr("adb_not_in_folder"))
            return
        self.selected_adb_dir = Path(directory)
        self.locate_status.setText("")
        self.pages.setCurrentIndex(2)

    def _check_connection(self) -> None:
        if self.selected_adb_dir is None:
            self.verify_status.setText(tr("specify_adb_first"))
            return
        self.config.settings.adb_path = str(self.selected_adb_dir)
        backend = AdbBackend(config=self.config)
        if not backend.is_available():
            self.verify_status.setText(tr("adb_not_found_check"))
            return
        status = backend.get_device_status()
        if status == "authorized":
            self.config.save()
            QMessageBox.information(self, tr("done_title"), tr("wizard_connected"))
            self.accept()
            return
        if status == "unauthorized":
            self.verify_status.setText(tr("wizard_unauthorized"))
            return
        self.verify_status.setText(tr("wizard_no_device"))
