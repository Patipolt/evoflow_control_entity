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
from PySide6.QtCore import Qt, QFile, QTimer, QDate, QTime, QIODeviceBase, QEvent, Signal, Slot, QObject
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QStandardItemModel, QStandardItem, QWheelEvent, QCloseEvent, QAction, QPixmap

from controlEntity.utils import resource_path
from controlEntity.widgets.evoflowWidget import EvoFlowTelemetry
from evoflow.device.communication import ProtocolPacket, Component, CMD, build_packet, cobs_decode, parse_packet


class Logic(QObject):
    """Coordinate device workers, wire Qt signals, and forward results to the UI."""
    
    # ===============================
    # EvoFlow Signals
    # ===============================
    telemetry_changed = Signal(EvoFlowTelemetry)
    
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
        self.evoflow_telemetry = EvoFlowTelemetry()
        
        # ===============================
        # Sample Extraction Worker Setup
        # ===============================

    
        # For testing, just setting a timer to update telemetry
        self.simulate_timer = QTimer(self)
        self.simulate_timer.timeout.connect(self.simulate_telemetry_update)
        self.simulate_timer.start(sampling_rate_ms)

        # For testing protocol encoding/decoding
        self.simulate_protocol_timer = QTimer(self)
        self.simulate_protocol_timer.timeout.connect(self.simulate_protocol_test)
        self.simulate_protocol_timer.start(5000)
        self.simulate_protocol_test()

    def simulate_telemetry_update(self):
        """Simulate incoming telemetry updates for testing."""
        import random
        self.evoflow_telemetry.pump_1_status = random.choice([True, False])
        self.evoflow_telemetry.pump_1_sp = random.uniform(0, 100)
        self.evoflow_telemetry.pump_1_speed = random.uniform(0, 100)
        self.evoflow_telemetry.pump_2_status = random.choice([True, False])
        self.evoflow_telemetry.pump_2_sp = random.uniform(0, 100)
        self.evoflow_telemetry.pump_2_speed = random.uniform(0, 100)
        self.evoflow_telemetry.pump_3_status = random.choice([True, False])
        self.evoflow_telemetry.pump_3_sp = random.uniform(0, 100)
        self.evoflow_telemetry.pump_3_speed = random.uniform(0, 100)
        self.evoflow_telemetry.pump_4_status = random.choice([True, False])
        self.evoflow_telemetry.pump_4_sp = random.uniform(0, 100)
        self.evoflow_telemetry.pump_4_speed = random.uniform(0, 100)

        self.evoflow_telemetry.magneticStirrer_bioreactor_status = random.choice([True, False])
        self.evoflow_telemetry.magneticStirrer_bioreactor_sp = random.uniform(0, 100)
        self.evoflow_telemetry.magneticStirrer_bioreactor_speed = random.uniform(0, 100)
        self.evoflow_telemetry.magneticStirrer_bioreactor_fan_duty_cycle = random.uniform(0, 100)

        self.evoflow_telemetry.magneticStirrer_lagoon_status = random.choice([True, False])
        self.evoflow_telemetry.magneticStirrer_lagoon_sp = random.uniform(0, 100)
        self.evoflow_telemetry.magneticStirrer_lagoon_speed = random.uniform(0, 100)
        self.evoflow_telemetry.magneticStirrer_lagoon_fan_duty_cycle = random.uniform(0, 100)

        self.evoflow_telemetry.valve_bio2lag_status = random.choice([True, False])
        self.evoflow_telemetry.valve_sug2lag_status = random.choice([True, False])

        self.evoflow_telemetry.od_bioreactor_status = random.choice([True, False])
        self.evoflow_telemetry.od_bioreactor_value = random.uniform(0, 2)
        self.evoflow_telemetry.od_lagoon_status = random.choice([True, False])
        self.evoflow_telemetry.od_lagoon_value = random.uniform(0, 2)

        self.evoflow_telemetry.tempCtrl_bioreactor_status = random.choice([True, False])
        self.evoflow_telemetry.tempCtrl_bioreactor_sp = random.uniform(20, 40)
        self.evoflow_telemetry.tempCtrl_bioreactor_value = random.uniform(20, 40)
        self.evoflow_telemetry.tempCtrl_bioreactor_heater_duty_cycle = random.uniform(0, 100)

        self.evoflow_telemetry.tempCtrl_lagoon_status = random.choice([True, False])
        self.evoflow_telemetry.tempCtrl_lagoon_sp = random.uniform(20, 40)
        self.evoflow_telemetry.tempCtrl_lagoon_value = random.uniform(20, 40)
        self.evoflow_telemetry.tempCtrl_lagoon_heater_duty_cycle = random.uniform(0, 100)

        self.evoflow_telemetry.phtCount_lagoon_status = random.choice([True, False])
        self.evoflow_telemetry.phtCount_lagoon_value = random.uniform(0, 14)
        self.evoflow_telemetry.phtCount_lagoon_overlight = random.choice([True, False])

        self.telemetry_changed.emit(self.evoflow_telemetry)

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
