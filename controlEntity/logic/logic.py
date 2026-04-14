"""
Central logic coordinator for the EvoFlow GUI application.

Sets up worker threads for EvoFlow and Pick&Place devices, wiring Qt signals
between UI components and device handlers.

Project: EvoFlow Innosuisse
Author: Based on existing Enantios pattern
Created: April 2026
"""

from PySide6.QtCore import QObject, Signal, QThread, Slot
from controlEntity.logic.evoflow_worker import EvoFlowWorker
from controlEntity.logic.pickplace_worker import PickPlaceWorker, PickPlaceProtocol
from evoflow.device.communication import EvoFlowTelemetry
from typing import Optional, List


class Logic(QObject):
    """Coordinate device workers, wire Qt signals, and forward results to the UI."""
    
    # ===============================
    # EvoFlow Signals
    # ===============================
    
    # Signals FROM workers TO UI
    evoflow_command_result = Signal(str, object)  # command, result dict
    evoflow_telemetry = Signal(object)  # EvoFlowTelemetry
    evoflow_status = Signal(str)  # Status messages
    evoflow_error = Signal(str)  # Error messages
    
    # Signals FROM UI TO workers (requests)
    evoflow_connect_requested = Signal(str, int)  # port, node_id
    evoflow_disconnect_requested = Signal()
    evoflow_set_velocity_requested = Signal(int, float)  # pump_id, velocity
    evoflow_set_temperature_requested = Signal(int, float)  # heater_id, temp
    evoflow_set_stirrer_requested = Signal(int, float)  # stir_id, voltage
    evoflow_start_requested = Signal()
    evoflow_stop_requested = Signal()
    
    # ===============================
    # Pick&Place Signals
    # ===============================
    
    # Signals FROM workers TO UI
    pickplace_command_result = Signal(str, object)  # command, result dict
    pickplace_status = Signal(str)
    pickplace_error = Signal(str)
    
    # Signals FROM UI TO workers (requests)
    pickplace_connect_requested = Signal(str)  # port
    pickplace_disconnect_requested = Signal()
    pickplace_move_requested = Signal(float, float, float)  # x, y, z
    pickplace_gripper_requested = Signal(bool)  # open (True/False)
    pickplace_home_requested = Signal()
    
    def __init__(self):
        super().__init__()
        
        # ===============================
        # EvoFlow Worker Setup
        # ===============================
        self.evoflow_thread = QThread(self)
        self.evoflow_worker = EvoFlowWorker()
        self.evoflow_worker.moveToThread(self.evoflow_thread)
        
        # Wire worker initialization
        self.evoflow_thread.started.connect(self.evoflow_worker.start)
        
        # Wire worker signals to logic signals (forward to UI)
        self.evoflow_worker.result.connect(self._on_evoflow_result)
        self.evoflow_worker.telemetry.connect(self._on_evoflow_telemetry)
        self.evoflow_worker.status.connect(self._on_evoflow_status)
        self.evoflow_worker.error.connect(self._on_evoflow_error)
        
        # Wire logic request signals to worker slots
        self.evoflow_connect_requested.connect(self.evoflow_worker.connect)
        self.evoflow_disconnect_requested.connect(self.evoflow_worker.disconnect)
        self.evoflow_set_velocity_requested.connect(self.evoflow_worker.set_velocity)
        self.evoflow_set_temperature_requested.connect(self.evoflow_worker.set_temperature)
        self.evoflow_set_stirrer_requested.connect(self.evoflow_worker.set_stirrer)
        self.evoflow_start_requested.connect(lambda: self.evoflow_worker.send_action(True))
        self.evoflow_stop_requested.connect(lambda: self.evoflow_worker.send_action(False))
        
        # Start EvoFlow thread
        self.evoflow_thread.start()
        
        # ===============================
        # Pick&Place Worker Setup
        # ===============================
        self.pickplace_thread = QThread(self)
        self.pickplace_worker = PickPlaceWorker(protocol=PickPlaceProtocol.SIMPLE)
        self.pickplace_worker.moveToThread(self.pickplace_thread)
        
        # Wire worker initialization
        self.pickplace_thread.started.connect(self.pickplace_worker.start)
        
        # Wire worker signals to logic signals
        self.pickplace_worker.result.connect(self._on_pickplace_result)
        self.pickplace_worker.status.connect(self._on_pickplace_status)
        self.pickplace_worker.error.connect(self._on_pickplace_error)
        
        # Wire logic request signals to worker slots
        self.pickplace_connect_requested.connect(self.pickplace_worker.connect)
        self.pickplace_disconnect_requested.connect(self.pickplace_worker.disconnect)
        self.pickplace_move_requested.connect(self.pickplace_worker.move_xyz)
        self.pickplace_gripper_requested.connect(self.pickplace_worker.control_gripper)
        self.pickplace_home_requested.connect(self.pickplace_worker.home)
        
        # Start Pick&Place thread
        self.pickplace_thread.start()
        
        # ===============================
        # Internal State
        # ===============================
        self.evoflow_connected = False
        self.pickplace_connected = False
        self.latest_evoflow_telemetry: Optional[EvoFlowTelemetry] = None
    
    # ===============================
    # EvoFlow Result Handlers
    # ===============================
    
    @Slot(str, object)
    def _on_evoflow_result(self, command: str, payload: dict):
        """Handle results from EvoFlow worker."""
        # Update connection state
        if command == 'connect':
            self.evoflow_connected = payload.get('result').success
        elif command == 'disconnect':
            self.evoflow_connected = False
        
        # Forward to UI
        self.evoflow_command_result.emit(command, payload)
    
    @Slot(object)
    def _on_evoflow_telemetry(self, telem: EvoFlowTelemetry):
        """Handle telemetry from EvoFlow worker."""
        self.latest_evoflow_telemetry = telem
        self.evoflow_telemetry.emit(telem)
    
    @Slot(str)
    def _on_evoflow_status(self, message: str):
        """Handle status messages from EvoFlow worker."""
        print(f"[EvoFlow] {message}")
        self.evoflow_status.emit(message)
    
    @Slot(str)
    def _on_evoflow_error(self, message: str):
        """Handle errors from EvoFlow worker."""
        print(f"[EvoFlow ERROR] {message}")
        self.evoflow_error.emit(message)
    
    # ===============================
    # Pick&Place Result Handlers
    # ===============================
    
    @Slot(str, object)
    def _on_pickplace_result(self, command: str, payload: dict):
        """Handle results from Pick&Place worker."""
        # Update connection state
        if command == 'connect':
            self.pickplace_connected = payload.get('result').success
        elif command == 'disconnect':
            self.pickplace_connected = False
        
        # Forward to UI
        self.pickplace_command_result.emit(command, payload)
    
    @Slot(str)
    def _on_pickplace_status(self, message: str):
        """Handle status messages from Pick&Place worker."""
        print(f"[Pick&Place] {message}")
        self.pickplace_status.emit(message)
    
    @Slot(str)
    def _on_pickplace_error(self, message: str):
        """Handle errors from Pick&Place worker."""
        print(f"[Pick&Place ERROR] {message}")
        self.pickplace_error.emit(message)
    
    # ===============================
    # Public Helper Methods
    # ===============================
    
    def is_evoflow_connected(self) -> bool:
        """Check if EvoFlow is connected."""
        return self.evoflow_connected
    
    def is_pickplace_connected(self) -> bool:
        """Check if Pick&Place is connected."""
        return self.pickplace_connected
    
    def get_latest_evoflow_telemetry(self) -> Optional[EvoFlowTelemetry]:
        """Get the most recent EvoFlow telemetry."""
        return self.latest_evoflow_telemetry
