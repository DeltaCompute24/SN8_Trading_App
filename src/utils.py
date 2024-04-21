import logging
from termcolor import colored
from colorama import init

# Initialize colorama for colored terminal output
init()

# Configure logging
def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    return logging.getLogger()
