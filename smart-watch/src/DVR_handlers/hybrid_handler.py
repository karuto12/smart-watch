import logging
import inspect
from DVR_handlers.rtsp_handler import RTSPHandler
from DVR_handlers.onvif_handler import ONVIFHandler
from DVR_handlers.proprietary_handler import ProprietaryHandler
from DVR_handlers.web_handler import WebHandler
from DVR_handlers.analog_handler import AnalogHandler

class HybridHandler:
    def __init__(self, config):
        """
        Initialize the hybrid handler.
        :param config: Dictionary containing DVR configuration (e.g., IP, username, etc.)
        """
        self.config = config
        self.logger = logging.getLogger("HybridHandler")

        self.handlers = {}

        # A list of all possible handler classes
        handler_classes = {
            "RTSP": RTSPHandler,
            "ONVIF": ONVIFHandler,
            "Proprietary": ProprietaryHandler,
            "Web": WebHandler,
            "Analog": AnalogHandler,
        }

        for handler_name, handler_class in handler_classes.items():
            required_params = self._get_required_params(handler_class)

            # Check if the required parameters are available in the config
            if all(param in self.config for param in required_params):
                # Initialize the handler dynamically by passing the required parameters from config
                handler_args = {param: self.config[param] for param in required_params}
                self.handlers[handler_name] = handler_class(**handler_args)

    def _get_required_params(self, handler_class):
        """
        Get a list of required parameters for the handler class' __init__ method.
        :param handler_class: The class of the handler.
        :return: List of required parameter names.
        """
        # Get the signature of the __init__ method
        signature = inspect.signature(handler_class.__init__)
        params = signature.parameters

        # Remove 'self' from parameters and return the rest
        required_params = [param for param in params if param != 'self']
        return required_params

    def detect_dvr_type(self):
        """
        Detect the type of DVR and return the corresponding handler key.
        :return: Key for the appropriate handler (e.g., "RTSP", "ONVIF").
        """
        # Try RTSP if handler exists
        if "RTSP" in self.handlers and self.handlers["RTSP"].test_connection():
            self.logger.info("DVR detected as RTSP-compatible.")
            return "RTSP"
        
        # Try ONVIF if handler exists
        if "ONVIF" in self.handlers and self.handlers["ONVIF"].test_connection():
            self.logger.info("DVR detected as ONVIF-compatible.")
            return "ONVIF"
        
        # Try Proprietary APIs if handler exists
        if "Proprietary" in self.handlers and self.handlers["Proprietary"].test_connection():
            self.logger.info("DVR detected as Proprietary API-compatible.")
            return "Proprietary"
        
        # Try Web Interface if handler exists
        if "Web" in self.handlers and self.handlers["Web"].test_connection():
            self.logger.info("DVR detected as Web Interface-compatible.")
            return "Web"
        
        # Fallback to Analog if handler exists
        if "Analog" in self.handlers and self.handlers["Analog"].test_connection():
            self.logger.info("DVR detected as Analog-based.")
            return "Analog"
        
        # If no handler could be detected
        self.logger.error("DVR detection failed. No compatible stream found.")
        return None

    def handle(self):
        """
        Detect DVR type and delegate to the appropriate handler.
        """
        dvr_type = self.detect_dvr_type()
        
        if dvr_type:
            handler = self.handlers[dvr_type]
            return handler
        else:
            self.logger.error("No compatible handler found for the DVR type.")
            return None
# Example usage
if __name__ == "__main__":
    dvr_config = {
        "ip": "192.168.1.100",
        "username": "admin",
        "password": "password",
        "port": 554,  # Default RTSP port
        "rtsp_url": "rtsp://192.168.1.100:554/stream",  # Example RTSP URL
        "user_fps": 1,  # Example FPS setting
        "duration": 5,  # Example duration
        "timeout": 10,   # Timeout duration
        "delay": 5,      # Delay before stream
    }
    hybrid_handler = HybridHandler(dvr_config)
    print(hybrid_handler.handle())
