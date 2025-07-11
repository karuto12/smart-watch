
import cv2
import numpy as np

def add_text(frame, text):
    """Adds text to the top-left corner of a frame."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, (10, 30), font, 1, (0, 255, 0), 2, cv2.LINE_AA)
    return frame

def arrange_frames(frames, frame_size=(320, 240), cams=[]):
    """Arrange frames in a grid layout."""
    num_frames = len(frames)
    cols = int(np.ceil(np.sqrt(num_frames)))
    rows = int(np.ceil(num_frames / cols))
    
    blank_image = np.zeros((rows * frame_size[1], cols * frame_size[0], 3), dtype=np.uint8)

    for idx, frame in enumerate(frames):
        if frame is None:
            frame = np.zeros((frame_size[1], frame_size[0], 3), dtype=np.uint8)
        resized_frame = cv2.resize(frame, frame_size)
        labeled_frame = add_text(resized_frame, f"{cams[idx].get('name', 'Cam Undefined')}")

        row, col = divmod(idx, cols)
        y_start, y_end = row * frame_size[1], (row + 1) * frame_size[1]
        x_start, x_end = col * frame_size[0], (col + 1) * frame_size[0]
        blank_image[y_start:y_end, x_start:x_end] = labeled_frame

    return blank_image
