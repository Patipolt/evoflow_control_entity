"""
Setup worker threads for EvoFlow device communication and telemetry processing.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

from PySide6.QtCore import QObject, QThread, Signal, Slot
from evoflow.device.evoflow import EvoFlowDevice, EvoFlowTelemetry

class EvoFlowWorker(QObject):
    """Worker class to handle EvoFlow device communication in a separate thread."""
    
    telemetry_updated = Signal(EvoFlowTelemetry)
    
    def __init__(self, port: str, baudrate: int = 115200, sender_addr: int = 0x01, receiver_addr: int = 0xC9, sampling_rate_ms: int = 200):
        super().__init__()
        self.evoflow = EvoFlowDevice(port, baudrate, sender_addr, receiver_addr)
        self.sampling_rate_ms = sampling_rate_ms

    @Slot()
    def start(self):
        """Start the worker thread and begin reading telemetry."""
        try:
            self.evoflow.connect()
            # Optionally, you could start a timer here to read telemetry at regular intervals
            # Set up another thread reading telemetry every X ms and emitting the telemetry_updated signal
            self.reading_thread = QThread()
            self.reading_thread.run = self.get_all_telemetry
            self.reading_thread.start()

            
        except Exception as e:
            print(f"Failed to connect to EvoFlow device: {e}")
            return
    
    @Slot()
    def stop(self):
        """Stop the worker thread and clean up resources."""
        try:
            self.evoflow.disconnect()
        except Exception as e:
            print(f"Failed to disconnect from EvoFlow device: {e}")

    @Slot(bool, bool, bool, bool)
    def set_on_off_pumps(self, pump_1_status: bool, pump_2_status: bool, pump_3_status: bool, pump_4_status: bool):
        """Set the on/off status of the pumps."""
        try:
            self.evoflow.set_on_off_pumps(pump_1_status, pump_2_status, pump_3_status, pump_4_status)
        except Exception as e:
            print(f"Failed to set pump status: {e}")

    @Slot(float, float, float, float)
    def set_setpoint_pumps(self, pump_1_setpoint: float, pump_2_setpoint: float, pump_3_setpoint: float, pump_4_setpoint: float):
        """Set the speed setpoints for the pumps."""
        try:
            self.evoflow.set_setpoint_pumps(pump_1_setpoint, pump_2_setpoint, pump_3_setpoint, pump_4_setpoint)
        except Exception as e:
            print(f"Failed to set pump setpoints: {e}")

    @Slot(bool, bool)
    def set_on_off_valves(self, valve_bio2lag_status: bool, valve_sug2lag_status: bool):
        """Set the on/off status of the valves."""
        try:
            self.evoflow.set_on_off_valves(valve_bio2lag_status, valve_sug2lag_status)
        except Exception as e:
            print(f"Failed to set valve status: {e}")

    @Slot(bool, bool)
    def set_on_off_temp_ctrls(self, tempCtrl_bioreactor_status: bool, tempCtrl_lagoon_status: bool):
        """Set the on/off status of the temperature controllers."""
        try:
            self.evoflow.set_on_off_temp_ctrls(tempCtrl_bioreactor_status, tempCtrl_lagoon_status)
        except Exception as e:
            print(f"Failed to set temperature controller status: {e}")
        
    @Slot(float, float)
    def set_setpoint_temp_ctrls(self, tempCtrl_bioreactor_sp: float, tempCtrl_lagoon_sp: float):
        """Set the temperature setpoints for the temperature controllers."""
        try:
            self.evoflow.set_setpoint_temp_ctrls(tempCtrl_bioreactor_sp, tempCtrl_lagoon_sp)
        except Exception as e:
            print(f"Failed to set temperature controller setpoints: {e}")

    @Slot(bool, bool)
    def set_on_off_od_ctrls(self, od_bioreactor_status: bool, od_lagoon_status: bool):
        """Set the on/off status of the OD controllers."""
        try:
            self.evoflow.set_on_off_od_ctrls(od_bioreactor_status, od_lagoon_status)
        except Exception as e:
            print(f"Failed to set OD controller status: {e}")

    @Slot(bool, bool)
    def set_on_off_magnetic_stirrers(self, magneticStirrer_bioreactor_status: bool, magneticStirrer_lagoon_status: bool):
        """Set the on/off status of the magnetic stirrers."""
        try:
            self.evoflow.set_on_off_magnetic_stirrers(magneticStirrer_bioreactor_status, magneticStirrer_lagoon_status)
        except Exception as e:
            print(f"Failed to set magnetic stirrer status: {e}")

    @Slot(float, float)
    def set_setpoint_magnetic_stirrers(self, magneticStirrer_bioreactor_sp: float, magneticStirrer_lagoon_sp: float):
        """Set the speed setpoints for the magnetic stirrers."""
        try:
            self.evoflow.set_setpoint_magnetic_stirrers(magneticStirrer_bioreactor_sp, magneticStirrer_lagoon_sp)
        except Exception as e:
            print(f"Failed to set magnetic stirrer setpoints: {e}")

    @Slot(bool)
    def set_on_off_pht_count(self, phtCount_lagoon_status: bool):
        """Set the on/off status of the photon counter."""
        try:
            self.evoflow.set_on_off_pht_count(phtCount_lagoon_status)
        except Exception as e:
            print(f"Failed to set photon counter status: {e}")

    @Slot()
    def get_telemetry(self):
        """Read telemetry data from the EvoFlow device and emit it."""
        try:
            self.evoflow.get_telemetry()
            self.telemetry_updated.emit(self.evoflow.evoflow_telemetry)
        except Exception as e:
            print(f"Failed to read telemetry: {e}")

    @Slot()
    def get_all_telemetry(self):
        """Continuously read telemetry data from the EvoFlow device and emit it."""
        while True:
            self.evoflow.get_all_telemetry()
            self.telemetry_updated.emit(self.evoflow.evoflow_telemetry)
            QThread.msleep(self.sampling_rate_ms)
