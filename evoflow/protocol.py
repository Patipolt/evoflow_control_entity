"""
EvoFlow protocol implementation based on EvoFlow_Protocol.xlsm.

Frame format before COBS:
  [sender][receiver+rw][id1][id2][npayload][payload...][crc16_le]

Transport format on wire:
  COBS(frame) + 0x00 delimiter
"""

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Optional, Tuple


# ===============================
# Core constants
# ===============================

COBS_DELIM = 0x00
COBS_MAX_CODE = 0xFF

CRC16_INIT = 0xFFFF
CRC16_POLY = 0x1021
CRC16_MASK = 0xFFFF

MAX_PAYLOAD_LEN = 255

N_PUMP = 4
N_VALVE = 2
N_TEMP_MODULE = 2
N_OD_MODULE = 2
N_MAG_MODULE = 2
N_PHOTON_COUNTER = 1
N_TRAY = 1

N_SINGLE_BYTE = 1
N_BYTE_POS = 2
N_BYTE_FLOAT = 4
N_BYTE_READ_ALL = 106 # for all read-commands for evoflow telemetry, (SUM of all payload lengths)


# ===============================
# Addresses
# ===============================

ADDR_GUI = 1
ADDR_EVOFLOW_NUCLEO = 100
ADDR_SAMPLE_EXTRACTION_NUCLEO = 101


# ===============================
# Components (id1)
# ===============================

class Component(IntEnum):
	PUMP = 10
	VALVE = 11
	TEMP_MODULE = 12
	OD_MODULE = 13
	MAG_MODULE = 14
	PHOTON_COUNTER = 15
	TRAY = 16
	TELEMETRY = 100


# ===============================
# Commands (id2)
# ===============================
class CMD(IntEnum):
	ON_OFF = 0
	SET_POINT = 1
	SPEED = 2
	TEMPERATURE = 2
	HEATER_DUTY_CYCLE = 3
	OD_VALUE = 1
	FAN_DUTY_CYCLE = 3
	PHOTON_COUNTS = 1
	OVERLIGHT_DETECTION = 2
	POSITION = 0
	START = 1
	READ_ALL = 0


@dataclass
class ProtocolPacket:
	sender: int
	receiver_addr: int
	is_write: bool
	id1: int
	id2: int
	payload: bytes

@dataclass(frozen=True)
class CommandSpec:
	payload_len: int
	allow_read: bool
	allow_write: bool

# To help check that commands have correct payload lengths and read/write permissions
COMMAND_SPECS: Dict[Tuple[int, int], CommandSpec] = {
	# Pump
	(Component.PUMP, 0): CommandSpec(payload_len=N_PUMP*N_SINGLE_BYTE, allow_read=True, allow_write=True),
	(Component.PUMP, 1): CommandSpec(payload_len=N_PUMP*N_BYTE_FLOAT, allow_read=True, allow_write=True),
	(Component.PUMP, 2): CommandSpec(payload_len=N_PUMP*N_BYTE_FLOAT, allow_read=True, allow_write=False),
	# Valve
	(Component.VALVE, 0): CommandSpec(payload_len=N_VALVE*N_SINGLE_BYTE, allow_read=True, allow_write=True),
	# Temp module
	(Component.TEMP_MODULE, 0): CommandSpec(payload_len=N_TEMP_MODULE*N_SINGLE_BYTE, allow_read=True, allow_write=True),
	(Component.TEMP_MODULE, 1): CommandSpec(payload_len=N_TEMP_MODULE*N_BYTE_FLOAT, allow_read=True, allow_write=True),
	(Component.TEMP_MODULE, 2): CommandSpec(payload_len=N_TEMP_MODULE*N_BYTE_FLOAT, allow_read=True, allow_write=False),
	(Component.TEMP_MODULE, 3): CommandSpec(payload_len=N_TEMP_MODULE*N_BYTE_FLOAT, allow_read=True, allow_write=False),
	# OD module
	(Component.OD_MODULE, 0): CommandSpec(payload_len=N_OD_MODULE*N_SINGLE_BYTE, allow_read=True, allow_write=True),
	(Component.OD_MODULE, 1): CommandSpec(payload_len=N_OD_MODULE*N_BYTE_FLOAT, allow_read=True, allow_write=False),
	# Magnetic stirrer module
	(Component.MAG_MODULE, 0): CommandSpec(payload_len=N_MAG_MODULE*N_SINGLE_BYTE, allow_read=True, allow_write=True),
	(Component.MAG_MODULE, 1): CommandSpec(payload_len=N_MAG_MODULE*N_BYTE_FLOAT, allow_read=True, allow_write=True),
	(Component.MAG_MODULE, 2): CommandSpec(payload_len=N_MAG_MODULE*N_BYTE_FLOAT, allow_read=True, allow_write=False),
	(Component.MAG_MODULE, 3): CommandSpec(payload_len=N_MAG_MODULE*N_BYTE_FLOAT, allow_read=True, allow_write=False),
	# Photon counter
	(Component.PHOTON_COUNTER, 0): CommandSpec(payload_len=N_PHOTON_COUNTER*N_SINGLE_BYTE, allow_read=True, allow_write=True),
	(Component.PHOTON_COUNTER, 1): CommandSpec(payload_len=N_PHOTON_COUNTER*N_BYTE_FLOAT, allow_read=True, allow_write=False),
	(Component.PHOTON_COUNTER, 2): CommandSpec(payload_len=N_PHOTON_COUNTER*N_SINGLE_BYTE, allow_read=True, allow_write=False),
	# Tray
	(Component.TRAY, 0): CommandSpec(payload_len=N_TRAY*N_BYTE_POS, allow_read=True, allow_write=True),
	(Component.TRAY, 1): CommandSpec(payload_len=N_TRAY*N_SINGLE_BYTE, allow_read=False, allow_write=True),
	# Telemetry
	(Component.TELEMETRY, 0): CommandSpec(payload_len=N_BYTE_READ_ALL, allow_read=True, allow_write=False),
}


