from onvif import ONVIFCamera
import cv2
import time
import numpy as np
from datetime import datetime
import threading

class ONVIFHandler:
    def __init__(self, ip, port, username, password, user_fps, duration, timeout=10, delay=5):
        """
        Initialize the ONVIF DVR handler with support for multiple cameras.

        Args:
            ip (str): The IP address of the DVR.
            port (int): The port of the ONVIF service (usually 80).
            username (str): Username for ONVIF authentication.
            password (str): Password for ONVIF authentication.
            user_fps (int): User-defined FPS for processing frames.
            duration (int): Duration (in seconds) to capture frames.
            timeout (int): Maximum time (in seconds) to wait for VideoCapture to open.
            delay (int): Delay (in seconds) before fetching frames.
        """
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.user_fps = user_fps
        self.duration = duration
        self.timeout = timeout
        self.delay = delay
        self.frames_to_read = self.user_fps * self.duration

        self.successes = []
        self.cameras = {}  # Store camera-specific details (profile, cap, dimensions, etc.)
        self._initialize_camera()  # Discover ONVIF profiles and prepare for processing

    def _initialize_camera(self):
        """
        Initialize the ONVIF camera, retrieve profiles, and calculate parameters for each.
        """
        try:
            self.camera = ONVIFCamera(self.ip, self.port, self.username, self.password)
            self.media_service = self.camera.create_media_service()
            profiles = self.media_service.GetProfiles()
            self.success = [False] * len(profiles)
            for i, profile in enumerate(profiles):
                rtsp_url = self._retrieve_rtsp_url(profile)
                if rtsp_url:
                    cap = cv2.VideoCapture(rtsp_url)
                    if not cap.isOpened():
                        print(f"Failed to connect to camera profile: {profile.name}")
                        continue
                    self.successes[i] = True

                    camera_fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    rows = int(np.ceil(np.sqrt(self.frames_to_read)))  # Grid rows
                    cols = int(np.ceil(self.frames_to_read / rows))  # Grid cols
                    rframe_height = frame_height // rows
                    rframe_width = frame_width // cols

                    # Store camera-specific parameters
                    self.cameras[profile.name] = {
                        "profile": profile,
                        "rtsp_url": rtsp_url,
                        "cap": cap,
                        "camera_fps": camera_fps,
                        "frame_width": frame_width,
                        "frame_height": frame_height,
                        "rows": rows,
                        "cols": cols,
                        "rframe_height": rframe_height,
                        "rframe_width": rframe_width,
                    }
                else:
                    print(f"Skipping profile {profile.name} due to missing RTSP URL.")
        except Exception as e:
            print(f"Error initializing ONVIF cameras: {e}")

    def _retrieve_rtsp_url(self, profile):
        """
        Retrieve the RTSP URL for a specific profile.

        Args:
            profile: ONVIF camera profile object.
        Returns:
            str: RTSP URL or None if retrieval fails.
        """
        try:
            stream_uri = self.media_service.GetStreamUri({
                'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}},
                'ProfileToken': profile.token
            })
            return stream_uri['Uri']
        except Exception as e:
            print(f"Error retrieving RTSP URL for profile {profile.name}: {e}")
            return None

    def process(self):
        """
        Process all cameras in the DVR, fetching frames for each, and return results.

        Returns:
            dict: A dictionary where keys are camera names and values are aggregated images or None.
        """
        results = {}
        for camera_name, camera_details in self.cameras.items():
            print(f"Processing camera: {camera_name}")
            results[camera_name] = self._process_camera(camera_name, camera_details)

        return results

    def _process_camera(self, camera_name, camera_details):
        """
        Process frames from a single camera.

        Args:
            camera_details (dict): Details about the camera (e.g., cap, frame dimensions).
        Returns:
            Aggregated image or None if processing fails.
        """
        try:
            cap = camera_details["cap"]
            camera_fps = camera_details["camera_fps"]
            rows = camera_details["rows"]
            cols = camera_details["cols"]
            rframe_width = camera_details["rframe_width"]
            rframe_height = camera_details["rframe_height"]

            current_time = time.time()
            start_time = current_time - self.duration - self.delay  # Fetch `duration` seconds of data from `delay` seconds ago
            start_frame_index = int(start_time * camera_fps)
            frames = []

            frame_positions = list(map(
                int,
                np.linspace(start_frame_index, start_frame_index + self.frames_to_read, self.frames_to_read)
            ))

            for frame_pos in frame_positions:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                ret, frame = cap.read()
                if not ret:
                    print(f"Warning: Failed to read frame at position {frame_pos}")
                    break
                frame = cv2.resize(frame, (rframe_width, rframe_height))
                frames.append(frame)

            # Aggregate frames into a grid image
            if frames:
                return self._aggregate_frames(frames, camera_details)
            else:
                print(f"No frames retrieved for camera: {camera_name}")
                return None

        except Exception as e:
            print(f"Error processing camera {camera_name}: {e}")
            return None

    def _aggregate_frames(self, frames, camera_details):
        """
        Aggregate frames into a single grid image.

        Args:
            frames: List of frames to aggregate.
            camera_details: Camera-specific details (e.g., dimensions, rows, cols).
        Returns:
            Aggregated grid image or None if frames are empty.
        """
        if not frames:
            return None

        frame_width = camera_details["frame_width"]
        frame_height = camera_details["frame_height"]
        rows = camera_details["rows"]
        cols = camera_details["cols"]
        rframe_width = camera_details["rframe_width"]
        rframe_height = camera_details["rframe_height"]

        grid_image = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        for idx, frame in enumerate(frames):
            row = idx // cols
            col = idx % cols
            grid_image[
                row * rframe_height : (row + 1) * rframe_height,
                col * rframe_width : (col + 1) * rframe_width
            ] = frame

        return grid_image

    def close(self):
        """
        Release all VideoCapture objects.
        """
        for camera_name, camera_details in self.cameras.items():
            if camera_details["cap"]:
                camera_details["cap"].release()
                print(f"Released VideoCapture for camera: {camera_name}")

    def test_connection(self):
        """
        Test the connection to the ONVIF camera.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        return any(self.successes)
    
    def video(self):
        """
        Generate a live video feed for all cameras.
        """
        results = {}
        for camera_name, camera_details in self.cameras.items():
            if camera_details["cap"]:
                cap = camera_details["cap"]
                ret, frame = cap.read()
                if not ret:
                    print(f"Warning: Failed to read frame for {camera_name}")
                    continue
                results[camera_name] = frame
        return results
