from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class AdbNotAvailableError(Exception):
    pass


class DeviceNotConnectedError(Exception):
    pass


class DeviceUnauthorizedError(Exception):
    pass


class DeviceBackend(ABC):
    @abstractmethod
    def list_dir(self, path: str) -> list[str]:
        ...

    @abstractmethod
    def pull_file(self, phone_path: str, local_path: Path) -> None:
        ...

    @abstractmethod
    def delete_file(self, phone_path: str) -> None:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


def get_backend() -> DeviceBackend:
    from app.config import AppConfig
    from app.device.adb import AdbBackend

    config = AppConfig.load()
    adb = AdbBackend(config=config)
    if not adb.is_available():
        raise AdbNotAvailableError("adb.exe not found")

    status = adb.get_device_status()
    if status == "authorized":
        return adb
    if status == "unauthorized":
        raise DeviceUnauthorizedError("Device is unauthorized")
    raise DeviceNotConnectedError("No device connected")
