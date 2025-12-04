import logging
import json
from onvif import ONVIFCamera as ZeepONVIFCamera

_LOGGER = logging.getLogger(__name__)


class CameraDevice:
    """
    Represents a single ONVIF camera with MQTT discovery and PTZ control.
    """

    def __init__(self, unique_id, name, ip, port, user, password, ha_mqtt):
        self.unique_id = unique_id
        self.name = name
        self.ip=ip
        self.port=port
        self.user=user
        self.password=password
        self.ha_mqtt = ha_mqtt
        self.mqtt_prefix='homeassistant'
 
        # Connect to ONVIF camera
        camera = ZeepONVIFCamera(ip, port, user, password)
        self._ptz = camera.create_ptz_service()
        media = camera.create_media_service()
        self._token = media.GetProfiles()[0].token

    async def setup(self):
        """Publish metadata, switches, and register callbacks once MQTT is connected."""
        self.publish_static_data()
        self.publish_switch_entities()
        self.register_callbacks()

    # ----------------------------
    # MQTT discovery publishing
    # ----------------------------
    def publish_static_data(self) -> bool:
        """
        Publishes static metadata for this camera to Home Assistant via MQTT.
        """
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
            _LOGGER.debug(
                "Published camera '%s' metadata to topic '%s'", self.name, topic
            )
            return True
        except Exception as e:
            _LOGGER.error(
                "Failed to publish metadata for camera %s: %s", self.unique_id, e
            )
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
                state_topic  = f"onvif_camera/{self.unique_id}/{action}/state"
                command_topic= f"onvif_camera/{self.unique_id}/{action}/set"

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
                # Publish initial state (retained)
                self.ha_mqtt.client.publish(state_topic, "OFF", retain=True)
                _LOGGER.debug(
                    "Published switch entity '%s' for camera '%s' to topic '%s'",
                    action, self.name, config_topic,
                )
            return True
        except Exception as e:
            _LOGGER.error(
                "Failed to publish switch entities for camera %s: %s", self.unique_id, e
            )
            return False
        
    # async def publish_discovery(self):
    #     switches = {
    #         "pan_up": "Pan Up",
    #         "pan_down": "Pan Down",
    #         "pan_left": "Pan Left",
    #         "pan_right": "Pan Right",
    #         "zoom_in": "Zoom In",
    #         "zoom_out": "Zoom Out",
    #     }

    #     for key, label in switches.items():
    #         object_id = f"{self.unique_id}_{key}"
    #         config_topic = f"homeassistant/switch/{object_id}/config"
    #         state_topic = f"{self.unique_id}/switch.{key}/state"
    #         command_topic = f"{self.unique_id}/switch.{key}/set"

    #         payload = {
    #             "name": f"{self.name} {label}",
    #             "unique_id": object_id,
    #             "state_topic": state_topic,
    #             "command_topic": command_topic,
    #             "device": {
    #                 "identifiers": [self.unique_id],
    #                 "name": self.name,
    #             },
    #         }
    #         self.ha_mqtt.publish(config_topic, json.dumps(payload), retain=True)
    #         _LOGGER.info("Published discovery for %s %s", self.name, label)

    def register_callbacks(self):
        """
        Register a single MQTT callback for all switch topics under this camera.
        """
        base_topic = f"{self.unique_id}/switch"
        # Subscribe to everything under {unique_id}/switch
        self.ha_mqtt.client.subscribe(f"onvif_camera/{self.unique_id}/+/set")
        self.ha_mqtt.client.on_message = self._on_command
   
    def _on_command(self, client, userdata, msg):
        payload = msg.payload.decode()
        _LOGGER.info("Camera %s received %s on %s", self.name, payload, msg.topic)

        # Extract the action keyword from the topic (e.g. "pan_up", "zoom_out")
        action = msg.topic.split("/")[-2]  # assumes ".../<action>/set"

        match payload:
            case "ON":
                match action:
                    case "pan_up":
                        self.continuous_move(0, 0.1, 0)
                    case "pan_down":
                        self.continuous_move(0, -0.1, 0)
                    case "pan_left":
                        self.continuous_move(-0.1, 0, 0)
                    case "pan_right":
                        self.continuous_move(0.1, 0, 0)
                    case "zoom_in":
                        self.continuous_zoom(0.1)
                    case "zoom_out":
                        self.continuous_zoom(-0.1)
                self.ha_mqtt.publish(msg.topic.replace("/set", "/state"), "ON", retain=True)

            case "OFF":
                match action:
                    case "pan_up" | "pan_down" | "pan_left" | "pan_right":
                        self.stop_move()
                    case "zoom_in" | "zoom_out":
                        self.stop_zoom()
                    case "restart":
                        self.reconnect()
                self.ha_mqtt.publish(msg.topic.replace("/set", "/state"), "OFF", retain=True)

    def reconnect(self):
            self.camera = None
            # Recreate ONVIF client
            self.camera = ZeepONVIFCamera(self.ip, self.port, self.user, self.password)
        # ----------------------------
    # PTZ control methods
    # ----------------------------
    def continuous_move(self, pan: float, tilt: float, zoom: float):
        req = self._ptz.create_type("ContinuousMove")
        req.ProfileToken = self._token
        req.Velocity = {"PanTilt": {"x": pan, "y": tilt}, "Zoom": zoom}
        return self._ptz.ContinuousMove(req)

    def stop_move(self):
        req = self._ptz.create_type("Stop")
        req.ProfileToken = self._token
        req.PanTilt = True
        req.Zoom = True
        return self._ptz.Stop(req)

    def continuous_zoom(self, speed: float = 0.1):
        req = self._ptz.create_type("ContinuousMove")
        req.ProfileToken = self._token
        req.Velocity = {"Zoom": speed}
        return self._ptz.ContinuousMove(req)

    def stop_zoom(self):
        req = self._ptz.create_type("Stop")
        req.ProfileToken = self._token
        req.Zoom = True
        return self._ptz.Stop(req)

    def go_home_position(self):
        req = self._ptz.create_type("GotoHomePosition")
        req.ProfileToken = self._token
        return self._ptz.GotoHomePosition(req)

    def set_home_position(self):
        req = self._ptz.create_type("SetHomePosition")
        req.ProfileToken = self._token
        resp = self._ptz.SetHomePosition(req)
        self._ptz.Stop({"ProfileToken": self._token})
        return resp

    def get_ptz_status(self):
        req = self._ptz.create_type("GetStatus")
        req.ProfileToken = self._token
        status = self._ptz.GetStatus(req)
        pan = status.Position.PanTilt.x
        tilt = status.Position.PanTilt.y
        zoom = status.Position.Zoom.x
        return pan, tilt, zoom
