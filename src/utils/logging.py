# src/utils/logging.py

import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def setup_logging(log_name='trading_app', level=logging.INFO):
    logger = logging.getLogger(log_name)
    logger.setLevel(level)
    
    log_file = os.path.join(LOG_DIR, f"{log_name}.log")
    handler = RotatingFileHandler(log_file, maxBytes=10**6, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger

# Example usage:
# logger = setup_logging()
# logger.info("Logging is set up.")
