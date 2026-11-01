"""YOLO detection labels with conflict checks and recoverable atomic saves."""

import hashlib
import math
import os
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


class DatasetError(Exception):
    """An actionable dataset error suitable for showing in the review UI."""

    def __init__(self, english: str, chinese: str | None = None) -> None:
        super().__init__(english)
        self.english = english
        self.chinese = chinese if chinese is not None else english

    def translated(self, language: str) -> str:
        """Return localized text without binding the data layer to a GUI locale."""
        return self.chinese if language == "zh" else self.english


@dataclass(frozen=True)
class Annotation:
    """A normalized YOLO detection box in source-image coordinates."""

    class_id: int
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class Document:
    """Loaded labels and the revision needed for a conflict-checked save."""

    annotations: list[Annotation]
    revision: str | None
    label_path: Path


def _revision(content: bytes | None) -> str | None:
    return None if content is None else hashlib.sha256(content).hexdigest()


def _read_optional(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _validate(annotation: Annotation) -> None:
    if (
        isinstance(annotation.class_id, bool)
        or not isinstance(annotation.class_id, int)
        or annotation.class_id < 0
    ):
        raise DatasetError("Class IDs must be non-negative integers.", "类别编号必须是非负整数。")
    coordinates = (annotation.x, annotation.y, annotation.width, annotation.height)
    try:
        valid = all(math.isfinite(value) and 0 <= value <= 1 for value in coordinates)
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise DatasetError(
            "Box coordinates must be finite numbers between 0 and 1.",
            "框坐标必须是 0 到 1 之间的有限数值。",
        )
    if annotation.width <= 0 or annotation.height <= 0:
        raise DatasetError(
            "Box width and height must be greater than 0.", "标注框的宽度和高度必须大于 0。"
        )


def _atomic_write(path: Path, content: bytes) -> None:
    """Replace a file only after its complete contents have reached disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        descriptor, temporary = tempfile.mkstemp(
            prefix="." + path.name + ".", suffix=".tmp", dir=path.parent
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _natural_key(path: Path) -> tuple:
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part.casefold())
        for part in re.split(r"(\d+)", str(path))
    )


class Dataset:
    """Discover image/label pairs and preserve originals before saving edits."""

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        image_root = self.root / "images"
        if not image_root.is_dir():
            raise DatasetError(
                f"Image directory not found: {image_root}", f"找不到图片目录：{image_root}"
            )
        self.images = sorted(
            (
                path
                for path in image_root.rglob("*")
                if path.is_file() and path.suffix.lower() in self.IMAGE_EXTENSIONS
            ),
            key=lambda path: (_natural_key(path.relative_to(image_root)), str(path)),
        )
        label_paths = [path.relative_to(image_root).with_suffix(".txt") for path in self.images]
        if len(label_paths) != len(set(label_paths)):
            raise DatasetError(
                "Images in the same folder share a stem but have different extensions. "
                "They would share a label file; rename them first.",
                "存在同目录同名但扩展名不同的图片，会共用标签文件；请先重命名。",
            )
        classes_path = self.root / "classes.txt"
        try:
            lines = classes_path.read_text(encoding="utf-8-sig").splitlines()
        except FileNotFoundError:
            lines = []
        except UnicodeError as error:
            raise DatasetError(
                f"classes.txt is not a valid UTF-8 file: {error}",
                f"classes.txt 不是有效的 UTF-8 文件：{error}",
            ) from error
        self.class_names = {index: name.strip() for index, name in enumerate(lines)}
        if not self.class_names:
            self.class_names = {0: ""}

    def label_path(self, index: int) -> Path:
        if not isinstance(index, int) or not 0 <= index < len(self.images):
            raise DatasetError("Image index is out of range.", "图片序号超出范围。")
        relative = self.images[index].relative_to(self.root / "images")
        return self.root / "labels" / relative.with_suffix(".txt")

    def load(self, index: int) -> Document:
        """Read and validate a label file without changing any dataset files."""
        path = self.label_path(index)
        content = _read_optional(path)
        if content is None:
            return Document([], None, path)
        try:
            text = content.decode("utf-8-sig")
        except UnicodeError as error:
            raise DatasetError(
                f"{path.name} is not a valid UTF-8 label file.",
                f"{path.name} 不是有效的 UTF-8 标签文件。",
            ) from error
        annotations = []
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            fields = line.split()
            try:
                if len(fields) != 5:
                    raise DatasetError(
                        "Expected 5 columns: class, center x, center y, width, height.",
                        "需要 5 列：类别、中心 x、中心 y、宽度、高度。",
                    )
                if not re.fullmatch(r"\d+", fields[0]):
                    raise DatasetError(
                        "Class IDs must be non-negative integers.", "类别编号必须是非负整数。"
                    )
                annotation = Annotation(int(fields[0]), *(float(field) for field in fields[1:]))
                _validate(annotation)
            except (ValueError, DatasetError) as error:
                english_detail = (
                    error.translated("en") if isinstance(error, DatasetError) else str(error)
                )
                chinese_detail = (
                    error.translated("zh")
                    if isinstance(error, DatasetError)
                    else "坐标必须是数值。"
                )
                raise DatasetError(
                    f"Invalid labels in {path.name}, line {line_number}: {english_detail}",
                    f"{path.name} 第 {line_number} 行格式错误：{chinese_detail}",
                ) from error
            annotations.append(annotation)
        return Document(annotations, _revision(content), path)

    def _backup_once(self, path: Path, content: bytes | None) -> None:
        backup = (
            self.root
            / ".yolo_review"
            / "backups"
            / "labels"
            / path.relative_to(self.root / "labels")
        )
        missing_marker = backup.with_name(backup.name + ".missing")
        if backup.exists() or missing_marker.exists():
            return
        # The marker records that this image originally had no label file.
        if content is None:
            _atomic_write(missing_marker, b"Original label file did not exist.\n")
        else:
            _atomic_write(backup, content)

    def save(
        self, index: int, annotations: Iterable[Annotation], expected_revision: str | None
    ) -> str:
        """Back up originals and save labels unless another editor changed them."""
        path = self.label_path(index)
        annotations = list(annotations)
        for annotation in annotations:
            if not isinstance(annotation, Annotation):
                raise DatasetError(
                    "Only valid Annotation boxes can be saved.",
                    "只能保存有效的 Annotation 标注框。",
                )
            _validate(annotation)
        content = _read_optional(path)
        if _revision(content) != expected_revision:
            raise DatasetError(
                "Another application changed these labels. Navigate away and back to reload before editing.",
                "标签已被其他程序修改；请切换图片重新加载后再编辑。",
            )
        output = "".join(
            f"{box.class_id} {box.x:.10f} {box.y:.10f} {box.width:.10f} {box.height:.10f}\n"
            for box in annotations
        ).encode("utf-8")
        self._backup_once(path, content)
        # Catch edits made while the initial backup was being created.
        if _revision(_read_optional(path)) != expected_revision:
            raise DatasetError(
                "Another application changed these labels during saving. Please reload them.",
                "标签在保存期间被其他程序修改；请重新加载。",
            )
        _atomic_write(path, output)
        return hashlib.sha256(output).hexdigest()
