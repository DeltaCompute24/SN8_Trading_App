
import logging
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.sql import or_, and_, text

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction , Status
from src.services.fee_service import get_taoshi_values
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import get_live_price, push_to_redis_queue
from src.utils.websocket_manager import websocket_manager
from schemas.redis_position import RedisPosition
from src.services.trade_service import close_transaction, update_transaction


logger = logging.getLogger(__name__)



async def open_position(db, position, current_price, entry_price=False):
   
    try:
        logger.info("Open Position Called!")
        open_submitted = await websocket_manager.submit_trade(position.trader_id, position.trade_pair, position.order_type,
                                           position.leverage)
        if not open_submitted:
            return
        #Creating a position immediately with status PROCESSING
        await update_transaction(db, position.order_id, position.trader_id, entry_price= current_price,old_status=position.status
                                , status=Status.processing)


    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Opening Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while opening position {position.position_id}: {e}")


async def close_position( db , position, redis_position : RedisPosition):

    try:
        logger.info("Close Position Called!")
        close_submitted = await websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1)
        if not close_submitted:
            return
        
        #Closing a position immediately with status CLOSE_PROCESSING
        await close_transaction(db, position.order_id, position.trader_id, redis_position.price, profit_loss=redis_position.profit_loss,
                                old_status=position.status, profit_loss_without_fee=redis_position.profit_loss_without_fee,
                                taoshi_profit_loss=redis_position.taoshi_profit_loss, status=Status.close_processing,
                                taoshi_profit_loss_without_fee=redis_position.taoshi_profit_loss_without_fee, order_level=redis_position.len_order,
                                average_entry_price=redis_position.average_entry_price)

        # Remove closed position from the monitored_positions table
        await db.execute(
            text("DELETE FROM monitored_positions WHERE position_id = :position_id"),
            {"position_id": position.position_id}
        )
        await db.commit()
        
    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Closing Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred while closing position {position.position_id}: {e}")


def check_take_profit(trailing, take_profit, profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected profit
    profit_loss should be > 0
    take_profit should be > 0
    """
    # if profit_loss < 0 it means there is no profit so return False
    if trailing or profit_loss <= 0:
        return False
    if profit_loss >= take_profit:
        return True
    return False


def check_stop_loss(trailing, stop_loss, profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected loss
    """
    # if profit_loss > 0 it means there is no loss so return False
    if trailing or profit_loss > 0:
        return False

    if profit_loss <= -stop_loss:
        return True
    return False


def check_trailing_stop_loss(trailing, stop_loss, max_profit_loss, current_profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected trailing loss
    """
    # return if trailing is false or stop_loss value is None or zero
    if not trailing or stop_loss == 0:
        return False

    difference = max_profit_loss - current_profit_loss

    if difference >= stop_loss:
        return True
    return False


def should_close_position(profit_loss, position) -> bool:
    """
     This function should run for OPEN or ADJUST_PROCESSING positions.
     So check before it.
    """
    try:
        #Cumulatives are set in create_transaction , all set, need to check in DB
        take_profit = position.cumulative_take_profit
        stop_loss = position.cumulative_stop_loss        
        max_profit = position.max_profit_loss
        trailing = position.trailing

        close_result = any([
            check_trailing_stop_loss(trailing, stop_loss, max_profit, profit_loss),
            check_stop_loss(trailing, stop_loss, profit_loss),
            check_take_profit(trailing, take_profit, profit_loss)
        ])

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
    opened = any[(
            (position.upward == 0 and current_price <= position.entry_price),
            (position.upward == 1 and current_price >= position.entry_price)
    )]
    

    
    if opened:
        open_position(position, current_price)


def check_open_position(db, position):
    """
    For Open Position to be Closed
    """
    # get values from taoshi platform
    redis_array = get_taoshi_values(
        position.trader_id,
        position.trade_pair,
        position_uuid=position.uuid,
        challenge=position.source
    )
    
    redis_position = RedisPosition.from_redis_array(redis_array)
    
    
    if redis_position.price == 0:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Checking Open Position {position.trader_id}-{position.trade_pair}-{position.order_id} - Price is Zero in Redis Queue",
            queue_name=ERROR_QUEUE_NAME
        )
        return False
     
    print(f"Comparing Position Core Logic:{position.uuid} - profit:{redis_position.profit_loss} SL-{position.cumulative_stop_loss} TP-{position.cumulative_take_profit}")

    if should_close_position(redis_position.profit_loss, position):
        logger.info(f"Position should be closed: {position.position_id}: {position.trader_id}: {position.trade_pair}")
        close_position(db, position, redis_position)
        return True


def monitor_position(db, position):
    """
    Monitor a single position

    if status is OPEN then check if it meets the criteria to CLOSE the position
    if status is PENDING then check if it meets the criteria to OPEN the position
    """
   
    try:
        logger.error(f"Current Pair: {position.trader_id}-{position.trade_pair}")
        # ---------------------------- OPENED POSITION ---------------------------------
        if position.status in [Status.open , Status.adjust_processing]:
            return check_open_position(db , position)

        # ---------------------------- PENDING POSITION --------------------------------
        
        if position.status in [Status.pending]:
            current_price = get_live_price(position.trade_pair)
            if not current_price:
                return
            print(f"Processing Pending Position: UUID:{position.uuid} trade-pair:{position.trade_pair} current-price:{current_price}")
            # if it is not a trailing pending position
            
            check_pending_position(position, current_price)
            # else:  # trailing pending position
            #     position = update_position_prices(db, position, current_price)
            #     check_pending_trailing_position(position, current_price)

    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Monitoring Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while monitoring position {position.position_id}: {e}")


def get_monitored_positions(db):
    try:
        logger.info("Fetching monitored positions from database")
        # Use joinedload to prevent N+1 queries
        result = db.execute(
            select(Transaction)
            .where(
                or_(
                    Transaction.status.in_([Status.open, Status.pending, Status.adjust_processing]),
                    and_(
                        Transaction.take_profit.isnot(None),
                        Transaction.take_profit != 0
                    ),
                    and_(
                        Transaction.stop_loss.isnot(None),
                        Transaction.stop_loss != 0
                    )
                )
            )
        )
        positions = result.scalars().unique().all()
        return positions
    except Exception as e:
        push_to_redis_queue(data=f"**Monitor Positions** Database Error - {e}", queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred while fetching monitored positions: {e}")
        return []


def monitor_positions_sync():
    """
    loop through all the positions and monitor them one by one
    """
 
    try:
        logger.info("Starting monitor_positions_sync")

        with TaskSessionLocal_() as db:
            for position in get_monitored_positions(db):

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
