from onvif import ONVIFCamera as ZeepONVIFCamera

class ONVIFCameraAPI:
    """
    Wrapper for controlling cameras using ONVIF (via onvif-zeep).
    """

    def __init__(self, ip, port, username, password):
        # Connect to camera
        camera = ZeepONVIFCamera(ip, port, username, password)

        # Create services
        self.__ptz = camera.create_ptz_service()
        media = camera.create_media_service()

        # Use the first profile
        self.__token = media.GetProfiles()[0].token

    def absolute_move(self, pan: float, tilt: float, zoom: float):
        req = self.__ptz.create_type('AbsoluteMove')
        req.ProfileToken = self.__token
        req.Position = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': zoom}
        return self.__ptz.AbsoluteMove(req)

    def continuous_move(self, pan: float, tilt: float, zoom: float):
        req = self.__ptz.create_type('ContinuousMove')
        req.ProfileToken = self.__token
        req.Velocity = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': zoom}
        return self.__ptz.ContinuousMove(req)

    def relative_move(self, pan: float, tilt: float, zoom: float):
        req = self.__ptz.create_type('RelativeMove')
        req.ProfileToken = self.__token
        req.Translation = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': zoom}
        return self.__ptz.RelativeMove(req)
    
    def continuous_zoom(self, speed: float = 0.1):
        req = self.__ptz.create_type('ContinuousMove')
        req.ProfileToken = self.__token
        req.Velocity = {'Zoom': speed}
        self.__ptz.ContinuousMove(req)

    
    def stop_zoom(self):
        stop_req = self.__ptz.create_type('Stop')
        stop_req.ProfileToken = self.__token
        stop_req.Zoom = True
        self.__ptz.Stop(stop_req)

    def stop_move(self):
        stop_req = self.__ptz.create_type('Stop')
        stop_req.ProfileToken = self.__token
        # Explicitly tell it to stop both axes
        stop_req.PanTilt = True
        stop_req.Zoom = True
        return self.__ptz.Stop(stop_req)

    def set_home_position(self):
        req = self.__ptz.create_type('SetHomePosition')
        req.ProfileToken = self.__token
        resp = self.__ptz.SetHomePosition(req)
        self.__ptz.Stop({'ProfileToken': self.__token})
        return resp

    def go_home_position(self):
        req = self.__ptz.create_type('GotoHomePosition')
        req.ProfileToken = self.__token
        return self.__ptz.GotoHomePosition(req)

    def get_ptz_status(self):
        req = self.__ptz.create_type('GetStatus')
        req.ProfileToken = self.__token
        status = self.__ptz.GetStatus(req)
        pan = status.Position.PanTilt.x
        tilt = status.Position.PanTilt.y
        zoom = status.Position.Zoom.x
        return pan, tilt, zoom

    def set_preset(self, preset_name: str):
        presets = self.get_preset_complete()
        req = self.__ptz.create_type('SetPreset')
        req.ProfileToken = self.__token
        req.PresetName = preset_name

        for preset in presets:
            if str(preset.Name) == preset_name:
                return None
        return self.__ptz.SetPreset(req)

    def get_preset(self):
        presets = self.get_preset_complete()
        return [(i, presets[i].Name) for i in range(len(presets))]

    def get_preset_complete(self):
        req = self.__ptz.create_type('GetPresets')
        req.ProfileToken = self.__token
        return self.__ptz.GetPresets(req)

    def remove_preset(self, preset_name: str):
        presets = self.get_preset_complete()
        req = self.__ptz.create_type('RemovePreset')
        req.ProfileToken = self.__token
        for preset in presets:
            if str(preset.Name) == preset_name:
                req.PresetToken = preset.token
                return self.__ptz.RemovePreset(req)
        return None

    def go_to_preset(self, preset_position: str):
        presets = self.get_preset_complete()
        req = self.__pt