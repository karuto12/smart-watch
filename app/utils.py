import cv2
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import numpy as np
from json import load
import time
import threading
import queue
# import pywhatkit as kit
import onnxruntime as ort

from whatnot import send_whatsapp_message

# Create a queue for email tasks
email_queue = queue.Queue()


def email_worker():
    """Worker function to process email tasks from the queue."""
    while True:
        task = email_queue.get()
        if task is None:  # Exit signal
            break
        try:
            send_email_alert(*task)
        except Exception as e:
            print("Error sending email:", e)
        email_queue.task_done()

# Start the email worker thread
email_thread = threading.Thread(target=email_worker, daemon=True)
email_thread.start()

def queue_email_alert(timestamp, camera_info, frame):
    """Add an email alert task to the queue."""
    email_queue.put((timestamp, camera_info, frame))


def run_nanodet_onnx(image_path, model_path="nanodet_api/nanodet.onnx", score_thresh=0.5, nms_thresh=0.6):
    """
    Runs NanoDet ONNX inference on a single image.
    Args:
        image_path (str): Path to the input image.
        model_path (str): Path to the ONNX model.
        score_thresh (float): Detection score threshold.
        nms_thresh (float): NMS IoU threshold.
    Returns:
        dict: Detection results with 'boxes', 'labels', 'scores'.
    """
    # Preprocess
    INPUT_SIZE = 320
    REG_MAX = 7
    STRIDES = [8, 16, 32]
    img = cv2.imread(image_path)
    img = cv2.resize(img, (INPUT_SIZE, INPUT_SIZE))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    img = np.expand_dims(img, axis=0).astype(np.float32)

    # Inference
    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: img})
    outputs = outputs[0] if isinstance(outputs, (list, tuple)) else outputs
    if outputs.ndim == 3:
        outputs = outputs[0]
    NUM_CLASSES = 80  # Change this if your model uses a different number of classes

    # Generate center priors
    center_priors = []
    for stride in STRIDES:
        feat_w = INPUT_SIZE // stride
        feat_h = INPUT_SIZE // stride
        for y in range(feat_h):
            for x in range(feat_w):
                center_priors.append([x, y, stride])
    center_priors = np.array(center_priors, dtype=np.float32)

    # Postprocess
    cls_logits = outputs[:, :NUM_CLASSES]
    bbox_pred = outputs[:, NUM_CLASSES:]
    scores = 1 / (1 + np.exp(-cls_logits))  # sigmoid
    labels = np.argmax(scores, axis=1)
    scores = np.max(scores, axis=1)
    keep = scores > score_thresh
    if not np.any(keep):
        return {"boxes": [], "labels": [], "scores": []}
    scores = scores[keep]
    labels = labels[keep]
    bbox_pred = bbox_pred[keep]
    center_priors = center_priors[keep]
    bbox_pred = bbox_pred.reshape(-1, 4, REG_MAX + 1)
    bbox_pred = np.exp(bbox_pred - np.max(bbox_pred, axis=2, keepdims=True))
    bbox_pred = bbox_pred / np.sum(bbox_pred, axis=2, keepdims=True)
    dis = np.dot(bbox_pred, np.arange(REG_MAX + 1, dtype=np.float32))
    def distance2bbox(center, distance, max_shape=None):
        x1 = center[:, 0] * center[:, 2] - distance[:, 0]
        y1 = center[:, 1] * center[:, 2] - distance[:, 1]
        x2 = center[:, 0] * center[:, 2] + distance[:, 2]
        y2 = center[:, 1] * center[:, 2] + distance[:, 3]
        if max_shape is not None:
            x1 = np.clip(x1, 0, max_shape[1])
            y1 = np.clip(y1, 0, max_shape[0])
            x2 = np.clip(x2, 0, max_shape[1])
            y2 = np.clip(y2, 0, max_shape[0])
        return np.stack([x1, y1, x2, y2], axis=-1)
    boxes = distance2bbox(center_priors, dis, max_shape=(INPUT_SIZE, INPUT_SIZE))
    # NMS
    def nms(boxes, scores, iou_threshold):
        idxs = scores.argsort()[::-1]
        keep = []
        while idxs.size > 0:
            i = idxs[0]
            keep.append(i)
            if idxs.size == 1:
                break
            xx1 = np.maximum(boxes[i, 0], boxes[idxs[1:], 0])
            yy1 = np.maximum(boxes[i, 1], boxes[idxs[1:], 1])
            xx2 = np.minimum(boxes[i, 2], boxes[idxs[1:], 2])
            yy2 = np.minimum(boxes[i, 3], boxes[idxs[1:], 3])
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            inter = w * h
            area1 = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
            area2 = (boxes[idxs[1:], 2] - boxes[idxs[1:], 0]) * (boxes[idxs[1:], 3] - boxes[idxs[1:], 1])
            ovr = inter / (area1 + area2 - inter)
            idxs = idxs[1:][ovr < iou_threshold]
        return keep
    keep_idx = nms(boxes, scores, nms_thresh)
    boxes = boxes[keep_idx].tolist()
    labels = labels[keep_idx].tolist()
    scores = scores[keep_idx].tolist()
    return {"boxes": boxes, "labels": labels, "scores": scores}

