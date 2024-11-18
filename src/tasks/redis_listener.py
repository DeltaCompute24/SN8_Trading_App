import json
import logging

import redis
from sqlalchemy import update

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.models.transaction import Transaction
from src.utils.constants import CHALLENGE_QUEUE_NAME
from src.utils.redis_manager import get_queue_left_item, pop_queue_right_item

logger = logging.getLogger(__name__)


def bulk_update(data):
    if not data:
        logger.info("No data to update")
        return
    with TaskSessionLocal_() as db:
        db.execute(
            update(Transaction),
            data,
        )
        db.commit()


def bulk_update_challenge(data):
    if not data:
        logger.info("No data to update")
        return
    with TaskSessionLocal_() as db:
        db.execute(
            update(Challenge),
            data,
        )
        db.commit()


@celery_app.task(name='src.tasks.redis_listener.event_listener')
def event_listener():
    logger.info("Starting process_db_operations task")
    try:
        item = get_queue_left_item()
        if item:
            data = json.loads(item)
            bulk_update(data)
            pop_queue_right_item()

        # for monitor challenge
        item = get_queue_left_item(queue_name=CHALLENGE_QUEUE_NAME)
        if not item:
            return
        data = json.loads(item)
        bulk_update_challenge(data)
        pop_queue_right_item(queue_name=CHALLENGE_QUEUE_NAME)
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
    except Exception as e:
        logger.error(f"An error occurred in process_db_operations: {e}")
