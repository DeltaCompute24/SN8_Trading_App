import logging

from discordwebhook import Discord

from src.config import WEBHOOK_URL
from src.core.celery_app import celery_app
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import get_queue_data, pop_queue_right_item

logger = logging.getLogger(__name__)


@celery_app.task(name='src.tasks.send_notification.send_notifications')
def send_notifications():
    error_data = get_queue_data(queue_name=ERROR_QUEUE_NAME)
    length = len(error_data)

    if length == 0:
        return
    try:
        for content in error_data:
            discord = Discord(url=WEBHOOK_URL)
            discord.post(content=content)

        pop_queue_right_item(queue_name=ERROR_QUEUE_NAME, count=length)
    except Exception as e:
        pass
