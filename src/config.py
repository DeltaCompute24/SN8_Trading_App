import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('POLYGON_API_KEY')
SIGNAL_API_KEY = os.getenv('SIGNAL_API_KEY')
SIGNAL_API_BASE_URL = os.getenv('SIGNAL_API_BASE_URL')
FORECAST_API_URL = os.getenv('FORECAST_API_URL')
