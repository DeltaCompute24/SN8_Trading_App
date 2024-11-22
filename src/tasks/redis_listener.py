import json
import logging

import redis
from sqlalchemy import update

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import get_queue_right_item, pop_queue_right_item, push_to_redis_queue

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


@celery_app.task(name='src.tasks.redis_listener.event_listener')
def event_listener():
    logger.info("Starting process_db_operations task")
    try:
        item = get_queue_right_item()
        if not item:
            return
        data = json.loads(item)
        bulk_update(data)
        pop_queue_right_item()

    except redis.ConnectionError as e:
        push_to_redis_queue(data=f"**Redis Listener** => Redis Connection Error - {e}", queue_name=ERROR_QUEUE_NAME)
        logger.error(f"Redis connection error: {e}")
    except Exception as e:
        push_to_redis_queue(data=f"**Redis Listener** => Error Occurred in process_db_operations - {e}",
                            queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred in process_db_operations: {e}")