def run_nanodet_onnx_batch(image_paths, model_path="nanodet_api/nanodet.onnx", score_thresh=0.5, nms_thresh=0.6, batch_size=4):
    """
    Runs NanoDet ONNX inference on multiple images in batches for better efficiency.
    Args:
        image_paths (list): List of paths to input images.
        model_path (str): Path to the ONNX model.
        score_thresh (float): Detection score threshold.
        nms_thresh (float): NMS IoU threshold.
        batch_size (int): Number of images to process in each batch.
    Returns:
        list: List of detection results, each with 'boxes', 'labels', 'scores'.
    """
    INPUT_SIZE = 320
    REG_MAX = 7
    STRIDES = [8, 16, 32]
    NUM_CLASSES = 80  # Change this if your model uses a different number of classes
    
    # Generate center priors (only once)
    center_priors = []
    for stride in STRIDES:
        feat_w = INPUT_SIZE // stride
        feat_h = INPUT_SIZE // stride
        for y in range(feat_h):
            for x in range(feat_w):
                center_priors.append([x, y, stride])
    center_priors = np.array(center_priors, dtype=np.float32)
    
    # Initialize ONNX session
    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    
    def preprocess_batch(image_paths_batch):
        """Preprocess a batch of images."""
        batch_imgs = []
        for img_path in image_paths_batch:
            img = cv2.imread(img_path)
            if img is None:
                # Return zero image if file not found
                img = np.zeros((INPUT_SIZE, INPUT_SIZE, 3), dtype=np.uint8)
            img = cv2.resize(img, (INPUT_SIZE, INPUT_SIZE))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.astype(np.float32) / 255.0
            img = np.transpose(img, (2, 0, 1))
            batch_imgs.append(img)
        return np.array(batch_imgs, dtype=np.float32)
    
    def postprocess_single(outputs, center_priors, score_thresh, nms_thresh):
        """Postprocess outputs for a single image."""
        if outputs.ndim == 3:
            outputs = outputs[0]
        
        cls_logits = outputs[:, :NUM_CLASSES]
        bbox_pred = outputs[:, NUM_CLASSES:]
        scores = 1 / (1 + np.exp(-cls_logits))  # sigmoid
        labels = np.argmax(scores, axis=1)
        scores = np.max(scores, axis=1)
        keep = scores > score_thresh
        if not np.any(keep):
            return {"boxes": [], "labels": [], "scores": []}
        
        scores = scores[keep]
        labels = labels[keep]
        bbox_pred = bbox_pred[keep]
        center_priors_keep = center_priors[keep]
        bbox_pred = bbox_pred.reshape(-1, 4, REG_MAX + 1)
        bbox_pred = np.exp(bbox_pred - np.max(bbox_pred, axis=2, keepdims=True))
        bbox_pred = bbox_pred / np.sum(bbox_pred, axis=2, keepdims=True)
        dis = np.dot(bbox_pred, np.arange(REG_MAX + 1, dtype=np.float32))
        
        def distance2bbox(center, distance, max_shape=None):
            x1 = center[:, 0] * center[:, 2] - distance[:, 0]
            y1 = center[:, 1] * center[:, 2] - distance[:, 1]
            x2 = center[:, 0] * center[:, 2] + distance[:, 2]
            y2 = center[:, 1] * center[:, 2] + distance[:, 3]
            if max_shape is not None:
                x1 = np.clip(x1, 0, max_shape[1])
                y1 = np.clip(y1, 0, max_shape[0])
                x2 = np.clip(x2, 0, max_shape[1])
                y2 = np.clip(y2, 0, max_shape[0])
            return np.stack([x1, y1, x2, y2], axis=-1)
        
        boxes = distance2bbox(center_priors_keep, dis, max_shape=(INPUT_SIZE, INPUT_SIZE))
        
        # NMS
        def nms(boxes, scores, iou_threshold):
            idxs = scores.argsort()[::-1]
            keep = []
            while idxs.size > 0:
                i = idxs[0]
                keep.append(i)
                if idxs.size == 1:
                    break
                xx1 = np.maximum(boxes[i, 0], boxes[idxs[1:], 0])
                yy1 = np.maximum(boxes[i, 1], boxes[idxs[1:], 1])
                xx2 = np.minimum(boxes[i, 2], boxes[idxs[1:], 2])
                yy2 = np.minimum(boxes[i, 3], boxes[idxs[1:], 3])
                w = np.maximum(0, xx2 - xx1)
                h = np.maximum(0, yy2 - yy1)
                inter = w * h
                area1 = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
                area2 = (boxes[idxs[1:], 2] - boxes[idxs[1:], 0]) * (boxes[idxs[1:], 3] - boxes[idxs[1:], 1])
                ovr = inter / (area1 + area2 - inter)
                idxs = idxs[1:][ovr < iou_threshold]
            return keep
        
        keep_idx = nms(boxes, scores, nms_thresh)
        boxes = boxes[keep_idx].tolist()
        labels = labels[keep_idx].tolist()
        scores = scores[keep_idx].tolist()
        return {"boxes": boxes, "labels": labels, "scores": scores}
    
    # Process images in batches
    all_results = []
    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i:i + batch_size]
        batch_imgs = preprocess_batch(batch_paths)
        
        # Run inference
        outputs = session.run(None, {input_name: batch_imgs})
        outputs = outputs[0] if isinstance(outputs, (list, tuple)) else outputs
        
        # Postprocess each image in the batch
        for j in range(len(batch_paths)):
            if j < outputs.shape[0]:
                result = postprocess_single(outputs[j], center_priors, score_thresh, nms_thresh)
            else:
                result = {"boxes": [], "labels": [], "scores": []}
            all_results.append(result)
    
    return all_results

