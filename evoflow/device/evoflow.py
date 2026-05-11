"""
Low-level API for EvoFlow devices.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

import struct

import serial
import time

from evoflow.protocol import (
    ProtocolPacket,
    Component,
    CMD,
    ADDR_GUI,
    ADDR_EVOFLOW_NUCLEO,
    build_packet,
    cobs_decode,
    parse_packet,
)

verbose = False  # Set to True to enable debug prints

class EvoFlowTelemetry:
    """Structured data class for EvoFlow telemetry"""
    def __init__(self):
        self.pump_1_status  : bool = False
        self.pump_1_sp      : float = 0.0
        self.pump_1_speed   : float = 0.0
        self.pump_2_status  : bool = False
        self.pump_2_sp      : float = 0.0
        self.pump_2_speed   : float = 0.0
        self.pump_3_status  : bool = False
        self.pump_3_sp      : float = 0.0
        self.pump_3_speed   : float = 0.0
        self.pump_4_status  : bool = False
        self.pump_4_sp      : float = 0.0
        self.pump_4_speed   : float = 0.0

        self.magneticStirrer_bioreactor_status          : bool = False
        self.magneticStirrer_bioreactor_sp              : float = 0.0
        self.magneticStirrer_bioreactor_speed           : float = 0.0
        self.magneticStirrer_bioreactor_fan_duty_cycle  : float = 0.0

        self.magneticStirrer_lagoon_status          : bool = False
        self.magneticStirrer_lagoon_sp              : float = 0.0
        self.magneticStirrer_lagoon_speed           : float = 0.0
        self.magneticStirrer_lagoon_fan_duty_cycle  : float  = 0.0

        self.valve_bio2lag_status   : bool = False
        self.valve_sug2lag_status   : bool = False

        self.od_bioreactor_status   : bool = False
        self.od_bioreactor_value    : float = 0.0
        self.od_lagoon_status       : bool = False
        self.od_lagoon_value        : float = 0.0

        self.tempCtrl_bioreactor_status             : bool = False
        self.tempCtrl_bioreactor_sp                 : float = 0.0
        self.tempCtrl_bioreactor_value              : float = 0.0
        self.tempCtrl_bioreactor_heater_duty_cycle  : float = 0.0

        self.tempCtrl_lagoon_status             : bool = False
        self.tempCtrl_lagoon_sp                 : float = 0.0
        self.tempCtrl_lagoon_value              : float = 0.0
        self.tempCtrl_lagoon_heater_duty_cycle  : float = 0.0

        self.phtCount_lagoon_status     : bool = False
        self.phtCount_lagoon_value      : float = 0.0
        self.phtCount_lagoon_overlight  : bool = False


class EvoFlowDevice:
    """Class representing the EvoFlow device, handling serial communication and telemetry."""
    def __init__(
        self,
        port: str,
        baudrate: int = 2000000,
        sender_addr: int = ADDR_GUI,
        receiver_addr: int = ADDR_EVOFLOW_NUCLEO,
    ):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self._rx_buffer = bytearray()
        self.evoflow_telemetry = EvoFlowTelemetry()
        self.profile_telemetry = False

        self.protocol_packet = ProtocolPacket(
            sender=sender_addr,
            receiver_addr=receiver_addr,
            is_write=False,
            id1=0,
            id2=0,
            payload=b"",
        )

    def connect(self):
        """Establish serial connection to the EvoFlow device."""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0.5)
            print(f"Connected to EvoFlow device on {self.port} at {self.baudrate} baud.")
        except serial.SerialException as e:
            print(f"Failed to connect to EvoFlow device: {e}")
            raise

    def disconnect(self):
        """Close the serial connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Disconnected from EvoFlow device.")

    def read_serial(self) -> bytes:
        """Read data from serial port until delimiter (0x00) is found, return the raw packet without the delimiter."""
        if not self.serial or not self.serial.is_open:
            raise serial.SerialException("Serial port is not open")

        while True:
            delimiter_index = self._rx_buffer.find(0x00)
            if delimiter_index != -1:
                packet = bytes(self._rx_buffer[:delimiter_index])
                del self._rx_buffer[: delimiter_index + 1]

                # Ignore empty frames from repeated delimiters/noise.
                if not packet:
                    continue
                return packet

            bytes_waiting = self.serial.in_waiting
            bytes_to_read = bytes_waiting if bytes_waiting > 0 else 1
            chunk = self.serial.read(bytes_to_read)
            if not chunk:
                raise serial.SerialException("Timeout while reading from serial port")
            self._rx_buffer.extend(chunk)

    def set_on_off_pumps(self, pump_1_status: bool, pump_2_status: bool, pump_3_status: bool, pump_4_status: bool):
        """Send command to start/stop pumps based on their status."""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.PUMP
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([
                (1 if pump_1_status else 0),
                (1 if pump_2_status else 0),
                (1 if pump_3_status else 0),
                (1 if pump_4_status else 0),
            ])

            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(f"Sent pump status command: {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send pump status command: {e}")
            raise

    def get_on_off_pumps(self):
        """Read start/stop pump status from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.PUMP
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([0, 0, 0, 0])
            
            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes) 
                if verbose:
                    print(f"Sent pump status read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                pump_statuses = decoded_protocol_packet.payload
                self.evoflow_telemetry.pump_1_status = bool(pump_statuses[0])
                self.evoflow_telemetry.pump_2_status = bool(pump_statuses[1])
                self.evoflow_telemetry.pump_3_status = bool(pump_statuses[2])
                self.evoflow_telemetry.pump_4_status = bool(pump_statuses[3])
                if verbose:
                    print(f"Received pump status: {pump_statuses.hex()}")
        except serial.SerialException as e:
            print(f"Failed to read pump status: {e}")
            raise
    
    def set_setpoint_pumps(self, pump_1_sp: float, pump_2_sp: float, pump_3_sp: float, pump_4_sp: float):
        """Send command to set pump speed based on their setpoints."""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.PUMP
            self.protocol_packet.id2 = CMD.SET_POINT
            self.protocol_packet.payload = bytes(struct.pack('<4f', pump_1_sp, pump_2_sp, pump_3_sp, pump_4_sp))

            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(f"Sent pump setpoint command: {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send pump setpoint command: {e}")
            raise

    def get_setpoint_pumps(self):
        """Read pump speed setpoints from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.PUMP
            self.protocol_packet.id2 = CMD.SET_POINT
            self.protocol_packet.payload = bytes(struct.pack('<4f', 0.0, 0.0, 0.0, 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent pump setpoint read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                pump_sps = struct.unpack('<4f', decoded_protocol_packet.payload)
                self.evoflow_telemetry.pump_1_sp = pump_sps[0]
                self.evoflow_telemetry.pump_2_sp = pump_sps[1]
                self.evoflow_telemetry.pump_3_sp = pump_sps[2]
                self.evoflow_telemetry.pump_4_sp = pump_sps[3]
                if verbose:
                    print(f"Received pump setpoints: {pump_sps}")
        except serial.SerialException as e:
            print(f"Failed to read pump setpoints: {e}")
            raise

    def get_speed_pumps(self):
        """Read pump speeds from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.PUMP
            self.protocol_packet.id2 = CMD.SPEED
            self.protocol_packet.payload = bytes(struct.pack('<4f', 0.0, 0.0, 0.0, 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes)
            if verbose:
                print(f"Sent pump speed read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                pump_speeds = struct.unpack('<4f', decoded_protocol_packet.payload)
                self.evoflow_telemetry.pump_1_speed = pump_speeds[0]
                self.evoflow_telemetry.pump_2_speed = pump_speeds[1]
                self.evoflow_telemetry.pump_3_speed = pump_speeds[2]
                self.evoflow_telemetry.pump_4_speed = pump_speeds[3]
                if verbose:
                    print(f"Received pump speeds: {pump_speeds}")
        except serial.SerialException as e:
            print(f"Failed to read pump speeds: {e}")
            raise

    def set_on_off_valves(self, valve_bio2lag_status: bool, valve_sug2lag_status: bool):
        """Send command to open/close valves based on their status."""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.VALVE
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([
                (1 if valve_bio2lag_status else 0),
                (1 if valve_sug2lag_status else 0),
            ])

            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(f"Sent valve status command: {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send valve status command: {e}")
            raise

    def get_on_off_valves(self):
        """Read open/close valve status from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.VALVE
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([0, 0])
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent valve status read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                valve_statuses = decoded_protocol_packet.payload
                self.evoflow_telemetry.valve_bio2lag_status = bool(valve_statuses[0])
                self.evoflow_telemetry.valve_sug2lag_status = bool(valve_statuses[1])
                if verbose:
                    print(f"Received valve status: {valve_statuses.hex()}")
        except serial.SerialException as e:
            print(f"Failed to read valve status: {e}")
            raise

    def set_on_off_temp_ctrls(self, tempCtrl_bioreactor_status: bool, tempCtrl_lagoon_status: bool):
        """Send command to turn on/off temperature controllers based on their status."""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.TEMP_MODULE
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([
                (1 if tempCtrl_bioreactor_status else 0),
                (1 if tempCtrl_lagoon_status else 0),
            ])

            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(f"Sent temperature controller status command: {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send temperature controller status command: {e}")
            raise
    
    def get_on_off_temp_ctrls(self):
        """Read on/off temperature controller status from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.TEMP_MODULE
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([0, 0])
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent temperature controller status read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                temp_ctrl_statuses = decoded_protocol_packet.payload
                self.evoflow_telemetry.tempCtrl_bioreactor_status = bool(temp_ctrl_statuses[0])
                self.evoflow_telemetry.tempCtrl_lagoon_status = bool(temp_ctrl_statuses[1])
                if verbose:
                    print(f"Received temperature controller status: {temp_ctrl_statuses.hex()}")
        except serial.SerialException as e:
            print(f"Failed to read temperature controller status: {e}")
            raise
    
    def set_setpoint_temp_ctrls(self, tempCtrl_bioreactor_sp: float, tempCtrl_lagoon_sp: float):
        """Send command to set temperature controller setpoints."""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.TEMP_MODULE
            self.protocol_packet.id2 = CMD.SET_POINT
            self.protocol_packet.payload = bytes(struct.pack('<2f', tempCtrl_bioreactor_sp, tempCtrl_lagoon_sp))

            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(f"Sent temperature controller setpoint command: {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send temperature controller setpoint command: {e}")
            raise

    def get_setpoint_temp_ctrls(self):
        """Read temperature controller setpoints from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.TEMP_MODULE
            self.protocol_packet.id2 = CMD.SET_POINT
            self.protocol_packet.payload = bytes(struct.pack('<2f', 0.0, 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent temperature controller setpoint read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                temp_ctrl_sps = struct.unpack('<2f', decoded_protocol_packet.payload)
                self.evoflow_telemetry.tempCtrl_bioreactor_sp = temp_ctrl_sps[0]
                self.evoflow_telemetry.tempCtrl_lagoon_sp = temp_ctrl_sps[1]
                if verbose:
                    print(f"Received temperature controller setpoints: {temp_ctrl_sps}")
        except serial.SerialException as e:
            print(f"Failed to read temperature controller setpoints: {e}")
            raise
    
    def get_temperature_temp_ctrls(self):
        """Read temperature controller values from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.TEMP_MODULE
            self.protocol_packet.id2 = CMD.TEMPERATURE
            self.protocol_packet.payload = bytes(struct.pack('<2f', 0.0, 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent temperature controller value read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                temp_ctrl_values = struct.unpack('<2f', decoded_protocol_packet.payload)
                self.evoflow_telemetry.tempCtrl_bioreactor_value = temp_ctrl_values[0]
                self.evoflow_telemetry.tempCtrl_lagoon_value = temp_ctrl_values[1]
                if verbose:
                    print(f"Received temperature controller values: {temp_ctrl_values}")
        except serial.SerialException as e:
            print(f"Failed to read temperature controller values: {e}")
            raise
    
    def get_heater_duty_cycle_temp_ctrls(self):
        """Read temperature controller heater duty cycles from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.TEMP_MODULE
            self.protocol_packet.id2 = CMD.HEATER_DUTY_CYCLE
            self.protocol_packet.payload = bytes(struct.pack('<2f', 0.0, 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent temperature controller heater duty cycle read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                temp_ctrl_heater_duty_cycles = struct.unpack('<2f', decoded_protocol_packet.payload)
                self.evoflow_telemetry.tempCtrl_bioreactor_heater_duty_cycle = temp_ctrl_heater_duty_cycles[0]
                self.evoflow_telemetry.tempCtrl_lagoon_heater_duty_cycle = temp_ctrl_heater_duty_cycles[1]
                if verbose:
                    print(f"Received temperature controller heater duty cycles: {temp_ctrl_heater_duty_cycles}")
        except serial.SerialException as e:
            print(f"Failed to read temperature controller heater duty cycles: {e}")
            raise

    def set_on_off_od_ctrls(self, od_bioreactor_status: bool, od_lagoon_status: bool):
        """Send command to turn on/off OD controllers based on their status."""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.OD_MODULE
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([
                (1 if od_bioreactor_status else 0),
                (1 if od_lagoon_status else 0),
            ])

            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(f"Sent OD controller status command: {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send OD controller status command: {e}")
            raise
    
    def get_on_off_od_ctrls(self):
        """Read on/off OD controller status from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.OD_MODULE
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([0, 0])
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent OD controller status read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                od_ctrl_statuses = decoded_protocol_packet.payload
                self.evoflow_telemetry.od_bioreactor_status = bool(od_ctrl_statuses[0])
                self.evoflow_telemetry.od_lagoon_status = bool(od_ctrl_statuses[1])
                if verbose:
                    print(f"Received OD controller status: {od_ctrl_statuses.hex()}")
        except serial.SerialException as e:
            print(f"Failed to read OD controller status: {e}")
            raise
    
    def get_od_value_od_ctrls(self):
        """Read OD values from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.OD_MODULE
            self.protocol_packet.id2 = CMD.OD_VALUE
            self.protocol_packet.payload = bytes(struct.pack('<2f', 0.0, 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes)
            if verbose:
                print(f"Sent OD controller value read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                od_values = struct.unpack('<2f', decoded_protocol_packet.payload)
                self.evoflow_telemetry.od_bioreactor_value = od_values[0]
                self.evoflow_telemetry.od_lagoon_value = od_values[1]
                if verbose:
                    print(f"Received OD controller values: {od_values}")
        except serial.SerialException as e:
            print(f"Failed to read OD controller values: {e}")
            raise

    def set_on_off_magnetic_stirrers(self, magneticStirrer_bioreactor_status: bool, magneticStirrer_lagoon_status: bool):
        """Send command to turn on/off magnetic stirrers based on their status."""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.MAG_MODULE
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([
                (1 if magneticStirrer_bioreactor_status else 0),
                (1 if magneticStirrer_lagoon_status else 0),
            ])

            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(f"Sent magnetic stirrer status command: {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send magnetic stirrer status command: {e}")
            raise

    def get_on_off_magnetic_stirrers(self):
        """Read on/off magnetic stirrer status from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.MAG_MODULE
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([0, 0])
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent magnetic stirrer status read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                magnetic_stirrer_statuses = decoded_protocol_packet.payload
                self.evoflow_telemetry.magneticStirrer_bioreactor_status = bool(magnetic_stirrer_statuses[0])
                self.evoflow_telemetry.magneticStirrer_lagoon_status = bool(magnetic_stirrer_statuses[1])
                if verbose:
                    print(f"Received magnetic stirrer status: {magnetic_stirrer_statuses.hex()}")
        except serial.SerialException as e:
            print(f"Failed to read magnetic stirrer status: {e}")
            raise

    def set_setpoint_magnetic_stirrers(self, magneticStirrer_bioreactor_sp: float, magneticStirrer_lagoon_sp: float):
        """Send command to set magnetic stirrer setpoints."""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.MAG_MODULE
            self.protocol_packet.id2 = CMD.SET_POINT
            self.protocol_packet.payload = bytes(struct.pack('<2f', magneticStirrer_bioreactor_sp, magneticStirrer_lagoon_sp))

            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(f"Sent magnetic stirrer setpoint command: {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send magnetic stirrer setpoint command: {e}")
            raise
        
    def get_setpoint_magnetic_stirrers(self):
        """Read magnetic stirrer setpoints from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.MAG_MODULE
            self.protocol_packet.id2 = CMD.SET_POINT
            self.protocol_packet.payload = bytes(struct.pack('<2f', 0.0, 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent magnetic stirrer setpoint read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                magnetic_stirrer_sps = struct.unpack('<2f', decoded_protocol_packet.payload)
                self.evoflow_telemetry.magneticStirrer_bioreactor_sp = magnetic_stirrer_sps[0]
                self.evoflow_telemetry.magneticStirrer_lagoon_sp = magnetic_stirrer_sps[1]
                if verbose:
                    print(f"Received magnetic stirrer setpoints: {magnetic_stirrer_sps}")
        except serial.SerialException as e:
            print(f"Failed to read magnetic stirrer setpoints: {e}")
            raise

    def get_speed_magnetic_stirrers(self):
        """Read magnetic stirrer speeds from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.MAG_MODULE
            self.protocol_packet.id2 = CMD.SPEED
            self.protocol_packet.payload = bytes(struct.pack('<2f', 0.0, 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent magnetic stirrer speed read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                magnetic_stirrer_speeds = struct.unpack('<2f', decoded_protocol_packet.payload)
                self.evoflow_telemetry.magneticStirrer_bioreactor_speed = magnetic_stirrer_speeds[0]
                self.evoflow_telemetry.magneticStirrer_lagoon_speed = magnetic_stirrer_speeds[1]
                if verbose:
                    print(f"Received magnetic stirrer speeds: {magnetic_stirrer_speeds}")
        except serial.SerialException as e:
            print(f"Failed to read magnetic stirrer speeds: {e}")
            raise
    
    def get_fan_duty_cycle_magnetic_stirrers(self):
        """Read magnetic stirrer fan duty cycles from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.MAG_MODULE
            self.protocol_packet.id2 = CMD.FAN_DUTY_CYCLE
            self.protocol_packet.payload = bytes(struct.pack('<2f', 0.0, 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent magnetic stirrer fan duty cycle read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                magnetic_stirrer_fan_duty_cycles = struct.unpack('<2f', decoded_protocol_packet.payload)
                self.evoflow_telemetry.magneticStirrer_bioreactor_fan_duty_cycle = magnetic_stirrer_fan_duty_cycles[0]
                self.evoflow_telemetry.magneticStirrer_lagoon_fan_duty_cycle = magnetic_stirrer_fan_duty_cycles[1]
                if verbose:
                    print(f"Received magnetic stirrer fan duty cycles: {magnetic_stirrer_fan_duty_cycles}")
        except serial.SerialException as e:
            print(f"Failed to read magnetic stirrer fan duty cycles: {e}")
            raise

    def set_on_off_pht_count(self, phtCount_lagoon_status: bool):
        """Send command to turn on/off pH count based on its status."""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.PHOTON_COUNTER
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([
                (1 if phtCount_lagoon_status else 0),
            ])

            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(f"Sent pH count status command: {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send pH count status command: {e}")
            raise
    
    def get_on_off_pht_count(self):
        """Read on/off pH count status from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.PHOTON_COUNTER
            self.protocol_packet.id2 = CMD.ON_OFF
            self.protocol_packet.payload = bytes([0])
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent pH count status read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                pht_count_statuses = decoded_protocol_packet.payload
                self.evoflow_telemetry.phtCount_lagoon_status = bool(pht_count_statuses[0])
                if verbose:
                    print(f"Received pH count status: {pht_count_statuses.hex()}")
        except serial.SerialException as e:
            print(f"Failed to read pH count status: {e}")
            raise

    def get_photon_counts_pht_count(self):
        """Read pH count photon counts from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.PHOTON_COUNTER
            self.protocol_packet.id2 = CMD.PHOTON_COUNTS
            self.protocol_packet.payload = bytes(struct.pack('<f', 0.0))
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent pH count photon counts read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                pht_count_photon_counts = struct.unpack('<f', decoded_protocol_packet.payload)[0]
                self.evoflow_telemetry.phtCount_lagoon_value = pht_count_photon_counts
                if verbose:
                    print(f"Received pH count photon counts: {pht_count_photon_counts}")
        except serial.SerialException as e:
            print(f"Failed to read pH count photon counts: {e}")
            raise
    
    def get_overlight_pht_count(self):
        """Read pH count overlight status from the EvoFlow device."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.PHOTON_COUNTER
            self.protocol_packet.id2 = CMD.OVERLIGHT_DETECTION
            self.protocol_packet.payload = bytes([0])
            packet_bytes = build_packet(self.protocol_packet)
            self.serial.write(packet_bytes) 
            if verbose:
                print(f"Sent pH count overlight status read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                pht_count_overlight_statuses = decoded_protocol_packet.payload
                self.evoflow_telemetry.phtCount_lagoon_overlight = bool(pht_count_overlight_statuses[0])
                if verbose:
                    print(f"Received pH count overlight status: {pht_count_overlight_statuses.hex()}")
        except serial.SerialException as e:
            print(f"Failed to read pH count overlight status: {e}")
            raise
    
    def get_telemetry(self):
        """Convenience method to read all statuses from the EvoFlow device."""
        calls = [
            ("pump_on_off", self.get_on_off_pumps),
            ("pump_setpoint", self.get_setpoint_pumps),
            ("pump_speed", self.get_speed_pumps),
            ("valve_on_off", self.get_on_off_valves),
            ("temp_on_off", self.get_on_off_temp_ctrls),
            ("temp_setpoint", self.get_setpoint_temp_ctrls),
            ("temp_value", self.get_temperature_temp_ctrls),
            ("temp_heater_duty", self.get_heater_duty_cycle_temp_ctrls),
            ("od_on_off", self.get_on_off_od_ctrls),
            ("od_value", self.get_od_value_od_ctrls),
            ("mag_on_off", self.get_on_off_magnetic_stirrers),
            ("mag_setpoint", self.get_setpoint_magnetic_stirrers),
            ("mag_speed", self.get_speed_magnetic_stirrers),
            ("mag_fan_duty", self.get_fan_duty_cycle_magnetic_stirrers),
            ("photon_on_off", self.get_on_off_pht_count),
            ("photon_counts", self.get_photon_counts_pht_count),
            ("photon_overlight", self.get_overlight_pht_count),
        ]

        if not self.profile_telemetry:
            for _, fn in calls:
                fn()
            return

        t_total_start = time.perf_counter()
        timings = []
        for name, fn in calls:
            t0 = time.perf_counter()
            fn()
            timings.append((name, (time.perf_counter() - t0) * 1000.0))

        total_ms = (time.perf_counter() - t_total_start) * 1000.0
        print(f"Telemetry cycle total: {total_ms:.2f} ms")
        for name, dt_ms in timings:
            print(f"  {name:>16}: {dt_ms:.2f} ms")

    def get_all_telemetry(self):
        """Continuously read telemetry data from the EvoFlow device and emit it."""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.TELEMETRY
            self.protocol_packet.id2 = CMD.READ_ALL
            # payload needs 106 bytes, setup 106 of 0 bytes
            dummy_payload_length = 106
            self.protocol_packet.payload = bytes([0] * dummy_payload_length)
            
            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes) 
                if verbose:
                    print(f"Sent telemetry read command: {packet_bytes.hex()}")

            raw_response = self.read_serial()
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                payload = decoded_protocol_packet.payload

                expected_payload_length = 106
                if len(payload) < expected_payload_length:
                    # ignore the payload
                    return
                    # raise ValueError(
                    #     f"Telemetry payload too short: {len(payload)} < {expected_payload_length}"
                    # )

                def read_f32(offset: int) -> float:
                    return struct.unpack_from('<f', payload, offset)[0]
                # [0-3] pump on/off status
                # [4-19] pump setpoints (4 floats)
                # [20-35] pump speeds (4 floats)
                # [36-37] valve on/off status
                # [38-39] temp ctrl on/off status
                # [40-47] temp ctrl setpoints (2 floats)
                # [48-55] temp values (2 floats)
                # [56-63] temp heater duty cycles (2 floats)
                # [64-65] OD ctrl on/off status
                # [66-73] OD values (2 floats)
                # [74-75] mag stirrer on/off status
                # [76-83] mag stirrer setpoints (2 floats)
                # [84-91] mag stirrer speeds (2 floats)
                # [92-99] mag stirrer fan duty cycles (2 floats)
                # [100] photon count on/off status
                # [101-104] photon count values (1 float)
                # [105] photon count overlight status
                self.evoflow_telemetry.pump_1_status = bool(payload[0])
                self.evoflow_telemetry.pump_2_status = bool(payload[1])
                self.evoflow_telemetry.pump_3_status = bool(payload[2])
                self.evoflow_telemetry.pump_4_status = bool(payload[3])
                self.evoflow_telemetry.pump_1_sp = read_f32(4)
                self.evoflow_telemetry.pump_2_sp = read_f32(8)
                self.evoflow_telemetry.pump_3_sp = read_f32(12)
                self.evoflow_telemetry.pump_4_sp = read_f32(16)
                self.evoflow_telemetry.pump_1_speed = read_f32(20)
                self.evoflow_telemetry.pump_2_speed = read_f32(24)
                self.evoflow_telemetry.pump_3_speed = read_f32(28)
                self.evoflow_telemetry.pump_4_speed = read_f32(32)
                self.evoflow_telemetry.valve_bio2lag_status = bool(payload[36])
                self.evoflow_telemetry.valve_sug2lag_status = bool(payload[37])
                self.evoflow_telemetry.tempCtrl_bioreactor_status = bool(payload[38])
                self.evoflow_telemetry.tempCtrl_lagoon_status = bool(payload[39])
                self.evoflow_telemetry.tempCtrl_bioreactor_sp = read_f32(40)
                self.evoflow_telemetry.tempCtrl_lagoon_sp = read_f32(44)
                self.evoflow_telemetry.tempCtrl_bioreactor_value = read_f32(48)
                self.evoflow_telemetry.tempCtrl_lagoon_value = read_f32(52)
                self.evoflow_telemetry.tempCtrl_bioreactor_heater_duty_cycle = read_f32(56)
                self.evoflow_telemetry.tempCtrl_lagoon_heater_duty_cycle = read_f32(60)
                self.evoflow_telemetry.od_bioreactor_status = bool(payload[64])
                self.evoflow_telemetry.od_lagoon_status = bool(payload[65])
                self.evoflow_telemetry.od_bioreactor_value = read_f32(66)
                self.evoflow_telemetry.od_lagoon_value = read_f32(70)
                self.evoflow_telemetry.magneticStirrer_bioreactor_status = bool(payload[74])
                self.evoflow_telemetry.magneticStirrer_lagoon_status = bool(payload[75])
                self.evoflow_telemetry.magneticStirrer_bioreactor_sp = read_f32(76)
                self.evoflow_telemetry.magneticStirrer_lagoon_sp = read_f32(80)
                self.evoflow_telemetry.magneticStirrer_bioreactor_speed = read_f32(84)
                self.evoflow_telemetry.magneticStirrer_lagoon_speed = read_f32(88)
                self.evoflow_telemetry.magneticStirrer_bioreactor_fan_duty_cycle = read_f32(92)
                self.evoflow_telemetry.magneticStirrer_lagoon_fan_duty_cycle = read_f32(96)
                self.evoflow_telemetry.phtCount_lagoon_status = bool(payload[100])
                self.evoflow_telemetry.phtCount_lagoon_value = read_f32(101)
                self.evoflow_telemetry.phtCount_lagoon_overlight = bool(payload[105])
                
                if verbose:
                    print(f"Received live feed telemetry: {payload.hex()}")
        except (serial.SerialException, struct.error, ValueError) as e:
            print(f"Failed to read live feed telemetry: {e}")
            raise
    
            