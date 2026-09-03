#ifndef PROTOCOL_CPP_H_
#define PROTOCOL_CPP_H_

#include <cstddef>
#include <cstdint>
#include <vector>
#include <cstdio>

#define COBS_DELIM                      0x00U
#define COBS_MAX_CODE                   0xFFU

#define CRC16_INIT                      0xFFFFU
#define CRC16_POLY                      0x1021U
#define CRC16_MASK                      0xFFFFU

#define MAX_PAYLOAD_LEN                 255U

#define N_PUMP                          4U
#define N_VALVE                         2U
#define N_TEMP_MODULE                   2U
#define N_OD_MODULE                     2U
#define N_MAG_MODULE                    2U
#define N_PHOTON_COUNTER                1U
#define N_TRAY                          1U
#define N_TEMP_IN_TEMP_ARRAY            6U
#define N_TEMP_IN_TEMP_ARRAY_SE         5U
#define N_FAN_SE_MODULE                 4U

#define N_SINGLE_BYTE                   1U
#define N_BYTE_POS                      2U
#define N_BYTE_FLOAT                    4U
#define N_BYTE_READ_ALL                 130U  // for all read-commands for evoflow telemetry, (SUM of all payload lengths)
#define N_BYTE_READ_ALL_SE              76U   // for all read-commands for sample extraction telemetry, (SUM of all payload lengths)

// Addresses
#define ADDR_GUI                        1U
#define ADDR_EVOFLOW_NUCLEO             100U
#define ADDR_SAMPLE_EXTRACTION_NUCLEO   101U

// Components (id1)
#define COMPONENT_PUMP                  10U
#define COMPONENT_VALVE                 11U
#define COMPONENT_TEMP_MODULE           12U
#define COMPONENT_OD_MODULE             13U
#define COMPONENT_MAG_MODULE            14U
#define COMPONENT_PHOTON_COUNTER        15U
#define COMPONENT_TRAY                  16U
#define COMPONENT_TEMPERATURE_SENSOR    17U
#define COMPONENT_FAN_MODULE            18U
#define COMPONENT_TELEMETRY             100U

// Commands (id2)
#define CMD_ON_OFF                      0U
#define CMD_SET_POINT                   1U
#define CMD_SPEED                       2U
#define CMD_TEMPERATURE                 2U
#define CMD_HEATER_DUTY_CYCLE           3U
#define CMD_OD_VALUE                    1U
#define CMD_FAN_DUTY_CYCLE              3U
#define CMD_PHOTON_COUNTS               1U
#define CMD_OVERLIGHT_DETECTION         2U
#define CMD_POSITION                    0U
#define CMD_START                       1U
#define CMD_DONE_FLAG                   2U
#define CMD_READ_ALL                    0U

typedef struct ProtocolPacket_t {
    uint8_t sender = 0;
    uint8_t receiver_addr = 0;   // 7-bit address: 0..127
    bool is_write = false;
    uint8_t id1 = 0;
    uint8_t id2 = 0;
    std::vector<uint8_t> payload;
} ProtocolPacket_t;

class Protocol_CPP {
public:
    Protocol_CPP() {};
    virtual ~Protocol_CPP() {};

    uint16_t crc16_ccitt_false(const std::vector<uint8_t>& data);

    std::vector<uint8_t> cobs_encode(const std::vector<uint8_t>& input);
    bool cobs_decode(const std::vector<uint8_t>& input, std::vector<uint8_t>& output);

    uint8_t encode_receiver_field(uint8_t receiver_addr, bool is_write);
    void decode_receiver_field(uint8_t raw_receiver, uint8_t& receiver_addr, bool& is_write);

    bool validate_against_spec(uint8_t sender,uint8_t id1, uint8_t id2, bool is_write, const std::vector<uint8_t>& payload);

    bool build_packet(const ProtocolPacket_t& protocol_packet, std::vector<uint8_t>& out_packet, bool validate_spec = true);
    bool parse_packet(const std::vector<uint8_t>& raw_cobs_frame_no_delim, ProtocolPacket_t& out_packet);
    bool parse_packet_wire(const std::vector<uint8_t>& wire_data, ProtocolPacket_t& out_packet);

private:
    bool get_command_spec(uint8_t sender,uint8_t id1, uint8_t id2, size_t& payload_len, bool& allow_read, bool& allow_write);
};

#endif // PROTOCOL_CPP_H_
