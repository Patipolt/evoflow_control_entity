from PySide6.QtCore import Qt, QRectF, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication, QVBoxLayout
import sys


class SlideSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(39, 24)

        self._checked = checked
        self._dragging = False

        # visual settings
        self._bg_off = QColor("#E5E5EA")   # iOS-ish off gray
        self._bg_on = QColor("#00FF40")    # iOS green
        self._thumb = QColor("#FFFFFF")
        self._border = QColor(0, 0, 0, 40)

        # animation value is thumb x-position in [0..1]
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"position", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    # ---------- API ----------
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, animate: bool = True):
        if self._checked == checked:
            return
        self._checked = checked
        self.toggled.emit(self._checked)

        target = 1.0 if self._checked else 0.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._pos = target
            self.update()

    # Property used by QPropertyAnimation
    def getPosition(self) -> float:
        return self._pos

    def setPosition(self, v: float):
        self._pos = max(0.0, min(1.0, float(v)))
        self.update()

    position = Property(float, getPosition, setPosition)

    # ---------- geometry helpers ----------
    def _metrics(self):
        w = self.width()
        h = self.height()
        margin = 3
        track = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        radius = track.height() / 2.0

        thumb_d = track.height()  # thumb diameter
        x_min = track.left()
        x_max = track.right() - thumb_d
        x = x_min + (x_max - x_min) * self._pos
        thumb = QRectF(x, track.top(), thumb_d, thumb_d)
        return track, radius, thumb, x_min, x_max

    # ---------- painting ----------
    def paintEvent(self, _):
        track, radius, thumb, _, _ = self._metrics()

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Track
        bg = self._bg_on if self._pos > 0.5 else self._bg_off
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(track, radius, radius)

        # Border (subtle)
        p.setPen(QPen(self._border, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(track, radius, radius)

        # Thumb
        p.setPen(Qt.NoPen)
        p.setBrush(self._thumb)
        p.drawEllipse(thumb)

        # Thumb shadow (simple)
        shadow = QColor(0, 0, 0, 35)
        p.setBrush(shadow)
        p.drawEllipse(thumb.adjusted(1.2, 1.6, 1.2, 1.6))

        # Thumb on top again
        p.setBrush(self._thumb)
        p.drawEllipse(thumb)

        p.end()

    # ---------- interaction ----------
    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self._dragging = True
        self._anim.stop()
        self._press_x = e.position().x()
        self._press_pos = self._pos
        e.accept()

    def mouseMoveEvent(self, e):
        if not self._dragging:
            return
        track, _, _, x_min, x_max = self._metrics()
        thumb_d = track.height()

        dx = e.position().x() - self._press_x
        # convert pixels -> normalized [0..1] movement
        span = max(1.0, (x_max - x_min))
        new_pos = self._press_pos + (dx / span)
        self._pos = max(0.0, min(1.0, new_pos))
        self.update()
        e.accept()

    def mouseReleaseEvent(self, e):
        if not self._dragging:
            return
        self._dragging = False

        # Click without drag = toggle
        # Release after drag = snap
        new_checked = self._pos >= 0.5
        self.setChecked(new_checked, animate=True)
        e.accept()
