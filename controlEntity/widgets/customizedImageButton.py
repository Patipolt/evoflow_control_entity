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
    """Custom QPushButton that changes its icon based on its checked state."""
    
    def __init__(self, icon_path_unchecked: str, icon_path_checked: str, width: int, height: int, parent=None):
        super().__init__(parent)
        self.icon_path_unchecked = icon_path_unchecked
        self.icon_path_checked = icon_path_checked
        self.setCheckable(True)
        self.setChecked(False)
        self.isChecked = False
        self.setIcon(QPixmap(self.icon_path_unchecked))
        self.toggled.connect(self.update_icon)
        self.width = width
        self.height = height
        self.setup_button()

    def setup_button(self):
        self.setFixedSize(self.width, self.height)
        self.background = QLabel(self)
        self.background.setFixedSize(self.width, self.height)
        self.background.setGeometry(0, 0, self.width, self.height)

    @Slot(bool)
    def update_icon(self, checked: bool):
        """Update the button's icon based on its checked state."""
        if checked:
            self.setIcon(QPixmap(self.icon_path_checked))
            self.isChecked = True
        else:
            self.setIcon(QPixmap(self.icon_path_unchecked))
            self.isChecked = False