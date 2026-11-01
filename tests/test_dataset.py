"""Exercise data preservation against temporary datasets only."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yolo_review.dataset import Annotation, Dataset, DatasetError


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "images").mkdir()
        (self.root / "labels").mkdir()
        (self.root / "images" / "frame1.png").touch()
        (self.root / "classes.txt").write_text("drone\ncar\n", encoding="utf-8")
        self.path = self.root / "labels" / "frame1.txt"
        self.backup = self.root / ".yolo_review" / "backups" / "labels" / "frame1.txt"
        self.box = Annotation(0, 0.5, 0.5, 0.2, 0.3)

    def dataset(self):
        return Dataset(self.root)

    def test_load_missing_label(self):
        document = self.dataset().load(0)
        self.assertEqual(document.annotations, [])
        self.assertIsNone(document.revision)
        self.assertEqual(document.label_path, self.path)
        self.assertFalse(self.path.exists())

    def test_save_roundtrip_and_original_backup_once(self):
        original = b"0 0.500000 0.500000 0.200000 0.300000\r\n\n"
        self.path.write_bytes(original)
        dataset = self.dataset()
        document = dataset.load(0)
        self.assertEqual(document.annotations, [self.box])
        self.assertEqual(document.revision, hashlib.sha256(original).hexdigest())
        next_box = Annotation(1, 0.4, 0.3, 0.1, 0.2)
        revision = dataset.save(0, [next_box], document.revision)
        self.assertEqual(dataset.load(0).annotations, [next_box])
        self.assertEqual(dataset.load(0).revision, revision)
        self.assertEqual(self.backup.read_bytes(), original)
        dataset.save(0, [], revision)
        self.assertEqual(self.path.read_bytes(), b"")
        self.assertEqual(self.backup.read_bytes(), original)

    def test_missing_label_retains_absence_record(self):
        dataset = self.dataset()
        revision = dataset.save(0, [self.box], None)
        marker = self.backup.with_name(self.backup.name + ".missing")
        self.assertTrue(marker.exists())
        self.assertFalse(self.backup.exists())
        dataset.save(0, [], revision)
        self.assertTrue(marker.exists())
        self.assertFalse(self.backup.exists())

    def test_external_modification_is_not_overwritten(self):
        self.path.write_text("0 0.5 0.5 0.2 0.3\n", encoding="utf-8")
        dataset = self.dataset()
        document = dataset.load(0)
        external = b"1 0.4 0.4 0.1 0.1\n"
        self.path.write_bytes(external)
        with self.assertRaises(DatasetError):
            dataset.save(0, [], document.revision)
        self.assertEqual(self.path.read_bytes(), external)
        self.assertFalse(self.backup.exists())

    def test_new_external_file_is_not_overwritten(self):
        dataset = self.dataset()
        dataset.load(0)
        self.path.write_bytes(b"")
        with self.assertRaises(DatasetError):
            dataset.save(0, [self.box], None)
        self.assertEqual(self.path.read_bytes(), b"")

    def test_malformed_rows_raise_without_modifying_file(self):
        bad_rows = [
            "0 .5 .5 .2",
            "0 .5 .5 .2 .2 .9",
            "x .5 .5 .2 .2",
            "0 nan .5 .2 .2",
            "0 .5 .5 0 .2",
            "0 1.1 .5 .2 .2",
            "0.5 .5 .5 .2 .2",
        ]
        for row in bad_rows:
            with self.subTest(row=row):
                original = ("0 .5 .5 .2 .2\n" + row + "\n").encode()
                self.path.write_bytes(original)
                with self.assertRaisesRegex(DatasetError, "line 2") as caught:
                    self.dataset().load(0)
                self.assertIn("第 2 行", caught.exception.translated("zh"))
                self.assertEqual(self.path.read_bytes(), original)

    def test_invalid_box_cannot_touch_file(self):
        self.path.write_bytes(b"")
        dataset = self.dataset()
        revision = dataset.load(0).revision
        invalid = [
            Annotation(-1, 0.5, 0.5, 0.2, 0.2),
            Annotation(0, float("inf"), 0.5, 0.2, 0.2),
            Annotation(0, 0.5, 0.5, -0.2, 0.2),
            Annotation(0, 0.5, 0.5, 0, 0.2),
        ]
        for box in invalid:
            with self.subTest(box=box):
                with self.assertRaises(DatasetError):
                    dataset.save(0, [box], revision)
                self.assertEqual(self.path.read_bytes(), b"")
                self.assertFalse(self.backup.exists())

    def test_failed_replace_keeps_original_and_cleans_tempfile(self):
        original = b"0 .5 .5 .2 .3\n"
        self.path.write_bytes(original)
        dataset = self.dataset()
        document = dataset.load(0)
        dataset._backup_once(self.path, original)
        with patch("yolo_review.dataset.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                dataset.save(0, [], document.revision)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.backup.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_backup_failure_prevents_edit(self):
        self.path.write_bytes(b"")
        dataset = self.dataset()
        revision = dataset.load(0).revision
        with patch.object(dataset, "_backup_once", side_effect=OSError("backup failure")):
            with self.assertRaises(OSError):
                dataset.save(0, [self.box], revision)
        self.assertEqual(self.path.read_bytes(), b"")

    def test_natural_sort_and_nested_label_paths(self):
        (self.root / "images" / "frame10.png").touch()
        (self.root / "images" / "frame2.JPG").touch()
        nested = self.root / "images" / "train"
        nested.mkdir()
        (nested / "frame1.png").touch()
        dataset = self.dataset()
        self.assertEqual(
            [p.relative_to(self.root / "images").as_posix() for p in dataset.images],
            ["frame1.png", "frame2.JPG", "frame10.png", "train/frame1.png"],
        )
        dataset.save(3, [self.box], None)
        self.assertEqual(dataset.load(3).label_path, self.root / "labels" / "train" / "frame1.txt")
        self.assertEqual(dataset.load(3).annotations, [self.box])

    def test_ambiguous_image_names_are_rejected(self):
        (self.root / "images" / "frame1.jpg").touch()
        with self.assertRaises(DatasetError):
            self.dataset()

    def test_classes_and_bom(self):
        (self.root / "classes.txt").write_text("\ufeffdrone\ncar\n", encoding="utf-8")
        self.path.write_text("\ufeff0 .5 .5 .2 .3\n", encoding="utf-8")
        dataset = self.dataset()
        self.assertEqual(dataset.class_names, {0: "drone", 1: "car"})
        self.assertEqual(dataset.load(0).annotations, [self.box])

    def test_blank_class_names_are_left_for_interface_translation(self):
        (self.root / "classes.txt").write_text("drone\n\n无人机\n", encoding="utf-8")
        self.assertEqual(self.dataset().class_names, {0: "drone", 1: "", 2: "无人机"})
        (self.root / "classes.txt").unlink()
        self.assertEqual(self.dataset().class_names, {0: ""})

    def test_dataset_error_supports_both_languages(self):
        error = DatasetError("Unable to save.", "无法保存。")
        self.assertEqual(str(error), "Unable to save.")
        self.assertEqual(error.translated("en"), "Unable to save.")
        self.assertEqual(error.translated("zh"), "无法保存。")
        self.assertEqual(DatasetError("Custom error").translated("zh"), "Custom error")

    def test_validation_details_are_available_in_both_languages(self):
        self.path.write_text("0 nan .5 .2 .3\n", encoding="utf-8")
        with self.assertRaises(DatasetError) as caught:
            self.dataset().load(0)
        self.assertIn("finite numbers", caught.exception.translated("en"))
        self.assertIn("有限数值", caught.exception.translated("zh"))

    def test_utf8_errors_are_available_in_both_languages(self):
        self.path.write_bytes(b"\xff")
        with self.assertRaises(DatasetError) as caught:
            self.dataset().load(0)
        self.assertIn("UTF-8 label file", caught.exception.translated("en"))
        self.assertIn("UTF-8 标签文件", caught.exception.translated("zh"))


if __name__ == "__main__":
    unittest.main()
