"""
Main UI for the EvoFlow control entity application

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau@zhaw.ch | patipol.thanuphol@zhaw.ch
Created: April 2026
"""

import time
import os
import sys
import configparser
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog, QHBoxLayout, QSizePolicy
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap
from controlEntity.widgets.evoflowWidget import EvoFlowWidget
from controlEntity.widgets.sampleExtractionWidget import SampleExtractionWidget
from controlEntity.widgets.PlotWidget import PlotWidget

from controlEntity.logic.logic import Logic


prog_size_width = 1800
prog_size_height = 900

class MainUI(QMainWindow):
    """Main UI class for the EvoFlow control entity application"""
    
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EvoFlow Control Entity")
        self.setGeometry(0, 0, prog_size_width, prog_size_height)
        self.setMinimumSize(prog_size_width, prog_size_height)

        self.logic = Logic()

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the UI components"""
        central_widget = QWidget(self)
        central_widget.setObjectName("central_widget")
        central_widget.setStyleSheet("#central_widget { background-color: '#252525'; }")

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.evoflow_widget = EvoFlowWidget(1800, 450)
        self.sample_extraction_widget = SampleExtractionWidget(560, 195)
        self.plot_widget = PlotWidget(self)
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout.addWidget(self.evoflow_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addWidget(self.plot_widget, stretch=1)

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
        self.logic.evoflow_worker.telemetry_updated.connect(self.logic.data_logging_worker.update_evoflow_telemetry)

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
        self.logic.sample_extraction_worker.telemetry_updated.connect(self.logic.data_logging_worker.update_sample_extraction_telemetry)

        # =====================================
        # Plot / Data logging signals
        # =====================================
        self.plot_widget.start_logging_requested.connect(self.logic.data_logging_worker.start_logging)
        self.plot_widget.stop_logging_requested.connect(self.logic.data_logging_worker.stop_logging)
        self.plot_widget.timespan_minutes_changed.connect(self.logic.data_logging_worker.set_timespan_minutes)

        self.logic.data_logging_worker.plot_data_updated.connect(self.plot_widget.update_plot_from_logged_data)
        self.logic.data_logging_worker.logging_state_changed.connect(self.plot_widget.set_logging_state)
        self.logic.data_logging_worker.status_message.connect(self.plot_widget.show_status_message)

    def closeEvent(self, event: QCloseEvent):
        """Stop background threads before the main window closes"""
        self.logic.shutdown()
        super().closeEvent(event)
