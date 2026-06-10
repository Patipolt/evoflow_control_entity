"""
Setup worker threads for EvoFlow device communication and telemetry processing.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

from PySide6.QtCore import QObject, QThread, Signal, Slot
from evoflow.device.evoflow import EvoFlowDevice, EvoFlowTelemetry

class EvoFlowWorker(QObject):
    """Worker class to handle EvoFlow device communication in a separate thread"""
    
    telemetry_updated = Signal(EvoFlowTelemetry)
    evoflow_status_updated = Signal(bool)
    
    def __init__(self, port: str, baudrate: int = 115200, 
                 timeout: float = 0.01, 
                 sender_addr: int = 0x01, 
                 receiver_addr: int = 0xC9, 
                 sampling_rate_ms: int = 200, 
                 auto_reset_after_seconds: int = 5, 
                 evoflow_status_gpio_pin: int = 27, 
                 evoflow_reset_gpio_pin: int = 17):
        super().__init__()
        self.evoflow = EvoFlowDevice(port, 
                                     baudrate, 
                                     timeout, 
                                     sender_addr, 
                                     receiver_addr, 
                                     evoflow_status_gpio_pin, 
                                     evoflow_reset_gpio_pin)
        self.sampling_rate_ms = sampling_rate_ms
        self.auto_reset_after_seconds = auto_reset_after_seconds
        self._running = False
        self.telemetry_thread = None
        self.evoflow_status_thread = None

    @Slot()
    def start(self):
        """Start the worker thread and begin reading telemetry"""
        try:
            self._running = True
            self.evoflow.connect()
            # Optionally, you could start a timer here to read telemetry at regular intervals
            # Set up another thread reading telemetry every X ms and emitting the telemetry_updated signal
            self.telemetry_thread = QThread()
            self.telemetry_thread.run = self.get_all_telemetry
            self.telemetry_thread.start()

            self.evoflow_status_thread = QThread()
            self.evoflow_status_thread.run = self.is_evoflow_ok
            self.evoflow_status_thread.start()

            self.auto_reset_timer = QThread()
            self.auto_reset_timer.run = self.auto_reset_evoflow
            self.auto_reset_timer.start()
        except Exception as e:
            # print(f"Failed to connect to EvoFlow device: {e}")
            return
    
    @Slot()
    def stop(self):
        """Stop the worker thread and clean up resources"""
        try:
            self._running = False
            if self.telemetry_thread and self.telemetry_thread.isRunning():
                self.telemetry_thread.requestInterruption()
                self.telemetry_thread.quit()
                if not self.telemetry_thread.wait(2000):
                    self.telemetry_thread.terminate()
                    self.telemetry_thread.wait(1000)
            self.evoflow.disconnect()
        except Exception as e:
            print(f"Failed to disconnect from EvoFlow device: {e}")

    @Slot(bool, bool, bool, bool)
    def set_on_off_pumps(self, pump_1_status: bool, pump_2_status: bool, pump_3_status: bool, pump_4_status: bool):
        """Set the on/off status of the pumps"""
        try:
            self.evoflow.set_on_off_pumps(pump_1_status, pump_2_status, pump_3_status, pump_4_status)
        except Exception as e:
            print(f"Failed to set pump status: {e}")

    @Slot(float, float, float, float)
    def set_setpoint_pumps(self, pump_1_setpoint: float, pump_2_setpoint: float, pump_3_setpoint: float, pump_4_setpoint: float):
        """Set the speed setpoints for the pumps"""
        try:
            self.evoflow.set_setpoint_pumps(pump_1_setpoint, pump_2_setpoint, pump_3_setpoint, pump_4_setpoint)
        except Exception as e:
            print(f"Failed to set pump setpoints: {e}")

    @Slot(bool, bool)
    def set_on_off_valves(self, valve_bio2lag_status: bool, valve_sug2lag_status: bool):
        """Set the on/off status of the valves"""
        try:
            self.evoflow.set_on_off_valves(valve_bio2lag_status, valve_sug2lag_status)
        except Exception as e:
            print(f"Failed to set valve status: {e}")

    @Slot(bool, bool)
    def set_on_off_temp_ctrls(self, tempCtrl_bioreactor_status: bool, tempCtrl_lagoon_status: bool):
        """Set the on/off status of the temperature controllers"""
        try:
            self.evoflow.set_on_off_temp_ctrls(tempCtrl_bioreactor_status, tempCtrl_lagoon_status)
        except Exception as e:
            print(f"Failed to set temperature controller status: {e}")
        
    @Slot(float, float)
    def set_setpoint_temp_ctrls(self, tempCtrl_bioreactor_sp: float, tempCtrl_lagoon_sp: float):
        """Set the temperature setpoints for the temperature controllers"""
        try:
            self.evoflow.set_setpoint_temp_ctrls(tempCtrl_bioreactor_sp, tempCtrl_lagoon_sp)
        except Exception as e:
            print(f"Failed to set temperature controller setpoints: {e}")

    @Slot(bool, bool)
    def set_on_off_od_ctrls(self, od_bioreactor_status: bool, od_lagoon_status: bool):
        """Set the on/off status of the OD controllers"""
        try:
            self.evoflow.set_on_off_od_ctrls(od_bioreactor_status, od_lagoon_status)
        except Exception as e:
            print(f"Failed to set OD controller status: {e}")

    @Slot(bool, bool)
    def set_on_off_magnetic_stirrers(self, magneticStirrer_bioreactor_status: bool, magneticStirrer_lagoon_status: bool):
        """Set the on/off status of the magnetic stirrers"""
        try:
            self.evoflow.set_on_off_magnetic_stirrers(magneticStirrer_bioreactor_status, magneticStirrer_lagoon_status)
        except Exception as e:
            print(f"Failed to set magnetic stirrer status: {e}")

    @Slot(float, float)
    def set_setpoint_magnetic_stirrers(self, magneticStirrer_bioreactor_sp: float, magneticStirrer_lagoon_sp: float):
        """Set the speed setpoints for the magnetic stirrers"""
        try:
            self.evoflow.set_setpoint_magnetic_stirrers(magneticStirrer_bioreactor_sp, magneticStirrer_lagoon_sp)
        except Exception as e:
            print(f"Failed to set magnetic stirrer setpoints: {e}")

    @Slot(bool)
    def set_on_off_pht_count(self, phtCount_lagoon_status: bool):
        """Set the on/off status of the photon counter"""
        try:
            self.evoflow.set_on_off_pht_count(phtCount_lagoon_status)
        except Exception as e:
            print(f"Failed to set photon counter status: {e}")

    @Slot()
    def get_telemetry(self):
        """Read telemetry data from the EvoFlow device and emit it"""
        while self._running:
            self.evoflow.get_telemetry()
            self.telemetry_updated.emit(self.evoflow.evoflow_telemetry)
            QThread.msleep(self.sampling_rate_ms)

    @Slot()
    def get_all_telemetry(self):
        """Continuously read telemetry data from the EvoFlow device and emit it"""
        while self._running:
            self.evoflow.get_all_telemetry()
            self.telemetry_updated.emit(self.evoflow.evoflow_telemetry)
            QThread.msleep(self.sampling_rate_ms)

    @Slot()
    def get_all_telemetry_wo_asking(self):
        """Continuously read telemetry data from the EvoFlow device and emit it"""
        while self._running:
            self.evoflow.get_all_telemetry_wo_asking()
            self.telemetry_updated.emit(self.evoflow.evoflow_telemetry)
            QThread.msleep(self.sampling_rate_ms)

    @Slot()
    def is_evoflow_ok(self):
        """Check if the EvoFlow device is operating normally"""
        while self._running:
            evoflow_ok = self.evoflow.is_evoflow_ok()
            self.evoflow_status_updated.emit(evoflow_ok)
            QThread.msleep(self.sampling_rate_ms)
    
    @Slot()
    def reset_evoflow(self):
        """Reset the EvoFlow device"""
        self.evoflow.reset_evoflow()

    def auto_reset_evoflow(self):
        """Automatically reset the EvoFlow device if it's not operating normally for a certain duration"""
        consecutive_not_ok_count = 0
        while self._running:
            evoflow_ok = self.evoflow.is_evoflow_ok()
            if not evoflow_ok:
                consecutive_not_ok_count += 1
            else:
                consecutive_not_ok_count = 0
            
            if consecutive_not_ok_count >= (self.auto_reset_after_seconds * 1000 / self.sampling_rate_ms):
                print("EvoFlow has been NOT OK for the specified duration. Resetting EvoFlow...")
                self.reset_evoflow()
                consecutive_not_ok_count = 0
            
            QThread.msleep(self.sampling_rate_ms)
