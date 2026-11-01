"""Native image review interface; all edits pass through atomic dataset saves."""

import sys
from pathlib import Path

from PyQt5.QtCore import QLockFile, Qt
from PyQt5.QtGui import QImageReader, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QShortcut,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .canvas import AnnotationCanvas
from .dataset import Annotation, Dataset, DatasetError
from .i18n import Translator, choose_language
from .settings import read_state, write_state
from .styles import STYLESHEET


class ReviewWindow(QMainWindow):
    def __init__(self, dataset_root: Path, language: str | None = None):
        super().__init__()
        dataset_root = Path(dataset_root).expanduser().resolve()
        self._state_path = dataset_root / ".yolo_review" / "state.json"
        self._state = read_state(self._state_path)
        self.t = Translator(choose_language(language, self._state.get("language")))
        self.dataset = Dataset(dataset_root)
        if not self.dataset.images:
            raise DatasetError(Translator("en")("no_images"), Translator("zh")("no_images"))
        self._text_widgets = []
        self._save_key = "autosave_on"
        self._status_key = "status_default"
        self._status_values = {}
        self._error_info = None
        self.index = -1
        self.annotations = []
        self.revision = None
        self.undo_stack = []
        self.redo_stack = []
        self._shortcuts = []
        self._build_ui()
        self._setup_shortcuts()
        self._update_navigation_hints()
        self.load_image(self._resume_index())

    def _build_ui(self):
        self.resize(1480, 930)
        self.setMinimumSize(900, 600)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 14, 18, 10)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = self._text(QLabel(), "app_title")
        title.setObjectName("appTitle")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._text(QLabel(), "language"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("简体中文", "zh")
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.t.language))
        self.language_combo.currentIndexChanged.connect(self._change_language)
        header.addWidget(self.language_combo)
        self.save_label = QLabel(self.t("autosave_on"))
        self.save_label.setObjectName("saveState")
        header.addWidget(self.save_label)
        layout.addLayout(header)
        quick_start = self._text(QLabel(), "quick_start")
        quick_start.setObjectName("quickStart")
        quick_start.setWordWrap(True)
        layout.addWidget(quick_start)
        self.filename_label = QLabel()
        self.filename_label.setTextFormat(Qt.PlainText)
        self.filename_label.setObjectName("filename")
        self.filename_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.filename_label)
        self.error_label = QLabel()
        self.error_label.setTextFormat(Qt.PlainText)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("background: #653a32; color: #fff0e6; padding: 10px;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        splitter = QSplitter(Qt.Horizontal)
        self.canvas = AnnotationCanvas(translator=self.t)
        self.canvas.class_names = self.dataset.class_names
        self.canvas.boxDrawn.connect(self.add_box)
        splitter.addWidget(self.canvas)
        sidebar = QWidget()
        sidebar.setMinimumWidth(310)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 6, 0, 0)
        self.count_label = QLabel(self.t("boxes", count=0))
        self.count_label.setObjectName("sectionTitle")
        sidebar_layout.addWidget(self.count_label)
        self.box_list = QListWidget()
        self.box_list.setObjectName("boxList")
        self.box_list.setSpacing(5)
        self.box_list.currentRowChanged.connect(self._select_box)
        sidebar_layout.addWidget(self.box_list, 1)
        select_hint = self._text(QLabel(), "select_hint")
        select_hint.setWordWrap(True)
        sidebar_layout.addWidget(select_hint)
        sidebar_layout.addSpacing(8)
        sidebar_layout.addWidget(self._text(QLabel(), "new_class"))
        self.class_combo = QComboBox()
        for class_id, name in sorted(self.dataset.class_names.items()):
            name = name or self.t("class_name", id=class_id)
            self.class_combo.addItem(f"{class_id} · {name}", class_id)
        if self.class_combo.count() == 0:
            self.class_combo.addItem("0", 0)
        sidebar_layout.addWidget(self.class_combo)
        hint = self._text(QLabel(), "draw_help")
        hint.setWordWrap(True)
        hint.setObjectName("helpText")
        sidebar_layout.addWidget(hint)
        self.delete_button = self._text(QPushButton(), "delete")
        self.delete_button.clicked.connect(self.delete_selected)
        sidebar_layout.addWidget(self.delete_button)
        history = QHBoxLayout()
        self.undo_button = self._text(QPushButton(), "undo")
        self.undo_button.clicked.connect(self.undo)
        self.redo_button = self._text(QPushButton(), "redo")
        self.redo_button.setToolTip("Ctrl+Shift+Z / Ctrl+Y")
        self.redo_button.clicked.connect(self.redo)
        history.addWidget(self.undo_button)
        history.addWidget(self.redo_button)
        sidebar_layout.addLayout(history)
        splitter.addWidget(sidebar)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1140, 310])
        layout.addWidget(splitter, 1)

        navigation = QHBoxLayout()
        self.previous_button = self._text(QPushButton(), "previous")
        self.previous_button.clicked.connect(lambda: self.navigate(-1))
        self.next_button = self._text(QPushButton(), "next")
        self.next_button.clicked.connect(lambda: self.navigate(1))
        navigation.addWidget(self.previous_button)
        navigation.addWidget(self.next_button)
        navigation.addStretch()
        self.image_info = QLabel()
        navigation.addWidget(self.image_info)
        self.zoom_label = QLabel()
        self.zoom_label.setMinimumWidth(65)
        self.canvas.zoomChanged.connect(lambda factor: self.zoom_label.setText(f"{factor:.0%}"))
        navigation.addWidget(self.zoom_label)
        fit_button = self._text(QPushButton(), "fit")
        fit_button.clicked.connect(self.canvas.fit_image)
        navigation.addWidget(fit_button)
        navigation.addSpacing(12)
        navigation.addWidget(self._text(QLabel(), "jump"))
        self.jump_spin = QSpinBox()
        self.jump_spin.setRange(1, len(self.dataset.images))
        self.jump_spin.setKeyboardTracking(False)
        self.jump_spin.setFixedWidth(95)
        self.jump_spin.lineEdit().returnPressed.connect(self._jump)
        navigation.addWidget(self.jump_spin)
        jump_button = self._text(QPushButton(), "go")
        jump_button.clicked.connect(self._jump)
        navigation.addWidget(jump_button)
        self.progress_label = QLabel()
        navigation.addWidget(self.progress_label)
        layout.addLayout(navigation)
        self.setCentralWidget(container)
        self._set_status("status_default")
        self.setStyleSheet(STYLESHEET)

    def _setup_shortcuts(self):
        bindings = {
            "A": lambda: self.navigate(-1),
            "D": lambda: self.navigate(1),
            "Delete": self.delete_selected,
            "Ctrl+Z": self._shortcut_undo,
            "Ctrl+Shift+Z": self._shortcut_redo,
            "Ctrl+Y": self._shortcut_redo,
            "F": self.canvas.fit_image,
            "Escape": self._escape,
        }
        for key, callback in bindings.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setAutoRepeat(key in ("A", "D"))
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _text(self, widget, key: str):
        """Register a static widget label for live language changes."""
        self._text_widgets.append((widget, key))
        widget.setText(self.t(key))
        return widget

    def _set_save_state(self, key: str) -> None:
        self._save_key = key
        self.save_label.setText(self.t(key))

    def _set_status(self, key: str, **values) -> None:
        self._status_key = key
        self._status_values = values
        self.statusBar().showMessage(self.t(key, **values))

    def _update_navigation_hints(self) -> None:
        for button in (self.previous_button, self.next_button):
            button.setToolTip(self.t("hold_hint"))

    def _change_language(self, _index: int) -> None:
        """Translate the current view without reloading or rewriting labels."""
        self.t.language = self.language_combo.currentData()
        for widget, key in self._text_widgets:
            widget.setText(self.t(key))
        for index in range(self.class_combo.count()):
            class_id = self.class_combo.itemData(index)
            name = self.dataset.class_names.get(class_id) or self.t("class_name", id=class_id)
            self.class_combo.setItemText(index, f"{class_id} · {name}")
        self._set_save_state(self._save_key)
        self._set_status(self._status_key, **self._status_values)
        self._update_navigation_hints()
        image_path = self.dataset.images[self.index]
        self.setWindowTitle(f"{image_path.name} — {self.t('app_title')}")
        if self._error_info is not None:
            key, values = self._error_info
            self.error_label.setText(self.t(key, **values))
        scroll = self.box_list.verticalScrollBar().value()
        self._refresh_boxes(self.box_list.currentRow())
        self.box_list.verticalScrollBar().setValue(scroll)
        self.canvas.viewport().update()
        self._save_position()

    def _resume_index(self) -> int:
        relative = self._state.get("image")
        for i, image in enumerate(self.dataset.images):
            if image.relative_to(self.dataset.root / "images").as_posix() == relative:
                return i
        return 0

    def _save_position(self) -> None:
        try:
            self._state.update(
                {
                    "image": self.dataset.images[self.index]
                    .relative_to(self.dataset.root / "images")
                    .as_posix(),
                    "language": self.t.language,
                }
            )
            write_state(self._state_path, self._state)
        except OSError as error:
            self._set_status("position_failed", error=error)

    def load_image(self, index):
        if not 0 <= index < len(self.dataset.images):
            return
        self.canvas.cancel_drawing()
        self.index = index
        self.annotations = []
        self.revision = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.error_label.hide()
        self._error_info = None
        self._set_status("status_default")
        self._set_save_state("autosave_on")
        image_path = self.dataset.images[index]
        self.setWindowTitle(f"{image_path.name} — {self.t('app_title')}")
        self.filename_label.setText(str(image_path.relative_to(self.dataset.root)))
        self.filename_label.setToolTip(str(image_path))
        # Keep stored pixel orientation: YOLO coordinates use the source image axes.
        reader = QImageReader(str(image_path))
        reader.setAutoTransform(False)
        pixmap = QPixmap.fromImage(reader.read())
        self.canvas.set_image(pixmap)
        self.canvas.editable = False
        if pixmap.isNull():
            self._load_error("image_failed", error=reader.errorString())
        else:
            try:
                document = self.dataset.load(index)
                self.annotations = list(document.annotations)
                self.revision = document.revision
                self.canvas.editable = True
            except (DatasetError, OSError) as error:
                self._load_error("labels_failed", error=error)
        self.image_info.setText(f"{pixmap.width()} × {pixmap.height()}")
        self.previous_button.setEnabled(index > 0)
        self.next_button.setEnabled(index + 1 < len(self.dataset.images))
        self.jump_spin.setValue(index + 1)
        self.progress_label.setText(f"/ {len(self.dataset.images)}")
        self._refresh_boxes()
        self._save_position()

    def _load_error(self, key, **values):
        self._error_info = (key, values)
        self.error_label.setText(self.t(key, **values))
        self.error_label.show()
        self._set_save_state("readonly")

    def navigate(self, offset):
        self.load_image(self.index + offset)

    def _jump(self):
        self.jump_spin.interpretText()
        target = self.jump_spin.value() - 1
        if target != self.index:
            self.load_image(target)
        self.canvas.setFocus()

    def _refresh_boxes(self, selected=-1):
        self.box_list.blockSignals(True)
        self.box_list.clear()
        width, height = self.canvas.image_rect.width(), self.canvas.image_rect.height()
        for i, box in enumerate(self.annotations):
            name = self.dataset.class_names.get(box.class_id) or self.t(
                "class_name", id=box.class_id
            )
            detail = self.t(
                "box_detail",
                width=box.width * width,
                height=box.height * height,
                x=box.x * width,
                y=box.y * height,
            )
            item = QListWidgetItem(f"{i + 1:02d}   {name}\n{detail}")
            item.setToolTip(
                f"{box.class_id} {box.x:.6f} {box.y:.6f} {box.width:.6f} {box.height:.6f}"
            )
            self.box_list.addItem(item)
        self.box_list.setCurrentRow(selected)
        self.box_list.blockSignals(False)
        self.count_label.setText(self.t("boxes", count=len(self.annotations)))
        self.canvas.set_annotations(self.annotations, selected)
        self.delete_button.setEnabled(
            self.canvas.editable and 0 <= selected < len(self.annotations)
        )
        self.class_combo.setEnabled(self.canvas.editable)
        self.undo_button.setEnabled(bool(self.undo_stack) and self.canvas.editable)
        self.redo_button.setEnabled(bool(self.redo_stack) and self.canvas.editable)

    def _select_box(self, index):
        self.canvas.selected = index
        self.canvas.viewport().update()
        self.delete_button.setEnabled(self.canvas.editable and 0 <= index < len(self.annotations))

    def _commit(self, annotations, selected=-1, record_history=True):
        if not self.canvas.editable:
            return False
        self.canvas.cancel_drawing()
        self._set_save_state("saving")
        try:
            revision = self.dataset.save(self.index, annotations, self.revision)
        except (DatasetError, OSError) as error:
            self._set_save_state("save_failed")
            QMessageBox.warning(
                self, self.t("save_error_title"), self.t("save_error_body", error=error)
            )
            return False
        if record_history:
            self.undo_stack.append((list(self.annotations), self.box_list.currentRow()))
            self.redo_stack.clear()
        self.annotations = list(annotations)
        self.revision = revision
        self._refresh_boxes(selected)
        self._set_save_state("saved")
        self._set_status(
            "status_saved",
            filename=self.dataset.label_path(self.index).name,
            count=len(annotations),
        )
        return True

    def add_box(self, rect):
        width, height = self.canvas.image_rect.width(), self.canvas.image_rect.height()
        if not self.canvas.editable or width <= 0 or height <= 0:
            return
        box = Annotation(
            int(self.class_combo.currentData()),
            rect.center().x() / width,
            rect.center().y() / height,
            rect.width() / width,
            rect.height() / height,
        )
        self._commit(self.annotations + [box], len(self.annotations))

    def delete_selected(self):
        # Let Delete retain its normal text-editing behavior in the jump field.
        if self.jump_spin.hasFocus() or self.jump_spin.lineEdit().hasFocus():
            self.jump_spin.lineEdit().del_()
            return
        index = self.box_list.currentRow()
        if self.canvas.editable and 0 <= index < len(self.annotations):
            remaining = self.annotations[:index] + self.annotations[index + 1 :]
            self._commit(remaining, min(index, len(remaining) - 1))

    def _shortcut_undo(self):
        if self.jump_spin.hasFocus() or self.jump_spin.lineEdit().hasFocus():
            self.jump_spin.lineEdit().undo()
        else:
            self.undo()

    def _shortcut_redo(self):
        if self.jump_spin.hasFocus() or self.jump_spin.lineEdit().hasFocus():
            self.jump_spin.lineEdit().redo()
        else:
            self.redo()

    def undo(self):
        if not self.undo_stack or not self.canvas.editable:
            return
        annotations, selected = self.undo_stack[-1]
        previous = (list(self.annotations), self.box_list.currentRow())
        if self._commit(annotations, selected, record_history=False):
            self.undo_stack.pop()
            self.redo_stack.append(previous)
            self._refresh_boxes(selected)

    def redo(self):
        if not self.redo_stack or not self.canvas.editable:
            return
        annotations, selected = self.redo_stack[-1]
        previous = (list(self.annotations), self.box_list.currentRow())
        if self._commit(annotations, selected, record_history=False):
            self.redo_stack.pop()
            self.undo_stack.append(previous)
            self._refresh_boxes(selected)

    def _escape(self):
        self.canvas.cancel_drawing()
        self.box_list.setCurrentRow(-1)

    def closeEvent(self, event):
        self.canvas.cancel_drawing()
        self._save_position()
        super().closeEvent(event)


def run(dataset_root: Path, language: str | None = None) -> int:
    """Launch one review window; a process lock prevents duplicate editors."""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("YOLO Label Review")
    app.setStyle("Fusion")
    dataset_root = Path(dataset_root).expanduser().resolve()
    state_dir = dataset_root / ".yolo_review"
    preferences = read_state(state_dir / "state.json")
    translator = Translator(choose_language(language, preferences.get("language")))
    if not dataset_root.is_dir() or not (dataset_root / "images").is_dir():
        QMessageBox.critical(
            None, translator("open_error"), translator("missing_images", path=dataset_root)
        )
        return 1
    lock = None
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(state_dir / "review.lock"))
        lock.setStaleLockTime(0)
        if not lock.tryLock(100):
            QMessageBox.warning(None, translator("open_error"), translator("locked"))
            return 1
        window = ReviewWindow(dataset_root, language=translator.language)
        window.show()
        return app.exec_()
    except (DatasetError, OSError) as error:
        detail = (
            error.translated(translator.language) if isinstance(error, DatasetError) else str(error)
        )
        QMessageBox.critical(None, translator("open_error"), detail)
        return 1
    finally:
        if lock is not None:
            lock.unlock()
