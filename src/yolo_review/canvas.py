"""Image-space rendering, direct box drawing, zooming and panning."""

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QFrame, QGraphicsScene, QGraphicsView

from .i18n import Translator


class AnnotationCanvas(QGraphicsView):
    """Scene coordinates always equal original image pixels."""

    boxDrawn = pyqtSignal(QRectF)
    zoomChanged = pyqtSignal(float)

    def __init__(self, parent=None, *, translator=None):
        super().__init__(parent)
        self.t = translator or Translator()
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QColor("#10151e"))
        self.setFrameShape(QFrame.NoFrame)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.viewport().setCursor(Qt.CrossCursor)
        self.image_rect = QRectF()
        self.annotations = []
        self.class_names = {}
        self.selected = -1
        self.editable = False
        self._start = None
        self._end = None
        self._pan_start = None
        self._fit_mode = True

    def set_image(self, pixmap):
        self.cancel_drawing()
        self.scene().clear()
        self.annotations = []
        self.selected = -1
        self.image_rect = QRectF(0, 0, pixmap.width(), pixmap.height())
        if not pixmap.isNull():
            self.scene().addPixmap(pixmap)
        self.setSceneRect(self.image_rect)
        self.fit_image()

    def set_annotations(self, annotations, selected=-1):
        self.annotations = list(annotations)
        self.selected = selected
        self.viewport().update()

    def fit_image(self):
        self._fit_mode = True
        if not self.image_rect.isEmpty():
            self.fitInView(self.image_rect, Qt.KeepAspectRatio)
            self.zoomChanged.emit(self.transform().m11())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_mode:
            self.fit_image()

    def wheelEvent(self, event):
        if self.image_rect.isEmpty():
            return
        factor = 1.2 ** (event.angleDelta().y() / 120)
        current = self.transform().m11()
        fit = min(
            self.viewport().width() / self.image_rect.width(),
            self.viewport().height() / self.image_rect.height(),
        )
        target = max(max(fit * 0.25, 0.01), min(current * factor, 32.0))
        self.scale(target / current, target / current)
        self._fit_mode = False
        self.zoomChanged.emit(target)
        event.accept()

    def _clamp(self, point):
        return QPointF(
            max(0, min(point.x(), self.image_rect.width())),
            max(0, min(point.y(), self.image_rect.height())),
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.cancel_drawing()
            self._pan_start = event.pos()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        point = self.mapToScene(event.pos())
        if event.button() == Qt.LeftButton and self.editable and self.image_rect.contains(point):
            self.setFocus()
            self._start = self._clamp(point)
            self._end = self._start
            self.viewport().update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start = event.pos()
            event.accept()
            return
        if self._start is not None:
            self._end = self._clamp(self.mapToScene(event.pos()))
            self.viewport().update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan_start = None
            self.viewport().setCursor(Qt.CrossCursor)
            event.accept()
            return
        if event.button() == Qt.LeftButton and self._start is not None:
            end = self._clamp(self.mapToScene(event.pos()))
            rect = QRectF(self._start, end).normalized()
            self.cancel_drawing()
            if rect.width() >= 2 and rect.height() >= 2:
                self.boxDrawn.emit(rect)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def cancel_drawing(self):
        self._start = None
        self._end = None
        self.viewport().update()

    def _paint_box(self, painter, rect, color, caption, selected=False, dashed=False):
        scale = max(self.transform().m11(), 0.001)
        pen = QPen(color, 3 if selected else 2)
        pen.setCosmetic(True)
        if dashed:
            pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(
            QColor(color.red(), color.green(), color.blue(), 32) if selected else Qt.NoBrush
        )
        painter.drawRect(rect)
        if selected:
            painter.setBrush(color)
            for point in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
                painter.drawRect(
                    QRectF(point.x() - 3 / scale, point.y() - 3 / scale, 6 / scale, 6 / scale)
                )
        painter.save()
        font = QFont("Sans Serif", 10)
        font.setBold(selected)
        painter.setFont(font)
        width = painter.fontMetrics().horizontalAdvance(caption) + 12
        label_x = max(0, min(rect.left(), self.image_rect.right() - width / scale))
        painter.translate(label_x, max(0, rect.top() - 22 / scale))
        painter.scale(1 / scale, 1 / scale)
        painter.fillRect(QRectF(0, 0, width, 21), color)
        painter.setPen(QColor("#10151e"))
        painter.drawText(QRectF(6, 0, width - 6, 21), Qt.AlignVCenter, caption)
        painter.restore()

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if self.image_rect.isEmpty():
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.image_rect.width(), self.image_rect.height()
        order = [i for i in range(len(self.annotations)) if i != self.selected]
        if 0 <= self.selected < len(self.annotations):
            order.append(self.selected)
        for i in order:
            box = self.annotations[i]
            bounds = QRectF(
                (box.x - box.width / 2) * width,
                (box.y - box.height / 2) * height,
                box.width * width,
                box.height * height,
            )
            selected = i == self.selected
            name = self.class_names.get(box.class_id) or self.t("class_name", id=box.class_id)
            self._paint_box(
                painter,
                bounds,
                QColor("#ffd166" if selected else "#47e5a0"),
                f"{i + 1}  {name}",
                selected,
            )
        if self._start is not None and self._end is not None:
            bounds = QRectF(self._start, self._end).normalized()
            self._paint_box(
                painter,
                bounds,
                QColor("#68bcff"),
                self.t("new_box", width=bounds.width(), height=bounds.height()),
                dashed=True,
            )
        painter.restore()
