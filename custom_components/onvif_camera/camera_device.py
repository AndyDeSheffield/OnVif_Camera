import logging
import json
import asyncio
import os

_LOGGER = logging.getLogger(__name__)
import onvif
from onvif import ONVIFCamera as ZeepONVIFCamera


class CameraDevice:
    """
    Represents a single ONVIF camera with MQTT discovery and PTZ control.
    """

    def __init__(self, unique_id, name, ip, port, user, password, ha_mqtt):
        self.unique_id = unique_id
        self.name = name
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        self.ha_mqtt = ha_mqtt
        self.mqtt_prefix = 'homeassistant'
        self.loop = asyncio.get_event_loop()
        # Placeholders until async setup runs
        self._ptz = None
        self._token = None
        self._camera = None

    async def setup(self):
        """Connect to ONVIF camera and publish MQTT discovery."""
        wsdl_dir= os.path.join(os.path.dirname(onvif.__file__), "wsdl")
        self._camera = ZeepONVIFCamera(self.ip, self.port, self.user, self.password,wsdl_dir=wsdl_dir)
        await self._camera.update_xaddrs()
        # Await service creation
        self._ptz = await self._camera.create_ptz_service()
        media = await self._camera.create_media_service()

        # Await profile retrieval
        profiles = await media.GetProfiles()
        self._token = profiles[0].token

        # Now publish MQTT discovery
        self.publish_static_data()
        self.publish_switch_entities()
        self.register_callbacks()

    # ----------------------------
    # MQTT discovery publishing
    # ----------------------------
    def publish_static_data(self) -> bool:
        topic = f"onvif_camera/device/{self.unique_id}/metadata"

        device_payload = {
            "identifiers": [self.unique_id],
            "name": self.name,
            "ip": self.ip,
            "port": self.port,
            "user": self.user,
        }
        device_payload = {k: v for k, v in device_payload.items() if v is not None}

        try:
            self.ha_mqtt.client.publish(topic, json.dumps(device_payload), retain=True)
            _LOGGER.debug("Published camera '%s' metadata to topic '%s'", self.name, topic)
            return True
        except Exception as e:
            _LOGGER.error("Failed to publish metadata for camera %s: %s", self.unique_id, e)
            return False

    def publish_switch_entities(self) -> bool:
        actions = [
            "pan_up", "pan_down", "pan_left", "pan_right",
            "zoom_in", "zoom_out",
            "go_home_position", "restart",
        ]
        try:
            for action in actions:
                object_id = f"{self.unique_id}_{action}"
                config_topic = f"{self.mqtt_prefix}/switch/{object_id}/config"
                state_topic = f"onvif_camera/{self.unique_id}/{action}/state"
                command_topic = f"onvif_camera/{self.unique_id}/{action}/set"

                payload = {
                    "name": f"{self.name} {action.replace('_',' ').title()}",
                    "unique_id": object_id,
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "device": {
                        "identifiers": [self.unique_id],
                        "name": self.name,
                    },
                }

                self.ha_mqtt.client.publish(config_topic, json.dumps(payload), retain=True)
                self.ha_mqtt.client.publish(state_topic, "OFF", retain=True)
                _LOGGER.debug("Published switch entity '%s' for camera '%s' to topic '%s'",
                              action, self.name, config_topic)
            return True
        except Exception as e:
            _LOGGER.error("Failed to publish switch entities for camera %s: %s", self.unique_id, e)
            return False

    def register_callbacks(self):
        # Nested sync callback that schedules your async handler
        def on_message(client, userdata, msg):
            self.loop.call_soon_threadsafe(asyncio.create_task, self._on_command(client, userdata, msg))

        # Subscribe to all command topics for this camera
        self.ha_mqtt.client.subscribe(f"onvif_camera/{self.unique_id}/+/set")
        self.ha_mqtt.client.on_message = on_message

 
    async def _on_command(self, client, userdata, msg):
        payload = msg.payload.decode()
        _LOGGER.info("Camera %s received %s on %s", self.name, payload, msg.topic)

        action = msg.topic.split("/")[-2]  # assumes ".../<action>/set"

        match payload:
            case "ON":
                match action:
                    case "pan_up":
                        await self.continuous_move(0, 0.1, 0)
                    case "pan_down":
                        await self.continuous_move(0, -0.1, 0)
                    case "pan_left":
                        await self.continuous_move(-0.1, 0, 0)
                    case "pan_right":
                        await self.continuous_move(0.1, 0, 0)
                    case "zoom_in":
                        await self.continuous_zoom(0.1)
                    case "zoom_out":
                        await self.continuous_zoom(-0.1)
                self.ha_mqtt.publish(msg.topic.replace("/set", "/state"), "ON", retain=True)

            case "OFF":
                match action:
                    case "pan_up" | "pan_down" | "pan_left" | "pan_right":
                        await self.stop_move()
                    case "zoom_in" | "zoom_out":
                        await self.stop_zoom()
                    case "restart":
                        await self.reconnect()
                self.ha_mqtt.publish(msg.topic.replace("/set", "/state"), "OFF", retain=True)

    async def reconnect(self):
        self._camera = ZeepONVIFCamera(self.ip, self.port, self.user, self.password)
        self._ptz = await self._camera.create_ptz_service()
        media = await self._camera.create_media_service()
        profiles = await media.GetProfiles()
        self._token = profiles[0].token

    # ----------------------------
    # PTZ control methods
    # ----------------------------
    async def continuous_move(self, pan: float, tilt: float, zoom: float):
        req = self._ptz.create_type("ContinuousMove")
        req.ProfileToken = self._token
        req.Velocity = {"PanTilt": {"x": pan, "y": tilt}, "Zoom": zoom}
        return await self._ptz.ContinuousMove(req)

    async def stop_move(self):
        req = self._ptz.create_type("Stop")
        req.ProfileToken = self._token
        req.PanTilt = True
        req.Zoom = True
        return await self._ptz.Stop(req)

    async def continuous_zoom(self, speed: float = 0.1):
        req = self._ptz.create_type("ContinuousMove")
        req.ProfileToken = self._token
        req.Velocity = {"Zoom": speed}
        return await self._ptz.ContinuousMove(req)

    async def stop_zoom(self):
        req = self._ptz.create_type("Stop")
        req.ProfileToken = self._token
        req.Zoom = True
        return await self._ptz.Stop(req)

    async def go_home_position(self):
        req = self._ptz.create_type("GotoHomePosition")
        req.ProfileToken = self._token
        return await self._ptz.GotoHomePosition(req)

    async def set_home_position(self):
        req = self._ptz.create_type("SetHomePosition")
        req.ProfileToken = self._token
        resp = await self._ptz.SetHomePosition(req)
        await self._ptz.Stop({"ProfileToken": self._token})
        return resp

    async def get_ptz_status(self):
        req = self._ptz.create_type("GetStatus")
        req.ProfileToken = self._token
        status = await self._ptz.GetStatus(req)
        pan = status.Position.PanTilt.x
        tilt = status.Position.PanTilt.y
        zoom = status.Position.Zoom.x
        return pan, tilt, zoom
