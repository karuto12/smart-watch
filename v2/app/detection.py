
import cv2
import numpy as np

def load_model(prototxt_path, model_path):
    """Loads the detection model."""
    return cv2.dnn.readNetFromCaffe(prototxt_path, model_path)

def detect_motion(backSub, kernel, frame):
    """Detects motion in a frame."""
    fgMask = backSub.apply(frame)
    fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(fgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        if 1000 < cv2.contourArea(contour) < 10000:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = h / float(w)
            if aspect_ratio > 1.2:
                return True
    return False

def detect_human(frame, net, confidence_threshold):
    """Detects humans in a frame."""
    blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > confidence_threshold:
            class_id = int(detections[0, 0, i, 1])
            if class_id == 15: # 15 is the class ID for 'person'
                return True
    return False
