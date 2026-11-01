"""Exercise the public CLI without opening a window."""

import contextlib
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from yolo_review import __version__
from yolo_review.cli import main


class CliTests(unittest.TestCase):
    def test_help_is_bilingual_and_does_not_load_qt(self):
        for language, expected in (("en", "dataset directory"), ("zh", "数据集目录")):
            with self.subTest(language=language):
                code = (
                    "import sys; from yolo_review.cli import main; "
                    "sys.modules['PyQt5'] = None; "
                    f"main(['--lang', '{language}', '--help'])"
                )
                result = subprocess.run(
                    [sys.executable, "-c", code], capture_output=True, text=True, check=False
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)

    def test_version_exits_without_starting_ui(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as exit_info:
            main(["--version"])
        self.assertEqual(exit_info.exception.code, 0)
        self.assertIn(__version__, output.getvalue())

    def test_dataset_path_and_language_are_forwarded(self):
        path = Path("dataset with spaces")
        with patch("yolo_review.gui.run", return_value=7) as run:
            self.assertEqual(main([str(path), "--lang", "zh"]), 7)
        run.assert_called_once_with(path, language="zh")

    def test_default_dataset_and_auto_language(self):
        with patch("yolo_review.gui.run", return_value=0) as run:
            main([])
        run.assert_called_once_with(Path.cwd(), language=None)
        with patch("yolo_review.gui.run", return_value=0) as run:
            main([], default_dataset=Path("legacy dataset"))
        run.assert_called_once_with(Path("legacy dataset"), language=None)

    def test_invalid_language_does_not_start_ui(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_info:
            main(["--lang", "fr"])
        self.assertEqual(exit_info.exception.code, 2)


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    unittest.main()
