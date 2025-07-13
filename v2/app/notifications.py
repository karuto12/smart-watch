import asyncio
import os
import cv2
from telegram import Bot
from config import get_absolute_path
import threading
import logging
from logger import setup_logging
from queue import Queue

class NotificationManager:
    """
    Manages sending notifications in a separate thread.
    """
    def __init__(self, config):
        self.config = config
        self.queue = Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.running = False

    def _run(self):
        while self.running:
            task = self.queue.get()
            if task is None: # Shutdown signal
                break
            
            timestamp, camera_info, frame = task
            try:
                self._send_telegram_alert(timestamp, camera_info, frame)
            except Exception as e:
                logging.error(f"Error sending notification: {e}")
            self.queue.task_done()

    def _send_telegram_alert(self, timestamp, camera_info, frame):
        """Sends a Telegram alert with an image."""
        token = self.config['telegram_token']
        chat_id = self.config['telegram_chat_id']
        
        if not token or not chat_id:
            logging.warning("Telegram token or chat_id not configured.")
            return

        asyncio.run(self._send_telegram_alert_async(token, chat_id, timestamp, camera_info, frame))

    async def _send_telegram_alert_async(self, token, chat_id, timestamp, camera_info, frame):
        bot = Bot(token=token)
        body = (
            f"Trespassing detected at {timestamp}.\n"
            f"Camera: {camera_info.get('name', 'N/A')}"
        )
        
        temp_image_path = get_absolute_path("temp_alert.jpg")
        cv2.imwrite(temp_image_path, frame)
        
        try:
            await bot.send_message(chat_id=chat_id, text=body)
            with open(temp_image_path, 'rb') as photo:
                await bot.send_photo(chat_id=chat_id, photo=photo)
            logging.info(f"Alert sent for {camera_info.get('name')}")
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    def start(self):
        self.running = True
        self.thread.start()

    def stop(self):
        self.running = False
        self.queue.put(None) # Send shutdown signal
        self.thread.join()

    def queue_notification(self, timestamp, camera_info, frame):
        self.queue.put((timestamp, camera_info, frame))