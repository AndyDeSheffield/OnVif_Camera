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
        self.ha_mqtt = ha_mqtt

        # Connect to ONVIF camera
        camera = ZeepONVIFCamera(ip, port, user, password)
        self._ptz = camera.create_ptz_service()
        media = camera.create_media_service()
        self._token = media.GetProfiles()[0].token

    # ----------------------------
    # MQTT discovery publishing
    # ----------------------------
    async def publish_discovery(self):
        switches = {
            "pan_up": "Pan Up",
            "pan_down": "Pan Down",
            "pan_left": "Pan Left",
            "pan_right": "Pan Right",
            "zoom_in": "Zoom In",
            "zoom_out": "Zoom Out",
        }

        for key, label in switches.items():
            object_id = f"{self.unique_id}_{key}"
            config_topic = f"homeassistant/switch/{object_id}/config"
            state_topic = f"{self.unique_id}/switch.{key}/state"
            command_topic = f"{self.unique_id}/switch.{key}/set"

            payload = {
                "name": f"{self.name} {label}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "command_topic": command_topic,
                "device": {
                    "identifiers": [self.unique_id],
                    "name": self.name,
                },
            }
            self.ha_mqtt.publish(config_topic, json.dumps(payload), retain=True)
            _LOGGER.info("Published discovery for %s %s", self.name, label)

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
