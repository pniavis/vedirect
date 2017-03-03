from collections import defaultdict

class Parser:

    def __init__(self, line_encoder):
        self._line_encoder = line_encoder
        self._commands = defaultdict(lambda : self._unknown_topic,
            {
                "battery/maximum_current/read": self._read_battery_max_current,
                "battery/float_voltage/read": self._read_float_voltage,
                "battery/equalization_voltage/read": self._read_equalization_voltage,
                "battery/auto_equalization_mode/read": self._read_auto_equalization_mode,
                "battery/auto_equalization_mode/write": self._write_auto_equalization_mode,
                "battery/bulk_time_limit/read": self._read_bulk_time_limit,
                "battery/absorption_time_limit/read": self._read_absorption_time_limit,
                "battery/voltage/read": self._read_battery_voltage,
                "battery/voltage/write": self._write_battery_voltage,
                "battery/temperature_compensation/read": self._read_battery_temperature_compensation,

            })

    def _unknown_topic(self, topic, payload):
        print('unknown topic: %s' % topic)

    def _read_battery_max_current(self, topic, payload):
        self._line_encoder.read_battery_max_current()

    def _read_float_voltage(self, topic, payload):
        self._line_encoder.read_float_voltage()

    def _read_equalization_voltage(self, topic, payload):
        self._line_encoder.read_equalization_voltage()

    def _read_auto_equalization_mode(self, topic, payload):
        self._line_encoder.read_auto_equalization_mode()

    def _write_auto_equalization_mode(self, topic, payload):
        self._line_encoder.write_auto_equalization_mode(int(payload))

    def _read_bulk_time_limit(self, topic, payload):
        self._line_encoder.read_bulk_time_limit()

    def _read_absorption_time_limit(self, topic, payload):
        self._line_encoder.read_absorption_time_limit()

    def _read_battery_voltage(self, topic, payload):
        self._line_encoder.read_battery_voltage()

    def _write_battery_voltage(self, topic, payload):
        self._line_encoder.write_battery_voltage(int(payload))

    def _read_battery_temperature_compensation(self, topic, payload):
        self._line_encoder.read_battery_temperature_compensation()

    def parse(self, topic, payload):
        self._commands[topic](topic, payload)