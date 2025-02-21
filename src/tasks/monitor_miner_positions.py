import logging
from datetime import datetime, timedelta
from collections import defaultdict

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.services.api_service import call_main_net, call_statistics_net
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import set_hash_value_generic, set_hash_value, push_to_redis_queue, delete_hash_value
from src.validations.time_validations import convert_timestamp_to_datetime

logger = logging.getLogger(__name__)


def populate_redis_positions(data, _type="Mainnet"):
    for hot_key, content in data.items():
        if not content:
            continue

        positions = content["positions"]
        currency_count = defaultdict(int)  # Initialize a dictionary to count currency pairs

        for position in positions:
            trade_pair = position.get("trade_pair", [])[0]
            currency = trade_pair  # Assuming the first element in trade_pair is the currency pair
            currency_count[currency] += 1  # Increment the count for the currency pair

        # Determine the most frequently used currency pair for the trader
        most_frequent_currency = max(currency_count, key=currency_count.get)
        
        trader_data = {
            "username": '',
            "email": '',
            "trader_pairs": most_frequent_currency,
            "all_time_returns": content.get("all_time_returns")
        }
        set_hash_value_generic(hash_name="trader_data", key=f"{hot_key}", value=trader_data)


    with TaskSessionLocal_() as db:
        challenges = db.query(Challenge).all()
        for challenge in challenges:
            hot_key = challenge.hot_key
            trader_id = challenge.trader_id

            content = data.get(challenge.hot_key)
            if not content:
                continue

            positions = content["positions"]
            currency_count = defaultdict(int)  # Initialize a dictionary to count currency pairs

            for position in positions:
                trade_pair = position.get("trade_pair", [])[0]
                currency = trade_pair  # Assuming the first element in trade_pair is the currency pair
                currency_count[currency] += 1  # Increment the count for the currency pair

                try:
                    key = f"{trade_pair}-{trader_id}"
                    current_time = datetime.utcnow() - timedelta(hours=1)
                    close_time = convert_timestamp_to_datetime(position["close_ms"])

                    if position["is_closed_position"] and current_time > close_time:
                        delete_hash_value(key)
                        continue

                    price, taoshi_profit_loss, taoshi_profit_loss_without_fee = position["orders"][-1]["price"], \
                        position["return_at_close"], position["current_return"]
                    profit_loss = (taoshi_profit_loss * 100) - 100
                    profit_loss_without_fee = (taoshi_profit_loss_without_fee * 100) - 100
                    position_uuid = position["position_uuid"]
                    
                    # Extract additional data
                    hotkey = content.get("hotkey")
                    email = challenge.user.email
                    username = challenge.user.username
                    all_time_returns = content.get("all_time_returns")

                    # Include additional data in the value
                    value = [
                        str(datetime.now()), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
                        taoshi_profit_loss_without_fee, position_uuid, hot_key, len(position["orders"]),
                        position["average_entry_price"], position["is_closed_position"], hotkey, email, username,
                        all_time_returns
                    ]
                    
                    set_hash_value(key=key, value=value)
                    
                    # Store all_time_returns in Redis using set_hash_value
                except Exception as ex:
                    push_to_redis_queue(
                        data=f"**Monitor Taoshi Positions** => Error Occurred While Fetching {_type} Position {trade_pair}-{trader_id}: {ex}",
                        queue_name=ERROR_QUEUE_NAME)
                    logger.error(f"An error occurred while fetching position {trade_pair}-{trader_id}: {ex}")

            # Determine the most frequently used currency pair for the trader
            most_frequent_currency = max(currency_count, key=currency_count.get)
            
            trader_data = {
                        "username": challenge.user.username,
                        "email": challenge.user.email,
                        "trader_pairs": most_frequent_currency,
                        "all_time_returns": content.get("all_time_returns")
                    }
            set_hash_value_generic(hash_name="trader_data", key=f"{challenge.hot_key}", value=trader_data)


def populate_redis_scores_rank(statistics_data):
    for position in statistics_data["data"]:
        try:
            # Prepare the value to be stored in Redis
            value = {
                "scores": position["scores"],
                "weight": position["weight"]
            }
            
            # Store the value in Redis
            set_hash_value_generic(hash_name="trader_rank_data", key=f"{position['hotkey']}", value=value)
            
            # Store all_time_returns in Redis using set_hash_value_generic
            set_hash_value_generic(hash_name="trader_returns", key=f"{position['hotkey']}", value=position['weight']['rank'])
        except Exception as ex:
            push_to_redis_queue(
                data=f"**Monitor Taoshi Positions** => Error Occurred While Fetching Position {position['hotkey']}: {ex}",
                queue_name=ERROR_QUEUE_NAME
            )
            logger.error(f"An error occurred while fetching position {position['hotkey']}: {ex}")


@celery_app.task(name='src.tasks.monitor_miner_positions.monitor_miner')
def monitor_miner():
    logger.info("Starting monitor miner positions task")
    main_net_data = call_main_net()
    statistics_data = call_statistics_net()
    if not main_net_data:
        push_to_redis_queue(
            data=f"**Monitor Taoshi Positions** => Mainnet api returns with status code other than 200",
            queue_name=ERROR_QUEUE_NAME
        )
        return

    populate_redis_positions(main_net_data)
    populate_redis_scores_rank(statistics_data)
