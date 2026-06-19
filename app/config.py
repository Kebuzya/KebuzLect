from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

import tomli_w

from app.models import Album

APP_VENDOR = "Kebuz"
APP_NAME = "KebuzLect"
CONFIG_FILENAME = "config.toml"
CACHE_DIRNAME = "cache"


def get_app_data_dir() -> Path:
    roaming = os.environ.get("APPDATA")
    base = Path(roaming) if roaming else Path.home() / "AppData" / "Roaming"
    return base / APP_VENDOR / APP_NAME


def default_output_root() -> str:
    return (Path.home() / "Documents" / "Лекции").as_posix()


@dataclass
class Settings:
    output_format: str = "{predmet}_{YYYYMMDD}"
    jpeg_quality: int = 70
    default_output_root: str = field(default_factory=default_output_root)
    blur_threshold: int = 100
    duplicate_threshold: int = 10
    lection_number_width: int = 3
    pdf_dpi: int = 144
    adb_path: str = ""
    theme: str = "light"
    language: str = "ru"


@dataclass
class AppConfig:
    settings: Settings = field(default_factory=Settings)
    albums: dict[str, Album] = field(default_factory=dict)

    @property
    def config_dir(self) -> Path:
        return get_app_data_dir()

    @property
    def config_path(self) -> Path:
        return self.config_dir / CONFIG_FILENAME

    @property
    def cache_dir(self) -> Path:
        return self.config_dir / CACHE_DIRNAME

    @classmethod
    def load(cls) -> AppConfig:
        config = cls()
        config.cache_dir.mkdir(parents=True, exist_ok=True)
        if not config.config_path.exists():
            config.save()
            return config
        with config.config_path.open("rb") as config_file:
            data = tomllib.load(config_file)
        config.settings = cls._settings_from_dict(data.get("settings", {}))
        config.albums = cls._albums_from_dict(data.get("albums", {}))
        return config

    def save(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "settings": asdict(self.settings),
            "albums": {key: self._album_to_dict(album) for key, album in self.albums.items()},
        }
        with self.config_path.open("wb") as config_file:
            tomli_w.dump(data, config_file)

    def add_album(self, key: str, display_name: str, phone_path: str, output_folder: str) -> Album:
        album = Album(
            key=key,
            display_name=display_name,
            phone_path=phone_path,
            output_folder=output_folder,
        )
        self.albums[key] = album
        self.save()
        return album

    def remove_album(self, key: str) -> None:
        if key in self.albums:
            del self.albums[key]
            self.save()

    def mark_converted(self, album_key: str, group_hash: str) -> None:
        album = self.albums.get(album_key)
        if album is None:
            return
        if group_hash not in album.converted_hashes:
            album.converted_hashes.append(group_hash)
            self.save()

    @staticmethod
    def _settings_from_dict(data: dict[str, object]) -> Settings:
        defaults = Settings()
        return Settings(
            output_format=str(data.get("output_format", defaults.output_format)),
            jpeg_quality=int(data.get("jpeg_quality", defaults.jpeg_quality)),
            default_output_root=str(data.get("default_output_root", defaults.default_output_root)),
            blur_threshold=int(data.get("blur_threshold", defaults.blur_threshold)),
            duplicate_threshold=int(data.get("duplicate_threshold", defaults.duplicate_threshold)),
            lection_number_width=int(data.get("lection_number_width", defaults.lection_number_width)),
            pdf_dpi=int(data.get("pdf_dpi", defaults.pdf_dpi)),
            adb_path=str(data.get("adb_path", defaults.adb_path)),
            theme=str(data.get("theme", defaults.theme)),
            language=str(data.get("language", defaults.language)),
        )

    @staticmethod
    def _albums_from_dict(data: dict[str, dict[str, object]]) -> dict[str, Album]:
        albums: dict[str, Album] = {}
        for key, raw in data.items():
            albums[key] = Album(
                key=key,
                display_name=str(raw.get("display_name", key)),
                phone_path=str(raw.get("phone_path", "")),
                output_folder=str(raw.get("output_folder", "")),
                output_format=str(raw.get("output_format", "")),
                converted_hashes=[str(value) for value in raw.get("converted", [])],
            )
        return albums

    @staticmethod
    def _album_to_dict(album: Album) -> dict[str, object]:
        return {
            "phone_path": album.phone_path,
            "display_name": album.display_name,
            "output_folder": album.output_folder,
            "output_format": album.output_format,
            "converted": album.converted_hashes,
        }
