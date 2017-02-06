import serial
import threading


class ReaderThread(threading.Thread):
    def __init__(self, port, parser):
        super(ReaderThread, self).__init__()

        self.port = port
        self.parser = parser

    def run(self):
        while True:
            try:
                data = self.port.read(512)
            except serial.SerialException:
                break
            if len(data) != 0:
                for b in data:
                    self.parser.parse(b)


class WritterThread(threading.Thread):
    def __init__(self, port, queue):
        super(WritterThread, self).__init__()

        self.port = port
        self.queue = queue

    def stop_processing(self):
        self.queue.put(None)

    def run(self):
        while True:
            data = self.queue.get()
            if data is None:
                break
            try:
                self.port.write(data)
            except serial.SerialException:
                break
