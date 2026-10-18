"""User-managed font collection for the J.A.R.V.I.S. desktop interface.

Custom font files are copied into ./custom_fonts and their selected family is
saved locally in config/ui_settings.json. Custom font files/settings are not
committed to the repository.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
)

ROOT = Path(__file__).resolve().parent
CUSTOM_FONT_DIR = ROOT / "custom_fonts"
SETTINGS_FILE = ROOT / "config" / "ui_settings.json"
SUPPORTED_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
MAX_FONT_FILE_BYTES = 100 * 1024 * 1024
_DEFAULT_FAMILY = "Segoe UI"
_REGISTRATIONS: dict[str, tuple[int, tuple[str, ...]]] = {}


def ensure_custom_font_dir() -> Path:
    CUSTOM_FONT_DIR.mkdir(parents=True, exist_ok=True)
    return CUSTOM_FONT_DIR


def _load_settings() -> dict:
    try:
        value = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get_font_settings() -> dict:
    stored = _load_settings()
    family = str(stored.get("font_family") or _DEFAULT_FAMILY).strip() or _DEFAULT_FAMILY
    try:
        families = set(available_font_families())
        if family not in families:
            system_family = QFontDatabase.systemFont(
                QFontDatabase.SystemFont.GeneralFont
            ).family()
            family = system_family or _DEFAULT_FAMILY
    except Exception:
        family = family or _DEFAULT_FAMILY
    return {"font_family": family}


def save_font_settings(family: str) -> None:
    family = str(family or _DEFAULT_FAMILY).strip() or _DEFAULT_FAMILY
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    settings = _load_settings()
    settings["font_family"] = family
    temp_path = SETTINGS_FILE.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(SETTINGS_FILE)


def registered_families(path: str | Path) -> tuple[str, ...]:
    entry = _REGISTRATIONS.get(str(Path(path).resolve()))
    return entry[1] if entry else ()


def register_font_file(path: str | Path) -> tuple[str, ...]:
    """Register a TTF/OTF/TTC font with Qt and return its family names."""
    file_path = Path(path).resolve()
    if file_path.suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
        raise ValueError("Use a .ttf, .otf, or .ttc font file.")
    if not file_path.is_file():
        raise FileNotFoundError(f"Font file not found: {file_path}")
    if file_path.stat().st_size > MAX_FONT_FILE_BYTES:
        raise ValueError("That font file is larger than the 100 MB safety limit.")

    cache_key = str(file_path)
    cached = _REGISTRATIONS.get(cache_key)
    if cached:
        return cached[1]

    font_id = QFontDatabase.addApplicationFont(str(file_path))
    if font_id < 0:
        return ()
    families = tuple(str(f).strip() for f in QFontDatabase.applicationFontFamilies(font_id) if str(f).strip())
    if not families:
        QFontDatabase.removeApplicationFont(font_id)
        return ()
    _REGISTRATIONS[cache_key] = (font_id, families)
    return families


def load_custom_fonts() -> list[str]:
    """Load fonts already stored in the user's custom_fonts folder."""
    try:
        folder = ensure_custom_font_dir()
    except OSError:
        return []
    loaded: list[str] = []
    for path in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
            continue
        try:
            loaded.extend(register_font_file(path))
        except (OSError, ValueError):
            continue
    return sorted(set(loaded), key=str.casefold)


def available_font_families() -> list[str]:
    return sorted({str(name) for name in QFontDatabase().families()}, key=str.casefold)


def custom_font_files() -> list[Path]:
    try:
        folder = ensure_custom_font_dir()
        return sorted(
            (p for p in folder.iterdir()
             if p.is_file() and p.suffix.lower() in SUPPORTED_FONT_EXTENSIONS),
            key=lambda p: p.name.casefold(),
        )
    except OSError:
        return []


def _unique_destination(filename: str) -> Path:
    folder = ensure_custom_font_dir()
    original = Path(filename).name
    candidate = folder / original
    if not candidate.exists():
        return candidate
    stem, suffix = Path(original).stem, Path(original).suffix
    index = 2
    while True:
        candidate = folder / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def import_custom_font(source: str | Path) -> tuple[Path, tuple[str, ...]]:
    """Copy a user-selected font into custom_fonts and register it."""
    source_path = Path(source).expanduser().resolve()
    if source_path.suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
        raise ValueError("Select a .ttf, .otf, or .ttc font file.")
    if not source_path.is_file():
        raise FileNotFoundError("The selected font file no longer exists.")
    if source_path.stat().st_size > MAX_FONT_FILE_BYTES:
        raise ValueError("That font file is larger than the 100 MB safety limit.")

    folder = ensure_custom_font_dir().resolve()
    try:
        is_already_stored = source_path.parent.resolve() == folder
    except OSError:
        is_already_stored = False
    destination = source_path if is_already_stored else _unique_destination(source_path.name)
    if not is_already_stored:
        shutil.copy2(source_path, destination)

    families = register_font_file(destination)
    if not families:
        if not is_already_stored:
            destination.unlink(missing_ok=True)
        raise ValueError("Qt could not load this file as a supported font. The file was not kept.")
    return destination, families


