
import cv2
import time

def initialize_cameras(cameras):
    """Initializes video captures for each camera."""
    caps = []
    for cam in cameras:
        link = cam.get('link')
        if isinstance(link, str) and link.isdigit():
            link = int(link)
        
        cap = cv2.VideoCapture(link, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            print(f"Error: Could not open camera {cam.get('name')}.")
            caps.append(None)
        else:
            caps.append(cap)
    return caps

def release_cameras(caps):
    """Releases all video captures."""
    for cap in caps:
        if cap:
            cap.release()

def read_frame(cap):
    """Reads a frame from a video capture, with retries."""
    for _ in range(3): # Retry 3 times
        ret, frame = cap.read()
        if ret:
            return frame
        time.sleep(0.1)
    return None
