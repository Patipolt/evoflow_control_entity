"""
Customized image button widget

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau@zhaw.ch | patipol.thanuphol@zhaw.ch
Created: August 2026
"""

import time
import os
import configparser
import numpy as np
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap

class CustomizedImageButton(QPushButton):
    """A QPushButton that displays a different image for each checked state."""
    clicked = Signal(bool)  # Signal to emit when the button is clicked

    def __init__(self, width: int, height: int, checked: bool, icon_path_unchecked: str, icon_path_checked: str, icon_path_inactive_pressed: str = None, parent=None):
        super().__init__(parent)
        self.icon_path_unchecked = icon_path_unchecked
        self.icon_path_checked = icon_path_checked
        self.icon_path_inactive_pressed = icon_path_inactive_pressed
        self.width = width
        self.height = height
        self._isChecked = bool(checked)

        self.setCheckable(True)
        self.setFixedSize(self.width, self.height)
        self.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: transparent;
            }
            QPushButton:disabled {
                border: none;
                background: transparent;
            }
            """
        )

        self.background = QLabel(self)
        self.background.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.background.setFixedSize(self.width, self.height)
        self.background.setGeometry(0, 0, self.width, self.height)
        self.background.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.background.raise_()

        self.toggled.connect(self.update_icon)
        self.setChecked(self._isChecked)
        self.setEnabled(True)

    def _resolve_asset_path(self, relative_path: str) -> str:
        if not relative_path:
            return ""
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        return os.path.join(assets_dir, relative_path)

    def _apply_pixmap(self, relative_path: str):
        if not relative_path:
            return
        pixmap = QPixmap(self._resolve_asset_path(relative_path))
        if pixmap.isNull():
            return
        scaled_pixmap = pixmap.scaled(
            self.width,
            self.height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.background.setPixmap(scaled_pixmap)

    def update_icon(self, checked: bool):
        """Update the button image based on its checked state."""
        if not self.isEnabled() and self.icon_path_inactive_pressed:
            self._apply_pixmap(self.icon_path_inactive_pressed)
            return

        self._isChecked = bool(checked)
        icon_path = self.icon_path_checked if checked else self.icon_path_unchecked
        self._apply_pixmap(icon_path)

    # ---------- API ----------
    def isChecked(self) -> bool:
        """Return the current checked state of the button."""
        return self._isChecked

    def setChecked(self, checked: bool):
        """Override setChecked to keep the custom image in sync with the checked state."""
        super().setChecked(checked)
        self._isChecked = bool(checked)
        self.update_icon(checked)
        self.clicked.emit(checked)

    def mousePressEvent(self, event):
        """Handle mouse press events to change the button image when pressed."""
        if event.button() == Qt.MouseButton.LeftButton and self.icon_path_inactive_pressed:
            self._apply_pixmap(self.icon_path_inactive_pressed)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Restore the normal image after release and keep the toggle state consistent."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self.isChecked())
            self.update_icon(self.isChecked())
            return
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)

    def setEnabled(self, enabled: bool):
        """Override setEnabled to ensure the button image matches its enabled state."""
        super().setEnabled(enabled)
        if enabled:
            self.update_icon(self.isChecked())
        elif self.icon_path_inactive_pressed:
            self._apply_pixmap(self.icon_path_inactive_pressed)
        else:
            self.update_icon(self.isChecked())
