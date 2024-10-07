import logging
from datetime import datetime

import redis

from src.core.celery_app import celery_app
from src.services.api_service import call_main_net, call_checkpoint_api
from src.services.user_service import get_challenge

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

logger = logging.getLogger(__name__)


@celery_app.task(name='src.tasks.listen_for_profit_loss.monitor_taoshi')
def monitor_taoshi():
    logger.info("Starting monitor_positions task")
    main_net_data = call_main_net()
    test_net_data = call_checkpoint_api()
    data = test_net_data | main_net_data

    if not data:
        return

    for hot_key, content in data.items():
        trader_id = ""
        trade_pair = ""
        try:
            challenge = get_challenge(hot_key)
            if not challenge:
                continue
            trader_id = challenge.trader_id

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
