import asyncio
import logging
import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


class HaMqtt:
    """
    Singleton MQTT interface for Home Assistant discovery.
    Manages one client connection, publishes messages, and dispatches incoming topics.
    """

    def __init__(self, mqtt_host="localhost", mqtt_port=1883,
                 mqtt_username=None, mqtt_password=None, client_id="ha_mqtt"):
        self.client = mqtt.Client(client_id=client_id)
        if mqtt_username and mqtt_password:
            self.client.username_pw_set(mqtt_username, mqtt_password)

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        self.connected = asyncio.Event()
        self.client.connect(mqtt_host, mqtt_port, keepalive=10)
        self.client.loop_start()

        # registry of camera devices keyed by unique_id
        self.devices = {}

    def register_device(self, device):
        """Register a CameraDevice to receive MQTT commands."""
        self.devices[device.unique_id] = device
        _LOGGER.info("Registered device %s", device.unique_id)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected.set()
            _LOGGER.info("MQTT connected successfully")
            # subscribe to all switch topics for all devices
            client.subscribe("+/switch.#")
        else:
            _LOGGER.error("MQTT connection failed with code %s", rc)

    def on_disconnect(self, client, userdata, rc):
        _LOGGER.info("MQTT disconnected with code %s", rc)
        self.connected.clear()

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        _LOGGER.info("Received %s on %s", payload, msg.topic)

        # Dispatch to the correct CameraDevice based on unique_id prefix
        unique_id = msg.topic.split("/")[0]
        device = self.devices.get(unique_id)
        if device:
            device.handle_mqtt_command(msg.topic, payload)

    def publish(self, topic, payload, retain=False):
        self.client.publish(topic, payload, retain=retain)
