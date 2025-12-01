import asyncio
from ha_stubs import HomeAssistant, ConfigType
from custom_components.onvif_camera import __init__ as onvif_init

async def main():
    hass = HomeAssistant()
    hass.loop = asyncio.get_event_loop()
    hass.data = {}

    config = {
        onvif_init.DOMAIN: {
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
    }

    await onvif_init.async_setup(hass, config)

    # Keep alive so MQTT loop runs
    try:
        while True:
            await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("Shutting down")

if __name__ == "__main__":
    asyncio.run(main())
