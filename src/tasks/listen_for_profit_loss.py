import asyncio
import logging
from datetime import datetime

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.services.api_service import call_main_net, testnet_websocket
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import set_hash_value, push_to_redis_queue

logger = logging.getLogger(__name__)


@celery_app.task(name='src.tasks.listen_for_profit_loss.monitor_taoshi')
def monitor_taoshi():
    logger.info("Starting monitor_positions task")
    main_net_data = call_main_net()
    test_net_data = asyncio.run(testnet_websocket())
    data = test_net_data | main_net_data

    if not data:
        push_to_redis_queue(
            data=f"**Monitor Taoshi** => Validator Checkpoint and Mainnet api returns with status code other than 200",
            queue_name=ERROR_QUEUE_NAME
        )
        return

    with TaskSessionLocal_() as db:
        challenges = db.query(Challenge).all()
        for challenge in challenges:
            hot_key = challenge.hot_key
            trader_id = challenge.trader_id

            content = data.get(challenge.hot_key)
            if not content:
                continue

            positions = content["positions"]
            for position in positions:
                try:
                    if position["is_closed_position"] is True:
                        continue

                    trade_pair = position.get("trade_pair", [])[0]
                    price, taoshi_profit_loss, taoshi_profit_loss_without_fee = position["orders"][-1]["price"], \
                        position["return_at_close"], position["current_return"]
                    profit_loss = (taoshi_profit_loss * 100) - 100
                    profit_loss_without_fee = (taoshi_profit_loss_without_fee * 100) - 100
                    position_uuid = position["position_uuid"]
                    value = [str(datetime.now()), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
                             taoshi_profit_loss_without_fee, position_uuid, hot_key, len(position["orders"]),
                             position["average_entry_price"]]
                    set_hash_value(key=f"{trade_pair}-{trader_id}", value=value)
                except Exception as ex:
                    push_to_redis_queue(
                        data=f"**Monitor Taoshi** => Error Occurred While Fetching Position {trade_pair}-{trader_id}: {ex}",
                        queue_name=ERROR_QUEUE_NAME)
                    logger.error(f"An error occurred while fetching position {trade_pair}-{trader_id}: {ex}")
