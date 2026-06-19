from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.config import AppConfig
from app.device import DeviceBackend
from app.models import Album, LectureGroup

PAGE_MARGIN = 20
PHOTO_GAP = 10
SLOT_WIDTH_PT = 555
SLOT_HEIGHT_PT = 396
MM_PER_PT = 25.4 / 72
INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def convert_lecture(
    group: LectureGroup,
    album: Album,
    config: AppConfig,
    backend: DeviceBackend,
    photos_per_page: int = 2,
) -> Path:
    temp_dir = Path(tempfile.mkdtemp())
    try:
        prepared_images = _download_and_prepare(group, config, backend, temp_dir)
        output_folder = Path(album.output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        output_path = output_folder / build_output_filename(group, album, config)
        _render_pdf(prepared_images, output_path, photos_per_page)
        return output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def build_output_filename(group: LectureGroup, album: Album, config: AppConfig) -> str:
    settings = config.settings
    number = group.lecture_number if group.lecture_number is not None else 0
    lection_number = str(number).zfill(settings.lection_number_width)
    name = (
        settings.output_format
        .replace("{predmet}", album.display_name)
        .replace("{YYYYMMDD}", group.date.replace("-", ""))
        .replace("{lection_number}", lection_number)
    )
    return f"{_sanitize(name)}.pdf"


def _download_and_prepare(
    group: LectureGroup,
    config: AppConfig,
    backend: DeviceBackend,
    temp_dir: Path,
) -> list[Path]:
    slot_pixels = _slot_pixels(config.settings.pdf_dpi)
    prepared: list[Path] = []
    for index, photo in enumerate(group.photos):
        source_path = temp_dir / f"src_{index}"
        backend.pull_file(photo.phone_path, source_path)
        with Image.open(source_path) as image:
            normalized = ImageOps.exif_transpose(image)
            if photo.rotation:
                normalized = normalized.rotate(-photo.rotation, expand=True)
            normalized.thumbnail(slot_pixels, Image.LANCZOS)
            prepared_path = temp_dir / f"img_{index}.jpg"
            normalized.convert("RGB").save(
                prepared_path, format="JPEG", quality=config.settings.jpeg_quality
            )
        prepared.append(prepared_path)
    return prepared


def _slot_pixels(dpi: int) -> tuple[int, int]:
    slot_w_mm = SLOT_WIDTH_PT * MM_PER_PT
    slot_h_mm = SLOT_HEIGHT_PT * MM_PER_PT
    px_w = int(slot_w_mm / 25.4 * dpi)
    px_h = int(slot_h_mm / 25.4 * dpi)
    return px_w, px_h


def _render_pdf(image_paths: list[Path], output_path: Path, photos_per_page: int) -> None:
    page_width, page_height = A4
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    usable_width = page_width - 2 * PAGE_MARGIN
    gap = PHOTO_GAP if photos_per_page > 1 else 0
    slot_height = (page_height - 2 * PAGE_MARGIN - gap * (photos_per_page - 1)) / photos_per_page

    if not image_paths:
        pdf.showPage()
        pdf.save()
        return

    for page_start in range(0, len(image_paths), photos_per_page):
        page_images = image_paths[page_start:page_start + photos_per_page]
        for slot_index, image_path in enumerate(page_images):
            slot_top = page_height - PAGE_MARGIN - slot_index * (slot_height + gap)
            _draw_image(pdf, image_path, PAGE_MARGIN, slot_top - slot_height, usable_width, slot_height)
        pdf.showPage()
    pdf.save()


def _draw_image(
    pdf: canvas.Canvas,
    image_path: Path,
    slot_x: float,
    slot_y: float,
    slot_width: float,
    slot_height: float,
) -> None:
    reader = ImageReader(str(image_path))
    image_width, image_height = reader.getSize()
    scale = min(slot_width / image_width, slot_height / image_height)
    draw_width = image_width * scale
    draw_height = image_height * scale
    offset_x = slot_x + (slot_width - draw_width) / 2
    offset_y = slot_y + (slot_height - draw_height) / 2
    pdf.drawImage(reader, offset_x, offset_y, draw_width, draw_height)


def _sanitize(name: str) -> str:
    return "".join("_" if char in INVALID_FILENAME_CHARS else char for char in name)
