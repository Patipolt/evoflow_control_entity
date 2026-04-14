"""
Threaded worker for EvoFlow device serial communication.

Wraps `EvoFlowDevice` operations (connect, telemetry polling, setpoint control) and emits
results back to the UI thread via Qt signals. Runs continuous RX/TX loops at appropriate rates.

Project: EvoFlow Innosuisse
Author: Based on existing EvoFlow protocol
Created: April 2026
"""

import time
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from evoflow.device.evoflow_device import EvoFlowDevice, EvoFlowCommResult
from evoflow.device.communication import EvoFlowTelemetry


class EvoFlowWorker(QObject):
    """
    Run EvoFlow device serial comms on a worker thread and emit structured results.
    
    Signals:
        result: Emits (command_name: str, payload: dict)
        telemetry: Emits (EvoFlowTelemetry) at ~100 Hz
        status: Emits (message: str) for general info
        error: Emits (error_message: str) for error conditions
    """
    
    # Signals
    result = Signal(str, object)  # command_name, payload
    telemetry = Signal(object)  # EvoFlowTelemetry
    status = Signal(str)
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._device: Optional[EvoFlowDevice] = None
        self._rx_timer: Optional[QTimer] = None
        self._tx_timer: Optional[QTimer] = None
        self._running = False
    
    @Slot()
    def start(self):
        """Instantiate the EvoFlow device on this worker thread."""
        try:
            self._device = EvoFlowDevice()
            self._running = False  # Will be set True when connected
            self.status.emit("EvoFlow worker started")
        except Exception as e:
            self.error.emit(f"Failed to create EvoFlowDevice: {e}")
    
    @Slot(str, int)
    def connect(self, port: str, node_id: int = 1):
        """
        Open the EvoFlow serial connection.
        
        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0' or 'COM3')
            node_id: Target node ID (default: 1)
        """
        if not self._device:
            self.error.emit("EvoFlow worker not initialized")
            return
        
        try:
            self._device.node_id = node_id
            res: EvoFlowCommResult = self._device.connect(port)
            
            if res.success:
                # Start RX/TX timers
                self._start_communication_loops()
                self._running = True
            
            self.result.emit('connect', {'result': res})
        except Exception as e:
            self.error.emit(f"Exception in EvoFlow connect: {e}")
    
    @Slot()
    def disconnect(self):
        """Close the EvoFlow serial connection."""
        if not self._device:
            self.error.emit("EvoFlow worker not initialized")
            return
        
        try:
            # Stop timers
            self._stop_communication_loops()
            self._running = False
            
            res: EvoFlowCommResult = self._device.disconnect()
            self.result.emit('disconnect', {'result': res})
        except Exception as e:
            self.error.emit(f"Exception in EvoFlow disconnect: {e}")
    
    @Slot(int, float)
    def set_velocity(self, pump_id: int, velocity: float):
        """
        Set pump velocity setpoint.
        
        Args:
            pump_id: 1 or 2
            velocity: Target velocity in rps
        """
        if not self._device:
            self.error.emit("EvoFlow worker not initialized")
            return
        
        try:
            self._device.set_velocity(pump_id, velocity)
            self.status.emit(f"Pump {pump_id} velocity set to {velocity:.2f} rps")
        except Exception as e:
            self.error.emit(f"Exception setting velocity: {e}")
    
    @Slot(int, float)
    def set_temperature(self, heater_id: int, temperature: float):
        """
        Set temperature setpoint.
        
        Args:
            heater_id: 1 or 2
            temperature: Target temperature in °C
        """
        if not self._device:
            self.error.emit("EvoFlow worker not initialized")
            return
        
        try:
            self._device.set_temperature(heater_id, temperature)
            self.status.emit(f"Heater {heater_id} temperature set to {temperature:.2f} °C")
        except Exception as e:
            self.error.emit(f"Exception setting temperature: {e}")
    
    @Slot(int, float)
    def set_stirrer(self, stir_id: int, voltage: float):
        """
        Set stirrer voltage.
        
        Args:
            stir_id: 1 or 2
            voltage: Target voltage in V
        """
        if not self._device:
            self.error.emit("EvoFlow worker not initialized")
            return
        
        try:
            self._device.set_stirrer(stir_id, voltage)
            self.status.emit(f"Stirrer {stir_id} voltage set to {voltage:.2f} V")
        except Exception as e:
            self.error.emit(f"Exception setting stirrer: {e}")
    
    @Slot(bool)
    def send_action(self, run_state: bool):
        """
        Send start/stop action.
        
        Args:
            run_state: True to start, False to stop
        """
        if not self._device:
            self.error.emit("EvoFlow worker not initialized")
            return
        
        try:
            res: EvoFlowCommResult = self._device.send_action(run_state)
            action = "START" if run_state else "STOP"
            self.result.emit('action', {'result': res, 'action': action})
        except Exception as e:
            self.error.emit(f"Exception sending action: {e}")
    
    def _start_communication_loops(self):
        """Start RX (100 Hz) and TX (20 Hz) timers."""
        # RX timer: Read telemetry at 100 Hz
        self._rx_timer = QTimer()
        self._rx_timer.timeout.connect(self._rx_tick)
        self._rx_timer.start(10)  # 10 ms = 100 Hz
        
        # TX timer: Send setpoints at 20 Hz
        self._tx_timer = QTimer()
        self._tx_timer.timeout.connect(self._tx_tick)
        self._tx_timer.start(50)  # 50 ms = 20 Hz
    
    def _stop_communication_loops(self):
        """Stop RX/TX timers."""
        if self._rx_timer:
            self._rx_timer.stop()
            self._rx_timer = None
        
        if self._tx_timer:
            self._tx_timer.stop()
            self._tx_timer = None
    
    @Slot()
    def _rx_tick(self):
        """RX tick: Read and emit telemetry (100 Hz)."""
        if not self._device or not self._running:
            return
        
        try:
            telem = self._device.read_telemetry()
            if telem:
                self.telemetry.emit(telem)
        except Exception as e:
            self.error.emit(f"RX tick error: {e}")
    
    @Slot()
    def _tx_tick(self):
        """TX tick: Send setpoints (20 Hz)."""
        if not self._device or not self._running:
            return
        
        try:
            # Only send if bootstrapped
            if self._device.bootstrapped:
                self._device.send_setpoints()
        except Exception as e:
            self.error.emit(f"TX tick error: {e}")
