# src/utils/logging.py

import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()  # This will output logs to the console
        ]
    )
    return logging.getLogger(__name__)
