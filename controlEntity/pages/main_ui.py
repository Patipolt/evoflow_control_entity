import time
import os
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog, QHBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap
from controlEntity.widgets.evoflowWidget import EvoFlowWidget
from controlEntity.widgets.sampleExtractionWidget import SampleExtractionWidget

from controlEntity.logic.logic import Logic


prog_size_width = 1800
prog_size_height = 900

# ===============================================
# For Raspberry Pi OS title bar
# ===============================================
class _DragTitleBar(QWidget):
    """Custom draggable title bar used as Linux fallback when native decorations are missing."""

    def __init__(self, host_window: QMainWindow):
        super().__init__(host_window)
        self._host_window = host_window
        self._drag_offset = None

        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 10, 6)
        layout.setSpacing(8)

        title = QLabel("EvoFlow Control Entity")
        title.setStyleSheet("color: #f2f4f8; font-size: 14px; font-weight: 600;")
        layout.addWidget(title)
        layout.addStretch()

        self._minimize_btn = QPushButton("-")
        self._close_btn = QPushButton("x")

        for btn in (self._minimize_btn, self._close_btn):
            btn.setFixedSize(28, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {"
                "background-color: rgba(255,255,255,0.15);"
                "border: 1px solid rgba(255,255,255,0.25);"
                "border-radius: 6px;"
                "color: #ffffff;"
                "font-weight: 700;"
                "}"
                "QPushButton:hover {background-color: rgba(255,255,255,0.28);}"
            )
            layout.addWidget(btn)

        self._minimize_btn.clicked.connect(self._host_window.showMinimized)
        self._close_btn.clicked.connect(self._host_window.close)

        self.setStyleSheet("background-color: #1f2a37;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._host_window.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self._host_window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()
            return
        super().mouseReleaseEvent(event)
# ===============================================

class MainUI(QMainWindow):
    """Main UI class for the EvoFlow control entity application"""
    
    def __init__(self):
        super().__init__()
        # ===============================================
        # For Raspberry Pi OS title bar
        # ===============================================
        self._use_custom_title_bar = sys.platform.startswith("linux")

        if self._use_custom_title_bar:
            # Native decorations can be unavailable on some Raspberry Pi OS sessions.
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        else:
            self.setWindowFlags(
                Qt.WindowType.Window
                | Qt.WindowType.WindowTitleHint
                | Qt.WindowType.WindowSystemMenuHint
                | Qt.WindowType.WindowMinMaxButtonsHint
                | Qt.WindowType.WindowCloseButtonHint
            )
        # ===============================================

        self.setWindowTitle("EvoFlow Control Entity")
        self.setGeometry(0, 0, prog_size_width, prog_size_height)
        self.setFixedSize(prog_size_width, prog_size_height)

        self.logic = Logic()

        self.setup_ui()
        self.connect_signals()


    def setup_ui(self):
        """Set up the UI components"""
        central_widget = QWidget(self)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ===============================================
        # For Raspberry Pi OS title bar
        # ===============================================
        main_layout.setSpacing(0)

        if self._use_custom_title_bar:
            self._custom_title_bar = _DragTitleBar(self)
            main_layout.addWidget(self._custom_title_bar)

        # ===============================================

        self.evoflow_widget = EvoFlowWidget(1800, 450)
        self.sample_extraction_widget = SampleExtractionWidget(560, 195)

        main_layout.addWidget(self.evoflow_widget)
        main_layout.addStretch()
        self.setCentralWidget(central_widget)

        # Overlay the sample extraction widget on top of the EvoFlow widget.
        self.sample_extraction_widget.setParent(self.evoflow_widget)
        self.sample_extraction_widget.move(1218, 75)
        self.sample_extraction_widget.raise_()
        self.sample_extraction_widget.show()

    def connect_signals(self):
        """Connect signals to their respective slots"""
        # =====================================
        # Evoflow signals
        # =====================================
        
        # Telemetry
        self.logic.evoflow_worker.telemetry_updated.connect(self.evoflow_widget.update_telemetry)

        # Switches
        self.evoflow_widget.pump_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_pumps)
        self.evoflow_widget.magneticStirrer_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_magnetic_stirrers)
        self.evoflow_widget.od_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_od_ctrls)
        self.evoflow_widget.tempCtrl_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_temp_ctrls)
        self.evoflow_widget.valve_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_valves)
        self.evoflow_widget.phtCount_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_pht_count)

        # Buttons
        self.evoflow_widget.pump_sp_update_requested.connect(self.logic.evoflow_worker.set_setpoint_pumps)
        self.evoflow_widget.magneticStirrer_sp_update_requested.connect(self.logic.evoflow_worker.set_setpoint_magnetic_stirrers)
        self.evoflow_widget.tempCtrl_sp_update_requested.connect(self.logic.evoflow_worker.set_setpoint_temp_ctrls)


        # =====================================
        # Sample Extraction signals
        # =====================================

        self.sample_extraction_widget.start_sample_extraction_requested.connect(self.logic.sample_extraction_worker.start_sample_extraction)
        self.sample_extraction_widget.test_read_position_requested.connect(self.logic.sample_extraction_worker.get_all_telemetry)
        self.logic.sample_extraction_worker.telemetry_updated.connect(self.sample_extraction_widget.update_telemetry)

    def closeEvent(self, event: QCloseEvent):
        """Stop background threads before the main window closes"""
        self.logic.shutdown()
        super().closeEvent(event)
