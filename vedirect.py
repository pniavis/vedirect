class LineDecoder:
    [SYNC, HEADER, FIELD,
     CHECKSUM, VALUE, PACKET] = range(6)

    def __init__(self, text_callback, hex_callback):
        self.text_callback = text_callback
        self.hex_callback = hex_callback
        self.state = LineDecoder.SYNC
        self.pending_bytes = bytearray()
        self.checksum = 0
        self.field = bytearray()
        self.value = bytearray()
        self.text_data = {}
        self.packet = bytearray()

        self.nr_bytes = 0
        self.nr_text_frames = 0
        self.nr_text_errors = 0
        self.nr_hex_packets = 0
        self.nr_hex_errors = 0
        pass

    def sync_parse(self, byte):
        if byte == ord('\r'):
            self.checksum = 0
            self.text_data = {}
            return LineDecoder.HEADER, byte
        elif byte == ord(':'):
            self.checksum = 0
            self.packet = bytearray()
            return LineDecoder.PACKET, 0
        else:
            return LineDecoder.SYNC, 0

    def header_parse(self, byte):
        if byte == ord('\n'):
            self.field = bytearray()
            return LineDecoder.FIELD, byte
        elif byte == ord('\r'):
            self.pending_bytes.append(byte)
            return LineDecoder.HEADER, 0
        else:
            return LineDecoder.SYNC, 0

    def field_parse(self, byte):
        if byte == ord('\r'):
            self.pending_bytes.append(byte)
            return LineDecoder.HEADER, 0
        elif byte == ord('\t'):
            if len(self.field) == 0:
                return LineDecoder.SYNC, 0
            elif self.field == b'Checksum':
                return LineDecoder.CHECKSUM, byte
            else:
                self.value = bytearray()
                return LineDecoder.VALUE, byte
        else:
            self.field.append(byte)
            return LineDecoder.FIELD, byte

    def checksum_parse(self, byte):
        self.checksum += byte
        if self.checksum % 256 == 0:
            self.nr_text_frames += 1
            self.text_callback(self.text_data)
        else:
            self.nr_text_errors += 1
        return LineDecoder.SYNC, 0

    def value_parse(self, byte):
        if byte == ord('\r'):
            self.text_data[self.field.decode()] = self.value.decode()
            return LineDecoder.HEADER, byte
        else:
            self.value.append(byte)
            return LineDecoder.VALUE, byte

    def packet_parse(self, byte):
        if byte == ord('\n'):
            if self.checksum % 256 == 0x55:
                self.nr_hex_packets += 1
                self.hex_callback(self.packet)
            else:
                self.nr_hex_errors += 1
            return LineDecoder.SYNC, 0
        self.packet.append(byte)
        pktlen = len(self.packet)
        if pktlen == 1:
            check = int(self.packet.decode(), 16)
        elif pktlen % 2 == 1:
            check = int(self.packet[-2:].decode(), 16)
        else:
            check = 0
        return LineDecoder.PACKET, check

    # return (new_state, checksum modify)
    handlers = {
        SYNC: sync_parse,
        HEADER: header_parse,
        FIELD: field_parse,
        CHECKSUM: checksum_parse,
        VALUE: value_parse,
        PACKET: packet_parse,
    }

    def __parse(self, byte):
        handler = LineDecoder.handlers[self.state]
        (new_state, checksum_mod) = handler(self, byte)
        self.state = new_state
        self.checksum += checksum_mod

    def parse(self, byte):
        while len(self.pending_bytes) > 0:
            self.__parse(self.pending_bytes.pop(0))
        self.__parse(byte)

        self.nr_bytes += 1

class TextDecoder:
    def decode(text_data):
        battery_current = int(text_data["I"])
        battery_voltage = int(text_data["V"]) / 1000.0
        load_current = int(text_data["IL"])
        panel_voltage = int(text_data["VPV"]) / 1000.0
        panel_power = int(text_data["PPV"])
        yield_total = int(text_data["H19"]) * 10.0
        yield_today = int(text_data["H20"]) * 10.0
        max_power_today = int(text_data["H21"])

        topics = [{"topic": "battery/current", "payload": battery_current},
                  {"topic": "battery/voltage", "payload": battery_voltage},
                  {"topic": "panel/voltage", "payload": panel_voltage},
                  {"topic": "panel/power", "payload": panel_power},
                  {"topic": "load/current", "payload": load_current},
                  {"topic": "yield/today", "payload": yield_today},
                  {"topic": "yield/total", "payload": yield_total},
                  {"topic": "yield/max_power_today", "payload": max_power_today},]
        return topics


