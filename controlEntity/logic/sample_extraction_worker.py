"""
Setup worker threads for Sample Extraction device communication and telemetry processing.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer
from evoflow.device.sample_extraction import SampleExtractionDevice, SampleExtractionTelemetry

class SampleExtractionWorker(QObject):
    """Worker class to handle Sample Extraction device communication in a separate thread"""
    
    telemetry_updated = Signal(SampleExtractionTelemetry)
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.01, sender_addr: int = 0x01, receiver_addr: int = 0xC9, sampling_rate_ms: int = 200):
        super().__init__()
        self.sample_extraction = SampleExtractionDevice(port, baudrate, timeout, sender_addr, receiver_addr)
        self.sampling_rate_ms = sampling_rate_ms
        self._running = False
        self.reading_thread = None

        # Timer1 = QTimer(self)
        # Timer1.timeout.connect(self.get_all_telemetry)
        # Timer1.start(2000)

    @Slot()
    def start(self):
        """Start the worker thread and begin reading telemetry"""
        try:
            self._running = True
            self.sample_extraction.connect()
        except Exception as e:
            # print(f"Failed to connect to Sample Extraction device: {e}")
            return
    
    @Slot()
    def stop(self):
        """Stop the worker thread and clean up resources"""
        try:
            self._running = False
            if self.reading_thread and self.reading_thread.isRunning():
                self.reading_thread.requestInterruption()
                self.reading_thread.quit()
                if not self.reading_thread.wait(2000):
                    self.reading_thread.terminate()
                    self.reading_thread.wait(1000)
            self.sample_extraction.disconnect()
        except Exception as e:
            print(f"Failed to disconnect from Sample Extraction device: {e}")

    @Slot(tuple)
    def start_sample_extraction(self, position: tuple):
        """Start the sample extraction process"""
        try:
            self.sample_extraction.set_position(position[0], position[1])
            self.sample_extraction.start_sample_extraction()
        except Exception as e:
            print(f"Failed to start sample extraction on Sample Extraction device: {e}")

    @Slot()
    def get_all_telemetry(self):
        """Get all telemetry from the Sample Extraction device"""
        try:
            self.sample_extraction.get_all_telemetry()
            self.telemetry_updated.emit(self.sample_extraction.sample_extraction_telemetry)
        except Exception as e:
            print(f"Failed to get telemetry from Sample Extraction device: {e}")
            return None