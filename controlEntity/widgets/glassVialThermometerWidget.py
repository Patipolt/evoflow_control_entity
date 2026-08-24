"""
GlassVialThermometerWidget: an animated glass-vial thermometer indicator

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau@zhaw.ch | patipol.thanuphol@zhaw.ch
Created: August 2026
"""

import sys

from PySide6.QtCore import Qt, QRectF, QPointF, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient, QRadialGradient, QFont, QPainterPath
from PySide6.QtWidgets import QWidget, QApplication, QHBoxLayout


class GlassVialThermometerWidget(QWidget):
    """Animated thermometer widget showing a temperature reading between 0 and 50 degC.

    The mercury column color is interpolated along light blue -> green -> yellow -> red
    as the value rises from min to max, and value changes animate smoothly.
    """

    valueChanged = Signal(float)

    # gradient stops (position 0..1, color) used to color the mercury column
    _COLOR_STOPS = [
        (0.2, QColor("#4FC3F7")),   # light blue
        (0.5, QColor("#4CAF50")),   # green
        (0.6, QColor("#FFEB3B")),   # yellow
        (0.7, QColor("#F44336")),   # red
    ]

    def __init__(self, parent=None, min_value: float = 0.0, max_value: float = 50.0, value: float = 0.0):
        super().__init__(parent)
        self.setMinimumSize(40, 100)
        self.setMaximumSize(100, 300)

        self._min_value = min_value
        self._max_value = max_value
        self._value = min(max(value, min_value), max_value)
        self._display_value = self._value  # animated value used for painting

        self._decimals = 1
        self._unit = "\u00b0C"

        self._anim = QPropertyAnimation(self, b"displayValue", self)
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    # ---------- public API ----------
    def value(self) -> float:
        return self._value

    def setValue(self, value: float, animate: bool = True):
        """Set the current temperature reading, clamped to [min_value, max_value]."""
        value = min(max(float(value), self._min_value), self._max_value)
        if value == self._value:
            return
        self._value = value
        self.valueChanged.emit(self._value)

        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._display_value)
            self._anim.setEndValue(self._value)
            self._anim.start()
        else:
            self.displayValue = self._value

    def setRange(self, min_value: float, max_value: float):
        self._min_value = min_value
        self._max_value = max_value
        self._value = min(max(self._value, min_value), max_value)
        self.update()

    # Property driven by QPropertyAnimation for smooth transitions
    def getDisplayValue(self) -> float:
        return self._display_value

    def setDisplayValue(self, v: float):
        self._display_value = float(v)
        self.update()

    displayValue = Property(float, getDisplayValue, setDisplayValue)

    # ---------- helpers ----------
    def _fraction(self, value: float) -> float:
        span = self._max_value - self._min_value
        if span <= 0:
            return 0.0
        return min(max((value - self._min_value) / span, 0.0), 1.0)

    def _color_for_fraction(self, frac: float) -> QColor:
        """Interpolate a color along the light-blue -> green -> yellow -> red stops."""
        stops = self._COLOR_STOPS
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if frac <= p1 or (p0, c0) == stops[-2]:
                span = p1 - p0
                t = 0.0 if span <= 0 else (frac - p0) / span
                t = min(max(t, 0.0), 1.0)
                r = c0.red() + (c1.red() - c0.red()) * t
                g = c0.green() + (c1.green() - c0.green()) * t
                b = c0.blue() + (c1.blue() - c0.blue()) * t
                return QColor(int(r), int(g), int(b))
        return stops[-1][1]

    def _geometry(self):
        """Return the key geometric measurements for the tube/bulb layout."""
        w = self.width()
        h = self.height()

        bulb_d = min(w * 0.6, h * 0.28)
        bulb_d = max(bulb_d, 18)
        self.margin_top = 5  # pixel
        self.margin_bottom_percent = 20  # percent

        tube_w = bulb_d * 0.42
        tube_x = (w - tube_w) / 2.0
        tube_top = self.margin_top
        tube_bottom = h - (h * self.margin_bottom_percent / 100) - bulb_d
        tube_bottom = max(tube_bottom, tube_top + bulb_d)

        bulb_cx = w / 2.0
        bulb_cy = tube_bottom + bulb_d / 2.0

        tube_rect = QRectF(tube_x, tube_top, tube_w, tube_bottom - tube_top + bulb_d / 2.0)
        bulb_rect = QRectF(bulb_cx - bulb_d / 2.0, bulb_cy - bulb_d / 2.0, bulb_d, bulb_d)

        return tube_rect, bulb_rect, tube_w

    # ---------- painting ----------
    def paintEvent(self, _):
        tube_rect, bulb_rect, tube_w = self._geometry()
        radius = tube_w / 2.0

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # glass tube + bulb merged into a single outline (avoids a seam where they overlap)
        glass_pen = QPen(QColor(255, 255, 255, 255), 2.0)
        glass_fill = QColor(255, 255, 255, 255)

        bulb_path = QPainterPath()
        bulb_path.addEllipse(bulb_rect)

        glass_path = QPainterPath()
        glass_path.addRoundedRect(tube_rect, radius, radius)
        glass_path = glass_path.united(bulb_path)

        p.setPen(Qt.NoPen)
        p.setBrush(glass_fill)
        p.drawPath(glass_path)

        # mercury column color + fraction
        frac = self._fraction(self._display_value)
        color = self._color_for_fraction(frac)

        # mercury column height inside the tube
        column_area_top = tube_rect.top()
        column_area_bottom = tube_rect.bottom() - tube_rect.width() / 2.0  # stop above bulb overlap
        column_height = (column_area_bottom - column_area_top) * frac
        column_rect = QRectF(
            tube_rect.left() + 2,
            column_area_bottom - column_height,
            tube_rect.width() - 4,
            column_height + tube_rect.width(),  # extend into the bulb so it connects visually
        )

        column_path = QPainterPath()
        column_path.addRoundedRect(column_rect, radius - 2, radius - 2)
        mercury_path = column_path.intersected(glass_path)
        # keep the bulb always full of mercury regardless of the column level
        mercury_bulb_path = QPainterPath()
        mercury_bulb_path.addEllipse(bulb_rect.adjusted(3, 3, -3, -3))
        mercury_path = mercury_path.united(mercury_bulb_path)

        gradient = QLinearGradient(0, column_rect.bottom(), 0, column_rect.top())
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(1.0, color.lighter(115))

        p.setPen(Qt.NoPen)
        p.setBrush(gradient)
        p.drawPath(mercury_path)

        # glass outline on top, drawn once as a single unbroken path
        p.setPen(glass_pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(glass_path)

        # tick marks along the tube
        p.setPen(QPen(QColor(255, 255, 255, 255), 2))
        tick_count = 5
        for i in range(tick_count + 1):
            y = column_area_top + (column_area_bottom - column_area_top) * (i / tick_count)
            p.drawLine(QPointF(tube_rect.right() + 2, y), QPointF(tube_rect.right() + 8, y))

        # value label above the bulb
        p.setPen(QColor(255, 255, 255))
        font = QFont()
        # make the font size fit to the width of the widget
        height_for_font = self.margin_bottom_percent / 100 * self.height()
        width_for_font = self.width()
        # choose font size based on "xx.xoC" numbers of characters, which is 6 characters wide
        font_size = max(8, int(min(width_for_font / 6, height_for_font * 0.8)))
        font.setPointSize(font_size)
        font.setBold(True)
        p.setFont(font)
        label = f"{self._display_value:.{self._decimals}f}{self._unit}"
        text_rect = QRectF(0, self.height()-height_for_font, self.width(), height_for_font)
        p.drawText(text_rect, Qt.AlignCenter, label)

        p.end()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout(window)

    thermo = GlassVialThermometerWidget(min_value=0, max_value=50, value=0)
    layout.addWidget(thermo)

    window.resize(50, 100)
    window.show()

    thermo.setValue(15)
    sys.exit(app.exec())
