import cv2
import time
import numpy as np
from datetime import datetime
import threading

class RTSPDvrHandler:
    def __init__(self, rtsp_url, user_fps, duration, timeout=10, delay=5):
        """
        Initialize the RTSP DVR handler with timeout for opening the RTSP stream.
        
        Args:
            rtsp_url (str): The RTSP URL of the DVR.
            user_fps (int): User-defined FPS for processing frames.
            duration (int): Duration (in seconds) to capture frames.
            timeout (int): Maximum time (in seconds) to wait for VideoCapture to open.
        """
        self.rtsp_url = rtsp_url
        self.user_fps = user_fps
        self.duration = duration
        self.frames_to_read = self.user_fps * self.duration
        self.cap = None
        self.success = False
        self.timeout = timeout
        self.delay = delay

        # Call _establish_connection to open VideoCapture and check if the URL is valid
        self._establish_connection()

    def _establish_connection(self):
        """
        Attempts to connect to the RTSP stream with a timeout. Runs the connection check in a separate thread.
        """
        self.open_thread = threading.Thread(target=self._open_capture)
        self.open_thread.start()

        # Wait for the thread to finish or timeout
        self.open_thread.join(self.timeout)
        if __name__ == "__main__":
            # If unsuccessful, raise an error
            if not self.success:
                print(f"Error: Timeout after {self.timeout} seconds trying to connect to {self.rtsp_url}")
                raise RuntimeError("Failed to open the RTSP stream within timeout.")
            else:
                self.camera_fps = self.cap.get(cv2.CAP_PROP_FPS)
                print(f"Successfully connected to {self.rtsp_url} (FPS: {self.camera_fps})")
        
    def _open_capture(self):
        """
        Attempts to open the VideoCapture object in a separate thread. Sets the success flag to True if successful.
        """
        self.cap = cv2.VideoCapture(self.rtsp_url)
        if self.cap.isOpened():
            self.success = True
            self.camera_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.rows = int(np.ceil(np.sqrt(self.frames_to_read)))  # Number of rows
            self.cols = int(np.ceil(self.frames_to_read / self.rows))  # Number of columns
            self.rframe_height = self.frame_height // self.rows
            self.rframe_width = self.frame_width // self.cols
    def convert_time(self, t, fmt=None):
        """Convert Unix time to formatted time."""
        if fmt:
            start_datetime = datetime.fromtimestamp(t)
            t = start_datetime.strftime(fmt)
        return t

    def __str__(self):
        return f"RTSPDvrHandler(rtsp_url={self.rtsp_url}, camera_fps={self.camera_fps}, duration={self.duration})"

    def test_connection(self):
        return self.success

    def retrieve_frames(self, start_time):
        frames = []
        frame_positions = list(map(int, np.linspace(int(start_time * self.camera_fps),
                                                    int((start_time + self.duration) * self.camera_fps), 
                                                    self.frames_to_read)))
        for frame_pos in frame_positions:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = self.cap.read()
            if not ret:
                print(f"Warning: Failed to read frame at position {frame_pos}")
                break
            frame = cv2.resize(frame, (self.rframe_width, self.rframe_height))
            frames.append(frame)

        return frames

    def process(self):
        # Maintain a `duration` second delay
        current_time = time.time()
        start_time = current_time - self.duration -self.delay # Fetch `duration` seconds of data from 't' seconds ago
        start_time = self.convert_time(start_time)
        frames = self.retrieve_frames(start_time)

        if frames:
            aggregated_image = self.aggregate_frames(frames)
            return aggregated_image
        else:
            print("Error: No frames retrieved.")
            return None

    def aggregate_frames(self, frames):
        if len(frames) == 0:
            return None

        # Initialize a blank image of the same size as the original frames
        nimg = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        for idx, frame in enumerate(frames):
            row = idx // self.cols
            col = idx % self.cols
            # Place the resized frame in the grid
            nimg[
                row * self.rframe_height : (row + 1) * self.rframe_height,
                col * self.rframe_width : (col + 1) * self.rframe_width,
            ] = frame

        return nimg

    def close(self):
        self.cap.release()



