import logging
from datetime import datetime

import redis

from src.config import MAIN_NET
from src.core.celery_app import celery_app
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
                value = [datetime.now(), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
                         taoshi_profit_loss_without_fee]
                redis_client.hset('positions', f"{trade_pair}-{trader_id}", str(value))
        except Exception as ex:
            logger.error(f"An error occurred while fetching position {trade_pair}-{trader_id}: {ex}")
