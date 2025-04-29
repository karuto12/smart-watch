import cv2
import time
from datetime import datetime
from dotenv import load_dotenv
import sys

from utils import initialize_cameras, send_email_alert, detect_motion, detect_human, arrange_frames, send_whatsapp_alert

# Load environment variables
load_dotenv()

# Global variables
fps = 5
check_period = 5
notification_cooldown_period = (60) * 3 # 3 minutes

def detect(is_show=False):
    caps, cams = initialize_cameras('data.json')
    if not caps:
        print("No cameras initialized. Exiting...")
        return

    backSub = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=16, detectShadows=False)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    has_motions = [False] * len(caps)
    last_motion_ats = [0] * len(caps)
    last_trespass_alert_times = [0] * len(caps)
    frames = [0] * len(caps)

    isEnd = False
    i = 1

    while not isEnd:
        for idx, cap in enumerate(caps):
            ret, frames[idx] = cap.read()
            if not ret:
                break

            if has_motions[idx]:
                if i % fps != 0:
                    i += 1
                    continue
                i = 1

                human_detected = detect_human(frames[idx])
                if human_detected and time.time() - last_trespass_alert_times[idx] >= notification_cooldown_period:
                    last_trespass_alert_times[idx] = time.time()
                    detection_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    send_email_alert(detection_time_str, cams[idx], frames[idx])
                    send_whatsapp_alert(detection_time_str, cams[idx], frames[idx])

                if time.time() - last_motion_ats[idx] > check_period:
                    has_motions[idx] = False
                    last_motion_ats[idx] = time.time()
            else:
                has_motions[idx] = detect_motion(backSub, kernel, frames[idx], last_motion_ats, idx)

            if cv2.waitKey(1) == ord("q"):
                isEnd = True
        if cv2.waitKey(1) == ord("q"):
            isEnd = True

        if is_show:
            final = arrange_frames(frames, cams=cams)
            cv2.imshow("Frame", final)

    for cap in caps:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    is_show = False  # Default value for showing frames

    if len(sys.argv) > 1:
        is_show = sys.argv[1].lower() == 'true'  # Second argument is whether to show frames

    print(f"Starting detection, Show frames: {is_show}")
    detect(is_show=is_show)
