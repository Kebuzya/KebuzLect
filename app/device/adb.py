from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from app.device import (
    AdbNotAvailableError,
    DeviceBackend,
    DeviceNotConnectedError,
    DeviceUnauthorizedError,
)

if TYPE_CHECKING:
    from app.config import AppConfig

DeviceStatus = Literal["authorized", "unauthorized", "no_device"]

ADB_EXECUTABLE = "adb.exe"


class AdbBackend(DeviceBackend):
    def __init__(self, config: "AppConfig | None" = None) -> None:
        self.config = config
        self.adb_path: Path | None = self._locate_adb()

    def is_available(self) -> bool:
        return self.adb_path is not None

    def get_device_status(self) -> DeviceStatus:
        self._run(["start-server"])
        result = self._run(["devices"])
        device_lines = [
            line.strip()
            for line in result.stdout.splitlines()[1:]
            if line.strip() and "\t" in line
        ]
        if not device_lines:
            return "no_device"
        for line in device_lines:
            _serial, state = line.split("\t", 1)
            state = state.strip()
            if state == "device":
                return "authorized"
            if state == "unauthorized":
                return "unauthorized"
        return "no_device"

    def list_dir(self, path: str) -> list[str]:
        self._ensure_connected()
        result = self._run(["shell", "ls", "-1", self._escape(path)])
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def pull_file(self, phone_path: str, local_path: Path) -> None:
        self._ensure_connected()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["pull", phone_path, str(local_path)])

    def delete_file(self, phone_path: str) -> None:
        self._ensure_connected()
        self._run(["shell", "rm", self._escape(phone_path)])

    def get_file_info(self, phone_path: str) -> tuple[int, int]:
        self._ensure_connected()
        result = self._run(["shell", "stat", "-c", "%s_%Y", self._escape(phone_path)])
        parts = result.stdout.strip().split("_")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])
        return self._size_from_ls(phone_path), 0

    def _size_from_ls(self, phone_path: str) -> int:
        result = self._run(["shell", "ls", "-l", self._escape(phone_path)])
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) >= 5 and fields[4].isdigit():
                return int(fields[4])
        return 0

    def _locate_adb(self) -> Path | None:
        from_path = shutil.which("adb")
        if from_path:
            return Path(from_path)

        for candidate in self._standard_locations():
            if candidate.is_file():
                return candidate

        configured = self._configured_path()
        if configured is not None and configured.is_file():
            return configured

        return None

    def _standard_locations(self) -> list[Path]:
        locations: list[Path] = []
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            locations.append(
                Path(local_app_data) / "Android" / "Sdk" / "platform-tools" / ADB_EXECUTABLE
            )
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)")
        if program_files_x86:
            locations.append(
                Path(program_files_x86) / "Android" / "android-sdk" / "platform-tools" / ADB_EXECUTABLE
            )
        locations.append(Path(sys.executable).resolve().parent / ADB_EXECUTABLE)
        return locations

    def _configured_path(self) -> Path | None:
        if self.config is None:
            return None
        configured = self.config.settings.adb_path
        if not configured:
            return None
        path = Path(configured)
        if path.is_dir():
            return path / ADB_EXECUTABLE
        return path

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        if self.adb_path is None:
            raise AdbNotAvailableError("adb.exe not found")
        command = [str(self.adb_path), *args]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    def _ensure_connected(self) -> None:
        status = self.get_device_status()
        if status == "no_device":
            raise DeviceNotConnectedError("No device connected")
        if status == "unauthorized":
            raise DeviceUnauthorizedError("Device is unauthorized")

    @staticmethod
    def _escape(path: str) -> str:
        return path.replace(" ", "\\ ")
