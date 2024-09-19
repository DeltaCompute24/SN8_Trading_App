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
from src.services.api_service import get_profit_and_current_price
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
        current_price, profit_loss = get_profit_and_current_price(position.trader_id, position.trade_pair)
        logger.error(f"Current Price Pair: {position.trade_pair}")
        if current_price:
            current_price = float(current_price.decode('utf-8'))
            logger.error(f"Current Price Found: {current_price}")

            logger.error(f"Objects to be Updated: {objects_to_be_updated}")
            if position.status == "PENDING" and should_open_position(position, current_price):
                open_position(position, current_price)
            elif position.status == "OPEN" and should_close_position(profit_loss, position):
                logger.info(
                    f"Position shouldn't be closed: {position.position_id}: {position.trader_id}: {position.trade_pair}")
                close_position(position, current_price, profit_loss)

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
        if open_submitted:
            objects_to_be_updated.append(new_object)
    except Exception as e:
        logger.error(f"An error occurred while opening position {position.position_id}: {e}")


def close_position(position, close_price, profit_loss):
    global objects_to_be_updated
    try:
        new_object = {
            "order_id": position.order_id,
            "close_price": close_price,
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


def should_close_position(profit_loss, position):
    try:
        take_profit = position.cumulative_take_profit
        stop_loss = position.cumulative_stop_loss

        if position.cumulative_order_type == "LONG":

            if stop_loss is not None and stop_loss != 0 and profit_loss <= -stop_loss:
                logger.info(f"Determining whether to close position: True")
                return True

            if take_profit is not None and take_profit != 0 and profit_loss >= take_profit:
                logger.info(f"Determining whether to close position: True")

                return True
        elif position.cumulative_order_type == "SHORT":
            if stop_loss is not None and stop_loss != 0 and profit_loss >= stop_loss:
                logger.info(f"Determining whether to close position: True")

                return True
            if take_profit is not None and take_profit != 0 and profit_loss <= -take_profit:
                logger.info(f"Determining whether to close position: True")

                return True
        logger.info(f"closing position: False")
        return False

    except Exception as e:
        logger.error(f"An error occurred while determining if position should be closed: {e}")
        return False
