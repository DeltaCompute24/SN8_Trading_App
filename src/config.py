import os

from dotenv import load_dotenv

from src.utils.constants import MAIN_POSITIONS_URL, MAIN_POSITIONS_TOKEN, MAIN_STATISTICS_TOKEN, MAIN_STATISTICS_URL

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
SIGNAL_API_BASE_URL = os.getenv("SIGNAL_API_BASE_URL")
SIGNAL_API_KEY = os.getenv("TRADE_API_KEY")
CHECKPOINT_URL = os.getenv("CHECKPOINT_URL")
MAIN_NET = os.getenv("MAIN_NET", "false") == "true"

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# EMAIL CONFIGURATIONS
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "false") == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# EXTERNAL API
REGISTRATION_API_URL = os.getenv("REGISTRATION_API_URL")
POSITIONS_URL = os.getenv("POSITIONS_URL", MAIN_POSITIONS_URL)
POSITIONS_TOKEN = os.getenv("POSITIONS_TOKEN", MAIN_POSITIONS_TOKEN)
STATISTICS_URL = os.getenv("STATISTICS_URL", MAIN_STATISTICS_URL)
STATISTICS_TOKEN = os.getenv("STATISTICS_TOKEN", MAIN_STATISTICS_TOKEN)

# AWS CONFIGURATION
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_KEY")
