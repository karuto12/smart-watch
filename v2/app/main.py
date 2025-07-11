
import cv2
import time
from datetime import datetime
import sys

from config import load_config, load_cameras
from video_stream import initialize_cameras, release_cameras, read_frame
from detection import load_model, detect_motion, detect_human
from notifications import send_telegram_alert
from utils import arrange_frames

def main(show_frames=False):
    config = load_config()
    cameras = load_cameras()
    
    if not cameras:
        print("No cameras configured. Please run the CLI to add cameras.")
        return

    caps = initialize_cameras(cameras)
    net = load_model(config['prototxt_path'], config['model_path'])
    backSub = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=16, detectShadows=False)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    last_motion_times = [0] * len(caps)
    last_alert_times = [0] * len(caps)

    try:
        while True:
            frames = [read_frame(cap) if cap else None for cap in caps]
            
            for i, frame in enumerate(frames):
                if frame is None:
                    continue

                if detect_motion(backSub, kernel, frame):
                    last_motion_times[i] = time.time()

                    if detect_human(frame, net, config['confidence_threshold']):
                        if time.time() - last_alert_times[i] > config['notification_cooldown']:
                            last_alert_times[i] = time.time()
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            send_telegram_alert(
                                config['telegram_token'],
                                config['telegram_chat_id'],
                                timestamp,
                                cameras[i],
                                frame
                            )
                            print(f"Alert sent for {cameras[i]['name']}")

            if show_frames:
                display_frame = arrange_frames(frames, cams=cameras)
                cv2.imshow("Trespass Detection", display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        print("Stopping detection.")
    finally:
        release_cameras(caps)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    show = '--show' in sys.argv
    main(show_frames=show)
