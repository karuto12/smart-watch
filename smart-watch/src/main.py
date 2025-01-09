from src.modules.detection import misbehavior_detection, trespass_detection
from src.modules.config import setup_notification_methods
from src.DVR_handlers import hybrid_handler
from src.modules.notifications import notification_manager
from datetime import datetime
import logging
import os
# import time

PATH2THIS = "./smart-watch/smart-watch/src/main.py"
PATH2LOG = "./smart-watch/data/logs/main.log"
logging.basicConfig(level=logging.INFO,
                    filename=PATH2LOG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(os.path.basename(PATH2THIS))
logger.info(f"THE MSGS ARE FROM {PATH2THIS}")

config = {}
closing_time = datetime.strptime("18:00", "%H:%M").time()


handler = hybrid_handler.HybridHandler(config).handle()

model = misbehavior_detection.load_model()
model.eval()

notification_manager.init()


while True:
    # Detect misbehavior
    t1 = datetime.now()
    if t1.time() < closing_time:   # If the school is open
        frames = handler.aggregated_images()
        keys = frames.keys()
        values = frames.values()
        behavior_predictions = misbehavior_detection.predict(values, model)
        for i, behavior in enumerate(behavior_predictions):
            val = behavior.value()
            if val >= 2:
                msg = {
                    'title': 'Smart-Watch misbehavior detected',
                    'body': f'Misbehavior detected at {t1} \n\
                            Camera: {keys[i]} \n\
                            Misbehavior level: {val}'
                }
                logger.critical(f"Misbehavior detected (Camera: {keys[i]}   Time: {t1})") # behavior.name
                notification_manager.send_notification(msg)
    else:
        frames = handler.video()
        keys = frames.keys()
        values = frames.values()
        results = trespass_detection.get_motions(frames)
        for i, isMotion in enumerate(results):
            if isMotion:
                msg = {
                    'title': 'Smart-Watch trespass detected',
                    'body': f'Trespass detected at {t1} \n\
                            Camera: {keys[i]}'
                }
                logger.warning(f"Trespass detected (Camera: {keys[i]}   Time: {t1})")
                notification_manager.send_notification(msg)









