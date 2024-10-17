import asyncio
import json
import logging
import time
from datetime import datetime

import redis
from sqlalchemy.future import select

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction
from src.services.fee_service import get_taoshi_values
from src.utils.websocket_manager import websocket_manager

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 20
last_flush_time = time.time()
objects_to_be_updated = []
queue_name = "db_operations_queue"


def push_to_redis_queue(data):
    redis_client.lpush(queue_name, json.dumps(data))


def object_exists(obj_list, new_obj):
    new_obj_filtered = {k: v for k, v in new_obj.items() if
                        k not in ['close_time', 'close_price', 'profit_loss', 'initial_price']}

    raw_data = redis_client.lrange(queue_name, 0, -1)
    for item in raw_data:
        redis_objects = json.loads(item.decode('utf-8'))
        obj_list.extend(redis_objects)

    for obj in obj_list:
        obj_filtered = {k: v for k, v in obj.items() if
                        k not in ['close_time', 'close_price', 'profit_loss', 'initial_price']}

        if obj_filtered == new_obj_filtered:
            return True
    return False


@celery_app.task(name='src.tasks.position_monitor_sync.monitor_positions')
def monitor_positions():
    logger.info("Starting monitor_positions task")
    monitor_positions_sync()


def get_monitored_positions():
    try:
        logger.info("Fetching monitored positions from database")
        with TaskSessionLocal_() as db:
            result = db.execute(
                select(Transaction).where(Transaction.status != "CLOSED")
            )
            positions = result.scalars().all()
        logger.info(f"Retrieved {len(positions)} monitored positions")
        return positions
    except Exception as e:
        logger.error(f"An error occurred while fetching monitored positions: {e}")
        return []


def monitor_positions_sync():
    global objects_to_be_updated, last_flush_time
    try:
        logger.info("Starting monitor_positions_sync")

        current_time = time.time()
        if (current_time - last_flush_time) >= FLUSH_INTERVAL:
            logger.error(f"Going to Flush previous Objects!: {str(current_time - last_flush_time)}")
            push_to_redis_queue(objects_to_be_updated)
            last_flush_time = current_time
            logger.error(f"Before: {objects_to_be_updated}")
            objects_to_be_updated = []
            logger.error(f"After: {objects_to_be_updated}")

        positions = get_monitored_positions()

        for position in positions:
            logger.error(f"Current Prices Dict: {redis_client.hgetall('current_prices')}")
            # if position is open and take_profit and stop_loss are zero then don't monitor position
            if (position.status == "OPEN" and (not position.take_profit or position.take_profit == 0)
                    and (not position.stop_loss or position.stop_loss == 0)):
                logger.info(f"Skip position {position.position_id}: {position.trader_id}: {position.trade_pair}")
                continue
            logger.info(f"Processing position {position.position_id}: {position.trader_id}: {position.trade_pair}")
            monitor_position(position)
        logger.info("Finished monitor_positions_sync")
    except Exception as e:
        logger.error(f"An error occurred in monitor_positions_sync: {e}")


def monitor_position(position):
    global objects_to_be_updated
    try:
        # For Open Position to be Closed
        price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, *taoshi_profit_loss_without_fee = get_taoshi_values(
            position.trader_id,
            position.trade_pair,
            challenge=position.source,
        )
        update_position_profit(position, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
                               taoshi_profit_loss_without_fee)
        if position.status == "OPEN" and should_close_position(profit_loss, position):
            logger.info(
                f"Position shouldn't be closed: {position.position_id}: {position.trader_id}: {position.trade_pair}")
            close_position(position, profit_loss)
            return

        # For Pending Position to be opened
        current_price = redis_client.hget('current_prices', position.trade_pair)
        logger.error(f"Current Price Pair: {position.trade_pair}")
        if not current_price:
            return
        current_price = float(current_price.decode('utf-8'))
        logger.error(f"Current Price Found: {current_price}")

        logger.error(f"Objects to be Updated: {objects_to_be_updated}")
        if position.status == "PENDING" and should_open_position(position, current_price):
            open_position(position, current_price)

        return True
    except Exception as e:
        logger.error(f"An error occurred while monitoring position {position.position_id}: {e}")


def open_position(position, current_price):
    global objects_to_be_updated
    try:
        new_object = {
            "order_id": position.order_id,
            "initial_price": current_price,
            "operation_type": "open",
            "status": "OPEN",
            "old_status": position.status,
            "modified_by": "system",
        }
        if object_exists(objects_to_be_updated, new_object):
            logger.info("Return back as Open Position already exists in queue!")
            return
        logger.info("Open Position Called!")
        open_submitted = asyncio.run(
            websocket_manager.submit_trade(position.trader_id, position.trade_pair, position.order_type,
                                           position.leverage))
        if not open_submitted:
            return
        first_price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, uuid, hot_key, len_order, average_entry_price = get_taoshi_values(
            position.trader_id,
            position.trade_pair,
            challenge=position.source,
        )
        new_object["hot_key"] = hot_key
        new_object["uuid"] = uuid
        new_object["initial_price"] = first_price
        new_object["profit_loss"] = profit_loss
        new_object["profit_loss_without_fee"] = profit_loss_without_fee
        new_object["taoshi_profit_loss"] = taoshi_profit_loss
        new_object["taoshi_profit_loss_without_fee"] = taoshi_profit_loss_without_fee
        new_object["order_level"] = len_order
        new_object["average_entry_price"] = average_entry_price
        objects_to_be_updated.append(new_object)
    except Exception as e:
        logger.error(f"An error occurred while opening position {position.position_id}: {e}")


