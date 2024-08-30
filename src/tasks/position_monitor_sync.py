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
from src.services.trade_service import calculate_profit_loss
from src.utils.websocket_manager import websocket_manager

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 15
last_flush_time = time.time()
objects_to_be_updated = []


def push_to_redis_queue(queue_name, data):
    redis_client.lpush(queue_name, json.dumps(data))


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
            push_to_redis_queue('db_operations_queue', objects_to_be_updated)
            last_flush_time = current_time
            logger.error(f"Before: {objects_to_be_updated}")
            objects_to_be_updated = []
            logger.error(f"After: {objects_to_be_updated}")

        positions = get_monitored_positions()

        for position in positions:
            if position.status == "OPEN" and (not position.take_profit or
                                              position.take_profit == 0 or not position.stop_loss or position.stop_loss == 0):
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
        current_price = redis_client.hget('current_prices', position.trade_pair)
        logger.info(f"Current Prices Dict: {redis_client.hgetall('current_prices')}")
        logger.error(f"Current Price Pair: {position.trade_pair}")
        if current_price:
            current_price = float(current_price.decode('utf-8'))
            logger.error(f"Current Price Found: {current_price}")
            profit_loss = calculate_profit_loss(
                position.entry_price,
                current_price,
                position.cumulative_leverage,
                position.cumulative_order_type,
                position.asset_type
            )

            if should_open_position(position, current_price):
                open_position(position, current_price)
            elif should_close_position(profit_loss, position):
                close_position(position, current_price, profit_loss)
            # else:
            #     objects_to_be_updated.append({
            #         "order_id": position.order_id,
            #         "profit_loss": profit_loss
            #     })

        return True
    except Exception as e:
        logger.error(f"An error occurred while monitoring position {position.position_id}: {e}")


def open_position(position, current_price):
    global objects_to_be_updated
    try:
        open_submitted = asyncio.run(
            websocket_manager.submit_trade(position.trader_id, position.trade_pair, position.order_type,
                                           position.leverage))
        if open_submitted:
            objects_to_be_updated.append({
                "order_id": position.order_id,
                "entry_price": current_price,
                "operation_type": "open",
                "status": "OPEN",
                "old_status": position.status,
                "modified_by": "system",
            })
    except Exception as e:
        logger.error(f"An error occurred while opening position {position.position_id}: {e}")


def close_position(position, close_price, profit_loss):
    global objects_to_be_updated
    try:
        close_submitted = asyncio.run(
            websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
        if close_submitted:
            objects_to_be_updated.append({
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
            })
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
        result = (
                (position.status == "OPEN") and
                (position.cumulative_order_type == "LONG" and profit_loss >= position.cumulative_take_profit) or
                (position.cumulative_order_type == "LONG" and profit_loss <= position.cumulative_stop_loss) or
                (position.cumulative_order_type == "SHORT" and profit_loss <= position.cumulative_take_profit) or
                (position.cumulative_order_type == "SHORT" and profit_loss >= position.cumulative_stop_loss)
        )
        logger.info(f"Determining whether to close position: {result}")
        return result
    except Exception as e:
        logger.error(f"An error occurred while determining if position should be closed: {e}")
        return False
