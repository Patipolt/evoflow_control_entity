"""
Serial interface for the EvoFlow bioreactor control system.

Provides `EvoFlowDevice` to connect over serial, send setpoint commands, and parse real-time
telemetry at 100 Hz for dual pump/temperature/stirrer control.

Project: EvoFlow Innosuisse
Author: Based on existing EvoFlow protocol
Created: April 2026
"""

import serial
import serial.tools.list_ports
import time
import threading
from typing import Optional, List, Tuple
from dataclasses import dataclass
from evoflow.device.communication import (
    ProtocolEncoder, CobsStreamParser,
    decode_evoflow_telemetry, EvoFlowTelemetry,
    MSG_TELEM, MSG_ACK_CMD_SET, MSG_ACK_ACTION
)


@dataclass
class EvoFlowCommResult:
    """Result wrapper for EvoFlow serial commands."""
    success: bool
    message: str


class EvoFlowDevice:
    """
    Low-level communication handler for EvoFlow Nucleo.
    
    Handles serial connection, protocol encoding/decoding, and maintains
    device state. Thread-safe for use with worker threads.
    """
    
    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 230400,
        timeout: float = 0.01,
        node_id: int = 1
    ):
        """
        Configure serial settings and initialize state.
        
        Args:
            port: Serial port path (auto-detects if None)
            baudrate: Serial baud rate (default: 230400)
            timeout: Read timeout in seconds
            node_id: Target node ID for commands
        """
        # Serial configuration
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.node_id = node_id
        
        # Serial connection
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        self.communication_lock = threading.Lock()
        
        # Protocol handlers
        self.encoder = ProtocolEncoder()
        self.parser = CobsStreamParser()
        
        # Bootstrap state
        self.bootstrapped = False
        self.last_uptime_s: Optional[int] = None
        
        # Current setpoints (what we're commanding)
        self.cmd_vel_m1 = 0.0
        self.cmd_vel_m2 = 0.0
        self.cmd_temp_m1 = 32.0
        self.cmd_temp_m2 = 32.0
        self.cmd_stir_m1 = 9.0
        self.cmd_stir_m2 = 9.0
        
        # Latest telemetry
        self.latest_telemetry: Optional[EvoFlowTelemetry] = None
        
        # ACK tracking
        self.pending_ack_seq: Optional[int] = None
        self.ack_received = threading.Event()
    
    def connect(self, port: Optional[str] = None) -> EvoFlowCommResult:
        """
        Open serial connection to EvoFlow Nucleo.
        
        Args:
            port: Override port path (uses self.port if None)
        
        Returns:
            EvoFlowCommResult with success status
        """
        with self.communication_lock:
            if port:
                self.port = port
            
            if self.port is None:
                return EvoFlowCommResult(
                    success=False,
                    message="No port specified and auto-detection not implemented"
                )
            
            try:
                if self.serial_connection and self.serial_connection.is_open:
                    self.serial_connection.close()
                
                self.serial_connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=0.2,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
                
                # Flush buffers
                self.serial_connection.reset_input_buffer()
                self.serial_connection.reset_output_buffer()
                
                self.is_connected = True
                self.bootstrapped = False  # Need to re-bootstrap
                self.parser.reset()
                
                return EvoFlowCommResult(
                    success=True,
                    message=f"Connected to EvoFlow on {self.port}"
                )
            
            except serial.SerialException as e:
                self.is_connected = False
                return EvoFlowCommResult(
                    success=False,
                    message=f"Failed to connect: {e}"
                )
    
    def disconnect(self) -> EvoFlowCommResult:
        """Close serial connection."""
        with self.communication_lock:
            if self.serial_connection and self.serial_connection.is_open:
                try:
                    self.serial_connection.close()
                    self.is_connected = False
                    self.bootstrapped = False
                    return EvoFlowCommResult(
                        success=True,
                        message="Disconnected from EvoFlow"
                    )
                except Exception as e:
                    return EvoFlowCommResult(
                        success=False,
                        message=f"Error during disconnect: {e}"
                    )
            else:
                return EvoFlowCommResult(
                    success=True,
                    message="Already disconnected"
                )
    
    def send_setpoints(self) -> EvoFlowCommResult:
        """
        Send current setpoints to the Nucleo.
        
        Returns:
            EvoFlowCommResult with success status
        """
        if not self.is_connected or not self.serial_connection:
            return EvoFlowCommResult(
                success=False,
                message="Not connected"
            )
        
        try:
            packet = self.encoder.encode_evoflow_setpoints(
                self.node_id,
                self.cmd_vel_m1,
                self.cmd_vel_m2,
                self.cmd_temp_m1,
                self.cmd_temp_m2,
                self.cmd_stir_m1,
                self.cmd_stir_m2
            )
            
            with self.communication_lock:
                self.serial_connection.write(packet)
            
            return EvoFlowCommResult(
                success=True,
                message="Setpoints sent"
            )
        
        except Exception as e:
            return EvoFlowCommResult(
                success=False,
                message=f"Failed to send setpoints: {e}"
            )
    
    def send_action(self, run_state: bool) -> EvoFlowCommResult:
        """
        Send start/stop action to the Nucleo.
        
        Args:
            run_state: True to start, False to stop
        
        Returns:
            EvoFlowCommResult with success status
        """
        if not self.is_connected or not self.serial_connection:
            return EvoFlowCommResult(
                success=False,
                message="Not connected"
            )
        
        try:
            packet = self.encoder.encode_action(self.node_id, run_state)
            
            with self.communication_lock:
                self.serial_connection.write(packet)
            
            action = "START" if run_state else "STOP"
            return EvoFlowCommResult(
                success=True,
                message=f"Action {action} sent"
            )
        
        except Exception as e:
            return EvoFlowCommResult(
                success=False,
                message=f"Failed to send action: {e}"
            )
    
    def read_telemetry(self) -> Optional[EvoFlowTelemetry]:
        """
        Read and parse available telemetry from serial port.
        Non-blocking. Returns latest telemetry if available, None otherwise.
        
        Returns:
            EvoFlowTelemetry object or None
        """
        if not self.is_connected or not self.serial_connection:
            return None
        
        try:
            # Read available bytes
            available = self.serial_connection.in_waiting
            if available > 0:
                data = self.serial_connection.read(available)
                
                # Parse frames
                for msg_id, node_id, payload in self.parser.feed(data):
                    if msg_id == MSG_TELEM and node_id == self.node_id:
                        telem = decode_evoflow_telemetry(payload)
                        if telem:
                            # Bootstrap on first telemetry
                            if not self.bootstrapped:
                                self._bootstrap_from_telemetry(telem)
                            
                            # Detect MCU reset
                            if self.last_uptime_s is not None and telem.uptime_s < self.last_uptime_s:
                                self.bootstrapped = False
                                self._bootstrap_from_telemetry(telem)
                            
                            self.last_uptime_s = telem.uptime_s
                            self.latest_telemetry = telem
                            return telem
                    
                    elif msg_id == MSG_ACK_CMD_SET:
                        # Handle ACK (for future use)
                        pass
                    
                    elif msg_id == MSG_ACK_ACTION:
                        # Handle action ACK
                        pass
            
            return None
        
        except Exception as e:
            print(f"Error reading telemetry: {e}")
            return None
    
    def _bootstrap_from_telemetry(self, telem: EvoFlowTelemetry):
        """
        Bootstrap host setpoints from MCU's echoed values.
        This ensures we start from MCU's current state.
        """
        self.cmd_vel_m1 = telem.cmd_vel_m1
        self.cmd_vel_m2 = telem.cmd_vel_m2
        self.cmd_temp_m1 = telem.cmd_temp_m1
        self.cmd_temp_m2 = telem.cmd_temp_m2
        self.cmd_stir_m1 = telem.cmd_stir_m1
        self.cmd_stir_m2 = telem.cmd_stir_m2
        self.bootstrapped = True
        print(f"[EvoFlow] Bootstrapped from node {self.node_id}: "
              f"vel=({telem.cmd_vel_m1:.2f}, {telem.cmd_vel_m2:.2f}), "
              f"temp=({telem.cmd_temp_m1:.2f}, {telem.cmd_temp_m2:.2f})")
    
    def set_velocity(self, pump_id: int, velocity: float):
        """Update pump velocity setpoint (does not send immediately)."""
        if pump_id == 1:
            self.cmd_vel_m1 = velocity
        elif pump_id == 2:
            self.cmd_vel_m2 = velocity
    
    def set_temperature(self, heater_id: int, temperature: float):
        """Update temperature setpoint (does not send immediately)."""
        if heater_id == 1:
            self.cmd_temp_m1 = temperature
        elif heater_id == 2:
            self.cmd_temp_m2 = temperature
    
    def set_stirrer(self, stir_id: int, voltage: float):
        """Update stirrer voltage setpoint (does not send immediately)."""
        if stir_id == 1:
            self.cmd_stir_m1 = voltage
        elif stir_id == 2:
            self.cmd_stir_m2 = voltage
    
    @staticmethod
    def list_available_ports() -> List[Tuple[str, str]]:
        """Return a list of available serial ports with descriptions."""
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]
