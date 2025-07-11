
import asyncio
import os
import cv2
from telegram import Bot

async def send_telegram_alert_async(token, chat_id, timestamp, camera_info, frame):
    """Sends a Telegram alert with an image."""
    bot = Bot(token=token)
    body = (
        f"Trespassing detected at {timestamp}.\n"
        f"Camera: {camera_info.get('name', 'N/A')}"
    )
    
    # Save the frame to a temporary file
    temp_image_path = "temp_alert.jpg"
    cv2.imwrite(temp_image_path, frame)
    
    await bot.send_message(chat_id=chat_id, text=body)
    with open(temp_image_path, 'rb') as photo:
        await bot.send_photo(chat_id=chat_id, photo=photo)
        
    os.remove(temp_image_path)

def send_telegram_alert(token, chat_id, timestamp, camera_info, frame):
    """Wrapper to run the async Telegram alert function."""
    asyncio.run(send_telegram_alert_async(token, chat_id, timestamp, camera_info, frame))
