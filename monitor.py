import serial
import signal
import queue

import vedirect
import iothreads
import mqtthread
import mqttparser

READ_TIMEOUT = 1.0

class Throttler:
    def __init__(self, interval):
        self.interval = interval
        self.turn = 0

    def __call__(self, f):
        def wrapped_f(*args):
            self.turn += 1
            if self.turn == self.interval:
                self.turn = 0
                f(*args)

        return wrapped_f

@Throttler(10)
def text_handler(text_data):
    topics = vedirect.TextDecoder.decode(text_data)
    mqtt_thread.publish(topics)


def hex_handler(hex_packet):
    topics = vedirect.HexDecoder.decode(hex_packet)
    if len(topics) > 0:
        mqtt_thread.publish(topics)
        print(topics)

ser = serial.Serial(port='/dev/ttyAMA0',
                    baudrate=19200,
                    timeout=READ_TIMEOUT)
line_decoder = vedirect.LineDecoder(text_handler, hex_handler)
read_thread = iothreads.ReaderThread(ser, line_decoder)
read_thread.setDaemon(True)
read_thread.start()
write_queue = queue.Queue()
write_thread = iothreads.WritterThread(ser, write_queue)
write_thread.setDaemon(True)
write_thread.start()

def dispatch(data):
    write_queue.put(data)
line_coder = vedirect.LineCoder(dispatch)

mqtt_thread = mqtthread.MqttThread('localhost', mqttparser.Parser(line_coder))
mqtt_thread.start()

try:
    signal.pause()
finally:
    pass

mqtt_thread.stop_processing()
write_thread.stop_processing()
mqtt_thread.join()
write_thread.join()
ser.close()
read_thread.join()


