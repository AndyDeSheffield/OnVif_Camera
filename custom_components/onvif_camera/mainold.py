#!/usr/bin/env python3
from onvif_camera import ONVIFCamera   # assuming your class is saved in onvif_camera.py
import time
def main():
    # Replace with your camera details
    ip = "192.168.2.21"
    port = 8080
    user = "admin"
    password = "Ark674exc10"
    duration=0.5
    cam = ONVIFCamera(ip, port, user, password)

    print("Moving Up...")
    cam.continuous_move(0, 0.1, 0)
    time.sleep(duration)
    cam.stop_move()

    print("Moving Down...")
    cam.continuous_move(0, -0.1, 0)
    time.sleep(duration)
    cam.stop_move()

    print("Moving Left...")
    cam.continuous_move(-0.1, 0, 0)
    time.sleep(duration)
    cam.stop_move()

    print("Moving Right...")
    cam.continuous_move(0.1, 0, 0)
    time.sleep(duration)
    cam.stop_move()

    print("Zoom in...")
    cam.continuous_zoom(0.1)
    time.sleep(duration)
    cam.stop_zoom()

    print("Zoom out...")
    cam.continuous_zoom(-0.1,)
    time.sleep(duration)
    cam.stop_zoom()

    print("Getting PTZ status...")
    pan, tilt, zoom = cam.get_ptz_status()
    print(f"Pan={pan}, Tilt={tilt}, Zoom={zoom}")

if __name__ == "__main__":
    main()
