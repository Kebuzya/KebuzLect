from __future__ import annotations

import re
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.device import (
    AdbNotAvailableError,
    DeviceBackend,
    DeviceNotConnectedError,
    DeviceUnauthorizedError,
    get_backend,
)
from app.models import Album
from ui.album_view import AlbumView
from ui.convert_dialog import ConvertDialog
from ui.i18n import set_language, tr
from ui.settings_dialog import SettingsDialog
from ui.setup_wizard import SetupWizard
from ui.theme import apply_theme

PREVIEW_PREDMET = "Пример"
PREVIEW_DATE = "20260413"

PHONE_ROOT = "/sdcard"
DEVICE_ERRORS = (AdbNotAvailableError, DeviceNotConnectedError, DeviceUnauthorizedError)


def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parent.parent
    return str(root / relative)


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.backend: DeviceBackend | None = None
        self.is_offline = True
        self.album_view: AlbumView | None = None
        self.setWindowTitle("KebuzLect")
        self.setWindowIcon(QIcon(resource_path("resources/icon.ico")))
        self.resize(900, 600)
        self._build_ui()
        self._connect_backend()
        self._refresh_albums()
        self._update_connection_state()

    def _build_ui(self) -> None:
        self.stack = QStackedWidget(self)
        self.albums_page = QWidget()
        layout = QVBoxLayout(self.albums_page)

        header_row = QHBoxLayout()
        self.albums_label = QLabel(tr("albums_label"))
        header_row.addWidget(self.albums_label)
        header_row.addStretch()
        self.language_button = QPushButton()
        self.language_button.setFixedWidth(40)
        self.language_button.clicked.connect(self._toggle_language)
        header_row.addWidget(self.language_button)
        self.theme_button = QPushButton()
        self.theme_button.setFixedWidth(40)
        self.theme_button.clicked.connect(self._toggle_theme)
        header_row.addWidget(self.theme_button)

        self.album_list = QListWidget()
        self.album_list.itemDoubleClicked.connect(self._open_album_view)

        button_row = QHBoxLayout()
        self.add_button = QPushButton(tr("add_album"))
        self.add_button.clicked.connect(self._add_album)
        self.remove_button = QPushButton(tr("remove_album"))
        self.remove_button.clicked.connect(self._remove_album)
        self.settings_button = QPushButton(tr("settings"))
        self.settings_button.clicked.connect(self._open_settings)
        button_row.addWidget(self.add_button)
        button_row.addWidget(self.remove_button)
        button_row.addStretch()
        button_row.addWidget(self.settings_button)

        layout.addLayout(header_row)
        layout.addWidget(self.album_list)
        layout.addLayout(button_row)

        self.stack.addWidget(self.albums_page)
        self.setCentralWidget(self.stack)

        self.status_icon = QLabel()
        self.status_text = QLabel()
        self.statusBar().addWidget(self.status_icon)
        self.statusBar().addWidget(self.status_text)
        self.connect_button = QPushButton()
        self.connect_button.clicked.connect(self._toggle_connection)
        self.statusBar().addPermanentWidget(self.connect_button)
        self._update_theme_button()
        self._update_language_button()

    def _toggle_language(self) -> None:
        new_language = "en" if self.config.settings.language != "en" else "ru"
        self.config.settings.language = new_language
        self.config.save()
        set_language(new_language)
        self._retranslate()

    def _update_language_button(self) -> None:
        self.language_button.setText(self.config.settings.language.upper())

    def _retranslate(self) -> None:
        self.albums_label.setText(tr("albums_label"))
        self.add_button.setText(tr("add_album"))
        self.remove_button.setText(tr("remove_album"))
        self.settings_button.setText(tr("settings"))
        self._update_language_button()
        self._update_connection_state()

    def _connect_backend(self) -> None:
        while True:
            try:
                self.backend = get_backend()
                self.is_offline = False
                return
            except DeviceUnauthorizedError:
                QMessageBox.warning(
                    self,
                    tr("unauthorized_title"),
                    tr("unauthorized_body"),
                )
                self.backend = None
                self.is_offline = True
                return
            except DeviceNotConnectedError:
                self.backend = None
                self.is_offline = True
                return
            except AdbNotAvailableError:
                wizard = SetupWizard(self.config, self)
                if wizard.exec() == QDialog.DialogCode.Accepted:
                    continue
                self.backend = None
                self.is_offline = True
                return

    def _update_connection_state(self) -> None:
        if self.is_offline:
            self._set_status("#c0392b", tr("status_offline"))
            self.connect_button.setText(tr("connect"))
        else:
            self._set_status("#27ae60", tr("status_online"))
            self.connect_button.setText(tr("disconnect"))
        self.add_button.setEnabled(not self.is_offline)
        self.remove_button.setEnabled(not self.is_offline)

    def _toggle_connection(self) -> None:
        if self.is_offline:
            self._connect_backend()
            self._update_connection_state()
        else:
            self._go_offline()

    def _go_offline(self) -> None:
        self._close_album_view()
        self.backend = None
        self.is_offline = True
        self._update_connection_state()

    def _set_status(self, color: str, text: str) -> None:
        self.status_icon.setText("●")
        self.status_icon.setStyleSheet(f"color: {color};")
        self.status_text.setText(text)

    def _refresh_albums(self) -> None:
        self.album_list.clear()
        for key, album in self.config.albums.items():
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, key)
            row = AlbumRow(key, album.display_name)
            row.settings_clicked.connect(self._open_album_settings)
            item.setSizeHint(row.sizeHint())
            self.album_list.addItem(item)
            self.album_list.setItemWidget(item, row)

    def _toggle_theme(self) -> None:
        new_theme = "dark" if self.config.settings.theme != "dark" else "light"
        self.config.settings.theme = new_theme
        self.config.save()
        application = QApplication.instance()
        if application is not None:
            apply_theme(application, new_theme)
        self._update_theme_button()

    def _update_theme_button(self) -> None:
        if self.config.settings.theme == "dark":
            self.theme_button.setText("☾")
        else:
            self.theme_button.setText("☀")

    def _open_album_settings(self, key: str) -> None:
        album = self.config.albums.get(key)
        if album is None:
            return
        dialog = AlbumSettingsDialog(album, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        album.display_name = dialog.display_name()
        album.output_folder = dialog.output_folder()
        album.output_format = dialog.output_format()
        self.config.save()
        self._refresh_albums()

    def _add_album(self) -> None:
        if self.backend is None:
            return
        dialog = PhoneFolderDialog(self.backend, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_path:
            return
        phone_path = dialog.selected_path
        suggested = phone_path.rstrip("/").split("/")[-1]
        display_name, confirmed = QInputDialog.getText(
            self, tr("album_name_title"), tr("album_name_prompt"), text=suggested
        )
        if not confirmed or not display_name.strip():
            return
        display_name = display_name.strip()
        output_folder = QFileDialog.getExistingDirectory(self, tr("pdf_folder"))
        if not output_folder:
            return
        key = self._make_album_key(display_name)
        self.config.add_album(key, display_name, phone_path, output_folder)
        self._refresh_albums()

    def _remove_album(self) -> None:
        item = self.album_list.currentItem()
        if item is None:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        album = self.config.albums.get(key)
        name = album.display_name if album is not None else key
        answer = QMessageBox.question(self, tr("remove_album"), tr("remove_album_q", name=name))
        if answer == QMessageBox.StandardButton.Yes:
            self.config.remove_album(key)
            self._refresh_albums()

    def _open_album_view(self, item: QListWidgetItem) -> None:
        if self.backend is None or self.is_offline:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        album = self.config.albums.get(key)
        if album is None:
            return
        try:
            view = AlbumView(album, self.backend, self.config)
        except DEVICE_ERRORS as error:
            self._handle_device_lost(tr("album_open_failed", error=error))
            return
        self.album_view = view
        self.album_view.back_requested.connect(self._close_album_view)
        self.album_view.convert_requested.connect(self._open_convert_dialog)
        self.album_view.device_lost.connect(self._handle_device_lost)
        self.stack.addWidget(self.album_view)
        self.stack.setCurrentWidget(self.album_view)

    def _handle_device_lost(self, message: str) -> None:
        QMessageBox.warning(self, tr("device_unavailable_title"), message)
        self._go_offline()

    def _close_album_view(self) -> None:
        if self.album_view is None:
            return
        self.album_view.stop()
        self.stack.setCurrentWidget(self.albums_page)
        self.stack.removeWidget(self.album_view)
        self.album_view.deleteLater()
        self.album_view = None

    def _open_convert_dialog(self, groups: object) -> None:
        if self.backend is None or self.album_view is None:
            return
        album = self.album_view.album
        photos_per_page = self.album_view.photos_per_page()
        saved_format = self.config.settings.output_format
        if album.output_format:
            self.config.settings.output_format = album.output_format
        try:
            dialog = ConvertDialog(
                groups, album, self.config, self.backend, self, photos_per_page=photos_per_page
            )
            dialog.exec()
        finally:
            self.config.settings.output_format = saved_format

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        dialog.exec()
        self._refresh_albums()

    def _make_album_key(self, display_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")
        if not slug:
            slug = "album"
        key = slug
        index = 2
        while key in self.config.albums:
            key = f"{slug}_{index}"
            index += 1
        return key


class AlbumRow(QWidget):
    settings_clicked = pyqtSignal(str)

    def __init__(self, key: str, display_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.key = key
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.addWidget(QLabel(display_name))
        layout.addStretch()
        settings_button = QPushButton("⚙")
        settings_button.setFixedWidth(32)
        settings_button.clicked.connect(lambda: self.settings_clicked.emit(self.key))
        layout.addWidget(settings_button)


class AlbumSettingsDialog(QDialog):
    def __init__(self, album: Album, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.album = album
        self.setWindowTitle(tr("album_settings_title"))
        self.resize(520, 220)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(album.display_name)
        form.addRow(tr("name_label"), self.name_edit)

        self.folder_edit = QLineEdit(album.output_folder)
        browse_button = QPushButton(tr("browse"))
        browse_button.clicked.connect(self._browse_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(browse_button)
        folder_container = QWidget()
        folder_container.setLayout(folder_row)
        form.addRow(tr("output_folder_label"), folder_container)

        self.format_edit = QLineEdit(album.output_format)
        self.format_edit.textChanged.connect(self._update_preview)
        self.preview_label = QLabel()
        format_box = QVBoxLayout()
        format_box.addWidget(self.format_edit)
        format_box.addWidget(self.preview_label)
        format_container = QWidget()
        format_container.setLayout(format_box)
        form.addRow(tr("name_template_label"), format_container)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_preview()

    def display_name(self) -> str:
        return self.name_edit.text().strip() or self.album.display_name

    def output_folder(self) -> str:
        return self.folder_edit.text().strip()

    def output_format(self) -> str:
        return self.format_edit.text().strip()

    def _browse_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("pdf_folder"))
        if directory:
            self.folder_edit.setText(directory)

    def _update_preview(self) -> None:
        template = self.format_edit.text().strip()
        if not template:
            self.preview_label.setText(tr("preview_uses_global"))
            return
        name = (
            template
            .replace("{predmet}", PREVIEW_PREDMET)
            .replace("{YYYYMMDD}", PREVIEW_DATE)
            .replace("{lection_number}", "001")
        )
        self.preview_label.setText(tr("preview_file", name=name))


class PhoneFolderDialog(QDialog):
    def __init__(self, backend: DeviceBackend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self.current_path = PHONE_ROOT
        self.selected_path: str | None = None
        self.setWindowTitle(tr("phone_folder_title"))
        self.resize(500, 400)

        layout = QVBoxLayout(self)
        self.path_label = QLabel(self.current_path)
        self.entry_list = QListWidget()
        self.entry_list.itemDoubleClicked.connect(self._enter_entry)

        nav_row = QHBoxLayout()
        up_button = QPushButton(tr("up"))
        up_button.clicked.connect(self._go_up)
        select_button = QPushButton(tr("select_this_folder"))
        select_button.clicked.connect(self._select_current)
        nav_row.addWidget(up_button)
        nav_row.addStretch()
        nav_row.addWidget(select_button)

        layout.addWidget(self.path_label)
        layout.addWidget(self.entry_list)
        layout.addLayout(nav_row)
        self._load_entries()

    def _load_entries(self) -> None:
        self.path_label.setText(self.current_path)
        self.entry_list.clear()
        try:
            entries = self.backend.list_dir(self.current_path)
        except Exception:
            entries = []
        for name in entries:
            self.entry_list.addItem(name)

    def _enter_entry(self, item: QListWidgetItem) -> None:
        self.current_path = f"{self.current_path.rstrip('/')}/{item.text()}"
        self._load_entries()

    def _go_up(self) -> None:
        parent = self.current_path.rstrip("/").rsplit("/", 1)[0]
        self.current_path = parent if parent else "/"
        self._load_entries()

    def _select_current(self) -> None:
        self.selected_path = self.current_path
        self.accept()
