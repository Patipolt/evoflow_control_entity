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
from typing import Optional, List
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLCDNumber, QLineEdit, QComboBox, QCalendarWidget, QTextEdit, QTimeEdit
from PySide6.QtWidgets import QPushButton, QGroupBox, QTabWidget, QTableView, QMenuBar, QStatusBar, QLabel, QCheckBox, QColorDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QThread, Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject, QMetaObject
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap

from controlEntity.utils import resource_path
from controlEntity.logic.evoflow_worker import EvoFlowWorker, EvoFlowTelemetry
from controlEntity.logic.sample_extraction_worker import SampleExtractionWorker, SampleExtractionTelemetry
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
        
        self.linux_system = True
        config = self.read_settings_file()
        sampling_rate_ms = config.getint("HMI", "sampling_rate_ms", fallback=200)

        # ===============================
        # EvoFlow Worker Setup
        # ===============================
        self.evoflow_thread = QThread()
        self.evoflow_worker = EvoFlowWorker(port= config.get("Evoflow", "port_linux" if self.linux_system else "port_windows"),
                                            baudrate= config.getint("Evoflow", "baudrate"),
                                            timeout= config.getfloat("Evoflow", "serial_timeout"),
                                            sender_addr= config.getint("HMI", "address"),
                                            receiver_addr= config.getint("Evoflow", "address"),
                                            sampling_rate_ms= sampling_rate_ms)
        self.evoflow_worker.moveToThread(self.evoflow_thread)
        self.evoflow_thread.started.connect(self.evoflow_worker.start)
        self.evoflow_thread.start()


        # ===============================
        # Sample Extraction Worker Setup
        # ===============================
        self.sample_extraction_thread = QThread()
        self.sample_extraction_worker = SampleExtractionWorker(port= config.get("SampleExtraction", "port_linux" if self.linux_system else "port_windows"),
                                                              baudrate= config.getint("SampleExtraction", "baudrate"),
                                                              timeout= config.getfloat("SampleExtraction", "serial_timeout"),
                                                              sender_addr= config.getint("HMI", "address"),
                                                              receiver_addr= config.getint("SampleExtraction", "address"),
                                                              sampling_rate_ms= sampling_rate_ms)
        self.sample_extraction_worker.moveToThread(self.sample_extraction_thread)
        self.sample_extraction_thread.started.connect(self.sample_extraction_worker.start)
        self.sample_extraction_thread.start()

    def read_settings_file(self):
        """Load automation step defaults from config/settings.ini"""
        # config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.ini')      # for development
        config_path = resource_path("config/settings.ini")       # for bundling with PyInstaller
        config = configparser.ConfigParser()
        config.read(str(config_path))
        return config

    def shutdown(self):
        """Stop worker threads before Qt destroys objects"""
        try:
            # Execute stop() in the worker thread so it can stop its own child thread safely.
            QMetaObject.invokeMethod(self.evoflow_worker, "stop", Qt.BlockingQueuedConnection)
        except Exception as e:
            print(f"Failed to stop EvoFlow worker cleanly: {e}")

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
        except Exception as e:
            print(f"Failed to stop EvoFlow thread cleanly: {e}")
