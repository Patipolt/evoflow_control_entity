"""
Low-level communication protocol for EvoFlow and Pick&Place systems.

Provides COBS encoding, CRC16 validation, and packet building/parsing for the custom
binary protocol used by both EvoFlow and Pick&Place Nucleo microcontrollers.

Project: EvoFlow Innosuisse
Author: Adapted from existing protocol
Created: April 2026
"""

import struct
from typing import Optional, Tuple
from dataclasses import dataclass

# ===============================
# Protocol Constants
# ===============================

# Message IDs
MSG_TELEM = 0x01
MSG_CMD_SET = 0x10
MSG_ACK_CMD_SET = 0x11
MSG_CMD_ACTION = 0x20
MSG_ACK_ACTION = 0x21

# Pick&Place message IDs (extend as needed)
MSG_PP_MOVE = 0x30
MSG_PP_GRIPPER = 0x31
MSG_PP_TELEM = 0x32
MSG_PP_ACK = 0x33

# Action opcodes
ACTION_SET_RUN_STATE = 0x01

# COBS framing
COBS_DELIM = 0x00
COBS_MAX_CODE = 0xFF

# CRC16-CCITT-FALSE parameters
CRC16_INIT = 0xFFFF
CRC16_POLY = 0x1021

# Packet structure
MAX_PAYLOAD_LEN = 255


# ===============================
# Data Classes
# ===============================

@dataclass
class EvoFlowTelemetry:
    """Parsed telemetry from EvoFlow Nucleo."""
    uptime_s: int
    dtime_us: float
    vel_target_m1: float
    vel_target_m2: float
    vel_m1: float
    vel_m2: float
    heater_cur_m1: float
    heater_cur_m2: float
    temp_filt_m1: float
    temp_filt_m2: float
    cmd_vel_m1: float
    cmd_vel_m2: float
    cmd_temp_m1: float
    cmd_temp_m2: float
    cmd_stir_m1: float
    cmd_stir_m2: float


@dataclass
class PickPlaceTelemetry:
    """Parsed telemetry from Pick&Place Nucleo (extend as needed)."""
    uptime_s: int
    x_pos: float
    y_pos: float
    z_pos: float
    gripper_state: int


# ===============================
# CRC16-CCITT-FALSE
# ===============================

def crc16_ccitt_false(data: bytes) -> int:
    """Calculate CRC16-CCITT-FALSE checksum."""
    crc = CRC16_INIT
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ CRC16_POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


# ===============================
# COBS Encoding/Decoding
# ===============================

def cobs_encode(inp: bytes) -> bytes:
    """Encode bytes using COBS (Consistent Overhead Byte Stuffing)."""
    if not inp:
        return bytes([0x01])
    
    out = bytearray()
    code_index = 0
    out.append(0)  # placeholder
    code = 1
    
    for b in inp:
        if b == 0:
            out[code_index] = code
            code_index = len(out)
            out.append(0)  # placeholder
            code = 1
        else:
            out.append(b)
            code += 1
            if code == COBS_MAX_CODE:
                out[code_index] = code
                code_index = len(out)
                out.append(0)  # placeholder
                code = 1
    
    out[code_index] = code
    return bytes(out)


def cobs_decode(inp: bytes) -> Optional[bytes]:
    """Decode COBS-encoded bytes. Returns None on error."""
    out = bytearray()
    i = 0
    n = len(inp)
    
    while i < n:
        code = inp[i]
        if code == 0:
            return None  # Invalid COBS
        i += 1
        
        for _ in range(1, code):
            if i >= n:
                return None
            out.append(inp[i])
            i += 1
        
        if code != COBS_MAX_CODE and i < n:
            out.append(0)
    
    return bytes(out)


# ===============================
# Packet Building
# ===============================

def build_packet(msg_id: int, node_id: int, payload: bytes) -> bytes:
    """
    Build a complete packet with header, payload, CRC16, COBS encoding, and delimiter.
    
    Args:
        msg_id: Message type ID
        node_id: Target node ID
        payload: Raw payload bytes
    
    Returns:
        Complete packet ready for transmission
    """
    if len(payload) > MAX_PAYLOAD_LEN:
        raise ValueError(f"Payload too large: {len(payload)} > {MAX_PAYLOAD_LEN}")
    
    # Build header
    hdr = struct.pack("<BBB", msg_id & 0xFF, node_id & 0xFF, len(payload) & 0xFF)
    raw = hdr + payload
    
    # Add CRC16
    crc = crc16_ccitt_false(raw)
    raw += struct.pack("<H", crc)
    
    # COBS encode and add delimiter
    return cobs_encode(raw) + bytes([COBS_DELIM])


def parse_packet(raw: bytes) -> Optional[Tuple[int, int, bytes]]:
    """
    Parse and validate a raw packet.
    
    Args:
        raw: Decoded packet bytes (after COBS decode)
    
    Returns:
        Tuple of (msg_id, node_id, payload) or None if invalid
    """
    if len(raw) < 5:  # min: 3 bytes header + 2 bytes CRC
        return None
    
    msg_id, node_id, payload_len = struct.unpack("<BBB", raw[:3])
    expected_len = 3 + payload_len + 2
    
    if len(raw) != expected_len:
        return None
    
    # Validate CRC
    rx_crc = struct.unpack("<H", raw[3 + payload_len:3 + payload_len + 2])[0]
    calc_crc = crc16_ccitt_false(raw[:3 + payload_len])
    
    if rx_crc != calc_crc:
        return None
    
    payload = raw[3:3 + payload_len]
    return (msg_id, node_id, payload)


