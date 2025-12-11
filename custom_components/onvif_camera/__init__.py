import logging
import sys
import asyncio
import os
import yaml

from .ha_mqtt import HaMqtt
from .camera_device import CameraDevice

# Conditional HA type imports: use stubs on Windows, real HA in HA runtime
if sys.platform == "win32":
    from .ha_stubs import HomeAssistant, ConfigType
else:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)
DOMAIN = "onvif_camera"
def init_debugger():
    """Start debugpy if YAML toggle is enabled."""
    try:
        config_path = "/config/onvif_camera.yaml"
        debug_enabled = False

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                conf = yaml.safe_load(f) or {}
            debug_enabled = conf.get("debug", False)
        if debug_enabled:
            import debugpy
            debugpy.listen(("0.0.0.0", 5678))
            _LOGGER.warning("Debugger is listening on port 5678")
            # Optional: block until VS Code attaches
            # debugpy.wait_for_client()
    except Exception as e:
        _LOGGER.warning("debugpy not started: %s", e)

# Call immediately at import time
init_debugger()

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """
    Home Assistant entrypoint for the onvif_camera integration.
    """
    conf = config.get(DOMAIN, {})
    mqtt_conf = conf.get("mqtt", {})
    cameras_conf = conf.get("cameras", {})

    if not mqtt_conf:
        _LOGGER.error("No MQTT configuration found under config[%s]['mqtt']", DOMAIN)
        return False
    if not cameras_conf:
        _LOGGER.error("No cameras configured under config[%s]['cameras']", DOMAIN)
        return False
            
    # Initialise one shared MQTT client
    ha_mqtt = HaMqtt(
        mqtt_host=mqtt_conf.get("host", "localhost"),
        mqtt_port=mqtt_conf.get("port", 1883),
        mqtt_username=mqtt_conf.get("user"),
        mqtt_password=mqtt_conf.get("password"),
    )
    await ha_mqtt.connect()

    hass.data[DOMAIN] = {}

    # Create and fully set up CameraDevice objects sequentially
    for unique_id, cam_conf in cameras_conf.items():
        try:
            cam = CameraDevice(
                unique_id=unique_id,
                name=cam_conf.get("name", unique_id),
                ip=cam_conf["ip"],
                port=cam_conf.get("port", 8080),
                user=cam_conf["user"],
                password=cam_conf["password"],
                ha_mqtt=ha_mqtt,
            )
        except KeyError as e:
            _LOGGER.error("Camera '%s' missing required field: %s", unique_id, e)
            continue

        hass.data[DOMAIN][unique_id] = cam

        # Await setup here instead of scheduling
        await cam.setup()

    return True
