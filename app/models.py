from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Photo:
    filename: str
    phone_path: str
    size: int
    mtime: int
    local_thumb: Path | None = None
    is_blurry: bool = False
    is_duplicate: bool = False
    rotation: int = 0


@dataclass
class LectureGroup:
    date: str
    photos: list[Photo]
    is_converted: bool = False
    lecture_number: int | None = None


@dataclass
class Album:
    key: str
    display_name: str
    phone_path: str
    output_folder: str
    output_format: str = ""
    groups: list[LectureGroup] = field(default_factory=list)
    converted_hashes: list[str] = field(default_factory=list)
