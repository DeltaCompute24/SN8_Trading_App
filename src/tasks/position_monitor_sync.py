import asyncio
import json
import logging
import time
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.sql import or_

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction
from src.services.fee_service import get_taoshi_values
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import get_live_price, push_to_redis_queue, get_queue_data
from src.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 20
last_flush_time = time.time()
objects_to_be_updated = []


def object_exists(obj_list, new_obj_id):
    raw_data = get_queue_data()
    for item in raw_data:
        redis_objects = json.loads(item)
        obj_list.extend(redis_objects)

    for obj in obj_list:
        if obj["order_id"] == new_obj_id:
            return True
    return False


def open_position(position, current_price, entry_price=False):
    global objects_to_be_updated
    try:
        logger.info("Open Position Called!")
        open_submitted = asyncio.run(
            websocket_manager.submit_trade(position.trader_id, position.trade_pair, position.order_type,
                                           position.leverage))
        if not open_submitted:
            return
        for i in range(10):
            time.sleep(1)
            first_price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, uuid, hot_key, len_order, average_entry_price = get_taoshi_values(
                position.trader_id,
                position.trade_pair,
                challenge=position.source,
            )
            # 10 times
            if first_price != 0:
                break

        if first_price == 0:
            push_to_redis_queue(
                data=f"**Monitor Positions** While Opening Position {position.trader_id}-{position.trade_pair}-{position.order_id} - Price is Zero -- Trade is not Submitted",
                queue_name=ERROR_QUEUE_NAME,
            )
            return

        new_object = {
            "order_id": position.order_id,
            "operation_type": "open",
            "status": "OPEN",
            "old_status": position.status,
            "hot_key": hot_key,
            "uuid": uuid,
            "initial_price": first_price,
            "profit_loss": profit_loss,
            "profit_loss_without_fee": profit_loss_without_fee,
            "taoshi_profit_loss": taoshi_profit_loss,
            "taoshi_profit_loss_without_fee": taoshi_profit_loss_without_fee,
            "order_level": len_order,
            "average_entry_price": average_entry_price,
            "modified_by": "system",

        }
        if entry_price:
            new_object["entry_price"] = current_price

        objects_to_be_updated.append(new_object)
    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Opening Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while opening position {position.position_id}: {e}")


