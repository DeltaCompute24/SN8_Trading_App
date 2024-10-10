import json
import logging
import time
from datetime import datetime

import redis
import requests
from sqlalchemy import or_
from sqlalchemy.future import select
from sqlalchemy.sql import and_

from src.config import CHECKPOINT_URL
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.services.email_service import send_mail

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 30
last_flush_time = time.time()
objects_to_be_updated = []
queue_name = "challenges_queue"


def push_to_redis_queue(data):
    redis_client.lpush(queue_name, json.dumps(data))


def object_exists(obj_list, new_obj):
    new_obj_filtered = {k: v for k, v in new_obj.items() if k not in ['pass_the_challenge', 'draw_down', 'profit_sum']}

    raw_data = redis_client.lrange(queue_name, 0, -1)
    for item in raw_data:
        redis_objects = json.loads(item.decode('utf-8'))
        obj_list.extend(redis_objects)

    for obj in obj_list:
        obj_filtered = {k: v for k, v in obj.items() if k not in ['pass_the_challenge', 'draw_down', 'profit_sum']}
        if obj_filtered == new_obj_filtered:
            return True
    return False


def get_monitored_challenges():
    try:
        logger.info("Fetching monitored challenges from database")
        with TaskSessionLocal_() as db:
            result = db.execute(
                select(Challenge).where(
                    and_(
                        or_(
                            Challenge.status == "In Challenge",
                        ),
                        Challenge.active == "1",
                        Challenge.challenge == "test"
                    )
                )
            )
            challenges = result.scalars().all()
        logger.info(f"Retrieved {len(challenges)} monitored challenges")
        return challenges
    except Exception as e:
        logger.error(f"An error occurred while fetching monitored challenges: {e}")
        return []


def update_challenge(challenge, status, draw_down, profit_sum, subject, content, pass_the_challenge=None):
    with TaskSessionLocal_() as db:
        challenge.pass_the_challenge = pass_the_challenge
        challenge.status = status
        challenge.draw_down = draw_down
        challenge.profit_sum = profit_sum
        db.commit()
        db.refresh(challenge)
    email = challenge.user.email
    if not email:
        return
    send_mail(email, subject, content)


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

    positions = data["positions"]
    perf_ledgers = data["perf_ledgers"]

    for challenge in get_monitored_challenges():
        hot_key = challenge.hot_key
        p_content = positions.get(hot_key)
        l_content = perf_ledgers.get(hot_key)
        if not (p_content or l_content):
            continue

        profit_sum = 0
        for position in p_content["positions"]:
            profit_loss = (position["return_at_close"] * 100) - 100
            if position["is_closed_position"] is True:
                profit_sum += profit_loss

        draw_down = (l_content["cps"][-1]["mdd"] * 100) - 100

        if profit_sum >= 2:  # 2%
            # new_object = {"id": challenge.id, "pass_the_challenge": datetime.utcnow(), "status": "Passed"}
            update_challenge(challenge, "Passed", draw_down, profit_sum, "Challenge Passed",
                             "Congratulations! You have entered to Phase 2 from Phase 1!", datetime.utcnow())
        elif draw_down <= -5:  # 5%
            # new_object = {"id": challenge.id, "status": "Failed"}
            update_challenge(challenge, "Failed", draw_down, profit_sum, "Challenge Failed",
                             "Unfortunately! You have Failed!")

        # if new_object != {} and (not object_exists(objects_to_be_updated, new_object)):
        #     new_object["draw_down"] = draw_down
        #     new_object["profit_sum"] = profit_sum
        #     objects_to_be_updated.append(new_object)

    logger.info("Finished monitor_challenges task")