# ===============================
# COBS Stream Parser
# ===============================

class CobsStreamParser:
    """
    Stateful parser for COBS-encoded frames from a byte stream.
    Feed incoming bytes and yields decoded packets.
    """
    
    def __init__(self, max_frame_len: int = 4096):
        self.buffer = bytearray()
        self.max_frame_len = max_frame_len
    
    def feed(self, data: bytes):
        """
        Feed incoming bytes and yield decoded packets.
        
        Args:
            data: Raw bytes from serial port
        
        Yields:
            Tuples of (msg_id, node_id, payload) for each valid packet
        """
        for byte in data:
            if byte == COBS_DELIM:
                if self.buffer:
                    # Decode COBS frame
                    raw = cobs_decode(bytes(self.buffer))
                    self.buffer.clear()
                    
                    if raw is not None:
                        # Parse packet
                        parsed = parse_packet(raw)
                        if parsed is not None:
                            yield parsed
            else:
                if len(self.buffer) < self.max_frame_len:
                    self.buffer.append(byte)
                else:
                    # Overflow - discard
                    self.buffer.clear()
    
    def reset(self):
        """Clear the internal buffer."""
        self.buffer.clear()


# ===============================
# Protocol Encoders
# ===============================

class ProtocolEncoder:
    """Encodes commands into protocol packets."""
    
    def __init__(self):
        self.seq = 0
    
    def encode_evoflow_setpoints(
        self,
        node_id: int,
        vel_m1: float,
        vel_m2: float,
        temp_m1: float,
        temp_m2: float,
        stir_m1: float,
        stir_m2: float
    ) -> bytes:
        """Build CMD_SET packet for EvoFlow system."""
        seq = self._next_seq()
        payload = struct.pack(
            "<Bffffff",
            seq, vel_m1, vel_m2, temp_m1, temp_m2, stir_m1, stir_m2
        )
        return build_packet(MSG_CMD_SET, node_id, payload)
    
    def encode_action(self, node_id: int, run_state: bool) -> bytes:
        """Build ACTION packet (start/stop)."""
        seq = self._next_seq()
        payload = struct.pack(
            "<BBB",
            seq, ACTION_SET_RUN_STATE, 1 if run_state else 0
        )
        return build_packet(MSG_CMD_ACTION, node_id, payload)
    
    def encode_pickplace_move(self, node_id: int, x: float, y: float, z: float) -> bytes:
        """Build movement command for pick&place (extend as needed)."""
        seq = self._next_seq()
        payload = struct.pack("<Bfff", seq, x, y, z)
        return build_packet(MSG_PP_MOVE, node_id, payload)
    
    def encode_pickplace_gripper(self, node_id: int, open_gripper: bool) -> bytes:
        """Build gripper command for pick&place."""
        seq = self._next_seq()
        payload = struct.pack("<BB", seq, 1 if open_gripper else 0)
        return build_packet(MSG_PP_GRIPPER, node_id, payload)
    
    def _next_seq(self) -> int:
        """Get next sequence number (wraps at 255)."""
        seq = self.seq
        self.seq = (self.seq + 1) & 0xFF
        return seq


# ===============================
# Protocol Decoders
# ===============================

def decode_evoflow_telemetry(payload: bytes) -> Optional[EvoFlowTelemetry]:
    """Parse EvoFlow telemetry payload."""
    expected_len = 4 + 15 * 4  # uptime (u32) + 15 floats
    if len(payload) != expected_len:
        return None
    
    uptime_s = struct.unpack("<I", payload[:4])[0]
    floats = struct.unpack("<" + "f" * 15, payload[4:])
    
    return EvoFlowTelemetry(
        uptime_s=uptime_s,
        dtime_us=floats[0],
        vel_target_m1=floats[1],
        vel_target_m2=floats[2],
        vel_m1=floats[3],
        vel_m2=floats[4],
        heater_cur_m1=floats[5],
        heater_cur_m2=floats[6],
        temp_filt_m1=floats[7],
        temp_filt_m2=floats[8],
        cmd_vel_m1=floats[9],
        cmd_vel_m2=floats[10],
        cmd_temp_m1=floats[11],
        cmd_temp_m2=floats[12],
        cmd_stir_m1=floats[13],
        cmd_stir_m2=floats[14],
    )


def decode_pickplace_telemetry(payload: bytes) -> Optional[PickPlaceTelemetry]:
    """Parse Pick&Place telemetry (extend based on your protocol)."""
    # Example implementation - adjust to your actual protocol
    if len(payload) < 20:  # uptime + 4 floats
        return None
    
    uptime_s = struct.unpack("<I", payload[:4])[0]
    x, y, z = struct.unpack("<fff", payload[4:16])
    gripper = struct.unpack("<I", payload[16:20])[0]
    
    return PickPlaceTelemetry(
        uptime_s=uptime_s,
        x_pos=x,
        y_pos=y,
        z_pos=z,
        gripper_state=gripper
    )
