"""Preferences must not prevent startup or corrupt previous state on failure."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yolo_review.i18n import choose_language
from yolo_review.settings import read_state, write_state


class SettingsTests(unittest.TestCase):
    def test_missing_malformed_and_non_object_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            self.assertEqual(read_state(path), {})
            for content in (b"{broken", b"[]", b"null", b"\xff"):
                path.write_bytes(content)
                self.assertEqual(read_state(path), {})

    def test_round_trip_and_failed_replace_preserves_previous_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs" / "state.json"
            original = {"image": "无人机 01.png", "language": "zh"}
            write_state(path, original)
            self.assertEqual(read_state(path), original)
            with patch("yolo_review.settings.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    write_state(path, {"language": "en"})
            self.assertEqual(read_state(path), original)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_invalid_saved_language_does_not_crash_startup(self):
        for saved in ({}, [], 123, False):
            with self.subTest(saved=saved):
                self.assertIn(choose_language(None, saved), ("en", "zh"))


if __name__ == "__main__":
    unittest.main()
