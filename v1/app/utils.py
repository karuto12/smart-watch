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
import asyncio
from telegram import Bot


os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"



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

    temp_image_path = "./temp/temp_image_for_email.jpg"
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

def send_telegram_alert(timestamp, camera_info, frame):
    async def tele_msg():
        bot = Bot(token=os.getenv('TOKEN'))
        chat_id = os.getenv('CHAT_ID')
        body = (f"A human trespassing event was detected at {timestamp}. "
                f"Camera Info: Name: {camera_info.get('name', 'Cam Undefined')}, "
                f"Description: {camera_info.get('desc', 'No description')}, "
                f"Link: {camera_info.get('link', 'no link')}.")
        # Send a text message
        await bot.send_message(chat_id=chat_id, text=body)
        temp_image_path = "./temp/temp_image_for_telegram.jpg"
        cv2.imwrite(temp_image_path, frame)
        # Send an image from a local file
        with open(temp_image_path, 'rb') as photo:
            await bot.send_photo(chat_id=chat_id, photo=photo)
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
    asyncio.run(tele_msg())
    print(f"Alert telegram message sent at {timestamp}.")

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