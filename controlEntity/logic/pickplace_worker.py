"""
Threaded worker for Pick&Place machine serial communication.

Wraps `PickPlaceDevice` operations (connect, move, gripper control) and emits
results back to the UI thread via Qt signals.

Project: EvoFlow Innosuisse
Author: Based on existing EvoFlow protocol
Created: April 2026
"""

from PySide6.QtCore import QObject, Signal, Slot
from evoflow.device.pickplace_device import (
    PickPlaceDevice, PickPlaceCommResult, PickPlaceProtocol
)


class PickPlaceWorker(QObject):
    """
    Run Pick&Place device serial comms on a worker thread and emit structured results.
    
    Signals:
        result: Emits (command_name: str, payload: dict)
        status: Emits (message: str) for general info
        error: Emits (error_message: str) for error conditions
    """
    
    # Signals
    result = Signal(str, object)  # command_name, payload
    status = Signal(str)
    error = Signal(str)
    
    def __init__(self, protocol: PickPlaceProtocol = PickPlaceProtocol.SIMPLE, parent=None):
        super().__init__(parent)
        self._device: Optional[PickPlaceDevice] = None
        self._protocol = protocol
    
    @Slot()
    def start(self):
        """Instantiate the Pick&Place device on this worker thread."""
        try:
            self._device = PickPlaceDevice(protocol=self._protocol)
            self.status.emit(f"Pick&Place worker started ({self._protocol.value} protocol)")
        except Exception as e:
            self.error.emit(f"Failed to create PickPlaceDevice: {e}")
    
    @Slot(str)
    def connect(self, port: str):
        """
        Open the Pick&Place serial connection.
        
        Args:
            port: Serial port path (e.g., '/dev/ttyUSB1' or 'COM5')
        """
        if not self._device:
            self.error.emit("Pick&Place worker not initialized")
            return
        
        try:
            res: PickPlaceCommResult = self._device.connect(port)
            self.result.emit('connect', {'result': res})
        except Exception as e:
            self.error.emit(f"Exception in Pick&Place connect: {e}")
    
    @Slot()
    def disconnect(self):
        """Close the Pick&Place serial connection."""
        if not self._device:
            self.error.emit("Pick&Place worker not initialized")
            return
        
        try:
            res: PickPlaceCommResult = self._device.disconnect()
            self.result.emit('disconnect', {'result': res})
        except Exception as e:
            self.error.emit(f"Exception in Pick&Place disconnect: {e}")
    
    @Slot(float, float, float)
    def move_xyz(self, x: float, y: float, z: float):
        """
        Move to XYZ position.
        
        Args:
            x: X position in mm
            y: Y position in mm
            z: Z position in mm
        """
        if not self._device:
            self.error.emit("Pick&Place worker not initialized")
            return
        
        try:
            res: PickPlaceCommResult = self._device.move_xyz(x, y, z)
            self.result.emit('move', {'result': res, 'x': x, 'y': y, 'z': z})
        except Exception as e:
            self.error.emit(f"Exception moving Pick&Place: {e}")
    
    @Slot(bool)
    def control_gripper(self, open_gripper: bool):
        """
        Control gripper state.
        
        Args:
            open_gripper: True to open, False to close
        """
        if not self._device:
            self.error.emit("Pick&Place worker not initialized")
            return
        
        try:
            res: PickPlaceCommResult = self._device.control_gripper(open_gripper)
            action = "OPEN" if open_gripper else "CLOSE"
            self.result.emit('gripper', {'result': res, 'action': action})
        except Exception as e:
            self.error.emit(f"Exception controlling gripper: {e}")
    
    @Slot()
    def home(self):
        """Send homing command."""
        if not self._device:
            self.error.emit("Pick&Place worker not initialized")
            return
        
        try:
            res: PickPlaceCommResult = self._device.home()
            self.result.emit('home', {'result': res})
        except Exception as e:
            self.error.emit(f"Exception homing Pick&Place: {e}")
