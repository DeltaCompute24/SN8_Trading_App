import logging
from datetime import datetime

import redis
import requests
from sqlalchemy.future import select

from src.config import CHECKPOINT_URL, MAIN_NET
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models import Challenge
from src.services.api_service import call_checkpoint_api, ambassadors
from src.services.api_service import call_main_net

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

logger = logging.getLogger(__name__)


@celery_app.task(name='src.tasks.listen_for_profit_loss.monitor_taoshi')
def monitor_taoshi():
    logger.info("Starting monitor_positions task")
    if MAIN_NET:
        data = call_main_net()
    else:
        data = call_checkpoint_api()

    if not data:
        return

    for hot_key, content in data.items():
        trader_id = ""
        trade_pair = ""
        try:
            trader_id = ambassadors.get(hot_key, "")
            if not trader_id:
                continue

            positions = content["positions"]
            for position in positions:
                if position["is_closed_position"] is True:
                    continue

                trade_pair = position.get("trade_pair", [])[0]
                price, taoshi_profit_loss, taoshi_profit_loss_without_fee = position["orders"][-1]["price"], position[
                    "return_at_close"], position["current_return"]
                profit_loss = (taoshi_profit_loss * 100) - 100
                profit_loss_without_fee = (taoshi_profit_loss_without_fee * 100) - 100
                position_uuid = position["position_uuid"]
                value = [str(datetime.now()), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
                         taoshi_profit_loss_without_fee, position_uuid, hot_key]
                redis_client.hset('positions', f"{trade_pair}-{trader_id}", str(value))
        except Exception as ex:
            logger.error(f"An error occurred while fetching position {trade_pair}-{trader_id}: {ex}")


def get_monitored_challenges():
    try:
        logger.info("Fetching monitored challenges from database")
        with TaskSessionLocal_() as db:
            result = db.execute(
                select(Challenge).where(
                    Challenge.status == None,  # status is null
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
                profit_loss = round(profit_loss, 2)
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
            draw_down = round(draw_down, 2)
            challenges_data[hot_key]["draw_down"] = draw_down
        except Exception as ex:
            logger.error(f"An error occurred while setting maximum draw_down: {hot_key} - {ex}")


def update_challenge(challenge, status):
    try:
        logger.info("Update challenge status")
        with TaskSessionLocal_() as db:
            challenge.status = status
            db.commit()

    except Exception as e:
        logger.error(f"An error occurred while updating challenge status: {e}")


@celery_app.task(name='src.tasks.listen_for_profit_loss.monitor_challenges')
def monitor_challenges():
    logger.info("Starting monitor_challenges task")
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
        if _data["profit_sum"] >= 0.02:  # 2%
            update_challenge(challenge, status="Passed")
        elif _data["draw_down"] >= 0.05:  # 5%
            update_challenge(challenge, status="Failed")

    logger.info("Finished monitor_challenges task")
