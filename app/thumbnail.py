from __future__ import annotations

import hashlib
from pathlib import Path

from app.config import AppConfig
from app.models import Photo

THUMBNAILS_DIRNAME = "thumbnails"


class ThumbnailCache:
    def __init__(self, config: AppConfig) -> None:
        self.directory = config.cache_dir / THUMBNAILS_DIRNAME
        self.directory.mkdir(parents=True, exist_ok=True)

    def get(self, photo: Photo) -> Path | None:
        path = self._path_for(photo)
        return path if path.exists() else None

    def store(self, photo: Photo, image_data: bytes) -> Path:
        path = self._path_for(photo)
        path.write_bytes(image_data)
        return path

    def clear(self) -> None:
        for entry in self.directory.iterdir():
            if entry.is_file():
                entry.unlink()

    def _path_for(self, photo: Photo) -> Path:
        raw = f"{photo.phone_path}{photo.mtime}{photo.size}".encode("utf-8")
        return self.directory / f"{hashlib.md5(raw).hexdigest()}.jpg"
