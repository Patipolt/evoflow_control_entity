"""
Setup worker threads for Sample Extraction device communication and telemetry processing.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

import time

from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer, QCoreApplication, QEventLoop
from evoflow.device.sample_extraction import SampleExtractionDevice, SampleExtractionTelemetry
from controlEntity.utils import Utils

class SampleExtractionWorker(QObject):
    """Worker class to handle Sample Extraction device communication in a separate thread"""

    # Outgoing signals
    telemetry_updated = Signal(SampleExtractionTelemetry)
    sample_extraction_comm_status_updated = Signal(bool)
    sample_extraction_moving_status_updated = Signal(bool)
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.01, sender_addr: int = 0x01, receiver_addr: int = 0xC9, sampling_rate_ms: int = 200):
        super().__init__()
        self.sample_extraction = SampleExtractionDevice(port, baudrate, timeout, sender_addr, receiver_addr)
        self.sampling_rate_ms = sampling_rate_ms
        self._running = False
        self._telemetry_timer = None
        self.is_sample_extraction_moving = False
        self.utils = Utils()

    @Slot()
    def start(self):
        """Start the worker thread and begin reading telemetry"""
        try:
            if self._running:
                return  # Already running
            self._running = True
            self.sample_extraction.connect()
            self._homing_after_startup()
            self._telemetry_timer = QTimer(self)
            self._telemetry_timer.timeout.connect(self._poll_telemetry)
            self._telemetry_timer.start(self.sampling_rate_ms)
        except Exception as e:
            # print(f"Failed to connect to Sample Extraction device: {e}")
            return
    
    @Slot()
    def stop(self):
        """Stop the worker thread and clean up resources"""
        try:
            if not self._running:
                return  # Already stopped

            self._running = False
            if self._telemetry_timer is not None:
                self._telemetry_timer.stop()

            self.sample_extraction.disconnect()
        except Exception as e:
            print(f"Failed to disconnect from Sample Extraction device: {e}")

    @Slot()
    def _poll_telemetry(self):
        """Poll telemetry from the Sample Extraction device"""
        try:
            if self.sample_extraction.get_all_telemetry():
                self.telemetry_updated.emit(self.sample_extraction.sample_extraction_telemetry)
                self.sample_extraction_comm_status_updated.emit(True)
                if not self.sample_extraction.sample_extraction_telemetry.done_flag:
                    self.is_sample_extraction_moving = True
                    self.sample_extraction_moving_status_updated.emit(True)
                else:
                    self.is_sample_extraction_moving = False
                    self.sample_extraction_moving_status_updated.emit(False)
            else:
                self.sample_extraction_comm_status_updated.emit(False)
        except Exception as e:
            print(f"Failed to get telemetry from Sample Extraction device: {e}")
            return None

    def _homing_after_startup(self):
        """Perform homing after startup and wait for completion"""
        self.is_sample_extraction_moving = True
        ret_pos = self.utils.return_row_col_sample_extraction("Homing")  # Set to home position
        self.sample_extraction.set_position(ret_pos[0], ret_pos[1])  # Set to home position
        self.sample_extraction.start_sample_extraction()  # Start the homing process

    @Slot(tuple) 
    def start_sample_extraction(self, position: tuple):
        """Start the sample extraction process at the specified row and column"""
        try:
            self.sample_extraction.set_position(position[0], position[1])
            self.sample_extraction.start_sample_extraction()
        except Exception as e:
            print(f"Failed to start sample extraction on Sample Extraction device: {e}")
