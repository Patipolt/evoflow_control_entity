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
from PySide6.QtCore import QThread, Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap

from controlEntity.utils import resource_path
from controlEntity.widgets.evoflowWidget import EvoFlowTelemetry
from controlEntity.logic.evoflow_worker import EvoFlowWorker
from evoflow.protocol import ProtocolPacket, Component, CMD, build_packet, cobs_decode, parse_packet


class Logic(QObject):
    """Coordinate device workers, wire Qt signals, and forward results to the UI."""
    
    # ===============================
    # EvoFlow Signals
    # ===============================

    
    # ===============================
    # Sample Extraction Signals
    # ===============================
    
    
    def __init__(self):
        super().__init__()
        
        config = self.read_settings_file()
        sampling_rate_ms = config.getint("HMI", "sampling_rate_ms", fallback=200)

        # ===============================
        # EvoFlow Worker Setup
        # ===============================
        self.evoflow_thread = QThread()
        self.evoflow_worker = EvoFlowWorker(port= config.get("Evoflow", "port"),
                                            baudrate= config.getint("Evoflow", "baudrate"),
                                            sender_addr= config.getint("HMI", "address"),
                                            receiver_addr= config.getint("Evoflow", "address"))
        self.evoflow_worker.moveToThread(self.evoflow_thread)
        self.evoflow_thread.started.connect(self.evoflow_worker.start)
        self.evoflow_thread.start()


        # ===============================
        # Sample Extraction Worker Setup
        # ===============================


    def simulate_protocol_test(self):
        """Simulate encoding and decoding a protocol packet for testing."""
        # Simulate encoding a command to set pump speed to 3.56, 0.0, 0.0, 0.0 rpm (for example)
        sender_addr = 0  # HMI
        receiver_addr = 100  # EvoFlow Nucleo

        packet = ProtocolPacket(
            sender=sender_addr,
            receiver_addr=receiver_addr,
            is_write=True,
            id1=Component.PUMP,
            id2=CMD.SET_POINT,
            # because it sends 4 floats for the 4 pumps, we need to pack them into bytes.
            payload=bytes(struct.pack('<4f', 3.56, 0.0, 0.0, 0.0))
        )

        # Encoding the packet
        encoded_packet = build_packet(packet)
        print(f"Simulated encoded packet (hex): {encoded_packet.hex()}")

        # Simulate decoding the same packet
        delimiter_cut_out = encoded_packet[:-1]  # Remove trailing delimiters for testing
        print(f"Simulated raw packet for decoding (hex): {delimiter_cut_out.hex()}")

        decoded_packet = parse_packet(delimiter_cut_out)
        print(f"Simulated decoded packet bytes: {decoded_packet}")

    def read_settings_file(self):
        """Load automation step defaults from config/settings.ini."""
        # config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.ini')      # for development
        config_path = resource_path("config/settings.ini")       # for bundling with PyInstaller
        config = configparser.ConfigParser()
        config.read(str(config_path))
        return config
