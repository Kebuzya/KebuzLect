from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

FUSION = "Fusion"


def apply_light(app: QApplication) -> None:
    app.setStyle(FUSION)
    app.setPalette(app.style().standardPalette())


def apply_dark(app: QApplication) -> None:
    app.setStyle(FUSION)

    window = QColor(45, 45, 48)
    base = QColor(30, 30, 32)
    alternate = QColor(53, 53, 56)
    text = QColor(220, 220, 220)
    disabled = QColor(120, 120, 120)
    accent = QColor(86, 122, 168)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, window)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, alternate)
    palette.setColor(QPalette.ColorRole.ToolTipBase, window)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, window)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(232, 96, 96))
    palette.setColor(QPalette.ColorRole.Link, accent)
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled)

    app.setPalette(palette)


def apply_theme(app: QApplication, theme: str) -> None:
    if theme == "dark":
        apply_dark(app)
    else:
        apply_light(app)
