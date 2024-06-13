import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
SIGNAL_API_BASE_URL = os.getenv("SIGNAL_API_BASE_URL")
SIGNAL_API_KEY = os.getenv("TRADE_API_KEY")
