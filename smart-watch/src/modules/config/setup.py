import json
import os
import logging

PATH2THIS = "./smart-watch/src/modules/config/setup.py"
PATH2LOG = "./smart-watch/data/logs/notific-mode-setup.log"
logging.basicConfig(level=logging.INFO,
                    filename=PATH2LOG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(os.path.basename(PATH2THIS))
logger.info(f"THE MSGS ARE FROM {PATH2THIS}")

# Define the configuration file path
CONFIG_FILE = "./smart-watch/config/notification_config.json"

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

def add_notification_methods(available_methods=["WhatsApp", "Email", "SMS", "PushNotification"]):
    """Allow the user to set up notification methods."""

    print("Available methods for receiving messages:")
    for i, method in enumerate(available_methods, start=1):
        print(f"{i}. {method}")

    selected_methods = []
    try:
        choice = input("Enter the number of the methods to enable (comma seperated): ").strip().split(',')
        if choice:
            choice = list(map(lambda x: int(x)-1, choice))
        for i in choice:
            if 0 <= i < len(available_methods):
                av = available_methods[i]
                if av in selected_methods:
                    print(av, 'is already selected')
                    continue
                selected_methods.append(av)
        if selected_methods:
            print("Added method:", selected_methods)
            logger.info(f"Added method: {selected_methods}")
        else:
            print("selected method cannot be empty")
            logger.warning("Selected Method cannot be empty")
            add_notification_methods(available_methods)
            
            
    except ValueError:
        print("Invalid input. Please enter a number or 'done'.")
    return selected_methods

def main():
    """Main function to set up or update notification methods."""
    print("Notification Setup")
    config = load_config()
    print("\nCurrent Configuration:")
    print("Selected Methods:", ", ".join(config["selected-methods"]) if config.get("selected-methods", None) else "None")
    
    update = input("\nDo you want to update the selected notification methods? (yes/no): ").strip().lower()
    if update == "yes":
        selected_methods = add_notification_methods(config['available-methods'])
        if selected_methods:
            config["selected-methods"] = selected_methods
        save_config(config)
    else:
        print("No changes made.")

if __name__ == "__main__":
    main()
