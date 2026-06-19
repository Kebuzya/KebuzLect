"""win32com Shell API device backend (Phase 2 stub).

Fallback used when ADB is unavailable. Availability is detected here; the
browse/pull/delete logic over MTP through the Windows Shell API arrives later.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.device import DeviceBackend

NOT_IMPLEMENTED_MESSAGE = "Shell backend not yet implemented"


class ShellBackend(DeviceBackend):
    def is_available(self) -> bool:
        return importlib.util.find_spec("win32com") is not None

    def list_dir(self, path: str) -> list[str]:
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    def pull_file(self, phone_path: str, local_path: Path) -> None:
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    def delete_file(self, phone_path: str) -> None:
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)
