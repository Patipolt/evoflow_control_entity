"""
Serial interface for the Pick&Place machine control system.

Provides `PickPlaceDevice` to connect over serial and send commands. Supports both:
1. Full protocol (COBS + CRC) - compatible with EvoFlow protocol
2. Simple string protocol - for rapid development

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
from enum import Enum


class PickPlaceProtocol(Enum):
    """Protocol selection for Pick&Place communication."""
    FULL = "full"  # COBS + CRC protocol
    SIMPLE = "simple"  # String-based commands


@dataclass
class PickPlaceCommResult:
    """Result wrapper for Pick&Place serial commands."""
    success: bool
    message: str


class PickPlaceDevice:
    """
    Low-level communication handler for Pick&Place Nucleo.
    
    Supports two protocol modes:
    - FULL: Uses COBS encoding + CRC16 (same as EvoFlow)
    - SIMPLE: String commands like "MOVE 10.5 20.3 5.0\n"
    
    Thread-safe for use with worker threads.
    """
    
    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 115200,
        timeout: float = 0.1,
        protocol: PickPlaceProtocol = PickPlaceProtocol.SIMPLE
    ):
        """
        Configure serial settings and initialize state.
        
        Args:
            port: Serial port path (auto-detects if None)
            baudrate: Serial baud rate (default: 115200)
            timeout: Read timeout in seconds
            protocol: Protocol mode (FULL or SIMPLE)
        """
        # Serial configuration
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.protocol = protocol
        
        # Serial connection
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        self.communication_lock = threading.Lock()
        
        # State (for FULL protocol)
        if protocol == PickPlaceProtocol.FULL:
            from evoflow.device.communication import ProtocolEncoder, CobsStreamParser
            self.encoder = ProtocolEncoder()
            self.parser = CobsStreamParser()
            self.node_id = 2  # Different from EvoFlow
        
        # Current position/state
        self.x_pos = 0.0
        self.y_pos = 0.0
        self.z_pos = 0.0
        self.gripper_open = False
    
    def connect(self, port: Optional[str] = None) -> PickPlaceCommResult:
        """
        Open serial connection to Pick&Place Nucleo.
        
        Args:
            port: Override port path (uses self.port if None)
        
        Returns:
            PickPlaceCommResult with success status
        """
        with self.communication_lock:
            if port:
                self.port = port
            
            if self.port is None:
                return PickPlaceCommResult(
                    success=False,
                    message="No port specified"
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
                
                if self.protocol == PickPlaceProtocol.FULL:
                    self.parser.reset()
                
                return PickPlaceCommResult(
                    success=True,
                    message=f"Connected to Pick&Place on {self.port}"
                )
            
            except serial.SerialException as e:
                self.is_connected = False
                return PickPlaceCommResult(
                    success=False,
                    message=f"Failed to connect: {e}"
                )
    
    def disconnect(self) -> PickPlaceCommResult:
        """Close serial connection."""
        with self.communication_lock:
            if self.serial_connection and self.serial_connection.is_open:
                try:
                    self.serial_connection.close()
                    self.is_connected = False
                    return PickPlaceCommResult(
                        success=True,
                        message="Disconnected from Pick&Place"
                    )
                except Exception as e:
                    return PickPlaceCommResult(
                        success=False,
                        message=f"Error during disconnect: {e}"
                    )
            else:
                return PickPlaceCommResult(
                    success=True,
                    message="Already disconnected"
                )
    
    def move_xyz(self, x: float, y: float, z: float) -> PickPlaceCommResult:
        """
        Move to XYZ position.
        
        Args:
            x: X position in mm
            y: Y position in mm
            z: Z position in mm
        
        Returns:
            PickPlaceCommResult with success status
        """
        if not self.is_connected or not self.serial_connection:
            return PickPlaceCommResult(
                success=False,
                message="Not connected"
            )
        
        try:
            if self.protocol == PickPlaceProtocol.SIMPLE:
                # Send simple string command
                cmd = f"MOVE {x:.2f} {y:.2f} {z:.2f}\n"
                with self.communication_lock:
                    self.serial_connection.write(cmd.encode())
            else:
                # Use full protocol
                packet = self.encoder.encode_pickplace_move(self.node_id, x, y, z)
                with self.communication_lock:
                    self.serial_connection.write(packet)
            
            # Update internal state
            self.x_pos = x
            self.y_pos = y
            self.z_pos = z
            
            return PickPlaceCommResult(
                success=True,
                message=f"Move to ({x:.2f}, {y:.2f}, {z:.2f}) sent"
            )
        
        except Exception as e:
            return PickPlaceCommResult(
                success=False,
                message=f"Failed to send move command: {e}"
            )
    
    def control_gripper(self, open_gripper: bool) -> PickPlaceCommResult:
        """
        Control gripper state.
        
        Args:
            open_gripper: True to open, False to close
        
        Returns:
            PickPlaceCommResult with success status
        """
        if not self.is_connected or not self.serial_connection:
            return PickPlaceCommResult(
                success=False,
                message="Not connected"
            )
        
        try:
            if self.protocol == PickPlaceProtocol.SIMPLE:
                # Send simple string command
                cmd = f"GRIP {'OPEN' if open_gripper else 'CLOSE'}\n"
                with self.communication_lock:
                    self.serial_connection.write(cmd.encode())
            else:
                # Use full protocol
                packet = self.encoder.encode_pickplace_gripper(self.node_id, open_gripper)
                with self.communication_lock:
                    self.serial_connection.write(packet)
            
            self.gripper_open = open_gripper
            
            action = "OPEN" if open_gripper else "CLOSE"
            return PickPlaceCommResult(
                success=True,
                message=f"Gripper {action} sent"
            )
        
        except Exception as e:
            return PickPlaceCommResult(
                success=False,
                message=f"Failed to send gripper command: {e}"
            )
    
    def home(self) -> PickPlaceCommResult:
        """Send homing command."""
        if not self.is_connected or not self.serial_connection:
            return PickPlaceCommResult(
                success=False,
                message="Not connected"
            )
        
        try:
            if self.protocol == PickPlaceProtocol.SIMPLE:
                cmd = "HOME\n"
                with self.communication_lock:
                    self.serial_connection.write(cmd.encode())
            
            return PickPlaceCommResult(
                success=True,
                message="Homing command sent"
            )
        
        except Exception as e:
            return PickPlaceCommResult(
                success=False,
                message=f"Failed to send home command: {e}"
            )
    
    def read_response(self) -> Optional[str]:
        """
        Read response from Pick&Place (for SIMPLE protocol).
        
        Returns:
            Response string or None
        """
        if not self.is_connected or not self.serial_connection:
            return None
        
        try:
            if self.protocol == PickPlaceProtocol.SIMPLE:
                # Read until newline
                available = self.serial_connection.in_waiting
                if available > 0:
                    line = self.serial_connection.readline()
                    return line.decode().strip()
            
            return None
        
        except Exception as e:
            print(f"Error reading response: {e}")
            return None
    
    @staticmethod
    def list_available_ports() -> List[Tuple[str, str]]:
        """Return a list of available serial ports with descriptions."""
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]
