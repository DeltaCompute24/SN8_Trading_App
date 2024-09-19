import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
SIGNAL_API_BASE_URL = os.getenv("SIGNAL_API_BASE_URL")
SIGNAL_API_KEY = os.getenv("TRADE_API_KEY")
CHECKPOINT_URL = os.getenv("CHECKPOINT_URL")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
