import json
import logging

import redis
from redis import asyncio as aioredis
from sqlalchemy import update

from src.config import REDIS_URL
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.models.transaction import Transaction

redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

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
        item = redis_client.lindex('db_operations_queue', -1)
        if item:
            data = json.loads(item)
            bulk_update(data)
            redis_client.rpop('db_operations_queue')

        # for monitor challenge
        item = redis_client.lindex('challenges_queue', -1)
        if not item:
            return
        data = json.loads(item)
        bulk_update_challenge(data)
        redis_client.rpop('challenges_queue')
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
    except Exception as e:
        logger.error(f"An error occurred in process_db_operations: {e}")
