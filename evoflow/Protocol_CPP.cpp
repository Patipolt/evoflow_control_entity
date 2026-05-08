#include "Protocol_CPP.h"

uint16_t Protocol_CPP::crc16_ccitt_false(const std::vector<uint8_t>& data)
{
    uint16_t crc = CRC16_INIT;

    for (size_t i = 0; i < data.size(); i++) {
        crc ^= (uint16_t)(data[i] << 8);

        for (int bit = 0; bit < 8; bit++) {
            if (crc & 0x8000U) {
                crc = (uint16_t)(((crc << 1) ^ CRC16_POLY) & CRC16_MASK);
            } else {
                crc = (uint16_t)((crc << 1) & CRC16_MASK);
            }
        }
    }

    return crc;
}

std::vector<uint8_t> Protocol_CPP::cobs_encode(const std::vector<uint8_t>& input)
{
    std::vector<uint8_t> output;

    if (input.size() == 0) {
        output.push_back(0x01U);
        return output;
    }

    output.reserve(input.size() + 2);
    output.push_back(0U); // first code placeholder

    size_t code_index = 0;
    uint8_t code = 1U;

    for (size_t i = 0; i < input.size(); i++) {
        uint8_t b = input[i];

        if (b == 0U) {
            output[code_index] = code;
            code_index = output.size();
            output.push_back(0U); // next code placeholder
            code = 1U;
            continue;
        }

        output.push_back(b);
        code++;

        if (code == COBS_MAX_CODE) {
            output[code_index] = code;
            code_index = output.size();
            output.push_back(0U); // next code placeholder
            code = 1U;
        }
    }

    output[code_index] = code;
    return output;
}

bool Protocol_CPP::cobs_decode(const std::vector<uint8_t>& input, std::vector<uint8_t>& output)
{
    output.clear();

    size_t i = 0;
    size_t n = input.size();

    while (i < n) {
        uint8_t code = input[i];

        if (code == 0U) {
            return false;
        }

        i++;

        for (uint8_t j = 1; j < code; j++) {
            if (i >= n) {
                return false;
            }
            output.push_back(input[i]);
            i++;
        }

        if (code != COBS_MAX_CODE && i < n) {
            output.push_back(0U);
        }
    }

    return true;
}

uint8_t Protocol_CPP::encode_receiver_field(uint8_t receiver_addr, bool is_write)
{
    if (receiver_addr > 0x7FU) {
        return 0U;
    }

    return (uint8_t)(((receiver_addr & 0x7FU) << 1) | (is_write ? 1U : 0U));
}

void Protocol_CPP::decode_receiver_field(uint8_t raw_receiver, uint8_t& receiver_addr, bool& is_write)
{
    receiver_addr = (uint8_t)((raw_receiver >> 1) & 0x7FU);
    is_write = ((raw_receiver & 0x01U) != 0U);
}

bool Protocol_CPP::get_command_spec(uint8_t id1, uint8_t id2, size_t& payload_len, bool& allow_read, bool& allow_write)
{
    switch (id1) {
    case COMPONENT_PUMP:
        switch (id2) {
        case 0: payload_len = N_PUMP * N_SINGLE_BYTE; allow_read = true; allow_write = true; return true;
        case 1: payload_len = N_PUMP * N_BYTE_FLOAT;  allow_read = true; allow_write = true; return true;
        case 2: payload_len = N_PUMP * N_BYTE_FLOAT;  allow_read = true; allow_write = false; return true;
        default: return false;
        }

    case COMPONENT_VALVE:
        if (id2 == 0) {
            payload_len = N_VALVE * N_SINGLE_BYTE; allow_read = true; allow_write = true; return true;
        }
        return false;

    case COMPONENT_TEMP_MODULE:
        switch (id2) {
        case 0: payload_len = N_TEMP_MODULE * N_SINGLE_BYTE; allow_read = true; allow_write = true; return true;
        case 1: payload_len = N_TEMP_MODULE * N_BYTE_FLOAT;  allow_read = true; allow_write = true; return true;
        case 2: payload_len = N_TEMP_MODULE * N_BYTE_FLOAT;  allow_read = true; allow_write = false; return true;
        case 3: payload_len = N_TEMP_MODULE * N_BYTE_FLOAT;  allow_read = true; allow_write = false; return true;
        default: return false;
        }

    case COMPONENT_OD_MODULE:
        switch (id2) {
        case 0: payload_len = N_OD_MODULE * N_SINGLE_BYTE; allow_read = true; allow_write = true; return true;
        case 1: payload_len = N_OD_MODULE * N_BYTE_FLOAT;  allow_read = true; allow_write = false; return true;
        default: return false;
        }

    case COMPONENT_MAG_MODULE:
        switch (id2) {
        case 0: payload_len = N_MAG_MODULE * N_SINGLE_BYTE; allow_read = true; allow_write = true; return true;
        case 1: payload_len = N_MAG_MODULE * N_BYTE_FLOAT;  allow_read = true; allow_write = true; return true;
        case 2: payload_len = N_MAG_MODULE * N_BYTE_FLOAT;  allow_read = true; allow_write = false; return true;
        case 3: payload_len = N_MAG_MODULE * N_BYTE_FLOAT;  allow_read = true; allow_write = false; return true;
        default: return false;
        }

    case COMPONENT_PHOTON_COUNTER:
        switch (id2) {
        case 0: payload_len = N_PHOTON_COUNTER * N_SINGLE_BYTE; allow_read = true; allow_write = true; return true;
        case 1: payload_len = N_PHOTON_COUNTER * N_BYTE_FLOAT;  allow_read = true; allow_write = false; return true;
        case 2: payload_len = N_PHOTON_COUNTER * N_SINGLE_BYTE; allow_read = true; allow_write = false; return true;
        default: return false;
        }

    case COMPONENT_TRAY:
        switch (id2) {
        case 0: payload_len = N_TRAY * N_BYTE_POS;    allow_read = true;  allow_write = true; return true;
        case 1: payload_len = N_TRAY * N_SINGLE_BYTE; allow_read = false; allow_write = true; return true;
        default: return false;
        }

    default:
        return false;
    }
}

