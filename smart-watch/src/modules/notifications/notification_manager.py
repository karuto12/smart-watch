import json
import os
from src.modules.notifications import send_email, send_push_notification, send_sms, send_whatsapp


CONFIG_FILE = "./smart-watch/config/notification_config.json"
METHODS = {
    'WhatsApp': send_whatsapp,
    'PushNotification': send_push_notification,
    'Email': send_email,
    'SMS': send_sms
}


def load_config():
    """Load existing configuration from a file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {"methods": []}

def send_notification(msg):
    global config, selected_methods
    for sm in selected_methods:
        yield METHODS.get(sm).send(msg)

def init():
    global config, selected_methods
    config = load_config()
    selected_methods = config.get('selected-methods', [])
    for sm in selected_methods:
        METHODS[sm].init()


