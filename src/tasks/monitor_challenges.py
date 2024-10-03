import json
import logging
import time
from datetime import datetime

import redis
import requests
from sqlalchemy import or_
from sqlalchemy.future import select

from src.config import CHECKPOINT_URL
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.services.api_service import ambassadors

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 30
last_flush_time = time.time()
objects_to_be_updated = []
queue_name = "challenges_queue"


def push_to_redis_queue(data):
    redis_client.lpush(queue_name, json.dumps(data))


def object_exists(obj_list, new_obj):
    new_obj_filtered = {k: v for k, v in new_obj.items() if k not in ['pass_the_challenge']}

    raw_data = redis_client.lrange(queue_name, 0, -1)
    for item in raw_data:
        redis_objects = json.loads(item.decode('utf-8'))
        obj_list.extend(redis_objects)

    for obj in obj_list:
        obj_filtered = {k: v for k, v in obj.items() if k not in ['pass_the_challenge']}
        if obj_filtered == new_obj_filtered:
            return True
    return False


def get_monitored_challenges():
    try:
        logger.info("Fetching monitored challenges from database")
        with TaskSessionLocal_() as db:
            result = db.execute(
                select(Challenge).where(
                    or_(
                        Challenge.status == None,  # status is null
                        Challenge.status == ""  # status is an empty string
                    ),
                    Challenge.active == "1",  # active is "1"
                    Challenge.challenge == "test"  # challenge is "test"
                )
            )
            challenges = result.scalars().all()
        logger.info(f"Retrieved {len(challenges)} monitored challenges")
        return challenges
    except Exception as e:
        logger.error(f"An error occurred while fetching monitored challenges: {e}")
        return []


def get_profit_sum(data, challenges_data):
    for hot_key, content in data.items():
        profit_sum = 0
        try:
            trader_id = ambassadors.get(hot_key, "")
            if not trader_id:
                continue

            for position in content["positions"]:
                profit_loss = (position["return_at_close"] * 100) - 100
                if position["is_closed_position"] is True:
                    profit_sum += profit_loss

            challenges_data[hot_key] = {
                "profit_sum": profit_sum,
            }
        except Exception as ex:
            logger.error(f"An error occurred while setting profit_loss: {hot_key} - {ex}")


def get_draw_down(data, challenges_data):
    for hot_key, content in data.items():
        try:
            trader_id = ambassadors.get(hot_key, "")
            if not trader_id:
                continue

            draw_down = (content["cps"][-1]["mdd"] * 100) - 100
            challenges_data[hot_key]["draw_down"] = draw_down
        except Exception as ex:
            logger.error(f"An error occurred while setting maximum draw_down: {hot_key} - {ex}")


@celery_app.task(name='src.tasks.monitor_challenges.monitor_challenges')
def monitor_challenges():
    logger.info("Starting monitor_challenges task")

    global objects_to_be_updated, last_flush_time

    current_time = time.time()
    if (current_time - last_flush_time) >= FLUSH_INTERVAL:
        push_to_redis_queue(objects_to_be_updated)
        last_flush_time = current_time
        objects_to_be_updated = []

    response = requests.get(CHECKPOINT_URL)
    if response.status_code != 200:
        return

    data = response.json()

    if not data:
        return

    challenges_data = {}
    get_profit_sum(data["positions"], challenges_data)
    get_draw_down(data["perf_ledgers"], challenges_data)

    for challenge in get_monitored_challenges():
        _data = challenges_data.get(challenge.hot_key, {})
        if not _data:
            continue

        new_object = {}
        if _data["profit_sum"] >= 2:  # 2%
            new_object = {"id": challenge.id, "pass_the_challenge": datetime.utcnow(), "status": "Passed"}
        elif _data["draw_down"] <= -5:  # 5%
            new_object = {"id": challenge.id, "status": "Failed"}

        if new_object != {} and (not object_exists(objects_to_be_updated, new_object)):
            objects_to_be_updated.append(new_object)

    logger.info("Finished monitor_challenges task")
