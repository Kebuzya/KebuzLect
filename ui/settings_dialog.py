from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.thumbnail import ThumbnailCache
from ui.i18n import tr
from ui.setup_wizard import SetupWizard

PREVIEW_PREDMET = "Пример"
PREVIEW_DATE = "20260413"
PREVIEW_NUMBER = 1


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(tr("settings_title"))
        self.resize(560, 540)
        self._build_ui()
        self._load_values()
        self._update_preview()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.format_edit = QLineEdit()
        self.format_edit.textChanged.connect(self._update_preview)
        self.preview_label = QLabel()
        format_box = QVBoxLayout()
        format_box.addWidget(self.format_edit)
        format_box.addWidget(self.preview_label)
        form.addRow(tr("name_template_label"), self._wrap(format_box))

        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(50, 95)
        self.quality_value = QLabel()
        self.quality_slider.valueChanged.connect(
            lambda value: self.quality_value.setText(str(value))
        )
        form.addRow(tr("jpeg_quality_label"), self._slider_row(self.quality_slider, self.quality_value))

        self.output_root_edit = QLineEdit()
        browse_button = QPushButton(tr("browse"))
        browse_button.clicked.connect(self._browse_output_root)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_root_edit)
        output_row.addWidget(browse_button)
        form.addRow(tr("output_folder_label"), self._wrap(output_row))

        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(10, 500)
        self.blur_value = QLabel()
        self.blur_slider.valueChanged.connect(lambda value: self.blur_value.setText(str(value)))
        form.addRow(tr("blur_threshold_label"), self._slider_row(self.blur_slider, self.blur_value))

        self.duplicate_slider = QSlider(Qt.Orientation.Horizontal)
        self.duplicate_slider.setRange(0, 20)
        self.duplicate_value = QLabel()
        self.duplicate_slider.valueChanged.connect(
            lambda value: self.duplicate_value.setText(str(value))
        )
        form.addRow(tr("dup_threshold_label"), self._slider_row(self.duplicate_slider, self.duplicate_value))

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 6)
        self.width_spin.valueChanged.connect(self._update_preview)
        form.addRow(tr("number_width_label"), self.width_spin)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 300)
        self.dpi_spin.setSingleStep(12)
        form.addRow(tr("dpi_label"), self.dpi_spin)

        self.adb_edit = QLineEdit()
        self.adb_edit.setReadOnly(True)
        reconfigure_button = QPushButton(tr("reconfigure_adb"))
        reconfigure_button.clicked.connect(self._reconfigure_adb)
        adb_row = QHBoxLayout()
        adb_row.addWidget(self.adb_edit)
        adb_row.addWidget(reconfigure_button)
        form.addRow(tr("adb_path_label"), self._wrap(adb_row))

        layout.addLayout(form)
        layout.addWidget(self._build_data_group())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_data_group(self) -> QGroupBox:
        group = QGroupBox(tr("data_group"))
        box = QVBoxLayout(group)
        clear_cache_button = QPushButton(tr("clear_cache_btn"))
        clear_cache_button.clicked.connect(self._clear_cache)
        reset_converted_button = QPushButton(tr("reset_converted_btn"))
        reset_converted_button.clicked.connect(self._reset_converted)
        delete_albums_button = QPushButton(tr("delete_all_albums_btn"))
        delete_albums_button.clicked.connect(self._delete_all_albums)
        box.addWidget(clear_cache_button)
        box.addWidget(reset_converted_button)
        box.addWidget(delete_albums_button)
        return group

    def _load_values(self) -> None:
        settings = self.config.settings
        self.format_edit.setText(settings.output_format)
        self.quality_slider.setValue(settings.jpeg_quality)
        self.output_root_edit.setText(settings.default_output_root)
        self.blur_slider.setValue(settings.blur_threshold)
        self.duplicate_slider.setValue(settings.duplicate_threshold)
        self.width_spin.setValue(settings.lection_number_width)
        self.dpi_spin.setValue(settings.pdf_dpi)
        self.adb_edit.setText(settings.adb_path)

    def _update_preview(self) -> None:
        number = str(PREVIEW_NUMBER).zfill(self.width_spin.value())
        name = (
            self.format_edit.text()
            .replace("{predmet}", PREVIEW_PREDMET)
            .replace("{YYYYMMDD}", PREVIEW_DATE)
            .replace("{lection_number}", number)
        )
        self.preview_label.setText(tr("preview_file", name=name))

    def _browse_output_root(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("default_output_dialog"))
        if directory:
            self.output_root_edit.setText(directory)

    def _reconfigure_adb(self) -> None:
        wizard = SetupWizard(self.config, self)
        wizard.exec()
        self.adb_edit.setText(self.config.settings.adb_path)

    def _on_accept(self) -> None:
        settings = self.config.settings
        settings.output_format = self.format_edit.text()
        settings.jpeg_quality = self.quality_slider.value()
        settings.default_output_root = self.output_root_edit.text()
        settings.blur_threshold = self.blur_slider.value()
        settings.duplicate_threshold = self.duplicate_slider.value()
        settings.lection_number_width = self.width_spin.value()
        settings.pdf_dpi = self.dpi_spin.value()
        self.config.save()
        self.accept()

    def _clear_cache(self) -> None:
        ThumbnailCache(self.config).clear()
        QMessageBox.information(self, tr("cache_title"), tr("cache_cleared"))

    def _reset_converted(self) -> None:
        for album in self.config.albums.values():
            album.converted_hashes.clear()
        self.config.save()
        QMessageBox.information(self, tr("done_title"), tr("converted_reset"))

    def _delete_all_albums(self) -> None:
        answer = QMessageBox.question(self, tr("delete_all_albums_btn"), tr("delete_all_albums_q"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.config.albums.clear()
        self.config.save()
        QMessageBox.information(self, tr("done_title"), tr("all_albums_deleted"))

    def _slider_row(self, slider: QSlider, value_label: QLabel) -> QWidget:
        row = QHBoxLayout()
        row.addWidget(slider)
        row.addWidget(value_label)
        return self._wrap(row)

    def _wrap(self, inner_layout: QHBoxLayout | QVBoxLayout) -> QWidget:
        container = QWidget()
        container.setLayout(inner_layout)
        return container
