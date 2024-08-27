import json
import logging

import redis
from sqlalchemy import update

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models import Transaction

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

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
        logger.info(f"Pop from Queue: {redis_client.brpop('db_operations_queue')}")
        _, data = redis_client.brpop('db_operations_queue')
        logger.info(f"data: {data}")
        data = json.loads(data)
        logger.info(f"Processing data from Redis: {data}")
        bulk_update(data)
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
    except Exception as e:
        logger.error(f"An error occurred in process_db_operations: {e}")
