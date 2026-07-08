"""
Setup worker threads for EvoFlow device communication and telemetry processing.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from evoflow.device.evoflow import EvoFlowDevice, EvoFlowTelemetry

class EvoFlowWorker(QObject):
    """Worker class to handle EvoFlow device communication in a separate thread"""
    
    telemetry_updated = Signal(EvoFlowTelemetry)
    evoflow_status_updated = Signal(bool)
    evoflow_comm_status_updated = Signal(bool)
    rpi_temp_updated = Signal(int)
    no_of_evoflow_reset = Signal(int)
    
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
        self._consecutive_not_ok_count = 0
        self._no_of_evoflow_reset = 0
        self._telemetry_timer = None
        self._status_timer = None

    @Slot()
    def start(self):
        """Start device connection and periodic polling timers."""
        try:
            if self._running:
                return

            self._running = True
            self._consecutive_not_ok_count = 0
            self.evoflow.connect()

            if self._telemetry_timer is None:
                self._telemetry_timer = QTimer(self)
                self._telemetry_timer.timeout.connect(self._poll_telemetry)
            if self._status_timer is None:
                self._status_timer = QTimer(self)
                self._status_timer.timeout.connect(self._poll_status_and_temp)

            self._telemetry_timer.start(self.sampling_rate_ms)
            self._status_timer.start(self.sampling_rate_ms)
        except Exception as e:
            # print(f"Failed to connect to EvoFlow device: {e}")
            self._running = False
            return
    
    @Slot()
    def stop(self):
        """Stop polling timers and disconnect device."""
        try:
            if not self._running:
                return

            self._running = False
            self._consecutive_not_ok_count = 0

            if self._telemetry_timer is not None:
                self._telemetry_timer.stop()
            if self._status_timer is not None:
                self._status_timer.stop()

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
    def _poll_telemetry(self):
        """Timer callback to fetch telemetry and emit latest values."""
        if not self._running:
            return

        try:
            if self.evoflow.get_all_telemetry():
                self.telemetry_updated.emit(self.evoflow.evoflow_telemetry)
                self.evoflow_comm_status_updated.emit(True)
            else:
                self.evoflow_comm_status_updated.emit(False)
        except Exception as e:
            print(f"Failed to get telemetry from EvoFlow device: {e}")

    @Slot()
    def _poll_status_and_temp(self):
        """Timer callback to emit status/temp and perform auto-reset check."""
        if not self._running:
            return

        try:
            evoflow_ok = self.evoflow.is_evoflow_ok()
            rpi_temp = self.get_rpi_temp()
            self.evoflow_status_updated.emit(evoflow_ok)
            self.rpi_temp_updated.emit(rpi_temp)

            if not evoflow_ok:
                self._consecutive_not_ok_count += 1
            else:
                self._consecutive_not_ok_count = 0

            threshold = max(1, int((self.auto_reset_after_seconds * 1000) / self.sampling_rate_ms))
            if self._consecutive_not_ok_count >= threshold:
                print("EvoFlow has been NOT OK for the specified duration. Resetting EvoFlow...")
                self._no_of_evoflow_reset += 1
                self.no_of_evoflow_reset.emit(self._no_of_evoflow_reset)
                self.reset_evoflow()
                self._consecutive_not_ok_count = 0
        except Exception as e:
            print(f"Failed to check EvoFlow status / RPi temp: {e}")
    
    @Slot()
    def reset_evoflow(self):
        """Reset the EvoFlow device"""
        self.evoflow.reset_evoflow()

    def get_rpi_temp(self) -> int:
        """Get the Raspberry Pi's CPU temperature in Celsius"""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_str = f.read().strip()
                temp_c = int(temp_str) // 1000  # Convert from millidegrees to degrees
                return temp_c
        except Exception as e:
            print(f"Failed to read Raspberry Pi CPU temperature: {e}")
            return -1
        
    def low_pass_filter(self, current_value: float, previous_value: float, alpha: float = 0.1) -> float:
        """Apply a simple low-pass filter to smoothen"""
        
