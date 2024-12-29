from twilio.rest import Client
import os
import logging
import json


PATH2THIS = "./smart-watch/src/notifications/send_sms.py"
PATH2LOG = "./smart-watch/data/logs/notific-sms-details-setup.log"
logging.basicConfig(level=logging.INFO,
                    filename=PATH2LOG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(os.path.basename(PATH2THIS))
logger.info(f"THE MSGS ARE FROM {PATH2THIS}")

# Define the configuration file path
CONFIG_FILE = "./smart-watch/config/notification_config.json"


def send_sms(account_sid, auth_token, from_phone_number, to_phone_number, message):
    """
    Sends an SMS message using Twilio's API.
    
    :param account_sid: Twilio Account SID
    :param auth_token: Twilio Auth Token
    :param from_phone_number: Twilio's SMS-enabled number (e.g., '+14155238886')
    :param to_phone_number: Recipient's phone number (e.g., '+1234567890')
    :param message: The message content
    """
    try:
        # Initialize Twilio Client
        client = Client(account_sid, auth_token)
        
        # Send SMS message
        message = client.messages.create(
            from_=from_phone_number,
            body=message,
            to=to_phone_number
        )
        
        logger.info(f"SMS sent successfully! {message}")
        return True
    except Exception as e:
        logger.critical(f"Failed to send SMS. Error: {e}")
        return False


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


def setup_sms_details(account_sid, auth_token, from_phone_number, to_phone_number):
    """Setup SMS details in the configuration file."""
    config = load_config()
    config['setup-details']['SMS'] = {
        "account_sid": account_sid,
        "auth_token": auth_token,
        "from_phone_number": from_phone_number,
        "to_phone_number": to_phone_number,
    }
    save_config(config)


if __name__ == "__main__":
    # Input credentials and message details
    sms_config = load_config().get('setup-details', {}).get('SMS', {})
    bePolite = input("Press (y) if you want to change the details else press whatever: ")
    if not sms_config or bePolite == 'y':
        print("\n\nPerhaps this is your first time using Twilio! I would recommend you make an account at https://www.twilio.com/ and fill the details.\n\n")
        account_sid = input("Enter your Twilio Account SID: ").strip()
        auth_token = input("Enter your Twilio Auth Token: ").strip()
        from_phone_number = "+" + input("Enter your Twilio SMS-enabled phone number (e.g., '14155238886'): ").strip()
        to_phone_number = "+" + input("Enter the recipient's phone number (e.g., '1234567890'): ").strip()
        setup_sms_details(account_sid, auth_token, from_phone_number, to_phone_number)
    else:
        account_sid = sms_config['account_sid']
        auth_token = sms_config['auth_token']
        from_phone_number = sms_config['from_phone_number']
        to_phone_number = sms_config['to_phone_number']

    message = input("Enter the message to send: ").strip()
        
    # Send SMS
    success = send_sms(account_sid, auth_token, from_phone_number, to_phone_number, message)
    if success:
        print("Message sent successfully!")
    else:
        print("Failed to send the message.")
