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

verbose = False  # Set to True to enable debug prints

class SampleExtractionTelemetry:
    """Data class to hold telemetry information from the Sample Extraction device"""
    def __init__(self):
        self.position = [0, 0]  # Row, Col
        self.done_flag = False

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
            self.protocol_packet.payload = bytes([0])  # No additional data needed
            
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
            decoded_protocol_packet = parse_packet(raw_response)
            if decoded_protocol_packet and decoded_protocol_packet.payload:
                done_flag_status = decoded_protocol_packet.payload[0]
                self.sample_extraction_telemetry.done_flag = bool(done_flag_status)
                if verbose:
                    print(f"Received done flag telemetry: {self.sample_extraction_telemetry.done_flag}")
        except (serial.SerialException, struct.error) as e:
            print(f"Failed to get done flag telemetry: {e}")
            pass # ignore for now

    def get_all_telemetry(self):
        """Convenience method to get all telemetry data (position and done flag)"""
        self.get_position()
        self.get_done_flag()
