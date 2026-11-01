"""Small, explicit English and Simplified Chinese message catalog.

Dataset class names are user data and are intentionally never translated.
"""

import locale
import os
from dataclasses import dataclass

MESSAGES = {
    "en": {
        "app_title": "YOLO Label Review",
        "autosave_on": "Autosave enabled",
        "saving": "Saving…",
        "saved": "✓ Saved automatically",
        "save_failed": "Save failed · Change not applied",
        "readonly": "Editing disabled for this image",
        "boxes": "Boxes · {count}",
        "select_hint": "Select a row to highlight its box · Delete to remove",
        "new_class": "Class for new boxes",
        "class_name": "Class {id}",
        "draw_help": "Hold the left mouse button and drag to add a box.\nYou can start inside an existing box.\n\nMouse wheel: zoom\nMiddle button + drag: pan\nF: fit image\nEsc: cancel drawing / selection",
        "delete": "Delete selected  ·  Del",
        "undo": "Undo  Ctrl+Z",
        "redo": "Redo",
        "previous": "← Previous  A",
        "next": "Next  D →",
        "hold_hint": "Hold A / D to browse continuously; release to stop.",
        "fit": "Fit image  F",
        "jump": "Jump to",
        "go": "Go",
        "status_default": "Every edit is saved to labels · Originals are backed up before the first edit",
        "new_box": "New  {width:.0f} × {height:.0f}",
        "box_detail": "{width:.0f} × {height:.0f} px  ·  Center ({x:.0f}, {y:.0f})",
        "position_failed": "Could not save review position: {error}",
        "image_failed": "Cannot read image: {error}. You can continue to the next image.",
        "labels_failed": "Cannot read labels; editing is disabled for this image: {error}",
        "save_error_title": "Save failed",
        "save_error_body": "{error}\n\nThis change was not applied. Resolve the error and retry. If another application changed the labels, navigate away and back to reload them.",
        "status_saved": "Saved: {filename}  ·  {count} boxes",
        "open_error": "Cannot open dataset",
        "missing_images": "The dataset has no images folder:\n{path}",
        "no_images": "No supported images were found in the images folder.",
        "locked": "This dataset is already open in another review window, or its review state folder is not writable.",
        "language": "Language / 语言",
    },
    "zh": {
        "app_title": "YOLO 标注审核",
        "autosave_on": "自动保存已开启",
        "saving": "正在保存…",
        "saved": "✓ 已自动保存",
        "save_failed": "保存失败 · 修改未应用",
        "readonly": "当前图片不可编辑",
        "boxes": "标注框 · {count}",
        "select_hint": "点击条目高亮对应框 · Delete 删除",
        "new_class": "新增框类别",
        "class_name": "类别 {id}",
        "draw_help": "直接按住鼠标左键拖动，松开即新增。\n框内也可起笔，方便补充重叠目标。\n\n滚轮：缩放图片\n中键拖动：平移图片\nF：适应窗口\nEsc：取消绘制 / 取消选择",
        "delete": "删除选中框  ·  Del",
        "undo": "撤销  Ctrl+Z",
        "redo": "重做",
        "previous": "← 上一张  A",
        "next": "下一张  D →",
        "hold_hint": "长按 A / D 连续切图，松开停止。",
        "fit": "适应窗口  F",
        "jump": "跳转",
        "go": "前往",
        "status_default": "每次修改立即写入 labels · 首次修改前自动备份原标签",
        "new_box": "新增  {width:.0f} × {height:.0f}",
        "box_detail": "{width:.0f} × {height:.0f} px  ·  中心 ({x:.0f}, {y:.0f})",
        "position_failed": "审核位置未保存：{error}",
        "image_failed": "图片无法读取：{error}。可继续切换下一张。",
        "labels_failed": "标注读取失败，当前图片暂停编辑：{error}",
        "save_error_title": "保存失败",
        "save_error_body": "{error}\n\n本次修改未应用。请处理错误后重试；外部修改标签后需切图重新加载。",
        "status_saved": "已保存：{filename}  ·  {count} 个框",
        "open_error": "无法打开数据集",
        "missing_images": "数据集目录中没有 images 文件夹：\n{path}",
        "no_images": "images 目录中没有找到可支持的图片。",
        "locked": "此数据集已在另一审核窗口中打开，或审核状态目录不可写。",
        "language": "Language / 语言",
    },
}


def system_language() -> str:
    """Use Simplified Chinese for Chinese locales, English otherwise."""
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name)
        if value:
            return "zh" if value.lower().startswith("zh") else "en"
    try:
        value = locale.getlocale()[0] or "en"
    except (ValueError, TypeError):
        value = "en"
    return "zh" if value.lower().startswith("zh") else "en"


def choose_language(requested: str | None, saved: str | None = None) -> str:
    """Explicit CLI choice takes precedence over saved and system preferences."""
    if isinstance(requested, str) and requested in MESSAGES:
        return requested
    if isinstance(saved, str) and saved in MESSAGES:
        return saved
    return system_language()


@dataclass
class Translator:
    """A window-scoped translator, safe to change without reloading data."""

    language: str = "en"

    def __post_init__(self) -> None:
        if self.language not in MESSAGES:
            raise ValueError(f"Unsupported language: {self.language}")

    def __call__(self, key: str, **values: object) -> str:
        localized = {
            name: value.translated(self.language) if hasattr(value, "translated") else value
            for name, value in values.items()
        }
        return MESSAGES[self.language][key].format(**localized)
