"""Command-line entry point; help and version do not require a Qt import."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .i18n import choose_language


def main(argv: list[str] | None = None, *, default_dataset: Path | None = None) -> int:
    """Parse options and start the desktop reviewer."""
    args_list = list(sys.argv[1:] if argv is None else argv)
    probe = argparse.ArgumentParser(add_help=False)
    probe.add_argument("--lang", default="auto")
    preliminary, _ = probe.parse_known_args(args_list)
    chinese = choose_language(preliminary.lang) == "zh"
    parser = argparse.ArgumentParser(
        prog="yolo-review",
        add_help=False,
        description=(
            "YOLO 标注审核：直接拖框，每次修改自动保存。"
            if chinese
            else "Review YOLO boxes: drag to draw and save every edit automatically."
        ),
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        type=Path,
        default=default_dataset if default_dataset is not None else Path.cwd(),
        help="数据集目录（默认：当前目录）"
        if chinese
        else "dataset directory (default: current directory)",
    )
    parser.add_argument(
        "--lang",
        choices=("auto", "en", "zh"),
        default="auto",
        help="界面语言；auto 使用已保存的选择或系统语言"
        if chinese
        else "UI language; auto uses the saved choice or system locale",
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="显示帮助并退出" if chinese else "show this help and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="显示版本并退出" if chinese else "show version and exit",
    )
    if chinese:
        parser._positionals.title = "位置参数"
        parser._optionals.title = "选项"
    args = parser.parse_args(args_list)
    try:
        from .gui import run
    except ModuleNotFoundError as error:
        if (error.name or "").split(".")[0] not in {"PyQt5", "yaml"}:
            raise
        print(
            "缺少运行依赖，请在项目目录运行：python -m pip install ."
            if chinese
            else "Missing runtime dependencies. Run from the project directory: python -m pip install .",
            file=sys.stderr,
        )
        return 1
    return run(args.dataset, language=None if args.lang == "auto" else args.lang)
