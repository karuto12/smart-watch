import os
import logging
import json
import requests

# Paths for logging and configuration
PATH2THIS = "./smart-watch/src/notifications/send_push_notification.py"
PATH2LOG = "./smart-watch/data/logs/notific-push-details-setup.log"
logging.basicConfig(level=logging.INFO,
                    filename=PATH2LOG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(os.path.basename(PATH2THIS))
logger.info(f"The notifications are from {PATH2THIS}")

# Configuration file for storing notification details
CONFIG_FILE = "./smart-watch/config/notification_config.json"

FCM_URL = "https://fcm.googleapis.com/fcm/send"  # FCM endpoint


def send_push_notification(server_key, device_tokens, title, message, data=None):
    """
    Sends a push notification using Firebase Cloud Messaging (FCM).

    :param server_key: FCM Server Key for authentication
    :param device_tokens: List of recipient device tokens
    :param title: Title of the notification
    :param message: Message content of the notification
    :param data: Optional additional data payload
    """
    try:
        # FCM headers
        headers = {
            'Authorization': f'key={server_key}',
            'Content-Type': 'application/json',
        }

        # FCM payload
        payload = {
            "registration_ids": device_tokens,
            "notification": {
                "title": title,
                "body": message,
            },
            "data": data or {}  # Optional payload
        }

        # Send the push notification request
        response = requests.post(FCM_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an error for bad status codes

        logger.info(f"Push notification sent successfully: {response.json()}")
        return response.json()
    except Exception as e:
        logger.critical(f"Failed to send push notification. Error: {e}")
        return None


def load_config():
    """Load existing configuration from a file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {"methods": []}


def save_config(config):
    """Save the current configuration to a file."""
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)
    logger.info(f"Configuration saved to {CONFIG_FILE}.")


def setup_push_notification_details(server_key, device_tokens):
    """Setup push notification details in the configuration file."""
    config = load_config()
    config['setup-details']['PushNotification'] = {
        "server_key": server_key,
        "device_tokens": device_tokens,
    }
    save_config(config)

def init():
    global push_config
    push_config = load_config().get('setup-details', {}).get('PushNotification', {})


def send(msg):
    global push_config
    server_key = push_config['server_key']
    device_tokens = push_config['device_tokens']
    title = msg.get('title', 'Smart-Watch').strip()
    message = msg.get('message', 'Warning: There might be some error in msg formatting').strip()
    data = msg.get('data', {})
    response = send_push_notification(server_key, device_tokens, title, message, data)
    return response

if __name__ == "__main__":
    # Load configuration or ask user for setup
    push_config = load_config().get('setup-details', {}).get('PushNotification', {})
    bePolite = input("Press (y) if you want to change the push notification details else press whatever: ")
    if not push_config or bePolite == 'y':
        print("\n\nPerhaps this is your first time using the push notification sender! Please fill the details.\n\n")
        server_key = input("Enter your FCM Server Key: ").strip()
        device_tokens = input("Enter the recipient device tokens (comma-separated): ").strip()
        device_tokens = [token.strip() for token in device_tokens.split(",")]
        setup_push_notification_details(server_key, device_tokens)
    else:
        server_key = push_config['server_key']
        device_tokens = push_config['device_tokens']

    # Collect notification details
    title = 'Test MSG' #input("Enter the title of the notification: ").strip()
    message = "This is a test msg" #input("Enter the message content of the notification: ").strip()

    # Optional data payload
    data_input = '' #input("Enter any additional data payload (JSON format, or leave blank): ").strip()
    data = json.loads(data_input) if data_input else {}

    # Send push notification
    response = send_push_notification(server_key, device_tokens, title, message, data)
    if response:
        print("Push notification sent successfully!")
    else:
        print("Failed to send the push notification.")


