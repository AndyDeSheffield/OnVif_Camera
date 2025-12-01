import asyncio
import json
import logging
import paho.mqtt.client as mqtt
from onvif_camera import ONVIFCamera

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)

class HaMqtt:
    """
    Async MQTT interface for Home Assistant discovery and PTZ control.
    """

    def __init__(self, camera_name: str, camera_ip: str, camera_port: int,
                 camera_user: str, camera_password: str,
                 mqtt_host="localhost", mqtt_port=1883,
                 username=None, password=None, client_id="ha_mqtt"):
        self.camera_name = camera_name
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.username = username
        self.password = password
        self.client_id = client_id

        # Init ONVIF camera
        self.cam = ONVIFCamera(camera_ip, camera_port, camera_user, camera_password)

        # Init MQTT client
        self.client = mqtt.Client(client_id=self.client_id)
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        self.connected = asyncio.Event()

    async def connect(self):
        if self.connected.is_set():
            return True
        try:
            self.client.connect(self.mqtt_host, self.mqtt_port, keepalive=10)
            self.client.loop_start()
            for _ in range(50):  # wait up to 10s
                await asyncio.sleep(0.2)
                if self.connected.is_set():
                    break
            return self.connected.is_set()
        except Exception as e:
            _LOGGER.error(f"MQTT connection error: {e}")
            return False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected.set()
            _LOGGER.info("MQTT connected successfully")
            client.subscribe(f"{self.camera_name}/switch.#")
        else:
            _LOGGER.error(f"MQTT connection failed with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        _LOGGER.info(f"MQTT disconnected with code {rc}")
        self.connected.clear()

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        subtopic = msg.topic.split("/")[-1]  # e.g. "switch.pan_up/set"
        _LOGGER.info(f"Received {payload} on {msg.topic}")

        # Map commands to PTZ actions
        if payload == "start":
            if subtopic == "switch.pan_up/set":
                self.cam.continuous_move(0, 0.1, 0)
            elif subtopic == "switch.pan_down/set":
                self.cam.continuous_move(0, -0.1, 0)
            elif subtopic == "switch.pan_left/set":
                self.cam.continuous_move(-0.1, 0, 0)
            elif subtopic == "switch.pan_right/set":
                self.cam.continuous_move(0.1, 0, 0)
            elif subtopic == "switch.zoom_in/set":
                self.cam.continuous_zoom(0.1)
            elif subtopic == "switch.zoom_out/set":
                self.cam.continuous_zoom(-0.1)
            client.publish(msg.topic.replace("/set", "/state"), "ON", retain=True)

        elif payload == "stop":
            if subtopic.startswith("switch.pan_"):
                self.cam.stop_move()
            elif subtopic.startswith("switch.zoom_"):
                self.cam.stop_zoom()
            client.publish(msg.topic.replace("/set", "/state"), "OFF", retain=True)

    async def publish_discovery(self):
        if not await self.connect():
            return False

        switches = {
            "pan_up":   "Pan Up",
            "pan_down": "Pan Down",
            "pan_left": "Pan Left",
            "pan_right":"Pan Right",
            "zoom_in":  "Zoom In",
            "zoom_out": "Zoom Out",
        }

        for key, name in switches.items():
            object_id = f"{self.camera_name}_{key}"
            config_topic = f"homeassistant/switch/{object_id}/config"
            state_topic  = f"{self.camera_name}/switch.{key}/state"
            command_topic= f"{self.camera_name}/switch.{key}/set"

            payload = {
                "name": f"{self.camera_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "command_topic": command_topic,
                "device": {
                    "identifiers": [self.camera_name],
                    "name": self.camera_name
                }
            }
            self.client.publish(config_topic, json.dumps(payload), retain=True)
            _LOGGER.info(f"Published discovery for {name}")

        return True

    async def disconnect(self):
        if self.connected.is_set():
            self.client.disconnect()
            for _ in range(50):
                await asyncio.sleep(0.2)
                if not self.connected.is_set():
                    break
            self.client.loop_stop()
            _LOGGER.info("Disconnected from MQTT")
            return True
        return False
