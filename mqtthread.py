import paho.mqtt.client as mqtt
import threading
import queue


class MqttThread(threading.Thread):
    def __init__(self, hostname, parser):
        super().__init__()
        self.hostname = hostname
        self.parser = parser
        self.publish_queue = queue.Queue()
        self.client = mqtt.Client()
        self.setDaemon(True)

    def stop_processing(self):
        self.publish_queue.put(None)
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, msgs):
        self.publish_queue.put(msgs)

    def run(self):
        self.client.connect(self.hostname)

        def on_message(client, userdata, msg):
            self.parser.parse(msg.topic, msg.payload.decode())

        self.client.subscribe("+/+/read")
        self.client.subscribe("+/+/write")

        self.client.on_message = on_message
        self.client.loop_start()

        while True:
            msgs = self.publish_queue.get()
            if msgs is None:
                return
            for m in msgs:
                self.client.publish(m['topic'], m['payload'])
