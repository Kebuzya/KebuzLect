from __future__ import annotations

import io
import shutil
import tempfile
from collections import OrderedDict
from pathlib import Path

from PIL import Image, ImageOps
from PyQt6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QThread, QMimeData, pyqtSignal
from PyQt6.QtGui import QDrag, QPixmap, QTransform
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app import analyzer
from app.config import AppConfig
from app.device import (
    AdbNotAvailableError,
    DeviceBackend,
    DeviceNotConnectedError,
    DeviceUnauthorizedError,
)
from app.models import Album, LectureGroup, Photo
from app.scanner import scan_album
from app.thumbnail import ThumbnailCache
from ui.i18n import tr

DEVICE_ERRORS = (AdbNotAvailableError, DeviceNotConnectedError, DeviceUnauthorizedError)

THUMB_MIN = 80
THUMB_MAX = 300
THUMB_DEFAULT = 150
THUMB_BASE = (300, 400)
THUMB_QUALITY = 80
FULL_CACHE_SIZE = 5

COLOR_NEUTRAL = "#888888"
COLOR_BLURRY = "#e74c3c"
COLOR_DUPLICATE = "#f1c40f"
COLOR_ACTIVE = "#3498db"


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, spacing: int = 6) -> None:
        if parent is not None:
            super().__init__(parent)
        else:
            super().__init__()
        self._items: list = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.sizeHint())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0
        for item in self._items:
            width = item.sizeHint().width()
            height = item.sizeHint().height()
            next_x = x + width + self._spacing
            if next_x - self._spacing > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + self._spacing
                next_x = x + width + self._spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, height)
        return y + line_height - rect.y()


class ThumbnailWorker(QThread):
    thumbnail_ready = pyqtSignal(object)
    group_analyzed = pyqtSignal(object)

    def __init__(
        self,
        groups: list[LectureGroup],
        backend: DeviceBackend,
        cache: ThumbnailCache,
        blur_threshold: float,
        duplicate_threshold: int,
    ) -> None:
        super().__init__()
        self.groups = groups
        self.backend = backend
        self.cache = cache
        self.blur_threshold = blur_threshold
        self.duplicate_threshold = duplicate_threshold
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        for group in self.groups:
            for photo in group.photos:
                if self._cancelled:
                    return
                self._load_file_info(photo)
                thumb = self.cache.get(photo)
                if thumb is None:
                    thumb = self._create_thumbnail(photo)
                if thumb is not None:
                    photo.local_thumb = thumb
                    self.thumbnail_ready.emit(photo)
            if self._cancelled:
                return
            self._analyze_group(group)
            self.group_analyzed.emit(group)

    def _load_file_info(self, photo: Photo) -> None:
        try:
            size, mtime = self.backend.get_file_info(photo.phone_path)
            photo.size = size
            photo.mtime = mtime
        except Exception:
            pass

    def _create_thumbnail(self, photo: Photo) -> Path | None:
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            self.backend.pull_file(photo.phone_path, temp_path)
            with Image.open(temp_path) as image:
                normalized = ImageOps.exif_transpose(image)
                normalized.thumbnail(THUMB_BASE)
                buffer = io.BytesIO()
                normalized.convert("RGB").save(buffer, format="JPEG", quality=THUMB_QUALITY)
            return self.cache.store(photo, buffer.getvalue())
        except Exception:
            return None
        finally:
            temp_path.unlink(missing_ok=True)

    def _analyze_group(self, group: LectureGroup) -> None:
        for photo in group.photos:
            if photo.local_thumb is None:
                continue
            try:
                photo.is_blurry = analyzer.is_blurry(photo.local_thumb, self.blur_threshold)
            except Exception:
                photo.is_blurry = False
        for first, second in analyzer.find_duplicates(group.photos, self.duplicate_threshold):
            first.is_duplicate = True
            second.is_duplicate = True


class PreviewLoader(QThread):
    loaded = pyqtSignal(object, str)

    def __init__(self, photo: Photo, backend: DeviceBackend) -> None:
        super().__init__()
        self.photo = photo
        self.backend = backend

    def run(self) -> None:
        try:
            temp_dir = Path(tempfile.mkdtemp())
            target = temp_dir / "full"
            self.backend.pull_file(self.photo.phone_path, target)
            self.loaded.emit(self.photo, str(target))
        except Exception:
            pass


