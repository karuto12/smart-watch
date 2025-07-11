
import json
import os
from dotenv import load_dotenv

def load_config():
    """Loads camera configurations and environment variables."""
    load_dotenv()
    
    config = {
        "fps": int(os.getenv("FPS", 5)),
        "check_period": int(os.getenv("CHECK_PERIOD", 5)),
        "notification_cooldown": int(os.getenv("NOTIFICATION_COOLDOWN", 180)),
        "sender_email": os.getenv("SENDER_EMAIL"),
        "receiver_email": os.getenv("RECEIVER_EMAIL"),
        "sender_pass": os.getenv("SENDER_PASS"),
        "telegram_token": os.getenv("TELEGRAM_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "model_path": os.getenv("MODEL_PATH", "models/MobileNetSSD_deploy.caffemodel"),
        "prototxt_path": os.getenv("PROTOTXT_PATH", "models/MobileNetSSD_deploy.prototxt"),
        "confidence_threshold": float(os.getenv("CONFIDENCE_THRESHOLD", 0.5))
    }
    
    return config

def load_cameras(filepath="data.json"):
    """Loads camera data from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found. Returning empty camera list.")
        return []
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error loading JSON from {filepath}: {e}")
        return []

def save_cameras(data, filepath="data.json"):
    """Saves camera data to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
