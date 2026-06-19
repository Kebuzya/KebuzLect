from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.converter import build_output_filename, convert_lecture
from app.device import DeviceBackend
from app.models import Album, LectureGroup
from app.scanner import compute_group_hash
from ui.i18n import tr


class ConvertWorker(QThread):
    progress = pyqtSignal(int)
    conversion_finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        groups: list[LectureGroup],
        album: Album,
        config: AppConfig,
        backend: DeviceBackend,
        photos_per_page: int = 2,
    ) -> None:
        super().__init__()
        self.groups = groups
        self.album = album
        self.config = config
        self.backend = backend
        self.photos_per_page = photos_per_page

    def run(self) -> None:
        outputs: list[Path] = []
        try:
            for index, group in enumerate(self.groups):
                output_path = convert_lecture(
                    group, self.album, self.config, self.backend, self.photos_per_page
                )
                group_hash = compute_group_hash(group.photos)
                self.config.mark_converted(self.album.key, group_hash)
                outputs.append(output_path)
                self.progress.emit(index + 1)
            self.conversion_finished.emit(outputs)
        except Exception as failure:
            self.error.emit(str(failure))


class ConvertDialog(QDialog):
    def __init__(
        self,
        groups: list[LectureGroup],
        album: Album,
        config: AppConfig,
        backend: DeviceBackend,
        parent: QWidget | None = None,
        photos_per_page: int = 2,
    ) -> None:
        super().__init__(parent)
        self.groups = groups
        self.album = album
        self.config = config
        self.backend = backend
        self.photos_per_page = photos_per_page
        self.worker: ConvertWorker | None = None
        self.outputs: list[Path] = []

        self.setWindowTitle(tr("convert_title"))
        self.resize(520, 420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("album_line", name=self.album.display_name)))
        for group in self.groups:
            filename = build_output_filename(group, self.album, self.config)
            layout.addWidget(
                QLabel(tr("convert_row", date=group.date, count=len(group.photos), filename=filename))
            )

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.groups))
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        self.convert_button = QPushButton(tr("convert_btn"))
        self.convert_button.clicked.connect(self._start_conversion)
        self.open_button = QPushButton(tr("open_folder_btn"))
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_output_folder)
        button_row.addWidget(self.convert_button)
        button_row.addWidget(self.open_button)
        button_row.addStretch()
        layout.addLayout(button_row)

    def _start_conversion(self) -> None:
        if not self.groups:
            return
        self.convert_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.worker = ConvertWorker(
            self.groups, self.album, self.config, self.backend, self.photos_per_page
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.conversion_finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, outputs: list[Path]) -> None:
        self.outputs = outputs
        self.status_label.setText(tr("convert_done", count=len(outputs)))
        self.open_button.setEnabled(True)
        self.convert_button.setEnabled(True)

    def _on_error(self, message: str) -> None:
        QMessageBox.warning(self, tr("convert_error_title"), message)
        self.convert_button.setEnabled(True)

    def _open_output_folder(self) -> None:
        folder = self.album.output_folder
        if folder and os.path.isdir(folder):
            os.startfile(folder)

    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait()
        super().closeEvent(event)
