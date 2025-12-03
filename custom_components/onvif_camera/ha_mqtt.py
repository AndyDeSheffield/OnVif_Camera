import asyncio
import logging
import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)

class HaMqtt:
    def __init__(self, mqtt_host="localhost", mqtt_port=1883,
                 mqtt_username=None, mqtt_password=None, prefix="homeassistant"):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.mqtt_prefix = prefix
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.connected = asyncio.Event()

    async def connect(self,timeout=10):
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        self.client.connect(self.mqtt_host, self.mqtt_port, keepalive=10)
        self.client.loop_start()

        try:
            await asyncio.wait_for(self.connected.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise RuntimeError("MQTT connection timed out")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected.set()
            _LOGGER.info("MQTT connected successfully")
        else:
            _LOGGER.error("MQTT connection failed with code %s", rc)

    def on_disconnect(self, client, userdata, rc):
        _LOGGER.info("MQTT disconnected with code %s", rc)
        self.connected.clear()

    def publish(self, topic, payload, retain=False):
        _LOGGER.info("Publishing to %s retain=%s payload=%s", topic, retain, payload)
        self.client.publish(topic, payload, retain=retain)
