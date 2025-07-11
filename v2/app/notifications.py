
import asyncio
import os
import cv2
from telegram import Bot
from config import get_absolute_path

async def send_telegram_alert_async(token, chat_id, timestamp, camera_info, frame):
    """Sends a Telegram alert with an image."""
    bot = Bot(token=token)
    body = (
        f"Trespassing detected at {timestamp}.\n"
        f"Camera: {camera_info.get('name', 'N/A')}"
    )
    
    # Save the frame to a temporary file in the app directory
    temp_image_path = get_absolute_path("temp_alert.jpg")
    cv2.imwrite(temp_image_path, frame)
    
    try:
        await bot.send_message(chat_id=chat_id, text=body)
        with open(temp_image_path, 'rb') as photo:
            await bot.send_photo(chat_id=chat_id, photo=photo)
    finally:
        # Ensure the temporary file is always removed
        print("TELEGRAM ALERT SENT")
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)

def send_telegram_alert(token, chat_id, timestamp, camera_info, frame):
    """Wrapper to run the async Telegram alert function."""
    asyncio.run(send_telegram_alert_async(token, chat_id, timestamp, camera_info, frame))
