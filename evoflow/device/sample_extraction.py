"""
Low-level API for Sample Extraction device.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

import struct

import serial
import time

from evoflow.protocol import (
    ADDR_EVOFLOW_NUCLEO,
    ProtocolPacket,
    Component,
    CMD,
    ADDR_GUI,
    ADDR_SAMPLE_EXTRACTION_NUCLEO,
    build_packet,
    cobs_decode,
    parse_packet,
)
from evoflow.protocol import N_BYTE_READ_ALL_SE
from utils import colored_text as tc

verbose = False  # Set to True to enable debug prints

class SampleExtractionTelemetry:
    """Data class to hold telemetry information from the Sample Extraction device"""
    def __init__(self):
        self.position               : list = [0, 0]  # Row, Col
        self.start_flag             : bool = False
        self.done_flag              : bool = False
        self.nucleo_temp            : float = 0.0
        self.x_axis_motor_temp      : float = 0.0
        self.y_axis_motor_temp      : float = 0.0
        self.z_axis_motor_temp      : float = 0.0
        self.ambient_temp           : float = 0.0
        self.fan1_status            : bool = False
        self.fan1_sp                : float = 0.0
        self.fan1_speed             : float = 0.0
        self.fan1_speed_duty_cycle  : float = 0.0
        self.fan2_status            : bool = False
        self.fan2_sp                : float = 0.0
        self.fan2_speed             : float = 0.0
        self.fan2_speed_duty_cycle  : float = 0.0
        self.fan3_status            : bool = False
        self.fan3_sp                : float = 0.0
        self.fan3_speed             : float = 0.0
        self.fan3_speed_duty_cycle  : float = 0.0
        self.fan4_status            : bool = False
        self.fan4_sp                : float = 0.0
        self.fan4_speed             : float = 0.0
        self.fan4_speed_duty_cycle  : float = 0.0


class SampleExtractionDevice:
    """Class representing the Sample Extraction device, handling serial communication and telemetry"""
    def __init__(
        self,
        port: str,
        baudrate: int = 2000000,
        timeout: float = 0.01,
        sender_addr: int = ADDR_GUI,
        receiver_addr: int = ADDR_SAMPLE_EXTRACTION_NUCLEO,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self._rx_buffer = bytearray()
        self.sample_extraction_telemetry = SampleExtractionTelemetry()

        self.protocol_packet = ProtocolPacket(
            sender=sender_addr,
            receiver_addr=receiver_addr,
            is_write=False,
            id1=0,
            id2=0,
            payload=b"",
        )

    def connect(self):
        """Establish serial connection to the Sample Extraction device"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"Connected to Sample Extraction device on {self.port} at {self.baudrate} baud.")
        except serial.SerialException as e:
            print(f"Failed to connect to Sample Extraction device: {e}")
            raise

    def disconnect(self):
        """Close the serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Disconnected from Sample Extraction device.")

    def read_serial(self) -> bytes:
        """Read data from serial port until delimiter (0x00) is found, return the raw packet without the delimiter"""
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

    def set_position(self, row: int, col: int):
        """Send command to set the position of the sample extraction system"""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.TRAY
            self.protocol_packet.id2 = CMD.POSITION
            self.protocol_packet.payload = struct.pack('<BB', row, col)
            
            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes) 
                if verbose:
                    print(f"Sent position command: Row {row}, Col {col} -> {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send position command: {e}")
            pass # ignore for now

    def get_position(self):
        """Send command to get the current position of the sample extraction system"""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.TRAY
            self.protocol_packet.id2 = CMD.POSITION
            self.protocol_packet.payload = bytes([0, 0])
            
            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes) 
                if verbose:
                    print(f"Sent get position command -> {packet_bytes.hex()}")

            raw_response = self.read_serial()
            cobs_decoded = cobs_decode(raw_response)
            print(f"Raw response: {raw_response.hex()} | COBS decoded: {cobs_decoded.hex()}")
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                position = decoded_protocol_packet.payload
                self.sample_extraction_telemetry.position[0] = position[0]
                self.sample_extraction_telemetry.position[1] = position[1]
                if verbose:
                    print(f"Received position telemetry: Row {position[0]}, Col {position[1]}")
        except (serial.SerialException, struct.error) as e:
            print(f"Failed to get position telemetry: {e}")
            pass # ignore for now

    def start_sample_extraction(self):
        """Send command to start the sample extraction process"""
        try:
            self.protocol_packet.is_write = True
            self.protocol_packet.id1 = Component.TRAY
            self.protocol_packet.id2 = CMD.START
            self.protocol_packet.payload = bytes([1])  # 1 for Samuel
            
            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes) 
                if verbose:
                    print(f"Sent start sample extraction command -> {packet_bytes.hex()}")
        except serial.SerialException as e:
            print(f"Failed to send start sample extraction command: {e}")
            pass # ignore for now

    def get_done_flag(self):
        """Send command to get the done flag status of the sample extraction process"""
        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.TRAY
            self.protocol_packet.id2 = CMD.DONE_FLAG
            self.protocol_packet.payload = bytes([0])  # No additional data needed
            
            if self.serial and self.serial.is_open:
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes) 
                if verbose:
                    print(f"Sent get done flag command -> {packet_bytes.hex()}")

            raw_response = self.read_serial()
            cobs_decoded = cobs_decode(raw_response)
            print(f"Raw response: {raw_response.hex()} | COBS decoded: {cobs_decoded.hex()}")
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                done_flag_status = decoded_protocol_packet.payload[0]
                self.sample_extraction_telemetry.done_flag = bool(done_flag_status)
                if verbose:
                    print(f"Received done flag telemetry: {self.sample_extraction_telemetry.done_flag}")
        except (serial.SerialException, struct.error) as e:
            print(f"Failed to get done flag telemetry: {e}")
            pass # ignore for now

    def get_all_telemetry(self) -> bool:
        """Continuously read telemetry data from the sampler device and emit it"""
        def read_f32(offset: int) -> float:
            return struct.unpack_from('<f', payload, offset)[0]

        try:
            self.protocol_packet.is_write = False
            self.protocol_packet.id1 = Component.TELEMETRY
            self.protocol_packet.id2 = CMD.READ_ALL
            # payload needs N_BYTE_READ_ALL_SE bytes, setup N_BYTE_READ_ALL of 0 bytes
            dummy_payload_length = N_BYTE_READ_ALL_SE
            self.protocol_packet.payload = bytes([0] * dummy_payload_length)

            t_write = time.perf_counter()
            if self.serial and self.serial.is_open:
                # Flush stale/backlogged bytes so this read can only capture the fresh reply.
                self.serial.reset_input_buffer()
                self._rx_buffer.clear()
                packet_bytes = build_packet(self.protocol_packet)
                self.serial.write(packet_bytes)
                if verbose:
                    print(tc(f"Sent telemetry read command: {packet_bytes.hex()}", "Yellow"))
                    print(tc(f"in_waiting right after write: {self.serial.in_waiting} bytes", "Pink"))

            t_read = time.perf_counter()
            raw_response = self.read_serial()
            if verbose:
                print(tc(f"get_all_telemetry round trip: {(time.perf_counter() - t_write) * 1000:.2f} ms, read time: {(time.perf_counter() - t_read) * 1000:.2f} ms", "Pink"))
            decoded_protocol_packet = parse_packet(raw_response)
            # print(tc(f"Received payload length: {len(raw_response)} bytes", "Green"))
            if (decoded_protocol_packet and decoded_protocol_packet.payload 
                    and self._is_expected_response(decoded_protocol_packet, Component.TELEMETRY, CMD.READ_ALL)):
                payload = decoded_protocol_packet.payload

                expected_payload_length = N_BYTE_READ_ALL_SE
                if len(payload) < expected_payload_length:
                    print(tc(f"Telemetry payload too short: {len(payload)} < {expected_payload_length}", "Red"))
                    return False

                # [0-1] Position (Row, Col)
                self.sample_extraction_telemetry.position[0] = payload[0]
                self.sample_extraction_telemetry.position[1] = payload[1]
                # [2] Start Flag
                self.sample_extraction_telemetry.start_flag = bool(payload[2])
                # [3] Done Flag
                self.sample_extraction_telemetry.done_flag = bool(payload[3])
                # [4-7] Nucleo Temperature
                self.sample_extraction_telemetry.nucleo_temp = read_f32(4)
                # [8-11] X-axis Motor Temperature
                self.sample_extraction_telemetry.x_axis_motor_temp = read_f32(8)
                # [12-15] Y-axis Motor Temperature
                self.sample_extraction_telemetry.y_axis_motor_temp = read_f32(12)
                # [16-19] Z-axis Motor Temperature
                self.sample_extraction_telemetry.z_axis_motor_temp = read_f32(16)
                # [20-23] Ambient Temperature
                self.sample_extraction_telemetry.ambient_temp = read_f32(20)
                self.sample_extraction_telemetry.ntc5 = read_f32(20)
                # [24] Fan1 Status
                self.sample_extraction_telemetry.fan1_status = bool(payload[24])
                # [25-28] Fan1 SP
                self.sample_extraction_telemetry.fan1_sp = read_f32(25)
                # [29-32] Fan1 Speed
                self.sample_extraction_telemetry.fan1_speed = read_f32(29)
                # [33-36] Fan1 Speed Duty Cycle
                self.sample_extraction_telemetry.fan1_speed_duty_cycle = read_f32(33)
                # [37] Fan2 Status
                self.sample_extraction_telemetry.fan2_status = bool(payload[37])
                # [38-41] Fan2 SP
                self.sample_extraction_telemetry.fan2_sp = read_f32(38)
                # [42-45] Fan2 Speed
                self.sample_extraction_telemetry.fan2_speed = read_f32(42)
                # [46-49] Fan2 Speed Duty Cycle
                self.sample_extraction_telemetry.fan2_speed_duty_cycle = read_f32(46)
                # [50] Fan3 Status
                self.sample_extraction_telemetry.fan3_status = bool(payload[50])
                # [51-54] Fan3 SP
                self.sample_extraction_telemetry.fan3_sp = read_f32(51)
                # [55-58] Fan3 Speed
                self.sample_extraction_telemetry.fan3_speed = read_f32(55)
                # [59-62] Fan3 Speed Duty Cycle
                self.sample_extraction_telemetry.fan3_speed_duty_cycle = read_f32(59)
                # [63] Fan4 Status
                self.sample_extraction_telemetry.fan4_status = bool(payload[63])
                # [64-67] Fan4 SP
                self.sample_extraction_telemetry.fan4_sp = read_f32(64)
                # [68-71] Fan4 Speed
                self.sample_extraction_telemetry.fan4_speed = read_f32(68)
                # [72-75] Fan4 Speed Duty Cycle
                self.sample_extraction_telemetry.fan4_speed_duty_cycle = read_f32(72)

                if verbose:
                    print(tc(f"Received live feed telemetry: {payload.hex()}", "Green"))
                return True

            # Response failed to decode (bad COBS/CRC) or carried an empty payload.
            print(tc("Failed to decode telemetry response.", "Red"))
            return False
        except (serial.SerialException, struct.error, ValueError) as e:
            print(tc(f"Failed to read live feed telemetry: {e}", "Red"))
            return False

    def _is_expected_response(self, decoded_protocol_packet, expected_id1: int, expected_id2: int) -> bool:
            """Reject stale/misaligned replies that don't echo the component/command just requested"""
            if decoded_protocol_packet.id1 != expected_id1 or decoded_protocol_packet.id2 != expected_id2:
                print(tc(
                    f"Response mismatch: expected id1={expected_id1}, id2={expected_id2}, "
                    f"got id1={decoded_protocol_packet.id1}, id2={decoded_protocol_packet.id2}",
                    "Red",
                ))
                return False
            return True