class HexDecoder:
    def decode_get_response(packet_source):
        id = packet_source.getu16()
        flags = packet_source.getu8()
        if flags != 0:
            print('ERROR: id %d ==> flags %d' % (id, flags))
            return []

        def mktopic(topic, payload):
            return [{'topic':topic, 'payload':payload}]

        if id == 0x0201:
            return mktopic('device/state/value', packet_source.getu8())
        elif id == 0xedfd:
            return mktopic('battery/auto_equalization/value', packet_source.getu8())
        elif id == 0xedfc:
            return mktopic('battery/bulk_time_limit/value', packet_source.getu16())
        elif id == 0xedfb:
            return mktopic('battery/absorption_time_limit/value', packet_source.getu16())
        elif id == 0xedf7:
            return mktopic('battery/absorption_voltage/value', packet_source.getu16())
        elif id == 0xedf6:
            return mktopic('battery/float_voltage/value', packet_source.getu16())
        elif id == 0xedf4:
            return mktopic('battery/equalization_voltage/value', packet_source.getu16())
        elif id == 0xedf0:
            return mktopic('battery/maximum_current/value', packet_source.getu16())
        elif id == 0xedef:
            return mktopic('battery/voltage/value', packet_source.getu8())
        elif id == 0xedea:
            return mktopic('battery/voltage_setting/value', packet_source.getu8())

        return []

    def decode(packet):
        packet_source = _PacketSource(packet)
        cmd = packet_source.get4()
        if cmd == 7 or cmd == 8 or cmd == 10:
            return HexDecoder.decode_get_response(packet_source)


class _PacketSource:
    def __init__(self, packet):
        self._packet = bytearray(packet)

    def get4(self):
        nible = int(chr(self._packet[0]), 16)
        del self._packet[0]
        return nible

    def getu8(self):
        nible_high = self.get4()
        nible_low = self.get4()
        return (nible_high << 4) + nible_low

    def getu16(self):
        byte_low = self.getu8()
        byte_high = self.getu8()
        return (byte_high << 8) + byte_low
        pass

    def gets16(self):
        word = self.getu16()
        if word > 0x7fff:
            word = word - 0x10000
        return word

    def getu32(self):
        word_low = self.getu16()
        word_high = self.getu16()
        return (word_high << 16) + word_low
        pass

    def gets32(self):
        dword = self.getu32()
        if dword > 0x7fffffff:
            dword = dword - 0x100000000
        return dword


class _PacketBuilder:
    def __init__(self, command_id):
        self._packet = bytearray()
        self._checksum = 0
        self.__append_bytes(b':')
        self.add4(command_id)

    def __append_string(self, s):
        self.__append_bytes(s.encode())

    def __append_bytes(self, s):
        for b in s:
            self._packet.append(b)

    def add4(self, nible):
        self._checksum += nible
        self.__append_string('{:X}'.format(nible))

    def add8(self, byte):
        self._checksum += byte
        self.__append_string('{:02X}'.format(byte & 0xff))

    def add16(self, word):
        byte_low = word & 0xff
        byte_high = (word >> 8) & 0xff
        self.add8(byte_low)
        self.add8(byte_high)

    def add32(self, dword):
        word_low = dword & 0xffff
        word_high = (dword >> 16) & 0xffff
        self.add16(word_low)
        self.add16(word_high)

    def build(self):
        correction = (0x55 - self._checksum) % 256
        self.__append_string('{:02X}'.format(correction & 0xff))
        self.__append_bytes(b'\n')
        return self._packet


class LineCoder:
    _GET_COMMAND = 7
    _SET_COMMAND = 8

    def __init__(self, dispatch):
        self.dispatch = dispatch

    def __do_dispatch(self, data):
        self.dispatch(data)

    def __get_command(self, id):
        pb = _PacketBuilder(LineCoder._GET_COMMAND)
        pb.add16(id)
        pb.add8(0)
        return pb.build()

    def __set_command_byte(self, id, b):
        pb = _PacketBuilder(LineCoder._SET_COMMAND)
        pb.add16(id)
        pb.add8(0)
        pb.add8(b)
        return pb.build()

    def __check_range_inclusive(self, value, lb, ub):
        return value >= lb and value <= ub

    def __check_value_in_set(self, value, pset):
        return value in pset

    def read_battery_max_current(self):
        self.dispatch(self.__get_command(0xedf0))

    def read_float_voltage(self):
        self.dispatch(self.__get_command(0xedf6))

    def read_equalization_voltage(self):
        self.dispatch(self.__get_command(0xedf4))

    def read_auto_equalization_mode(self):
        self.dispatch(self.__get_command(0xedfd))

    def write_auto_equalization_mode(self, value):
        if not self.__check_range_inclusive(value, 0, 250):
            return
        self.dispatch(self.__set_command_byte(0xedfd, value))

    def read_bulk_time_limit(self):
        self.dispatch(self.__get_command(0xedfc))

    def read_absorption_time_limit(self):
        self.dispatch(self.__get_command(0xedfb))

    def read_absorption_voltage(self):
        self.dispatch(self.__get_command(0xedf7))

    def read_battery_voltage(self):
        self.dispatch(self.__get_command(0xedea))

    def write_battery_voltage(self, value):
        if not self.__check_value_in_set(value, [0, 12]):
            return
        self.dispatch(self.__set_command_byte(0xedef, value))

