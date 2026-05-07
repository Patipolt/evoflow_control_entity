from PySide6.QtCore import Qt, QRectF, Signal, QEvent, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel, QPushButton, QHBoxLayout


class TapSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(39, 24)

        self._checked = checked
        self._pos = 1.0 if checked else 0.0  # 0..1 thumb position

        # Base colors (enabled)
        self._bg_off = QColor("#E5E5EA")
        self._bg_on = QColor("#00FF40")
        self._thumb = QColor("#FFFFFF")
        self._border = QColor(0, 0, 0, 40)

        # Disabled look tuning
        self._disabled_opacity = 0.45  # smaller -> more dim

        self._anim = QPropertyAnimation(self, b"position", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    # ---- convenience enable/disable ----
    def disable(self):
        self.setEnabled(False)

    def enable(self):
        self.setEnabled(True)

    # ---- public API ----
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

    def toggle(self):
        # guard: never toggle if disabled
        if not self.isEnabled():
            return
        self.setChecked(not self._checked, animate=True)

    # Property for animation
    def getPosition(self) -> float:
        return self._pos

    def setPosition(self, v: float):
        self._pos = max(0.0, min(1.0, float(v)))
        self.update()

    position = Property(float, getPosition, setPosition)

    # ---- drawing helpers ----
    def _metrics(self):
        w, h = self.width(), self.height()
        m = 3
        track = QRectF(m, m, w - 2 * m, h - 2 * m)
        r = track.height() / 2.0

        thumb_d = track.height()
        x_min = track.left()
        x_max = track.right() - thumb_d
        x = x_min + (x_max - x_min) * self._pos
        thumb = QRectF(x, track.top(), thumb_d, thumb_d)
        return track, r, thumb

    def paintEvent(self, _):
        track, r, thumb = self._metrics()

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # If disabled, draw everything with lower opacity
        if not self.isEnabled():
            p.setOpacity(self._disabled_opacity)

        # Track
        bg = self._bg_on if self._pos > 0.5 else self._bg_off
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(track, r, r)

        # Border
        p.setPen(QPen(self._border, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(track, r, r)

        # Thumb shadow
        shadow = QColor(0, 0, 0, 35)
        p.setPen(Qt.NoPen)
        p.setBrush(shadow)
        p.drawEllipse(thumb.adjusted(1.2, 1.6, 1.2, 1.6))

        # Thumb
        p.setBrush(self._thumb)
        p.drawEllipse(thumb)

        p.end()

    def changeEvent(self, e):
        if e.type() == QEvent.EnabledChange:
            self.update()
        super().changeEvent(e)

    # ---- interaction: tap only ----
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.isEnabled():
            self.toggle()
            e.accept()
        else:
            super().mousePressEvent(e)

    # Keyboard accessibility
    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter) and self.isEnabled():
            self.toggle()
            e.accept()
        else:
            super().keyPressEvent(e)