def close_position(position, profit_loss):
    global objects_to_be_updated
    try:
        new_object = {
            "order_id": position.order_id,
            "close_time": str(datetime.utcnow()),
            "profit_loss": profit_loss,
            "operation_type": "close",
            "status": "CLOSED",
            "old_status": position.status,
            "modified_by": "system",
            "order_type": "FLAT",
            "leverage": 1,
        }
        if object_exists(objects_to_be_updated, new_object):
            logger.info("Return back as Close Position already exists in queue!")
            return
        logger.info("Close Position Called!")
        close_submitted = asyncio.run(
            websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
        if close_submitted:
            close_price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, uuid, hot_key, len_order, average_entry_price = \
                get_taoshi_values(position.trader_id, position.trade_pair, position_uuid=position.uuid,
                                  challenge=position.source)[0]
            if close_price == 0:
                return
            new_object["close_price"] = close_price
            new_object["profit_loss"] = profit_loss
            new_object["profit_loss_without_fee"] = profit_loss_without_fee
            new_object["taoshi_profit_loss"] = taoshi_profit_loss
            new_object["taoshi_profit_loss_without_fee"] = taoshi_profit_loss_without_fee
            new_object["order_level"] = len_order
            new_object["average_entry_price"] = average_entry_price
            objects_to_be_updated.append(new_object)
    except Exception as e:
        logger.error(f"An error occurred while closing position {position.position_id}: {e}")


def should_open_position(position, current_price):
    result = (
            (position.status == "PENDING") and
            (position.upward == 0 and current_price <= position.entry_price) or
            (position.upward == 1 and current_price >= position.entry_price)
    )
    logger.info(f"Determining whether to open position: {result}")
    return result


def check_take_profit(take_profit, profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected profit
    """
    # if profit_loss < 0 it means there is no profit so return False
    if profit_loss < 0:
        return False
    if take_profit is not None and take_profit != 0 and profit_loss >= take_profit:
        return True
    return False


def check_stop_loss(stop_loss, profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected loss
    """
    # if profit_loss > 0 it means there is no loss so return False
    if profit_loss > 0:
        return False

    if stop_loss is not None and stop_loss != 0 and profit_loss <= -stop_loss:
        return True
    return False


def check_trailing_stop_loss(trailing, stop_loss, max_profit, profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected trailing loss
    """
    # return if trailing is false or stop_loss value is None or zero
    if not trailing or stop_loss is None or stop_loss == 0:
        return False

    t_profit_loss = profit_loss - max_profit
    t_stop_loss = max_profit - stop_loss
    if t_profit_loss >= t_stop_loss:
        return True
    return False


def should_close_position(profit_loss, position):
    """
    profit_loss: Its direct
    """
    try:
        take_profit = position.cumulative_take_profit
        stop_loss = position.cumulative_stop_loss
        max_profit = position.max_profit_loss
        trailing = position.trailing

        close_result = (
                check_trailing_stop_loss(trailing, stop_loss, max_profit, profit_loss) or
                check_stop_loss(stop_loss, profit_loss) or
                check_take_profit(take_profit, profit_loss)
        )

        print(f"Determining whether to close position: {close_result}")
        return close_result

    except Exception as e:
        logger.error(f"An error occurred while determining if position should be closed: {e}")
        return False


def update_position_profit(position, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
                           taoshi_profit_loss_without_fee):
    global objects_to_be_updated
    try:
        max_profit_loss = position.max_profit_loss or 0.0
        if profit_loss <= max_profit_loss:
            return

        new_object = {
            "order_id": position.order_id,
            "profit_loss": profit_loss,
            "max_profit_loss": profit_loss,
            "profit_loss_without_fee": profit_loss_without_fee,
            "taoshi_profit_loss": taoshi_profit_loss,
            "taoshi_profit_loss_without_fee": taoshi_profit_loss_without_fee,
        }
        if object_exists(objects_to_be_updated, new_object):
            logger.info("Return back as Profit Loss Position already exists in queue!")
            return
        logger.info("Update Position Profit Called!")
        objects_to_be_updated.append(new_object)
    except Exception as e:
        logger.error(f"An error occurred while closing position {position.position_id}: {e}")
