from __future__ import annotations

import hashlib
import re

from app.device import DeviceBackend
from app.models import Album, LectureGroup, Photo

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
DATE_RUN = re.compile(r"\d{8}")


def scan_album(album: Album, backend: DeviceBackend) -> list[LectureGroup]:
    entries = backend.list_dir(album.phone_path)
    base_path = album.phone_path.rstrip("/")

    photos_by_date: dict[str, list[Photo]] = {}
    for name in entries:
        if not name.lower().endswith(IMAGE_EXTENSIONS):
            continue
        date = _extract_date(name)
        if date is None:
            continue
        photo = Photo(
            filename=name,
            phone_path=f"{base_path}/{name}",
            size=0,
            mtime=0,
        )
        photos_by_date.setdefault(date, []).append(photo)

    groups: list[LectureGroup] = []
    for date in sorted(photos_by_date):
        photos = sorted(photos_by_date[date], key=lambda photo: photo.filename)
        group_hash = compute_group_hash(photos)
        groups.append(
            LectureGroup(
                date=date,
                photos=photos,
                is_converted=group_hash in album.converted_hashes,
            )
        )
    return groups


def compute_group_hash(photos: list[Photo]) -> str:
    joined = "\n".join(sorted(photo.filename for photo in photos))
    return hashlib.md5(joined.encode("utf-8")).hexdigest()


def _extract_date(filename: str) -> str | None:
    for match in DATE_RUN.finditer(filename):
        candidate = match.group()
        month = int(candidate[4:6])
        day = int(candidate[6:8])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return candidate
    return None
