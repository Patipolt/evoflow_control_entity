import time
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap
from controlEntity.widgets.evoflowWidget import EvoFlowWidget

from controlEntity.logic.logic import Logic


prog_size_width = 1200
prog_size_height = 1100

class MainUI(QMainWindow):
    """Main UI class for the EvoFlow control entity application."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EvoFlow Control Entity")
        self.setGeometry(0, 0, prog_size_width, prog_size_height)
        self.setFixedSize(prog_size_width, prog_size_height)

        self.logic = Logic()

        self.setup_ui()
        self.connect_signals()


    def setup_ui(self):
        """Set up the UI components."""
        central_widget = QWidget(self)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.evoflow_widget = EvoFlowWidget(1200, 720)
        self.read_telemetry_btn = QPushButton("Read telemetry")

        main_layout.addWidget(self.evoflow_widget)
        main_layout.addWidget(self.read_telemetry_btn)
        main_layout.addStretch()
        self.setCentralWidget(central_widget)

    def connect_signals(self):
        """Connect signals to their respective slots."""
        # Evoflow signals
        self.logic.evoflow_worker.telemetry_updated.connect(self.evoflow_widget.update_telemetry)
        self.evoflow_widget.pump_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_pumps)
        self.evoflow_widget.magneticStirrer_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_magnetic_stirrers)
        self.evoflow_widget.od_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_od_ctrls)
        self.evoflow_widget.tempCtrl_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_temp_ctrls)
        self.evoflow_widget.valve_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_valves)
        self.evoflow_widget.phtCount_on_off_requested.connect(self.logic.evoflow_worker.set_on_off_pht_count)

        self.read_telemetry_btn.clicked.connect(self.logic.evoflow_worker.get_telemetry)
