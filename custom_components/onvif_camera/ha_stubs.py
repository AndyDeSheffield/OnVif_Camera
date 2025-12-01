# ha_stubs.py
class HomeAssistant:
    """Stub for Home Assistant core object."""
    def __init__(self):
        self.data = {}
        self.loop = None

ConfigType = dict
