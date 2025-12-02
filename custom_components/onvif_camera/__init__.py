import logging
import sys
import asyncio

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


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """
    Home Assistant entrypoint for the onvif_camera integration.

    - On Windows dev: main.py loads onvif_camera.yaml and injects it into config[DOMAIN].
    - In HA runtime: config[DOMAIN] should be provided via configuration.yaml or other HA mechanisms.

    Expected config dict:
      {
        "mqtt": {
          "host": "localhost",
          "port": 1883,
          "user": "user",
          "password": "pass"
        },
        "cameras": {
          "cam1": { "name": "...", "ip": "...", "port": 8080, "user": "...", "password": "..." },
          "cam2": { ... }
        }
      }
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

    hass.data[DOMAIN] = {}

    # Create and register CameraDevice objects
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
        ha_mqtt.register_device(cam)

        # Schedule discovery publish
        create_task = getattr(hass, "async_create_task", None)
        if callable(create_task):
            create_task(cam.publish_discovery())
        else:
            # Windows stubs/dev runner
            hass.loop.create_task(cam.publish_discovery())

    return True
