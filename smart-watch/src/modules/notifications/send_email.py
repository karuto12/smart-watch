import os
import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PATH2THIS = "./smart-watch/src/notifications/send_email.py"
PATH2LOG = "./smart-watch/data/logs/notific-email-details-setup.log"
logging.basicConfig(level=logging.INFO,
                    filename=PATH2LOG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(os.path.basename(PATH2THIS))
logger.info(f"THE MSGS ARE FROM {PATH2THIS}")

# Define the configuration file path
CONFIG_FILE = "./smart-watch/config/notification_config.json"


def send_email(smtp_server, port, sender_email, sender_password, recipient_email, subject, message, cc=None, bcc=None):
    """
    Sends an email using an SMTP server, with optional CC and BCC fields.

    :param smtp_server: SMTP server address (e.g., 'smtp.gmail.com')
    :param port: Port for the SMTP server (e.g., 587 for TLS)
    :param sender_email: Sender's email address
    :param sender_password: Sender's email password or app password
    :param recipient_email: Recipient's email address
    :param subject: Subject of the email
    :param message: The email content
    :param cc: List of CC email addresses (optional)
    :param bcc: List of BCC email addresses (optional)
    """
    try:
        # Create MIMEText email
        email_message = MIMEMultipart()
        email_message['From'] = sender_email
        email_message['To'] = recipient_email
        email_message['Subject'] = subject
        
        # Handle CC
        if cc:
            email_message['Cc'] = ', '.join(cc)  # Add CC header

        email_message.attach(MIMEText(message, 'plain'))

        # Gather all recipients (To, CC, BCC)
        all_recipients = [recipient_email]
        if cc:
            all_recipients.extend(cc)
        if bcc:
            all_recipients.extend(bcc)

        # Connect to SMTP server
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()  # Enable security
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, all_recipients, email_message.as_string())

        logger.info(f"Email sent successfully to {all_recipients}.")
        return True
    except Exception as e:
        logger.critical(f"Failed to send email. Error: {e}")
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


def save_email_details(smtp_server, port, sender_email, sender_password, recipient_email, cc=None, bcc=None):
    """Setup email details in the configuration file."""
    config = load_config()
    config['setup-details']['Email'] = {
        "smtp_server": smtp_server,
        "port": port,
        "sender_email": sender_email,
        "sender_password": sender_password,
        "recipient_email": recipient_email,
        "cc": cc,
        "bcc": bcc,
    }
    save_config(config)

def init():
    global email_config
    email_config = load_config().get('setup-details', {}).get('Email', {})

def send(msg):
    global email_config
    smtp_server = email_config['smtp_server']
    port = email_config['port']
    sender_email = email_config['sender_email']
    sender_password = email_config['sender_password']
    recipient_email = email_config['recipient_email']
    cc = email_config.get('cc', [])
    bcc = email_config.get('bcc', [])
    subject = msg['title']
    message = msg['body']

    # Send the email
    return send_email(smtp_server, port, sender_email, sender_password, recipient_email, subject, message, cc, bcc)

def setup():
    print("\n\nIf this is first time for Email Set-Up, you need to setup 2 step verification (2SV), then copy the 'App Passwords'.\n\n")
    smtp_server = input("Enter the SMTP server address (e.g., 'smtp.gmail.com'): ").strip()
    port = int(input("Enter the SMTP server port (e.g., 587 for TLS): ").strip())
    sender_email = input("Enter your email address: ").strip()
    sender_password = input("Enter your email password or app password: ").strip()
    recipient_email = input("Enter the recipient's email address: ").strip()
    cc = input("Enter the CC email addresses (comma separated): ").strip().split(',')
    bcc = input("Enter the BCC email addresses (comma separated): ").strip().split(',')
    save_email_details(smtp_server, port, sender_email, sender_password, recipient_email, cc, bcc)
    print("Email Configured Successfully")

if __name__ == "__main__":
    # Input credentials and email details
    email_config = load_config().get('setup-details', {}).get('Email', {})
    bePolite = input("Press (y) if you want to change the details else press whatever: ")
    if not email_config or bePolite == 'y':
        print("\n\nIf this is first time for Email Set-Up, you need to setup 2 step verification (2SV), then copy the 'App Passwords'.\n\n")
        smtp_server = input("Enter the SMTP server address (e.g., 'smtp.gmail.com'): ").strip()
        port = int(input("Enter the SMTP server port (e.g., 587 for TLS): ").strip())
        sender_email = input("Enter your email address: ").strip()
        sender_password = input("Enter your email password or app password: ").strip()
        recipient_email = input("Enter the recipient's email address: ").strip()
        cc = input("Enter the CC email addresses (comma separated): ").strip().split(',')
        bcc = input("Enter the BCC email addresses (comma separated): ").strip().split(',')
        save_email_details(smtp_server, port, sender_email, sender_password, recipient_email, cc, bcc)
    else:
        smtp_server = email_config['smtp_server']
        port = email_config['port']
        sender_email = email_config['sender_email']
        sender_password = email_config['sender_password']
        recipient_email = email_config['recipient_email']
        cc = email_config.get('cc', [])
        bcc = email_config.get('bcc', [])

    subject = input("Enter the subject of the email: ").strip()
    message = input("Enter the message content of the email: ").strip()

    # Send email
    success = send_email(smtp_server, port, sender_email, sender_password, recipient_email, subject, message, cc, bcc)
    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send the email.")
