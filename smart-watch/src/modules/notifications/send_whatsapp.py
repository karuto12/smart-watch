from twilio.rest import Client
import os
import logging
import json


PATH2THIS = "./smart-watch/src/notifications/send_whatsapp.py"
PATH2LOG = "./smart-watch/data/logs/notific-whatsapp-details-setup.log"
logging.basicConfig(level=logging.INFO,
                    filename=PATH2LOG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(os.path.basename(PATH2THIS))
logger.info(f"THE MSGS ARE FROM {PATH2THIS}")

# Define the configuration file path
CONFIG_FILE = "./smart-watch/config/notification_config.json"


def send_whatsapp_message(account_sid, auth_token, from_whatsapp_number, to_whatsapp_number, message):
    """
    Sends a WhatsApp message using Twilio's API.
    
    :param account_sid: Twilio Account SID
    :param auth_token: Twilio Auth Token
    :param from_whatsapp_number: Twilio's WhatsApp-enabled number (e.g., 'whatsapp:+14155238886')
    :param to_whatsapp_number: Recipient's WhatsApp number (e.g., 'whatsapp:+1234567890')
    :param message: The message content
    """
    try:
        # Initialize Twilio Client
        client = Client(account_sid, auth_token)
        
        # Send message
        message = client.messages.create(
            from_=from_whatsapp_number,
            body=message,
            to=to_whatsapp_number
        )
        
        logger.info(f"Message sent successfully! {message}")
        return True
    except Exception as e:
        logger.critical(f"Failed to send WhatsApp message. Error: {e}")
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


def setup_whatsapp_details(account_sid, auth_token, from_whatsapp_number, to_whatsapp_number):
    """Setup WhatsApp details in the configuration file."""
    config = load_config()
    config['setup-details']['WhatsApp'] = {
        "account_sid": account_sid,
        "auth_token": auth_token,
        "from_whatsapp_number": from_whatsapp_number,
        "to_whatsapp_number": to_whatsapp_number,
    }
    save_config(config)

def init():
    global whatsapp_config
    whatsapp_config = load_config().get('setup-details', {}).get('WhatsApp', {})

def send(msg):
    global whatsapp_config
    account_sid = whatsapp_config['account_sid']
    auth_token = whatsapp_config['auth_token']
    from_whatsapp_number = whatsapp_config['from_whatsapp_number']
    to_whatsapp_number = whatsapp_config['to_whatsapp_number']
    msg = f'{msg['title']} \n{msg['body']}'
    # Send WhatsApp message
    return send_whatsapp_message(account_sid, auth_token, from_whatsapp_number, to_whatsapp_number, msg)

if __name__ == "__main__":
    # Input credentials and message details
    whatsapp_config = load_config().get('setup-details', {}).get('WhatsApp', {})
    bePolite = input("Press (y) if you want to change the details else press whatever: ")
    if not whatsapp_config or bePolite=='y':
        print("\n\nPerhaps this is your first time using twilio! I would recommend you make an account at https://www.twilio.com/ and fill the details.\n\n")
        account_sid = input("Enter your Twilio Account SID: ").strip()
        auth_token = input("Enter your Twilio Auth Token: ").strip()
        from_whatsapp_number = "whatsapp:+" + input("Enter your Twilio WhatsApp-enabled number (e.g., '91XXXXXXXXXX'): ").strip()
        to_whatsapp_number = "whatsapp:+" + input("Enter the recipient's WhatsApp number (e.g., '91XXXXXXXXXX'): ").strip()
        setup_whatsapp_details(account_sid, auth_token, from_whatsapp_number, to_whatsapp_number)
    else:
        account_sid = whatsapp_config['account_sid']
        auth_token = whatsapp_config['auth_token']
        from_whatsapp_number = whatsapp_config['from_whatsapp_number']
        to_whatsapp_number = whatsapp_config['to_whatsapp_number']

    message = input("Enter the message to send: ").strip()
        
    # Send WhatsApp message
    success = send_whatsapp_message(account_sid, auth_token, from_whatsapp_number, to_whatsapp_number, message)
    if success:
        print("Message sent successfully!")
    else:
        print("Failed to send the message.")