def crc16_ccitt_false(data: bytes) -> int:
	"""Calculate CRC-16-CCITT-FALSE checksum for the given data"""
	crc = CRC16_INIT
	for b in data:
		crc ^= b << 8
		for _ in range(8):
			if crc & 0x8000:
				crc = ((crc << 1) ^ CRC16_POLY) & CRC16_MASK
			else:
				crc = (crc << 1) & CRC16_MASK
	return crc


def cobs_encode(inp: bytes) -> bytes:
	"""Encode the input bytes using Consistent Overhead Byte Stuffing (COBS)"""
	if not inp:
		return bytes([0x01])

	out = bytearray([0])
	code_index = 0
	code = 1

	for b in inp:
		if b == 0:
			out[code_index] = code
			code_index = len(out)
			out.append(0)
			code = 1
			continue

		out.append(b)
		code += 1
		if code == COBS_MAX_CODE:
			out[code_index] = code
			code_index = len(out)
			out.append(0)
			code = 1

	out[code_index] = code
	return bytes(out)


def cobs_decode(inp: bytes) -> Optional[bytes]:
	"""Decode the input bytes using Consistent Overhead Byte Stuffing (COBS)"""
	out = bytearray()
	i = 0
	n = len(inp)

	while i < n:
		code = inp[i]
		if code == 0:
			return None
		i += 1

		for _ in range(1, code):
			if i >= n:
				return None
			out.append(inp[i])
			i += 1

		if code != COBS_MAX_CODE and i < n:
			out.append(0)

	return bytes(out)


def encode_receiver_field(receiver_addr: int, is_write: bool) -> int:
	"""Encode the receiver address and read/write flag into a single byte
	7-bit address in [0, 127], LSB is 0 for read and 1 for write"""
	if receiver_addr < 0 or receiver_addr > 0x7F:
		raise ValueError(f"receiver_addr must be in [0, 127], got {receiver_addr}")
	return ((receiver_addr & 0x7F) << 1) | (1 if is_write else 0)


def decode_receiver_field(raw_receiver: int) -> Tuple[int, bool]:
	"""Decode the receiver address and read/write flag from a single byte"""
	return ((raw_receiver >> 1) & 0x7F, bool(raw_receiver & 0x01))


def _validate_against_spec(id1: int, id2: int, is_write: bool, payload: bytes) -> None:
	spec = COMMAND_SPECS.get((id1, id2))
	if spec is None:
		return

	if is_write and not spec.allow_write:
		raise ValueError(f"Command id1={id1}, id2={id2} is read-only")
	if (not is_write) and not spec.allow_read:
		raise ValueError(f"Command id1={id1}, id2={id2} is write-only")
	if len(payload) != spec.payload_len:
		raise ValueError(
			f"Invalid payload length for id1={id1}, id2={id2}: "
			f"{len(payload)} != {spec.payload_len}"
		)


def build_packet(
	protocol_packet: ProtocolPacket,
	validate_spec: bool = True,
) -> bytes:
	sender = protocol_packet.sender
	receiver_addr = protocol_packet.receiver_addr
	is_write = protocol_packet.is_write
	id1 = protocol_packet.id1
	id2 = protocol_packet.id2
	payload = protocol_packet.payload

	if len(payload) > MAX_PAYLOAD_LEN:
		raise ValueError(f"Payload too large: {len(payload)} > {MAX_PAYLOAD_LEN}")
	if validate_spec:
		_validate_against_spec(id1, id2, is_write, payload)

	receiver = encode_receiver_field(receiver_addr, is_write)
	raw = struct.pack(
		"<BBBBB",
		sender & 0xFF,
		receiver & 0xFF,
		id1 & 0xFF,
		id2 & 0xFF,
		len(payload) & 0xFF,
	) + payload

	# return raw	# For debugging without COBS and CRC

	crc = crc16_ccitt_false(raw)
	raw += struct.pack("<H", crc)
	return cobs_encode(raw) + bytes([COBS_DELIM])


def parse_packet(raw: bytes) -> Optional[ProtocolPacket]:
	if len(raw) < 7:
		print(f"Packet too short: {len(raw)} bytes")
		return None
	
	raw = cobs_decode(raw)
	if raw is None:
		print("COBS decoding failed")
		return None

	sender, receiver_raw, id1, id2, n_payload = struct.unpack("<BBBBB", raw[:5])
	expected_len = 5 + n_payload + 2
	if len(raw) != expected_len:
		print(f"Invalid packet length: {len(raw)} != expected {expected_len}")
		return None

	payload = raw[5 : 5 + n_payload]
	rx_crc = struct.unpack("<H", raw[5 + n_payload : 5 + n_payload + 2])[0]
	calc_crc = crc16_ccitt_false(raw[: 5 + n_payload])
	if rx_crc != calc_crc:
		print(f"Invalid packet CRC: {rx_crc} != expected {calc_crc}")
		return None

	receiver_addr, is_write = decode_receiver_field(receiver_raw)
	return ProtocolPacket(
		sender=sender,
		receiver_addr=receiver_addr,
		is_write=is_write,
		id1=id1,
		id2=id2,
		payload=payload,
	)
