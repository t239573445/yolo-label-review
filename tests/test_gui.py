"""Exercise real Qt input and on-disk results against temporary data only."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QEvent, QPointF, Qt
from PyQt5.QtGui import QColor, QImage, QKeyEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from yolo_review.gui import ReviewWindow


class ReviewWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "images").mkdir()
        (self.root / "labels").mkdir()
        (self.root / "classes.txt").write_text("drone\ncar\n", encoding="utf-8")
        for name in ("frame1", "frame2"):
            image = QImage(400, 300, QImage.Format_RGB32)
            image.fill(QColor("#202020"))
            self.assertTrue(image.save(str(self.root / "images" / f"{name}.png")))
        self.label = self.root / "labels" / "frame1.txt"
        self.original = b"0 0.5 0.5 0.2 0.2\n1 0.2 0.2 0.1 0.1\n"
        self.label.write_bytes(self.original)
        self.window = ReviewWindow(self.root, language="zh")
        self.addCleanup(self._close_window)
        self.window.show()
        self.window.activateWindow()
        self.window.canvas.setFocus()
        QTest.qWait(20)

    def _close_window(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def _drag(self, start, end):
        canvas = self.window.canvas
        start = canvas.mapFromScene(QPointF(*start))
        end = canvas.mapFromScene(QPointF(*end))
        QTest.mousePress(canvas.viewport(), Qt.LeftButton, pos=start)
        QTest.mouseMove(canvas.viewport(), end)
        QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, pos=end)
        self.app.processEvents()

    def _select(self, row):
        box_list = self.window.box_list
        point = box_list.visualItemRect(box_list.item(row)).center()
        QTest.mouseClick(box_list.viewport(), Qt.LeftButton, pos=point)
        self.app.processEvents()

    def _disk_boxes(self, index=0):
        return self.window.dataset.load(index).annotations

    def test_drag_saves_normalized_box_immediately_and_preserves_original(self):
        self.window.class_combo.setCurrentIndex(1)
        self._drag((100, 60), (220, 150))
        boxes = self._disk_boxes()
        self.assertEqual(len(boxes), 3)
        self.assertEqual(boxes[-1].class_id, 1)
        for actual, expected in zip(
            (boxes[-1].x, boxes[-1].y, boxes[-1].width, boxes[-1].height),
            (0.4, 0.35, 0.3, 0.3),
        ):
            self.assertAlmostEqual(actual, expected, delta=0.005)
        self.assertEqual(self.window.canvas.selected, 2)
        self.assertIn("已自动保存", self.window.save_label.text())
        backup = self.root / ".yolo_review" / "backups" / "labels" / "frame1.txt"
        self.assertEqual(backup.read_bytes(), self.original)

    def test_reverse_drag_inside_existing_box_and_click_without_drag(self):
        self._drag((220, 160), (180, 130))
        self.assertEqual(len(self._disk_boxes()), 3)
        self.assertGreater(self._disk_boxes()[-1].width, 0)
        self.assertGreater(self._disk_boxes()[-1].height, 0)
        saved = self.label.read_bytes()
        self._drag((180, 130), (180, 130))
        self.assertEqual(self.label.read_bytes(), saved)

    def test_sidebar_selection_visibly_highlights_and_delete_saves(self):
        canvas = self.window.canvas
        point = canvas.mapFromScene(QPointF(160, 145))

        def has_yellow_border():
            picture = canvas.viewport().grab().toImage()
            colors = [
                picture.pixelColor(point.x() + dx, point.y() + dy)
                for dx in range(-3, 4)
                for dy in range(-3, 4)
            ]
            return any(c.red() > 200 and 140 < c.green() < 235 and c.blue() < 130 for c in colors)

        self.assertFalse(has_yellow_border())
        self._select(0)
        self.assertEqual(canvas.selected, 0)
        self.assertTrue(has_yellow_border())
        QTest.keyClick(self.window.box_list, Qt.Key_Delete)
        self.assertEqual(len(self._disk_boxes()), 1)
        self.assertEqual(self._disk_boxes()[0].class_id, 1)
        QTest.keyClick(self.window.box_list, Qt.Key_Delete)
        self.assertEqual(self.label.read_bytes(), b"")
        self.assertEqual(self.window.box_list.count(), 0)

    def test_a_d_navigation_works_from_sidebar_and_canvas(self):
        self._select(0)
        QTest.keyClick(self.window.box_list, Qt.Key_D)
        self.assertEqual(self.window.index, 1)
        self.assertEqual(self.window.annotations, [])
        self.assertFalse((self.root / "labels" / "frame2.txt").exists())
        self.window.canvas.setFocus()
        QTest.keyClick(self.window.canvas, Qt.Key_A)
        self.assertEqual(self.window.index, 0)
        self.assertEqual(len(self.window.annotations), 2)
        QTest.keyClick(self.window.canvas, Qt.Key_A)
        self.assertEqual(self.window.index, 0)
        self.assertEqual(self.label.read_bytes(), self.original)

    def test_undo_redo_keyboard_shortcuts_also_save(self):
        self._select(1)
        QTest.keyClick(self.window.box_list, Qt.Key_Delete)
        self.assertEqual(len(self._disk_boxes()), 1)
        QTest.keyClick(self.window.box_list, Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(len(self._disk_boxes()), 2)
        QTest.keyClick(self.window.box_list, Qt.Key_Y, Qt.ControlModifier)
        self.assertEqual(len(self._disk_boxes()), 1)
        self.assertTrue(self.window.undo_button.isEnabled())
        self.assertFalse(self.window.redo_button.isEnabled())

    def test_failed_save_keeps_labels_view_and_history_unchanged(self):
        self._select(0)
        with (
            patch.object(self.window.dataset, "save", side_effect=OSError("disk full")),
            patch("yolo_review.gui.QMessageBox.warning") as warning,
        ):
            QTest.keyClick(self.window.box_list, Qt.Key_Delete)
        warning.assert_called_once()
        self.assertEqual(self.label.read_bytes(), self.original)
        self.assertEqual(len(self.window.annotations), 2)
        self.assertEqual(self.window.box_list.count(), 2)
        self.assertEqual(self.window.undo_stack, [])
        self.assertIn("保存失败", self.window.save_label.text())

    def test_invalid_labels_disable_editing_without_replacing_the_file(self):
        bad_path = self.root / "labels" / "frame2.txt"
        original = b"0 0.5 0.5 0.2\n"
        bad_path.write_bytes(original)
        QTest.keyClick(self.window.canvas, Qt.Key_D)
        self.assertEqual(self.window.index, 1)
        self.assertFalse(self.window.canvas.editable)
        self.assertTrue(self.window.error_label.isVisible())
        self._drag((10, 10), (100, 100))
        self.assertEqual(bad_path.read_bytes(), original)
        QTest.keyClick(self.window.canvas, Qt.Key_A)
        self.assertTrue(self.window.canvas.editable)

    def test_escape_cancels_in_progress_drawing(self):
        canvas = self.window.canvas
        start = canvas.mapFromScene(QPointF(10, 10))
        end = canvas.mapFromScene(QPointF(100, 100))
        QTest.mousePress(canvas.viewport(), Qt.LeftButton, pos=start)
        QTest.mouseMove(canvas.viewport(), end)
        QTest.keyClick(canvas, Qt.Key_Escape)
        QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, pos=end)
        self.assertEqual(self.label.read_bytes(), self.original)
        self.assertEqual(len(self.window.annotations), 2)

    def test_language_switch_preserves_labels_selection_and_undo(self):
        self._select(0)
        QTest.keyClick(self.window.box_list, Qt.Key_Delete)
        saved = self.label.read_bytes()
        self.window.class_combo.setCurrentIndex(1)
        selected = self.window.box_list.currentRow()
        history = list(self.window.undo_stack)
        self.window.language_combo.setCurrentIndex(self.window.language_combo.findData("en"))
        self.assertIn("Previous", self.window.previous_button.text())
        self.assertIn("Saved automatically", self.window.save_label.text())
        self.assertIn("car", self.window.box_list.item(0).text())
        self.assertIn("Center", self.window.box_list.item(0).text())
        self.assertEqual(self.window.box_list.currentRow(), selected)
        self.assertEqual(self.window.canvas.selected, selected)
        self.assertEqual(self.window.class_combo.currentData(), 1)
        self.assertEqual(self.window.undo_stack, history)
        self.assertEqual(self.label.read_bytes(), saved)
        self.window.undo()
        self.assertEqual(len(self._disk_boxes()), 2)
        self.window.language_combo.setCurrentIndex(self.window.language_combo.findData("zh"))
        self.assertIn("上一张", self.window.previous_button.text())
        self.assertIn("中心", self.window.box_list.item(0).text())

    def test_invalid_labels_error_translates_without_reloading(self):
        bad_path = self.root / "labels" / "frame2.txt"
        malformed = b"0 0.5 0.5 0.2\n"
        bad_path.write_bytes(malformed)
        self.window.navigate(1)
        self.assertIn("第 1 行", self.window.error_label.text())
        self.window.language_combo.setCurrentIndex(self.window.language_combo.findData("en"))
        self.assertIn("line 1", self.window.error_label.text())
        self.assertIn("editing is disabled", self.window.error_label.text())
        self.assertFalse(self.window.canvas.editable)
        self.assertEqual(bad_path.read_bytes(), malformed)

    def test_language_and_position_are_restored_with_explicit_language_override(self):
        self.window.language_combo.setCurrentIndex(self.window.language_combo.findData("en"))
        self.window.navigate(1)
        self.window.close()
        resumed = ReviewWindow(self.root)
        try:
            self.assertEqual(resumed.t.language, "en")
            self.assertEqual(resumed.index, 1)
            self.assertEqual(self.label.read_bytes(), self.original)
        finally:
            resumed.close()
            resumed.deleteLater()
        overridden = ReviewWindow(self.root, language="zh")
        try:
            self.assertEqual(overridden.t.language, "zh")
            self.assertEqual(overridden.index, 1)
        finally:
            overridden.close()
            overridden.deleteLater()

    def test_held_navigation_repeats_but_delete_does_not(self):
        # An OS key repeat is a KeyPress with autorep=True. QTest.keyClick alone
        # cannot exercise that path, so deliver a real Qt repeat event instead.
        QTest.keyClick(self.window.canvas, Qt.Key_D)
        self.assertEqual(self.window.index, 1)
        repeat = QKeyEvent(QEvent.KeyPress, Qt.Key_A, Qt.NoModifier, "a", True, 1)
        QApplication.sendEvent(self.window.canvas, repeat)
        self.assertEqual(self.window.index, 0)
        self._select(0)
        repeat_delete = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier, "", True, 1)
        QApplication.sendEvent(self.window.box_list, repeat_delete)
        self.assertEqual(self.label.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
