import cv2
import time
import numpy as np
import threading
# from datetime import datetime


class RTSPHandler:
    def __init__(self, rtsp_urls, user_fps, duration, timeout=10, delay=5):
        """
        Initialize the RTSP DVR handler for multiple cameras.

        Args:
            rtsp_urls (list): List of RTSP URLs for each camera.
            user_fps (int): User-defined FPS for processing frames.
            duration (int): Duration (in seconds) to capture frames.
            timeout (int): Maximum time (in seconds) to wait for each RTSP stream.
            delay (int): Delay in seconds to fetch data from the past.
        """
        self.rtsp_urls = rtsp_urls
        self.user_fps = user_fps
        self.duration = duration
        self.timeout = timeout
        self.delay = delay

        # Store connections and metadata for each camera
        self.cameras = []

        # Establish connections for all cameras
        for url in rtsp_urls:
            self.cameras.append(self._initialize_camera(url))

    def _initialize_camera(self, rtsp_url):
        """
        Initialize a single RTSP camera connection with timeout.
        
        Args:
            rtsp_url (str): RTSP URL for the camera.

        Returns:
            dict: A dictionary containing connection details for the camera.
        """
        camera_data = {
            "url": rtsp_url,
            "cap": None,
            "success": False,
            "camera_fps": None,
            "frame_width": None,
            "frame_height": None,
        }

        def _open_capture():
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                camera_data["success"] = True
                camera_data["cap"] = cap
                camera_data["camera_fps"] = int(cap.get(cv2.CAP_PROP_FPS))
                camera_data["frame_width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                camera_data["frame_height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Use a thread to establish the connection with timeout
        thread = threading.Thread(target=_open_capture)
        thread.start()
        thread.join(self.timeout)

        if not camera_data["success"]:
            print(f"Error: Timeout after {self.timeout} seconds for {rtsp_url}")
        else:
            print(f"Connected to {rtsp_url} (FPS: {camera_data['camera_fps']})")

        return camera_data

    def test_connection(self):
        """
        Test all camera connections.
        
        Returns:
            list: A list of booleans indicating success for each camera.
        """
        return any([camera["success"] for camera in self.cameras])

    def aggregated_images(self):
        """
        Process all cameras and return aggregated results for each.

        Returns:
            dict: A dictionary mapping each RTSP URL to its aggregated frame image.
        """
        results = {}
        for camera in self.cameras:
            if camera["success"]:
                cap = camera["cap"]
                camera_fps = camera["camera_fps"]
                frame_width = camera["frame_width"]
                frame_height = camera["frame_height"]

                start_time = time.time() - self.duration - self.delay
                frame_positions = list(
                    map(
                        int,
                        np.linspace(
                            int(start_time * camera_fps),
                            int((start_time + self.duration) * camera_fps),
                            self.user_fps * self.duration,
                        ),
                    )
                )

                frames = []
                for frame_pos in frame_positions:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                    ret, frame = cap.read()
                    if not ret:
                        print(f"Warning: Failed to read frame at position {frame_pos} for {camera['url']}")
                        break
                    frames.append(frame)

                # Aggregate frames into a single image
                if frames:
                    results[camera["url"]] = self._aggregate_frames(frames, frame_width, frame_height)
                else:
                    results[camera["url"]] = None
            else:
                results[camera["url"]] = None

        return results

    def _aggregate_frames(self, frames, frame_width, frame_height):
        """
        Aggregate multiple frames into a single grid image.
        
        Args:
            frames (list): List of frames.
            frame_width (int): Width of a single frame.
            frame_height (int): Height of a single frame.

        Returns:
            np.ndarray: Aggregated image.
        """
        rows = int(np.ceil(np.sqrt(len(frames))))  # Number of rows
        cols = int(np.ceil(len(frames) / rows))    # Number of columns

        rframe_height = frame_height // rows
        rframe_width = frame_width // cols

        # Initialize a blank image
        nimg = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        for idx, frame in enumerate(frames):
            row = idx // cols
            col = idx % cols
            resized_frame = cv2.resize(frame, (rframe_width, rframe_height))
            nimg[
                row * rframe_height : (row + 1) * rframe_height,
                col * rframe_width : (col + 1) * rframe_width,
            ] = resized_frame

        return nimg

    def close(self):
        """
        Close all camera connections.
        """
        for camera in self.cameras:
            if camera["cap"]:
                camera["cap"].release()

    def video(self):
        """
        Generate a live video feed for all cameras.
        """
        results = {}
        for camera in self.cameras:
            if camera["success"]:
                cap = camera["cap"]
                ret, frame = cap.read()
                if not ret:
                    print(f"Warning: Failed to read frame for {camera['url']}")
                    continue
                results[camera["url"]] = frame
        return results
                
