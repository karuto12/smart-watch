import logging
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
        self.handlers = {
            "RTSP": RTSPHandler(config),
            "ONVIF": ONVIFHandler(config),
            "Proprietary": ProprietaryHandler(config),
            "Web": WebHandler(config),
            "Analog": AnalogHandler(config),
        }
        self.logger = logging.getLogger("HybridHandler")

    def detect_dvr_type(self):
        """
        Detect the type of DVR and return the corresponding handler key.
        :return: Key for the appropriate handler (e.g., "RTSP", "ONVIF").
        """
        # Try RTSP
        if RTSPHandler.test_connection():
            self.logger.info("DVR detected as RTSP-compatible.")
            return "RTSP"
        
        # Try ONVIF
        if ONVIFHandler.test_connection():
            self.logger.info("DVR detected as ONVIF-compatible.")
            return "ONVIF"
        
        # Try Proprietary APIs
        if ProprietaryHandler.test_connection():
            self.logger.info("DVR detected as Proprietary API-compatible.")
            return "Proprietary"
        
        # Try Web Interface
        if WebHandler.test_connection():
            self.logger.info("DVR detected as Web Interface-compatible.")
            return "Web"
        
        # Fallback to Analog
        self.logger.info("DVR detected as Analog-based.")
        return "Analog"

    def handle(self):
        """
        Detect DVR type and delegate to the appropriate handler.
        """
        dvr_type = self.detect_dvr_type()
        handler = self.handlers[dvr_type]
        handler.process()

# Example usage
if __name__ == "__main__":
    dvr_config = {
        "ip": "192.168.1.100",
        "username": "admin",
        "password": "password",
        "port": 554,  # Default RTSP port
    }
    hybrid_handler = HybridHandler(dvr_config)
    hybrid_handler.handle()
