"""
Central logic coordinator for the EvoFlow HMI application.

Sets up worker threads for EvoFlow and Sample Extraction devices, wiring Qt signals
between UI components and device handlers.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

import configparser
import struct
import platform
from typing import Optional, List
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QThread, Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject, QMetaObject
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap

from controlEntity.utils import resource_path
from controlEntity.logic.evoflow_worker import EvoFlowWorker, EvoFlowTelemetry
from controlEntity.logic.sample_extraction_worker import SampleExtractionWorker, SampleExtractionTelemetry
from controlEntity.logic.data_logging_worker import DataLoggingWorker
from controlEntity.logic.odControl_worker import ODControlWorker
from evoflow.protocol import ProtocolPacket, Component, CMD, build_packet, cobs_decode, parse_packet


class Logic(QObject):
    """Coordinate device workers, wire Qt signals, and forward results to the UI"""
    
    # ===============================
    # EvoFlow Signals
    # ===============================

    
    # ===============================
    # Sample Extraction Signals
    # ===============================
    
    
    def __init__(self):
        super().__init__()
        
        self.current_os = platform.system().lower()
        config = self.read_settings_file()

        # ===============================
        # EvoFlow Worker Setup
        # ===============================
        self.evoflow_thread = QThread()
        self.evoflow_worker = EvoFlowWorker(port=self._resolve_port(config, "Evoflow"),
                                            baudrate= config.getint("Evoflow", "baudrate"),
                                            timeout= config.getfloat("Evoflow", "serial_timeout"),
                                            sender_addr= config.getint("HMI", "address"),
                                            receiver_addr= config.getint("Evoflow", "address"),
                                            sampling_rate_ms= config.getint("HMI", "sampling_rate_ms", fallback=200),
                                            auto_reset_after_seconds= config.getint("Evoflow", "auto_reset_after_seconds"),
                                            evoflow_status_gpio_pin= config.getint("RPI", "evoflow_status_gpio_pin", fallback=27),
                                            evoflow_reset_gpio_pin= config.getint("RPI", "evoflow_reset_gpio_pin", fallback=17))
        self.evoflow_worker.moveToThread(self.evoflow_thread)
        self.evoflow_thread.started.connect(self.evoflow_worker.start)
        self.evoflow_thread.start()

        # ===============================
        # Sample Extraction Worker Setup
        # ===============================
        self.sample_extraction_thread = QThread()
        self.sample_extraction_worker = SampleExtractionWorker(port=self._resolve_port(config, "SampleExtraction"),
                                                              baudrate= config.getint("SampleExtraction", "baudrate"),
                                                              timeout= config.getfloat("SampleExtraction", "serial_timeout"),
                                                              sender_addr= config.getint("HMI", "address"),
                                                              receiver_addr= config.getint("SampleExtraction", "address"),
                                                              sampling_rate_ms= config.getint("HMI", "sampling_rate_ms", fallback=200))
        self.sample_extraction_worker.moveToThread(self.sample_extraction_thread)
        self.sample_extraction_thread.started.connect(self.sample_extraction_worker.start)
        self.sample_extraction_thread.start()

        # ===============================
        # Data Logging Worker Setup
        # ===============================
        self.data_logging_thread = QThread()
        self.data_logging_worker = DataLoggingWorker()
        self.data_logging_worker.moveToThread(self.data_logging_thread)
        self.data_logging_thread.start()

        # ===============================
        # OD Control Worker Setup
        # ===============================
        self.ODController_bioreactor_thread = QThread()
        self.ODController_bioreactor_worker = ODControlWorker(V0= config.getfloat("ODController", "V0"),
                                                    A0= config.getfloat("ODController", "A0"),
                                                    mu0= config.getfloat("ODController", "mu0"),
                                                    kp= config.getfloat("ODController", "kp"),
                                                    ki= config.getfloat("ODController", "ki"),
                                                    q_max= config.getfloat("ODController", "q_max"),
                                                    Ts= config.getfloat("ODController", "Ts"),
                                                    A_setpoint= config.getfloat("ODController", "A_setpoint"))
        self.ODController_bioreactor_worker.moveToThread(self.ODController_bioreactor_thread)
        self.ODController_bioreactor_thread.start()

    def read_settings_file(self):
        """Load automation step defaults from config/settings.ini"""
        # config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.ini')      # for development
        config_path = resource_path("config/settings.ini")       # for bundling with PyInstaller
        config = configparser.ConfigParser()
        config.read(str(config_path))
        return config

    def _resolve_port(self, config: configparser.ConfigParser, section: str) -> str:
        """Pick the serial port key based on OS, with sensible fallbacks."""
        if self.current_os == "windows":
            return config.get(section, "port_windows")

        if self.current_os == "darwin":
            return config.get(section, "port_macos", fallback=config.get(section, "port_linux"))

        return config.get(section, "port_linux")

    def shutdown(self):
        """Stop worker threads before Qt destroys objects"""
        try:
            # Execute stop() in the worker thread so it can stop its own child thread safely.
            QMetaObject.invokeMethod(self.evoflow_worker, "stop", Qt.BlockingQueuedConnection)
        except Exception as e:
            print(f"Failed to stop EvoFlow worker cleanly: {e}")

        try:
            QMetaObject.invokeMethod(self.sample_extraction_worker, "stop", Qt.BlockingQueuedConnection)
        except Exception as e:
            print(f"Failed to stop Sample Extraction worker cleanly: {e}")

        try:
            QMetaObject.invokeMethod(self.data_logging_worker, "shutdown", Qt.BlockingQueuedConnection)
        except Exception as e:
            print(f"Failed to stop Data Logging worker cleanly: {e}")

        try:
            if self.evoflow_thread.isRunning():
                self.evoflow_thread.quit()
                if not self.evoflow_thread.wait(2000):
                    self.evoflow_thread.terminate()
                    self.evoflow_thread.wait(1000)
            if self.sample_extraction_thread.isRunning():
                self.sample_extraction_thread.quit()
                if not self.sample_extraction_thread.wait(2000):
                    self.sample_extraction_thread.terminate()
                    self.sample_extraction_thread.wait(1000)
            if self.data_logging_thread.isRunning():
                self.data_logging_thread.quit()
                if not self.data_logging_thread.wait(2000):
                    self.data_logging_thread.terminate()
                    self.data_logging_thread.wait(1000)
            if self.ODController_bioreactor_thread.isRunning():
                self.ODController_bioreactor_thread.quit()
                if not self.ODController_bioreactor_thread.wait(2000):
                    self.ODController_bioreactor_thread.terminate()
                    self.ODController_bioreactor_thread.wait(1000)
        except Exception as e:
            print(f"Failed to stop EvoFlow thread cleanly: {e}")
