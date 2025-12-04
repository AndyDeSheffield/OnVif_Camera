import asyncio
import yaml
from pathlib import Path

# Import your integration setup
from custom_components.onvif_camera import async_setup

# Spoof HomeAssistant and ConfigType for dev
class FakeHass:
    def __init__(self):
        self.data = {}
        self.loop = asyncio.get_event_loop()

class FakeConfig(dict):
    pass

async def main():
    # Load local YAML
    from pathlib import Path

# main.py is at repo root, YAML is inside custom_components/onvif_camera
    yaml_path = Path(__file__).resolve().parent / "custom_components" / "onvif_camera" / "onvif_camera.yaml"

    with open(yaml_path, "r") as f:
        file_conf = yaml.safe_load(f) or {}

    # Wrap into HA-style config
    config = FakeConfig()
    config["onvif_camera"] = file_conf

    # Create fake hass
    hass = FakeHass()

    # Call your setup
    ok = await async_setup(hass, config)
    print("Setup result:", ok)
    print("Cameras loaded:", list(hass.data.get("onvif_camera", {}).keys()))
    await asyncio.Event().wait()  # blocks forever
if __name__ == "__main__":
    asyncio.run(main())
