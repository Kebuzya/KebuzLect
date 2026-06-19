from __future__ import annotations

DEFAULT_LANGUAGE = "ru"

_current = DEFAULT_LANGUAGE

STRINGS: dict[str, dict[str, str]] = {
    "browse": {"ru": "Обзор", "en": "Browse"},
    "back": {"ru": "Назад", "en": "Back"},
    "next": {"ru": "Далее", "en": "Next"},
    "up": {"ru": "Вверх", "en": "Up"},
    "done_title": {"ru": "Готово", "en": "Done"},
    "error_title": {"ru": "Ошибка", "en": "Error"},

    "albums_label": {"ru": "Альбомы:", "en": "Albums:"},
    "add_album": {"ru": "Добавить альбом", "en": "Add album"},
    "remove_album": {"ru": "Удалить альбом", "en": "Remove album"},
    "settings": {"ru": "Настройки", "en": "Settings"},
    "connect": {"ru": "Подключиться", "en": "Connect"},
    "disconnect": {"ru": "Отключиться", "en": "Disconnect"},
    "status_offline": {"ru": "Офлайн: телефон не подключён", "en": "Offline: phone not connected"},
    "status_online": {"ru": "ADB: подключён", "en": "ADB: connected"},
    "unauthorized_title": {"ru": "Телефон не авторизован", "en": "Phone not authorized"},
    "unauthorized_body": {
        "ru": "Разрешите отладку на экране телефона.",
        "en": "Allow debugging on the phone screen.",
    },
    "device_unavailable_title": {"ru": "Устройство недоступно", "en": "Device unavailable"},
    "album_open_failed": {
        "ru": "Не удалось открыть альбом: {error}",
        "en": "Failed to open album: {error}",
    },
    "album_name_title": {"ru": "Название альбома", "en": "Album name"},
    "album_name_prompt": {"ru": "Отображаемое имя:", "en": "Display name:"},
    "pdf_folder": {"ru": "Папка для PDF", "en": "PDF folder"},
    "remove_album_q": {"ru": "Удалить альбом '{name}'?", "en": "Remove album '{name}'?"},
    "album_settings_title": {"ru": "Настройки альбома", "en": "Album settings"},
    "name_label": {"ru": "Название:", "en": "Name:"},
    "output_folder_label": {"ru": "Папка вывода:", "en": "Output folder:"},
    "name_template_label": {"ru": "Шаблон имени:", "en": "Name template:"},
    "preview_uses_global": {
        "ru": "Пример: используется общий шаблон из настроек",
        "en": "Example: the global template from settings is used",
    },
    "preview_file": {"ru": "Пример: {name}.pdf", "en": "Example: {name}.pdf"},
    "phone_folder_title": {"ru": "Выбор папки на телефоне", "en": "Select phone folder"},
    "select_this_folder": {"ru": "Выбрать эту папку", "en": "Select this folder"},

    "blur": {"ru": "Размытость", "en": "Blur"},
    "duplicates": {"ru": "Дубли", "en": "Duplicates"},
    "scale": {"ru": "Масштаб", "en": "Scale"},
    "photos_per_page_1": {"ru": "1 фото на странице", "en": "1 photo per page"},
    "photos_per_page_2": {"ru": "2 фото на странице", "en": "2 photos per page"},
    "convert_selected": {"ru": "Конвертировать выбранные", "en": "Convert selected"},
    "group_header": {"ru": "{date}  ({count} фото)", "en": "{date}  ({count} photos)"},
    "delete_photo_title": {"ru": "Удалить фото", "en": "Delete photo"},
    "delete_photo_q": {
        "ru": "Удалить '{name}' с телефона?",
        "en": "Delete '{name}' from the phone?",
    },
    "phone_disconnected": {"ru": "Телефон отключился: {error}", "en": "Phone disconnected: {error}"},
    "delete_failed": {
        "ru": "Не удалось удалить файл: {error}",
        "en": "Could not delete file: {error}",
    },

    "settings_title": {"ru": "Настройки", "en": "Settings"},
    "language_label": {"ru": "Язык:", "en": "Language:"},
    "jpeg_quality_label": {"ru": "Качество JPEG:", "en": "JPEG quality:"},
    "default_output_dialog": {"ru": "Папка вывода по умолчанию", "en": "Default output folder"},
    "blur_threshold_label": {"ru": "Порог размытости:", "en": "Blur threshold:"},
    "dup_threshold_label": {"ru": "Порог дублей:", "en": "Duplicate threshold:"},
    "number_width_label": {"ru": "Ширина номера:", "en": "Number width:"},
    "dpi_label": {"ru": "DPI (разрешение PDF):", "en": "DPI (PDF resolution):"},
    "adb_path_label": {"ru": "Путь к ADB:", "en": "ADB path:"},
    "reconfigure_adb": {"ru": "Перенастроить ADB", "en": "Reconfigure ADB"},
    "data_group": {"ru": "Данные", "en": "Data"},
    "clear_cache_btn": {"ru": "Очистить кеш миниатюр", "en": "Clear thumbnail cache"},
    "reset_converted_btn": {
        "ru": "Сбросить список сконвертированных",
        "en": "Reset converted list",
    },
    "delete_all_albums_btn": {"ru": "Удалить все альбомы", "en": "Delete all albums"},
    "cache_title": {"ru": "Кеш", "en": "Cache"},
    "cache_cleared": {"ru": "Кеш очищен", "en": "Cache cleared"},
    "converted_reset": {
        "ru": "Список сконвертированных сброшен",
        "en": "Converted list reset",
    },
    "delete_all_albums_q": {"ru": "Удалить все альбомы?", "en": "Delete all albums?"},
    "all_albums_deleted": {"ru": "Все альбомы удалены", "en": "All albums deleted"},

    "convert_title": {"ru": "Конвертация в PDF", "en": "Convert to PDF"},
    "album_line": {"ru": "Альбом: {name}", "en": "Album: {name}"},
    "convert_row": {
        "ru": "{date} - {count} фото -> {filename}",
        "en": "{date} - {count} photos -> {filename}",
    },
    "convert_btn": {"ru": "Конвертировать", "en": "Convert"},
    "open_folder_btn": {"ru": "Открыть папку", "en": "Open folder"},
    "convert_done": {"ru": "Готово. Создано файлов: {count}", "en": "Done. Files created: {count}"},
    "convert_error_title": {"ru": "Ошибка конвертации", "en": "Conversion error"},

    "adb_setup_title": {"ru": "Настройка ADB", "en": "ADB setup"},
    "wizard_intro": {
        "ru": "Для подключения телефона нужен ADB (Android Platform Tools). "
              "Скачайте архив, распакуйте его в любую папку и нажмите 'Далее'.",
        "en": "Connecting the phone needs ADB (Android Platform Tools). "
              "Download the archive, unpack it into any folder and press 'Next'.",
    },
    "download_platform_tools": {"ru": "Скачать Platform Tools", "en": "Download Platform Tools"},
    "locate_label": {
        "ru": "Укажите папку, в которую распакован Platform Tools (с файлом adb.exe):",
        "en": "Specify the folder where Platform Tools is unpacked (containing adb.exe):",
    },
    "specify_folder": {"ru": "Укажите папку.", "en": "Specify a folder."},
    "adb_not_in_folder": {
        "ru": "adb.exe не найден в этой папке.",
        "en": "adb.exe not found in this folder.",
    },
    "wizard_instruction": {
        "ru": "На телефоне: Настройки -> О телефоне -> 7 раз нажмите 'Номер сборки' -> "
              "вернитесь назад -> Для разработчиков -> включите 'Отладка по USB'. "
              "Подключите телефон кабелем и подтвердите запрос отладки на экране телефона.",
        "en": "On the phone: Settings -> About phone -> tap 'Build number' 7 times -> "
              "go back -> Developer options -> enable 'USB debugging'. "
              "Connect the cable and confirm the debugging prompt on the phone screen.",
    },
    "check_connection": {"ru": "Проверить подключение", "en": "Check connection"},
    "adb_folder_dialog": {"ru": "Папка с adb.exe", "en": "Folder with adb.exe"},
    "specify_adb_first": {
        "ru": "Сначала укажите папку с adb.exe.",
        "en": "Specify the adb.exe folder first.",
    },
    "adb_not_found_check": {
        "ru": "adb.exe не найден. Проверьте указанную папку.",
        "en": "adb.exe not found. Check the specified folder.",
    },
    "wizard_connected": {
        "ru": "Телефон подключён. ADB настроен.",
        "en": "Phone connected. ADB configured.",
    },
    "wizard_unauthorized": {
        "ru": "Телефон подключён, но не авторизован. "
              "Подтвердите запрос отладки на экране телефона.",
        "en": "Phone connected but not authorized. "
              "Confirm the debugging prompt on the phone screen.",
    },
    "wizard_no_device": {
        "ru": "Устройство не найдено. Подключите телефон и включите отладку по USB.",
        "en": "No device found. Connect the phone and enable USB debugging.",
    },
}


def set_language(language: str) -> None:
    global _current
    _current = language if language in ("ru", "en") else DEFAULT_LANGUAGE


def current_language() -> str:
    return _current


def tr(key: str, **kwargs: object) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        text = key
    else:
        text = entry.get(_current) or entry.get(DEFAULT_LANGUAGE) or key
    return text.format(**kwargs) if kwargs else text