def load_mobilenet_model():
    """
    Load the MobileNet-SSD model.
    
    Returns:
        cv2.dnn_Net: The loaded model.
    """
    prototxt_path = "MobileNetSSD_deploy.prototxt"
    model_path = "MobileNetSSD_deploy.caffemodel"
    net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
    return net


net = load_mobilenet_model()


def initialize_cameras(config_file):
    """Initialize cameras from a configuration file."""
    caps = []
    cams = []
    with open(config_file, 'r') as file:
        data = load(file)
        for item in data:
            link = item.get('link', None)
            if isinstance(link, str) and link.isdigit():
                link = int(link)
                cap = cv2.VideoCapture(link)
            else:
                cap = cv2.VideoCapture(link, cv2.CAP_FFMPEG)
                

            if cap.isOpened():
                width = item.get('width', None)
                height = item.get('height', None)
                if width and height:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                caps.append(cap)
                cams.append(item)
            else:
                print(f"Unable to open camera {item['link']}")
    return caps, cams


def send_whatsapp_alert(timestamp, camera_info, frame):
    """Send a WhatsApp alert for trespassing."""
    phone_num = os.getenv('PHONE_NUM')
    message = (f"A human trespassing event was detected at {timestamp}. "
               f"Camera Info: Name: {camera_info.get('name', 'Cam Undefined')}, "
                f"Description: {camera_info.get('desc', 'No description')}, "
                f"Link: {camera_info.get('link', 'no link')}."
                f"An email has also been sent with the captured picture.")
    temp_image_path = "temp_image_for_whatsapp.jpg"
    cv2.imwrite(temp_image_path, frame)
    try:
        # kit.sendwhatmsg_instantly(phone_num, message, tab_close=True)
        # kit.sendwhats_image(phone_num, temp_image_path, message, tab_close=True)
        send_whatsapp_message([phone_num], message)
        print(f"WhatsApp alert sent at {timestamp}.")
        return True
    except Exception as e:
        print("Failed to send WhatsApp alert:", e)
        return False
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
    
    
def send_email_alert(timestamp, camera_info, frame):
    """Send an email alert for trespassing."""
    sender_email = os.getenv('SENDER_EMAIL')
    receiver_email = os.getenv('RECEIVER_EMAIL')
    email_password = os.getenv("SENDER_PASS")
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    subject = "Trespassing Alert"
    body = (f"A human trespassing event was detected at {timestamp}. "
            f"Camera Info: Name: {camera_info.get('name', 'Cam Undefined')}, "
            f"Description: {camera_info.get('desc', 'No description')}, "
            f"Link: {camera_info.get('link', 'no link')}.")

    print(sender_email, receiver_email, subject, '\n', body)

    temp_image_path = "temp_image_for_email.jpg"
    cv2.imwrite(temp_image_path, frame)

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.attach(MIMEText(body, "plain"))

    with open(temp_image_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(temp_image_path)}",
        )
        msg.attach(part)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, email_password)
        server.sendmail(sender_email, [receiver_email], msg.as_string())
        server.quit()
        print(f"Alert email sent at {timestamp}.")
        return True
    except Exception as e:
        print("Failed to send email:", e)
        return False
    finally:
        # Clean up the temporary image file
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)



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