def close_position(position, profit_loss):
    global objects_to_be_updated
    try:
        logger.info("Close Position Called!")
        close_submitted = asyncio.run(
            websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
        if not close_submitted:
            return
        for i in range(10):
            time.sleep(1)
            close_price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, uuid, hot_key, len_order, average_entry_price = get_taoshi_values(
                position.trader_id,
                position.trade_pair,
                position_uuid=position.uuid,
                challenge=position.source
            )
            # 10 times
            if close_price != 0 and position.order_level < len_order:
                break

        if close_price == 0:
            push_to_redis_queue(
                data=f"**Monitor Positions** While Closing Position {position.trader_id}-{position.trade_pair}-{position.order_id} - Price is Zero",
                queue_name=ERROR_QUEUE_NAME,
            )
            return
        objects_to_be_updated.append(
            {
                "order_id": position.order_id,
                "close_time": str(datetime.utcnow()),
                "operation_type": "close",
                "status": "CLOSED",
                "old_status": position.status,
                "close_price": close_price,
                "profit_loss": profit_loss,
                "profit_loss_without_fee": profit_loss_without_fee,
                "taoshi_profit_loss": taoshi_profit_loss,
                "taoshi_profit_loss_without_fee": taoshi_profit_loss_without_fee,
                "order_level": len_order,
                "average_entry_price": average_entry_price,
                "modified_by": "system",
            }
        )
    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Closing Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred while closing position {position.position_id}: {e}")


def check_take_profit(trailing, take_profit, profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected profit
    """
    # if profit_loss < 0 it means there is no profit so return False
    if trailing or profit_loss < 0:
        return False
    if take_profit is not None and take_profit != 0 and profit_loss >= take_profit:
        return True
    return False


def check_stop_loss(trailing, stop_loss, profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected loss
    """
    # if profit_loss > 0 it means there is no loss so return False
    if trailing or profit_loss > 0:
        return False

    if stop_loss is not None and stop_loss != 0 and profit_loss <= -stop_loss:
        return True
    return False


def check_trailing_stop_loss(trailing, stop_loss, max_profit_loss, current_profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected trailing loss
    """
    # return if trailing is false or stop_loss value is None or zero
    if not trailing or stop_loss is None or stop_loss == 0:
        return False

    difference = max_profit_loss - current_profit_loss

    if difference >= stop_loss:
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
                check_stop_loss(trailing, stop_loss, profit_loss) or
                check_take_profit(trailing, take_profit, profit_loss)
        )

        print(f"Determining whether to close position: {close_result}")
        logger.info(f"Determining whether to close position: {close_result}")
        return close_result

    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Determining if Position Should be Closed {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while determining if position should be closed: {e}")
        return False


def update_position_profit(db, position, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
                           taoshi_profit_loss_without_fee):
    try:
        max_profit_loss = position.max_profit_loss or 0.0
        if max_profit_loss != 0 and profit_loss <= max_profit_loss:
            return position

        data = {
            "profit_loss": profit_loss,
            "max_profit_loss": profit_loss,
            "profit_loss_without_fee": profit_loss_without_fee,
            "taoshi_profit_loss": taoshi_profit_loss,
            "taoshi_profit_loss_without_fee": taoshi_profit_loss_without_fee,
        }

        for key, value in data.items():
            setattr(position, key, value)

        db.commit()
        db.refresh(position)
        return position
    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Updating Position Profit {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while updating position {position.position_id}: {e}")


def update_position_prices(db, position, current_price):
    try:
        max_price = position.max_price or 0.0
        min_price = position.min_price or 0.0
        changed = False

        if max_price == 0 or current_price >= max_price:
            max_price = current_price
            changed = True

        if min_price == 0 or current_price <= min_price:
            min_price = current_price
            changed = True

        if not changed:
            return position

        data = {
            "min_price": min_price,
            "max_price": max_price,
        }

        for key, value in data.items():
            setattr(position, key, value)

        db.commit()
        db.refresh(position)
        return position
    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Updating Position Prices {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while updating position {position.position_id}: {e}")


def check_pending_trailing_position(position, current_price):
    """
    Open Pending Position based on the trailing limit order
    """
    # calculate percentage
    limit_order_price = (position.limit_order * position.initial_price) / 100

    if position.order_type == "LONG":
        trailing_price = position.min_price + limit_order_price
    else:
        trailing_price = position.max_price - limit_order_price

    opened = (
            (position.order_type == "LONG" and current_price >= trailing_price) or
            (position.order_type == "SHORT" and current_price <= trailing_price)
    )

    logger.error(f"Determining whether to open pending trailing position: {opened}")
    if opened:
        open_position(position, current_price, entry_price=True)


def check_pending_position(position, current_price):
    """
    For Pending Position to be Opened
    """
    opened = (
            (position.upward == 0 and current_price <= position.entry_price) or
            (position.upward == 1 and current_price >= position.entry_price)
    )
    logger.error(f"Determining whether to open pending position: {opened}")

    if opened:
        open_position(position, current_price)


def check_open_position(db, position):
    """
    For Open Position to be Closed
    """
    # get values from taoshi platform
    price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, *taoshi_profit_loss_without_fee = get_taoshi_values(
        position.trader_id,
        position.trade_pair,
        challenge=position.source,
        position_uuid=position.uuid,
    )
    if price == 0:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Checking Open Position {position.trader_id}-{position.trade_pair}-{position.order_id} - Price is Zero",
            queue_name=ERROR_QUEUE_NAME
        )
        return False

    position = update_position_profit(db, position, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
                                      taoshi_profit_loss_without_fee[0])
    if position.status == "OPEN" and should_close_position(profit_loss, position):
        logger.info(f"Position should be closed: {position.position_id}: {position.trader_id}: {position.trade_pair}")
        close_position(position, profit_loss)
        return True


def monitor_position(db, position):
    """
    Monitor a single position

    if status is OPEN then check if it meets the criteria to CLOSE the position
    if status is PENDING then check if it meets the criteria to OPEN the position
    """
    global objects_to_be_updated
    if object_exists(objects_to_be_updated, position.order_id):
        logger.info("Return back as Close Position already exists in queue!")
        return
    try:
        logger.error(f"Current Pair: {position.trader_id}-{position.trade_pair}")
        # ---------------------------- OPENED POSITION ---------------------------------
        if position.status == "OPEN":
            return check_open_position(db, position)

        # ---------------------------- PENDING POSITION --------------------------------
        current_price = get_live_price(position.trade_pair)
        if not current_price:
            return

        # if it is not a trailing pending position
        if position.limit_order is None or position.limit_order == 0:
            check_pending_position(position, current_price)
        else:  # trailing pending position
            position = update_position_prices(db, position, current_price)
            check_pending_trailing_position(position, current_price)

    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Monitoring Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while monitoring position {position.position_id}: {e}")


def get_monitored_positions(db):
    """
    fetch OPEN and PENDING positions from database
    """
    try:
        logger.info("Fetching monitored positions from database")
        result = db.execute(
            select(Transaction).where(
                or_(
                    Transaction.status == "OPEN",
                    Transaction.status == "PENDING",
                )
            )
        )
        positions = result.scalars().all()
        logger.info(f"Retrieved {len(positions)} monitored positions")
        return positions
    except Exception as e:
        push_to_redis_queue(data=f"**Monitor Positions** Database Error - {e}", queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred while fetching monitored positions: {e}")
        return []


def monitor_positions_sync():
    """
    loop through all the positions and monitor them one by one
    """
    global objects_to_be_updated, last_flush_time
    try:
        logger.info("Starting monitor_positions_sync")

        current_time = time.time()

        if objects_to_be_updated and (current_time - last_flush_time) >= FLUSH_INTERVAL:
            logger.error(f"Going to Flush previous Objects!: {str(current_time - last_flush_time)}")
            last_flush_time = current_time
            push_to_redis_queue(json.dumps(objects_to_be_updated))
            objects_to_be_updated = []

        with TaskSessionLocal_() as db:
            for position in get_monitored_positions(db):

                # if position is open and take_profit and stop_loss are zero then don't monitor position
                skip_position = (
                        (position.status == "OPEN") and
                        (not position.take_profit or position.take_profit == 0) and
                        (not position.stop_loss or position.stop_loss == 0)
                )

                if skip_position:
                    logger.info(f"Skip position {position.position_id}: {position.trader_id}: {position.trade_pair}")
                    continue

                logger.info(f"Processing position {position.position_id}: {position.trader_id}: {position.trade_pair}")
                monitor_position(db, position)

        logger.info("Finished monitor_positions_sync")
    except Exception as e:
        logger.error(f"An error occurred in monitor_positions_sync: {e}")
        push_to_redis_queue(data=f"**Monitor Positions** Celery Task - {e}", queue_name=ERROR_QUEUE_NAME)


@celery_app.task(name='src.tasks.position_monitor_sync.monitor_positions')
def monitor_positions():
    logger.info("Starting monitor_positions task")
    monitor_positions_sync()