bool Protocol_CPP::validate_against_spec(uint8_t id1, uint8_t id2, bool is_write, const std::vector<uint8_t>& payload)
{
    size_t payload_len = 0;
    bool allow_read = false;
    bool allow_write = false;

    bool known_command = get_command_spec(id1, id2, payload_len, allow_read, allow_write);
    if (!known_command) {
        // Keep same behavior as Python: unknown commands are allowed.
        return true;
    }

    if (is_write && !allow_write) {
        return false;
    }

    if (!is_write && !allow_read) {
        return false;
    }

    if (payload.size() != payload_len) {
        return false;
    }

    return true;
}

bool Protocol_CPP::build_packet(const ProtocolPacket& protocol_packet, std::vector<uint8_t>& out_packet, bool validate_spec)
{
    out_packet.clear();

    if (protocol_packet.payload.size() > MAX_PAYLOAD_LEN) {
        return false;
    }

    if (validate_spec) {
        if (!validate_against_spec(protocol_packet.id1, protocol_packet.id2, protocol_packet.is_write, protocol_packet.payload)) {
            return false;
        }
    }

    if (protocol_packet.receiver_addr > 0x7FU) {
        return false;
    }

    uint8_t receiver = encode_receiver_field(protocol_packet.receiver_addr, protocol_packet.is_write);

    std::vector<uint8_t> raw;
    raw.reserve((size_t)5 + protocol_packet.payload.size() + 2);

    raw.push_back(protocol_packet.sender);
    raw.push_back(receiver);
    raw.push_back(protocol_packet.id1);
    raw.push_back(protocol_packet.id2);
    raw.push_back((uint8_t)(protocol_packet.payload.size() & 0xFFU));

    for (size_t i = 0; i < protocol_packet.payload.size(); i++) {
        raw.push_back(protocol_packet.payload[i]);
    }

    uint16_t crc = crc16_ccitt_false(raw);
    raw.push_back((uint8_t)(crc & 0xFFU));
    raw.push_back((uint8_t)((crc >> 8) & 0xFFU));

    out_packet = cobs_encode(raw);
    out_packet.push_back(COBS_DELIM);

    return true;
}

bool Protocol_CPP::parse_packet(const std::vector<uint8_t>& raw_cobs_frame_no_delim, ProtocolPacket& out_packet)
{
    if (raw_cobs_frame_no_delim.size() < 7) {
        return false;
    }

    std::vector<uint8_t> raw;
    if (!cobs_decode(raw_cobs_frame_no_delim, raw)) {
        return false;
    }

    if (raw.size() < 7) {
        return false;
    }

    uint8_t sender = raw[0];
    uint8_t receiver_raw = raw[1];
    uint8_t id1 = raw[2];
    uint8_t id2 = raw[3];
    uint8_t n_payload = raw[4];

    size_t expected_len = (size_t)(5 + n_payload + 2);
    if (raw.size() != expected_len) {
        return false;
    }

    std::vector<uint8_t> payload;
    payload.reserve(n_payload);
    for (size_t i = 0; i < n_payload; i++) {
        payload.push_back(raw[5 + i]);
    }

    uint16_t rx_crc = (uint16_t)raw[5 + n_payload] | (uint16_t)(raw[5 + n_payload + 1] << 8);

    std::vector<uint8_t> crc_data;
    crc_data.reserve(5 + n_payload);
    for (size_t i = 0; i < (size_t)(5 + n_payload); i++) {
        crc_data.push_back(raw[i]);
    }

    uint16_t calc_crc = crc16_ccitt_false(crc_data);
    if (rx_crc != calc_crc) {
        return false;
    }

    uint8_t receiver_addr = 0;
    bool is_write = false;
    decode_receiver_field(receiver_raw, receiver_addr, is_write);

    out_packet.sender = sender;
    out_packet.receiver_addr = receiver_addr;
    out_packet.is_write = is_write;
    out_packet.id1 = id1;
    out_packet.id2 = id2;
    out_packet.payload = payload;

    return true;
}

bool Protocol_CPP::parse_packet_wire(const std::vector<uint8_t>& wire_data, ProtocolPacket& out_packet)
{
    if (wire_data.size() == 0) {
        return false;
    }

    if (wire_data[wire_data.size() - 1] != COBS_DELIM) {
        return false;
    }

    std::vector<uint8_t> frame;
    frame.reserve(wire_data.size() - 1);

    for (size_t i = 0; i < wire_data.size() - 1; i++) {
        frame.push_back(wire_data[i]);
    }

    return parse_packet(frame, out_packet);
}