def remove_custom_font(path: str | Path) -> None:
    """Remove only a font file inside this project's custom_fonts directory."""
    file_path = Path(path).resolve()
    folder = ensure_custom_font_dir().resolve()
    if file_path.parent != folder:
        raise ValueError("Only files inside the custom_fonts folder can be removed.")
    if file_path.suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
        raise ValueError("That is not a supported custom font file.")
    registration = _REGISTRATIONS.pop(str(file_path), None)
    if registration:
        QFontDatabase.removeApplicationFont(registration[0])
    file_path.unlink(missing_ok=True)


def apply_font_preferences(app, window, family: str) -> None:
    """Apply the chosen family to ordinary widgets; keep diagnostic text mono."""
    family = str(family or _DEFAULT_FAMILY).strip() or _DEFAULT_FAMILY
    app.setFont(QFont(family, 9))
    try:
        from ui_theme import polish_window
        polish_window(window, font_family=family)
    except Exception:
        pass
    try:
        window.update()
    except Exception:
        pass


class FontManagerDialog(QDialog):
    """Small font library manager with import, preview, save, and safe removal."""

    def __init__(self, app, window, parent=None):
        super().__init__(parent or window)
        self._app = app
        self._window = window
        self.setWindowTitle("J.A.R.V.I.S. — Font Collection")
        self.setMinimumSize(580, 500)
        self.resize(640, 560)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background: #0b1520; color: #c7e3eb; }
            QLabel { color: #c7e3eb; }
            QComboBox, QListWidget {
                color: #c7e3eb; background: #111e2c;
                border: 1px solid #304b60; border-radius: 5px; padding: 6px;
            }
            QPushButton {
                color: #c7e3eb; background: #111e2c;
                border: 1px solid #304b60; border-radius: 5px;
                padding: 7px 10px; min-height: 20px;
            }
            QPushButton:hover { background: #1a3547; border-color: #78d5ed; }
        """)

        load_custom_fonts()
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        title = QLabel("Aa   FONT COLLECTION")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #78d5ed;")
        root.addWidget(title)
        intro = QLabel(
            "Choose a font for the JARVIS controls, or import your own. "
            "Imported font files are copied into the local custom_fonts folder."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        row = QHBoxLayout()
        row.addWidget(QLabel("Interface font"))
        self._family = QComboBox()
        self._family.setMinimumHeight(34)
        self._family.setMaxVisibleItems(24)
        self._family.currentTextChanged.connect(self._update_preview)
        row.addWidget(self._family, 1)
        root.addLayout(row)

        self._preview = QLabel("J.A.R.V.I.S.   Systems online. 0123456789")
        self._preview.setMinimumHeight(68)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(
            "background: #111e2c; border: 1px solid #304b60; "
            "border-radius: 6px; padding: 10px; color: #e8f1f5;"
        )
        root.addWidget(self._preview)

        list_header = QHBoxLayout()
        list_header.addWidget(QLabel("Custom font files stored locally"))
        list_header.addStretch(1)
        self._refresh_button = QPushButton("Refresh")
        self._refresh_button.clicked.connect(self._refresh_files)
        list_header.addWidget(self._refresh_button)
        root.addLayout(list_header)

        self._files = QListWidget()
        self._files.setMinimumHeight(150)
        self._files.setToolTip("Select a file here to remove it from the custom font folder.")
        root.addWidget(self._files, 1)

        file_row = QHBoxLayout()
        import_button = QPushButton("＋ Import font…")
        import_button.clicked.connect(self._import_font)
        file_row.addWidget(import_button)
        open_folder_button = QPushButton("Open custom_fonts folder")
        open_folder_button.clicked.connect(self._open_folder)
        file_row.addWidget(open_folder_button)
        remove_button = QPushButton("Remove selected")
        remove_button.clicked.connect(self._remove_selected)
        file_row.addWidget(remove_button)
        root.addLayout(file_row)

        footer = QHBoxLayout()
        self._status = QLabel("")
        self._status.setWordWrap(True)
        footer.addWidget(self._status, 1)
        apply_button = QPushButton("Apply & Save")
        apply_button.setStyleSheet(
            "QPushButton { color: #0b1520; background: #78d5ed; "
            "border-color: #78d5ed; font-weight: 700; }"
            "QPushButton:hover { background: #a7e9f7; }"
        )
        apply_button.clicked.connect(self._apply)
        footer.addWidget(apply_button)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        footer.addWidget(close_button)
        root.addLayout(footer)

        self._populate_families(get_font_settings()["font_family"])
        self._refresh_files()

    def _populate_families(self, selected: str) -> None:
        selected = str(selected or _DEFAULT_FAMILY)
        families = available_font_families()
        self._family.blockSignals(True)
        self._family.clear()
        self._family.addItems(families)
        index = self._family.findText(selected, Qt.MatchFlag.MatchFixedString)
        if index < 0:
            self._family.addItem(selected)
            index = self._family.findText(selected, Qt.MatchFlag.MatchFixedString)
        self._family.setCurrentIndex(max(0, index))
        self._family.blockSignals(False)
        self._update_preview()

    def _update_preview(self, *_args) -> None:
        family = self._family.currentText().strip() or _DEFAULT_FAMILY
        self._preview.setFont(QFont(family, 14))
        self._preview.setText(
            f"{family}  |  J.A.R.V.I.S.   Systems online.   AaBbCc  0123456789"
        )

    def _refresh_files(self) -> None:
        self._files.clear()
        paths = custom_font_files()
        invalid = 0
        for path in paths:
            try:
                families = registered_families(path) or register_font_file(path)
                label = ", ".join(families) if families else f"Could not load: {path.stem}"
                if not families:
                    invalid += 1
            except (OSError, ValueError):
                label = f"Could not load: {path.stem}"
                invalid += 1
            item = QListWidgetItem(f"{label}   —   {path.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self._files.addItem(item)
        extra = f" {invalid} invalid file(s) ignored." if invalid else ""
        self._status.setText(
            f"{len(paths)} custom file(s). Folder: {CUSTOM_FONT_DIR}.{extra}"
        )

    def _import_font(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Import custom font",
            str(Path.home()),
            "Font files (*.ttf *.otf *.ttc);;All files (*.*)",
        )
        if not selected:
            return
        try:
            path, families = import_custom_font(selected)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Font import failed", str(exc))
            return
        self._populate_families(self._family.currentText())
        self._refresh_files()
        self._status.setText(f"Imported: {', '.join(families)}")
        self._window._log.append_log(f"SYS: Custom font imported — {path.name}")

    def _open_folder(self) -> None:
        try:
            folder = ensure_custom_font_dir()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        except OSError as exc:
            QMessageBox.warning(self, "Folder unavailable", str(exc))

    def _remove_selected(self) -> None:
        item = self._files.currentItem()
        if item is None:
            QMessageBox.information(self, "Font collection", "Select a custom font file first.")
            return
        path = Path(str(item.data(Qt.ItemDataRole.UserRole)))
        answer = QMessageBox.question(
            self, "Remove custom font",
            f"Delete {path.name} from the local custom_fonts folder?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            old_families = registered_families(path)
            remove_custom_font(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Could not remove font", str(exc))
            return
        current = self._family.currentText()
        if current in old_families:
            current = _DEFAULT_FAMILY
            try:
                save_font_settings(current)
                apply_font_preferences(self._app, self._window, current)
            except OSError:
                pass
        load_custom_fonts()
        self._populate_families(current)
        self._refresh_files()
        self._status.setText(f"Removed {path.name}.")

    def _apply(self) -> None:
        family = self._family.currentText().strip() or _DEFAULT_FAMILY
        try:
            save_font_settings(family)
            apply_font_preferences(self._app, self._window, family)
        except OSError as exc:
            QMessageBox.warning(self, "Could not save font preference", str(exc))
            return
        try:
            self._window._log.append_log(f"SYS: Interface font saved — {family}")
        except Exception:
            pass
        self.accept()


def install_font_menu(window, app) -> None:
    """Expose the manager in the main window's Appearance menu."""
    from PyQt6.QtGui import QAction

    menu = window.menuBar().addMenu("Appearance")
    font_action = QAction("Font collection…", window)
    font_action.setToolTip("Import custom fonts and choose the interface font.")
    font_action.triggered.connect(
        lambda _checked=False: _show_manager(window, app)
    )
    menu.addAction(font_action)
    menu.addSeparator()
    folder_action = QAction("Open custom_fonts folder", window)
    folder_action.triggered.connect(
        lambda _checked=False: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(ensure_custom_font_dir()))
        )
    )
    menu.addAction(folder_action)


def _show_manager(window, app) -> None:
    dialog = FontManagerDialog(app, window, parent=window)
    window._font_manager_dialog = dialog
    dialog.exec()
