import cv2
import math
import numpy as np
import os

class VideoProcess:
    def __init__(self, video_path, f, t):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        # Check if the video file is opened successfully
        if not self.cap.isOpened():
            raise ValueError(f"Error: Could not open video file at {video_path}")
        
        self.fps = round(self.cap.get(cv2.CAP_PROP_FPS))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frames_to_read = f * t  # Total frames to read
        self.rows = math.ceil(math.sqrt(self.frames_to_read))  # Number of rows
        self.cols = math.ceil(self.frames_to_read / self.rows)  # Number of columns
        self.nframe_height = self.frame_height // self.rows
        self.nframe_width = self.frame_width // self.cols
        self.f = f
        self.t = t

    def get_frame(self):
        return self.fps

    def new_image(self, doSave=False, sPath=None):
        # Pre-allocate resized frames list based on frames to read
        resized_frames = [None] * self.frames_to_read
        video = self.cap

        for fc in range(self.frames_to_read):
            # Calculate frame position to skip frames
            frame_position = (fc // self.f) * self.fps + (fc % self.f)
            
            # Set video capture to the correct frame position
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
            ret, frame = video.read()
            
            if not ret:
                print(f"Warning: Failed to read frame at position {frame_position}")
                continue
            
            # Resize the frame
            resized_frame = cv2.resize(frame, (self.nframe_width, self.nframe_height))
            resized_frames[fc] = resized_frame

        # Create an empty array to hold the final stacked image
        nimg = np.zeros((self.nframe_height * self.rows, self.nframe_width * self.cols, 3), dtype=np.uint8)

        # Stack the resized frames into the final image
        for i in range(self.rows):
            for j in range(self.cols):
                idx = i * self.cols + j
                if idx < len(resized_frames) and resized_frames[idx] is not None:
                    nimg[i * self.nframe_height:(i + 1) * self.nframe_height,
                         j * self.nframe_width:(j + 1) * self.nframe_width] = resized_frames[idx]

        # Optionally save the final image to disk
        if doSave and sPath:
            cv2.imwrite(sPath, nimg)

        # Store the final image as an attribute and return it
        self.img = nimg
        return nimg

    def new_images(self, doSave=True, sPath='imgs'):
        if not os.path.exists(sPath):
            os.mkdir(sPath)
        
        Imgs = []
        video = self.cap
        fc = 0
        while fc < self.total_frames:
            resized_frames = [None] * self.frames_to_read
            frame_positions = list(map(int, np.linspace(fc, fc + self.fps * self.t, self.frames_to_read)))
            
            for i, frame_position in enumerate(frame_positions):
                if frame_position >= self.total_frames:  # Stop if we exceed total frames
                    break
                video.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
                ret, frame = video.read()
                if not ret:  # Break if the video ends
                    break
                resized_frames[i] = cv2.resize(frame, (self.nframe_width, self.nframe_height))
            
            # Add the batch of resized frames to Imgs
            Imgs.append(resized_frames)
            
            # Move the frame counter by the duration of the current batch
            fc += self.fps * self.t
        
        # Stack and save images
        nImgs = [None] * len(Imgs)
        for k, resized_frames in enumerate(Imgs):
            nimg = np.zeros((self.nframe_height * self.rows, self.nframe_width * self.cols, 3), dtype=np.uint8)
            
            for i in range(self.rows):
                for j in range(self.cols):
                    idx = i * self.cols + j
                    if idx < len(resized_frames) and resized_frames[idx] is not None:
                        nimg[i * self.nframe_height:(i + 1) * self.nframe_height,
                            j * self.nframe_width:(j + 1) * self.nframe_width] = resized_frames[idx]
            
            nImgs[k] = nimg
            if doSave:
                imgpath = os.path.join(sPath, f'img{k}.jpg')
                cv2.imwrite(imgpath, nimg)
        
        self.Imgs = Imgs


class FrameAggregator:
    def __init__(self, num_cameras, frame_width, frame_height, t, f):
        """
        :param num_cameras: Total number of cameras.
        :param frame_width: Width of each frame.
        :param frame_height: Height of each frame.
        :param t: Duration in seconds to collect frames.
        :param f: Frames per second to collect.
        """
        self.num_cameras = num_cameras
        self.t = t
        self.f = f
        self.frames_to_read = t * f  # Total frames per camera
        self.grid_size = num_cameras * self.frames_to_read  # Total frames for grid
        self.rows = math.ceil(math.sqrt(self.grid_size))  # Rows for the grid
        self.cols = math.ceil(self.grid_size / self.rows)  # Columns for the grid
        self.frame_width = frame_width // self.cols
        self.frame_height = frame_height // self.rows

    def aggregate_frames(self, camera_frames):
        """
        Combine frames from multiple cameras into one image.
        :param camera_frames: A dictionary with camera_id as keys and frames as values.
        :return: Combined image.
        """
        nimg = np.zeros((self.frame_height * self.rows, self.frame_width * self.cols, 3), dtype=np.uint8)
        
        frame_list = []
        for cam_id in camera_frames:
            frame_list.extend(camera_frames[cam_id])

        for i in range(self.rows):
            for j in range(self.cols):
                idx = i * self.cols + j
                if idx < len(frame_list):
                    resized_frame = cv2.resize(frame_list[idx], (self.frame_width, self.frame_height))
                    nimg[i * self.frame_height:(i + 1) * self.frame_height,
                         j * self.frame_width:(j + 1) * self.frame_width] = resized_frame
        return nimg

import json
import os

class StateManager:
    def __init__(self, state_file="state.json"):
        self.state_file = state_file
        if not os.path.exists(state_file):
            self.state = {}
            self.save_state()
        else:
            self.load_state()

    def load_state(self):
        with open(self.state_file, "r") as file:
            self.state = json.load(file)

    def save_state(self):
        with open(self.state_file, "w") as file:
            json.dump(self.state, file, indent=4)

    def update_camera_state(self, camera_id, timestamp):
        self.state[camera_id] = timestamp
        self.save_state()

    def get_last_timestamp(self, camera_id):
        return self.state.get(camera_id, 0)


if __name__ == '__main__':
    vpath = 'v1.mp4'
    video = VideoProcess(vpath, 1, 2)
    # video.new_images()
    cv2.waitKey(0)
    cv2.destroyAllWindows()