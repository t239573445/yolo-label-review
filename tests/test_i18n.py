"""Check language resolution and message formatting without a GUI."""

import os
import unittest
from string import Formatter
from unittest.mock import patch

from yolo_review.dataset import DatasetError
from yolo_review.i18n import MESSAGES, Translator, choose_language, system_language


class TranslationTests(unittest.TestCase):
    def test_catalogs_have_matching_messages_and_placeholders(self):
        self.assertEqual(set(MESSAGES["en"]), set(MESSAGES["zh"]))
        for key in MESSAGES["en"]:
            with self.subTest(key=key):
                placeholders = []
                for language in ("en", "zh"):
                    message = MESSAGES[language][key]
                    self.assertTrue(message.strip())
                    placeholders.append(
                        {
                            field
                            for _, field, _, _ in Formatter().parse(message)
                            if field is not None
                        }
                    )
                self.assertEqual(*placeholders)

    def test_explicit_language_overrides_saved_and_system_preferences(self):
        with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}, clear=True):
            self.assertEqual(choose_language("en", "zh"), "en")
            self.assertEqual(choose_language("zh", "en"), "zh")
            self.assertEqual(choose_language(None, "zh"), "zh")
            self.assertEqual(choose_language(None, "unsupported"), "en")

    def test_locale_environment_uses_standard_precedence(self):
        cases = [
            ({"LANG": "zh_CN.UTF-8"}, "zh"),
            ({"LANG": "zh_TW.UTF-8"}, "zh"),
            ({"LANG": "de_DE.UTF-8"}, "en"),
            ({"LC_MESSAGES": "en_US.UTF-8", "LANG": "zh_CN.UTF-8"}, "en"),
            ({"LC_ALL": "zh_CN.UTF-8", "LC_MESSAGES": "en_US.UTF-8"}, "zh"),
            ({"LC_ALL": "", "LANG": "zh_CN.UTF-8"}, "zh"),
        ]
        for environment, expected in cases:
            with (
                self.subTest(environment=environment),
                patch.dict(os.environ, environment, clear=True),
            ):
                self.assertEqual(system_language(), expected)

    def test_system_locale_is_used_without_environment_and_errors_fall_back_to_english(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("yolo_review.i18n.locale.getlocale", return_value=("zh_CN", "UTF-8")):
                self.assertEqual(system_language(), "zh")
            with patch("yolo_review.i18n.locale.getlocale", side_effect=ValueError("bad locale")):
                self.assertEqual(system_language(), "en")

    def test_dataset_error_details_follow_the_selected_language(self):
        error = DatasetError("Invalid annotation", "标注无效")
        self.assertIn("Invalid annotation", Translator("en")("labels_failed", error=error))
        self.assertIn("标注无效", Translator("zh")("labels_failed", error=error))

    def test_unknown_translator_language_is_rejected(self):
        with self.assertRaises(ValueError):
            Translator("unsupported")


if __name__ == "__main__":
    unittest.main()