def detect_motion(backSub, kernel, frame, last_motion_ats, idx):
    """Detect motion in a frame."""
    fgMask = backSub.apply(frame)
    fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(fgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        if 1000 < cv2.contourArea(contour) < 10000:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = h / float(w)
            if aspect_ratio > 1.2:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                last_motion_ats[idx] = time.time()
                return True
    return False

def detect_human(frame, confidence_threshold=0.5):
    """Detect humans in a frame using YOLO model."""
    return detect_human_with_mobilenet(frame, net, confidence_threshold)


def detect_human_with_mobilenet(frame, net, confidence_threshold=0.5):
    """
    Detect humans in a frame using MobileNet-SSD.
    
    Args:
        frame (numpy.ndarray): The input frame.
        net (cv2.dnn_Net): The preloaded MobileNet-SSD model.
        confidence_threshold (float): Minimum confidence to consider a detection valid.
    
    Returns:
        bool: True if a human is detected, False otherwise.
    """
    # Preprocess the frame for the model
    blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    # Loop through detections
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > confidence_threshold:
            class_id = int(detections[0, 0, i, 1])
            # Class ID 15 corresponds to 'person' in MobileNet-SSD
            if class_id == 15:
                box = detections[0, 0, i, 3:7] * np.array([frame.shape[1], frame.shape[0], frame.shape[1], frame.shape[0]])
                (x1, y1, x2, y2) = box.astype("int")
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"Person: {confidence:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                return True
    return False


# Shutdown the email worker thread gracefully (call this when the program exits)
def shutdown_email_worker():
    email_queue.put(None)  # Send exit signal
    email_thread.join()