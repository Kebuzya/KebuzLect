[Русский](README.md) | [English](README_EN.md)

# KebuzLect

Desktop application that turns photos of lectures taken on an Android phone into clean PDF files.

Author: Kebuzya. License: MIT.

## What it is

KebuzLect connects to an Android phone over USB (via ADB), reads the folders where lecture photos are stored, groups the photos by day into lectures, lets you clean them up (rotate, drop blurry shots and duplicates, reorder) and exports each lecture as a PDF with one or two photos per A4 page.

It is built for a very specific but common workflow: you photograph the board during a lecture, one folder per subject, and you want each day's photos as one tidy PDF without doing it by hand.

## Why

- No manual copying over MTP and fighting Explorer glitches.
- One day of photos becomes one lecture PDF automatically.
- Already converted lectures are remembered, so you never redo work.
- Blurry shots and duplicates are flagged for you before export.
- Light and dark themes, plus a Russian and English interface.

## Requirements

- Windows 10 or later
- Python 3.11+ (uses the built-in `tomllib`)
- Android Platform Tools (ADB). The app helps you install and configure it on first run.
- An Android phone with USB debugging enabled

## Installation

```
git clone <repository-url>
cd KebuzLect
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` covers everything: PyQt6, Pillow, reportlab, tomli-w, numpy, imagehash and pywin32. Two of these are easy to miss because they are pulled in indirectly: `numpy` is required by the blur detector in `app/analyzer.py`, and `imagehash` is required by the duplicate detector (`find_duplicates`). Both must be installed for the album review screen to work.

## Usage

```
python main.py
```

On first launch:

1. If ADB is not found, the setup wizard opens. It links to the official Google Platform Tools download, lets you point to the folder containing `adb.exe` (the path is saved to the config), and explains how to enable USB debugging on the phone.
2. Connect the phone over USB and confirm the debugging prompt on the phone screen.
3. Add an album by browsing the phone folders directly inside the app.
4. Open an album to review photos grouped by date, then convert the lectures you want to PDF.

If the phone is not connected, the app runs in offline mode: cached data is shown but editing is disabled.

## Folder structure on the phone

Photos are expected under the gallery owner folder, one folder per subject:

```
/sdcard/Pictures/Gallery/owner/
├── CAD Lectures/
│   ├── IMG_20260413_135545.jpg
│   ├── IMG_20260413_135555.jpg
│   ├── IMG_20260420_135052.jpg
│   └── ...
├── DSP Lectures/
└── Electronics Lectures/
```

Photos can be in any folder on the phone, one folder per subject. The folder is picked through the in-app browser when adding an album. The following filename date formats are supported: IMG_YYYYMMDD_HHMMSS.jpg, YYYYMMDD_HHMMSS.jpg, 20260413_135545.jpg, and other common patterns with the date embedded in the name.

## Where data is stored

```
%APPDATA%\Kebuz\KebuzLect\
├── config.toml      configuration and albums
└── cache\           thumbnail cache
```

## Output filename template

The output filename is a template configured in settings:

| Token | Meaning |
|---|---|
| `{predmet}` | Album display name |
| `{YYYYMMDD}` | Lecture date |
| `{lection_number}` | Running lecture number, padded to a configurable width |

Examples:

- `{predmet}_{YYYYMMDD}` -> `CAD_20260413.pdf`
- `{predmet}_{lection_number}` -> `CAD_007.pdf`
- `{predmet}_{lection_number}_{YYYYMMDD}` -> `CAD_007_20260413.pdf`

## Project structure

```
KebuzLect/
├── main.py
├── requirements.txt
├── LICENSE
├── README.md
├── README_EN.md
├── KebuzLect.spec
├── resources/
│   └── icon.ico
├── app/
│   ├── config.py        config read/write (TOML, %APPDATA%)
│   ├── models.py        dataclass models (Album, LectureGroup, Photo)
│   ├── device/          device backends (ADB, win32com fallback)
│   ├── scanner.py       folder listing, grouping by date
│   ├── converter.py     PDF generation (ReportLab)
│   ├── thumbnail.py     thumbnail cache
│   └── analyzer.py      blur (Laplacian) and duplicate (pHash) detection
└── ui/
    ├── main_window.py
    ├── album_view.py
    ├── setup_wizard.py
    ├── settings_dialog.py
    ├── convert_dialog.py
    ├── theme.py
    └── i18n.py
```

## Notes

- Photos on the phone are never deleted automatically after conversion.
- Lecture numbering is running and not reset; deleting a lecture leaves a gap, and a "Renumber all" action is available.
- iOS is not supported in the first version. A plain computer folder can be used as a source for photos copied manually.

## Building a standalone .exe

The project ships with a PyInstaller spec that produces a single windowed executable with the app icon:

```
pip install pyinstaller
pyinstaller KebuzLect.spec
```

The result is `dist/KebuzLect.exe`. The `resources/` folder (icon) is bundled automatically.

## License

MIT. See [LICENSE](LICENSE).