class ThumbnailTile(QFrame):
    def __init__(self, photo: Photo, view: "AlbumView") -> None:
        super().__init__()
        self.photo = photo
        self.view = view
        self._base: QPixmap | None = None
        self._aspect = 4 / 3
        self._width = view.thumb_size()
        self._press: QPoint | None = None
        self._maybe_click = False

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.check = QCheckBox()
        self.check.setChecked(view.is_checked(photo))
        self.check.toggled.connect(self._on_toggled)
        self.green = QLabel("✓")
        self.green.setStyleSheet("color: #2ecc71; font-weight: bold;")
        self.green.setVisible(view.group_of(photo).is_converted)

        grid = QGridLayout(self)
        grid.setContentsMargins(3, 3, 3, 3)
        grid.setSpacing(0)
        grid.addWidget(self.image_label, 0, 0)
        grid.addWidget(self.check, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self.green, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        if photo.local_thumb is not None:
            pixmap = QPixmap(str(photo.local_thumb))
            if not pixmap.isNull():
                self.set_thumb(pixmap)
        self.set_size(self._width)
        self.update_border()

    def set_thumb(self, pixmap: QPixmap) -> None:
        self._base = pixmap
        if pixmap.width() > 0:
            self._aspect = pixmap.height() / pixmap.width()
        self.set_size(self._width)

    def set_size(self, width: int) -> None:
        self._width = width
        height = int(width * self._aspect)
        self.setFixedSize(width, height)
        self._rescale()

    def is_checked(self) -> bool:
        return self.check.isChecked()

    def update_border(self) -> None:
        if self.photo.is_blurry:
            color = COLOR_BLURRY
        elif self.photo.is_duplicate:
            color = COLOR_DUPLICATE
        elif self.view.current_photo() is self.photo:
            color = COLOR_ACTIVE
        else:
            color = COLOR_NEUTRAL
        self.setStyleSheet(f"QFrame {{ border: 3px solid {color}; }}")

    def _rescale(self) -> None:
        if self._base is None:
            return
        pixmap = self._base
        if self.photo.rotation:
            pixmap = pixmap.transformed(QTransform().rotate(self.photo.rotation))
        target = QSize(self._width - 8, int(self._width * self._aspect) - 8)
        self.image_label.setPixmap(
            pixmap.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _on_toggled(self, checked: bool) -> None:
        self.view.set_checked(self.photo, checked)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position().toPoint()
            self._maybe_click = True

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._press is None:
            return
        moved = (event.position().toPoint() - self._press).manhattanLength()
        if moved < QApplication.startDragDistance():
            return
        self._maybe_click = False
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(str(id(self.photo)))
        drag.setMimeData(mime)
        if self.image_label.pixmap() is not None:
            drag.setPixmap(self.image_label.pixmap())
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event) -> None:
        if self._maybe_click and event.button() == Qt.MouseButton.LeftButton:
            self.view.select_photo(self.photo)
        self._maybe_click = False


class GroupSection(QWidget):
    def __init__(self, group: LectureGroup, view: "AlbumView") -> None:
        super().__init__()
        self.group = group
        self.view = view
        self.tiles: list[ThumbnailTile] = []
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.header_check = QCheckBox()
        self.header_check.setChecked(self._all_checked())
        self.header_check.toggled.connect(self._toggle_all)
        header.addWidget(self.header_check)
        title = tr("group_header", date=group.date, count=len(group.photos))
        if group.is_converted:
            title = f"{title}  ✓"
        header.addWidget(QLabel(title))
        header.addStretch()
        layout.addLayout(header)

        self.grid_container = QWidget()
        self.flow = FlowLayout(self.grid_container)
        for photo in group.photos:
            tile = ThumbnailTile(photo, view)
            self.tiles.append(tile)
            self.flow.addWidget(tile)
        layout.addWidget(self.grid_container)

    def _all_checked(self) -> bool:
        return all(self.view.is_checked(photo) for photo in self.group.photos)

    def _toggle_all(self, checked: bool) -> None:
        for tile in self.tiles:
            tile.check.setChecked(checked)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        photo = self.view.photo_by_token(event.mimeData().text())
        if photo is None:
            return
        position = self.grid_container.mapFrom(self, event.position().toPoint())
        self.view.move_photo(photo, self.group, self._drop_index(position))
        event.acceptProposedAction()

    def _drop_index(self, position: QPoint) -> int:
        for index, tile in enumerate(self.tiles):
            geometry = tile.geometry()
            if position.y() <= geometry.bottom() and position.x() <= geometry.center().x():
                return index
        return len(self.tiles)


class AlbumView(QWidget):
    back_requested = pyqtSignal()
    convert_requested = pyqtSignal(object)
    device_lost = pyqtSignal(str)

    def __init__(
        self,
        album: Album,
        backend: DeviceBackend,
        config: AppConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.album = album
        self.backend = backend
        self.config = config
        self.cache = ThumbnailCache(config)

        self._thumb_size = THUMB_DEFAULT
        self._checked: dict[int, bool] = {}
        self._current: Photo | None = None
        self._preview_base: QPixmap | None = None
        self._full_cache: "OrderedDict[str, QPixmap]" = OrderedDict()
        self._preview_loader: PreviewLoader | None = None
        self.worker: ThumbnailWorker | None = None
        self._sections: list[GroupSection] = []
        self._tiles: dict[int, ThumbnailTile] = {}
        self._group_of: dict[int, LectureGroup] = {}
        self._photo_by_token: dict[str, Photo] = {}
        self._flat: list[Photo] = []

        self.setWindowTitle(album.display_name)
        self.resize(1000, 700)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._build_ui()
        self.album.groups = scan_album(self.album, self.backend)
        self._build_sections()
        self._apply_zoom_all()
        self._start_worker()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_settings_panel())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left_column())
        splitter.addWidget(self._build_preview_pane())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(THUMB_MIN, THUMB_MAX)
        self.zoom_slider.setValue(self._thumb_size)
        self.zoom_slider.setFixedWidth(200)
        self.zoom_slider.valueChanged.connect(self._on_zoom)
        bottom.addWidget(QLabel(tr("scale")))
        bottom.addWidget(self.zoom_slider)
        bottom.addStretch()
        convert_button = QPushButton(tr("convert_selected"))
        convert_button.clicked.connect(self._convert_selected)
        bottom.addWidget(convert_button)
        layout.addLayout(bottom)

    def _build_settings_panel(self) -> QWidget:
        panel = QWidget()
        row = QHBoxLayout(panel)
        back_button = QPushButton(tr("back"))
        back_button.clicked.connect(self.back_requested.emit)
        row.addWidget(back_button)

        settings = self.config.settings
        self.blur_slider, self.blur_value = self._make_slider(10, 500, settings.blur_threshold)
        self.blur_slider.valueChanged.connect(self._on_blur_changed)
        row.addWidget(QLabel(tr("blur")))
        row.addWidget(self.blur_slider)
        row.addWidget(self.blur_value)

        self.dup_slider, self.dup_value = self._make_slider(0, 20, settings.duplicate_threshold)
        self.dup_slider.valueChanged.connect(self._on_duplicate_changed)
        row.addWidget(QLabel(tr("duplicates")))
        row.addWidget(self.dup_slider)
        row.addWidget(self.dup_value)

        self.quality_slider, self.quality_value = self._make_slider(50, 95, settings.jpeg_quality)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        row.addWidget(QLabel("JPEG"))
        row.addWidget(self.quality_slider)
        row.addWidget(self.quality_value)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 300)
        self.dpi_spin.setSingleStep(12)
        self.dpi_spin.setValue(settings.pdf_dpi)
        self.dpi_spin.valueChanged.connect(self._on_dpi_changed)
        row.addWidget(QLabel("DPI"))
        row.addWidget(self.dpi_spin)

        self.photos_per_page_combo = QComboBox()
        self.photos_per_page_combo.addItem(tr("photos_per_page_1"), 1)
        self.photos_per_page_combo.addItem(tr("photos_per_page_2"), 2)
        self.photos_per_page_combo.setCurrentIndex(1)
        row.addWidget(self.photos_per_page_combo)

        row.addStretch()
        return panel

    def photos_per_page(self) -> int:
        return self.photos_per_page_combo.currentData()

    def _make_slider(self, minimum: int, maximum: int, value: int) -> tuple[QSlider, QLabel]:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.setFixedWidth(120)
        label = QLabel(str(value))
        return slider, label

    def _build_left_column(self) -> QWidget:
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumWidth(150)
        self.groups_container = QWidget()
        self.groups_layout = QVBoxLayout(self.groups_container)
        self.scroll.setWidget(self.groups_container)
        self.scroll.viewport().installEventFilter(self)
        return self.scroll

    def _build_preview_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        self.date_label = QLabel("")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.date_label)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setMinimumSize(200, 200)
        layout.addWidget(self.preview_label, 1)

        controls = QHBoxLayout()
        controls.addStretch()
        for symbol, handler in (
            ("‹", lambda: self._navigate(-1)),
            ("⟲", lambda: self._rotate(-90)),
            ("⟳", lambda: self._rotate(90)),
            ("✕", self._delete_current),
            ("›", lambda: self._navigate(1)),
        ):
            button = QPushButton(symbol)
            button.setFixedWidth(44)
            button.clicked.connect(handler)
            controls.addWidget(button)
        controls.addStretch()
        layout.addLayout(controls)
        return pane

    def thumb_size(self) -> int:
        return self._thumb_size

    def is_checked(self, photo: Photo) -> bool:
        return self._checked.get(id(photo), True)

    def set_checked(self, photo: Photo, checked: bool) -> None:
        self._checked[id(photo)] = checked

    def group_of(self, photo: Photo) -> LectureGroup:
        return self._group_of[id(photo)]

    def current_photo(self) -> Photo | None:
        return self._current

    def photo_by_token(self, token: str) -> Photo | None:
        return self._photo_by_token.get(token)

    def select_photo(self, photo: Photo) -> None:
        self.setFocus()
        self._set_current(photo)

    def _build_sections(self) -> None:
        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._sections = []
        self._tiles = {}
        self._group_of = {
            id(photo): group for group in self.album.groups for photo in group.photos
        }
        self._photo_by_token = {
            str(id(photo)): photo for group in self.album.groups for photo in group.photos
        }
        for group in self.album.groups:
            section = GroupSection(group, self)
            self._sections.append(section)
            for tile in section.tiles:
                self._tiles[id(tile.photo)] = tile
            self.groups_layout.addWidget(section)
        self.groups_layout.addStretch()
        self._flat = [photo for section in self._sections for photo in section.group.photos]

    def _start_worker(self) -> None:
        self.worker = ThumbnailWorker(
            self.album.groups,
            self.backend,
            self.cache,
            float(self.config.settings.blur_threshold),
            self.config.settings.duplicate_threshold,
        )
        self.worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.worker.group_analyzed.connect(self._on_group_analyzed)
        self.worker.start()

    def _on_thumbnail_ready(self, photo: Photo) -> None:
        tile = self._tiles.get(id(photo))
        if tile is None or photo.local_thumb is None:
            return
        pixmap = QPixmap(str(photo.local_thumb))
        if not pixmap.isNull():
            tile.set_thumb(pixmap)

    def _on_group_analyzed(self, group: LectureGroup) -> None:
        for photo in group.photos:
            tile = self._tiles.get(id(photo))
            if tile is not None:
                tile.update_border()

    def _on_blur_changed(self, value: int) -> None:
        self.blur_value.setText(str(value))
        self.config.settings.blur_threshold = value
        self._recompute_blur()

    def _on_duplicate_changed(self, value: int) -> None:
        self.dup_value.setText(str(value))
        self.config.settings.duplicate_threshold = value
        self._recompute_duplicates()

    def _on_quality_changed(self, value: int) -> None:
        self.quality_value.setText(str(value))
        self.config.settings.jpeg_quality = value

    def _on_dpi_changed(self, value: int) -> None:
        self.config.settings.pdf_dpi = value

    def _recompute_blur(self) -> None:
        threshold = self.config.settings.blur_threshold
        for photo in self._flat:
            if photo.local_thumb is None:
                continue
            try:
                photo.is_blurry = analyzer.is_blurry(photo.local_thumb, threshold)
            except Exception:
                photo.is_blurry = False
        self._refresh_borders()

    def _recompute_duplicates(self) -> None:
        threshold = self.config.settings.duplicate_threshold
        for photo in self._flat:
            photo.is_duplicate = False
        for section in self._sections:
            for first, second in analyzer.find_duplicates(section.group.photos, threshold):
                first.is_duplicate = True
                second.is_duplicate = True
        self._refresh_borders()

    def _refresh_borders(self) -> None:
        for tile in self._tiles.values():
            tile.update_border()

    def _on_zoom(self, value: int) -> None:
        self._thumb_size = value
        self._apply_zoom_all()

    def _apply_zoom_all(self) -> None:
        for tile in self._tiles.values():
            tile.set_size(self._thumb_size)

    def _set_current(self, photo: Photo, scroll: bool = True, load: bool = True) -> None:
        previous = self._current
        self._current = photo
        if previous is not None and id(previous) in self._tiles:
            self._tiles[id(previous)].update_border()
        active_tile = self._tiles.get(id(photo))
        if active_tile is not None:
            active_tile.update_border()
        group = self._group_of.get(id(photo))
        self.date_label.setText(group.date if group is not None else "")
        self._show_preview(photo, load)
        if scroll and active_tile is not None:
            self.scroll.ensureWidgetVisible(active_tile)

    def _show_preview(self, photo: Photo, load: bool) -> None:
        base = self._full_cache.get(photo.phone_path)
        if base is None and photo.local_thumb is not None:
            base = QPixmap(str(photo.local_thumb))
        self._preview_base = base
        self._render_preview()
        if load and photo.phone_path not in self._full_cache:
            self._start_preview_loader(photo)

    def _start_preview_loader(self, photo: Photo) -> None:
        loader = PreviewLoader(photo, self.backend)
        loader.loaded.connect(self._on_full_loaded)
        self._preview_loader = loader
        loader.start()

    def _on_full_loaded(self, photo: Photo, path: str) -> None:
        pixmap = QPixmap(path)
        shutil.rmtree(Path(path).parent, ignore_errors=True)
        if pixmap.isNull():
            return
        self._full_cache[photo.phone_path] = pixmap
        self._full_cache.move_to_end(photo.phone_path)
        while len(self._full_cache) > FULL_CACHE_SIZE:
            self._full_cache.popitem(last=False)
        if self._current is photo:
            self._preview_base = pixmap
            self._render_preview()

    def _render_preview(self) -> None:
        if self._preview_base is None or self._preview_base.isNull():
            self.preview_label.clear()
            return
        pixmap = self._preview_base
        if self._current is not None and self._current.rotation:
            pixmap = pixmap.transformed(QTransform().rotate(self._current.rotation))
        self.preview_label.setPixmap(
            pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _navigate(self, step: int) -> None:
        self.setFocus()
        if not self._flat:
            return
        if self._current is None:
            self._set_current(self._flat[0])
            return
        index = next((i for i, photo in enumerate(self._flat) if photo is self._current), 0)
        index = max(0, min(len(self._flat) - 1, index + step))
        self._set_current(self._flat[index])

    def _rotate(self, degrees: int) -> None:
        if self._current is None:
            return
        self._current.rotation = (self._current.rotation + degrees) % 360
        self._render_preview()
        tile = self._tiles.get(id(self._current))
        if tile is not None:
            tile._rescale()

    def _delete_current(self) -> None:
        photo = self._current
        if photo is None:
            return
        answer = QMessageBox.question(
            self, tr("delete_photo_title"), tr("delete_photo_q", name=photo.filename)
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.backend.delete_file(photo.phone_path)
        except DEVICE_ERRORS as error:
            self.device_lost.emit(tr("phone_disconnected", error=error))
            return
        except Exception as error:
            QMessageBox.warning(self, tr("error_title"), tr("delete_failed", error=error))
            return
        index = next((i for i, item in enumerate(self._flat) if item is photo), -1)
        group = self._group_of.get(id(photo))
        if group is not None and photo in group.photos:
            group.photos.remove(photo)
        self._checked.pop(id(photo), None)
        self._current = None
        self._build_sections()
        self._apply_zoom_all()
        if self._flat:
            new_index = max(0, min(index, len(self._flat) - 1))
            self._set_current(self._flat[new_index])
        else:
            self._preview_base = None
            self.preview_label.clear()

    def move_photo(self, photo: Photo, target_group: LectureGroup, target_index: int) -> None:
        source_group = self._group_of.get(id(photo))
        if source_group is None or photo not in source_group.photos:
            return
        same_group = source_group is target_group
        old_index = source_group.photos.index(photo)
        insert_index = max(0, min(target_index, len(target_group.photos)))
        if same_group and insert_index in (old_index, old_index + 1):
            return
        source_group.photos.remove(photo)
        if same_group and old_index < insert_index:
            insert_index -= 1
        insert_index = max(0, min(insert_index, len(target_group.photos)))
        target_group.photos.insert(insert_index, photo)
        keep = self._current
        self._build_sections()
        self._apply_zoom_all()
        if keep is not None and id(keep) in self._tiles:
            self._set_current(keep, scroll=True, load=False)

    def _convert_selected(self) -> None:
        filtered: list[LectureGroup] = []
        for section in self._sections:
            photos = [tile.photo for tile in section.tiles if tile.is_checked()]
            if photos:
                filtered.append(
                    LectureGroup(
                        date=section.group.date,
                        photos=photos,
                        is_converted=section.group.is_converted,
                        lecture_number=section.group.lecture_number,
                    )
                )
        if filtered:
            self.convert_requested.emit(filtered)

    def eventFilter(self, source, event) -> bool:
        if event.type() == QEvent.Type.Wheel and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            step = 10 if event.angleDelta().y() > 0 else -10
            new_size = max(THUMB_MIN, min(THUMB_MAX, self._thumb_size + step))
            self.zoom_slider.setValue(new_size)
            return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Left:
            self._navigate(-1)
        elif event.key() == Qt.Key.Key_Right:
            self._navigate(1)
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._delete_current()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.setFocus()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_preview()

    def stop(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.worker.wait()
        if self._preview_loader is not None and self._preview_loader.isRunning():
            self._preview_loader.wait()

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)
