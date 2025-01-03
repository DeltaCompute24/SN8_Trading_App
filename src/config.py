import os

from dotenv import load_dotenv

load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# DISCORD CONFIGURATION
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
