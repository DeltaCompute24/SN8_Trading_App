import logging
from datetime import datetime, timedelta

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.services.api_service import call_main_net
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import set_hash_value, push_to_redis_queue, delete_hash_value
from src.validations.time_validations import convert_timestamp_to_datetime

logger = logging.getLogger(__name__)


def populate_redis_positions(data, _type="Mainnet"):
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
                trade_pair = position.get("trade_pair", [])[0]
                try:
                    key = f"{trade_pair}-{trader_id}"
                    current_time = datetime.utcnow() - timedelta(hours=1)
                    close_time = convert_timestamp_to_datetime(position["close_ms"])

                    if position["is_closed_position"] is True and current_time > close_time:
                        delete_hash_value(key)
                        continue

                    price, taoshi_profit_loss, taoshi_profit_loss_without_fee = position["orders"][-1]["price"], \
                        position["return_at_close"], position["current_return"]
                    profit_loss = (taoshi_profit_loss * 100) - 100
                    profit_loss_without_fee = (taoshi_profit_loss_without_fee * 100) - 100
                    position_uuid = position["position_uuid"]
                    value = [str(datetime.now()), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
                             taoshi_profit_loss_without_fee, position_uuid, hot_key, len(position["orders"]),
                             position["average_entry_price"], position["is_closed_position"]]
                    set_hash_value(key=key, value=value)
                except Exception as ex:
                    push_to_redis_queue(
                        data=f"**Monitor Taoshi Positions** => Error Occurred While Fetching {_type} Position {trade_pair}-{trader_id}: {ex}",
                        queue_name=ERROR_QUEUE_NAME)
                    logger.error(f"An error occurred while fetching position {trade_pair}-{trader_id}: {ex}")


@celery_app.task(name='src.tasks.monitor_miner_positions.monitor_miner')
def monitor_miner():
    logger.info("Starting monitor miner positions task")
    main_net_data = call_main_net()

    if not main_net_data:
        push_to_redis_queue(
            data=f"**Monitor Taoshi Positions** => Mainnet api returns with status code other than 200",
            queue_name=ERROR_QUEUE_NAME
        )
        return

    populate_redis_positions(main_net_data)
