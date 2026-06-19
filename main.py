import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app.config import AppConfig
from ui.i18n import set_language
from ui.main_window import MainWindow
from ui.theme import apply_theme


def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parent
    return str(root / relative)


def main() -> int:
    config = AppConfig.load()
    set_language(config.settings.language)
    app = QApplication(sys.argv)
    app.setApplicationName("KebuzLect")
    app.setOrganizationName("Kebuz")
    app.setWindowIcon(QIcon(resource_path("resources/icon.ico")))
    apply_theme(app, config.settings.theme)
    window = MainWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
