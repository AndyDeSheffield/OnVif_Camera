import logging
import asyncio
# from homeassistant.core import HomeAssistant
# from homeassistant.helpers.typing import ConfigType
from .ha_stubs import HomeAssistant, ConfigType
from .ha_mqtt import HaMqtt

_LOGGER = logging.getLogger(__name__)

DOMAIN = "onvif_camera"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the ONVIF Camera MQTT PTZ integration from configuration.yaml."""

    conf = config.get(DOMAIN, {})
    if not conf:
        _LOGGER.warning("No configuration found for %s, using defaults", DOMAIN)
        conf = {
            "camera_name": "above_garage",
            "camera_ip": "192.168.2.21",
            "camera_port": 8080,
            "camera_user": "admin",
            "camera_password": "Ark674exc10",
            "mqtt_host": "localhost",
            "mqtt_port": 1883,
            "mqtt_user": "mqtt_user",
            "mqtt_password": "pj3NoqyHw2wzAOjj16xB!"
        }
    camera_name = conf.get("camera_name", "above_garage")
    camera_ip = conf.get("camera_ip")
    camera_port = conf.get("camera_port", 8080)
    camera_user = conf.get("camera_user")
    camera_password = conf.get("camera_password")
    mqtt_host = conf.get("mqtt_host", "localhost")
    mqtt_port = conf.get("mqtt_port", 1883)
    mqtt_user = conf.get("mqtt_user")
    mqtt_password = conf.get("mqtt_password")

    if not camera_ip or not camera_user or not camera_password:
        _LOGGER.error("Missing required camera configuration values")
        return False

    ha_mqtt = HaMqtt(
        camera_name=camera_name,
        camera_ip=camera_ip,
        camera_port=camera_port,
        camera_user=camera_user,
        camera_password=camera_password,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_user,
        mqtt_password=mqtt_password
    )

    # Store instance in hass.data for later use
    hass.data[DOMAIN] = ha_mqtt

    # Publish discovery payloads on startup
    hass.loop.create_task(ha_mqtt.publish_discovery())
    while True:
        await asyncio.sleep(30)
    _LOGGER.info("ONVIF Camera MQTT PTZ integration initialized for %s", camera_name)
    return True
