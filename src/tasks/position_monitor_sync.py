import logging
from datetime import datetime
import asyncio
from sqlalchemy.future import select
from sqlalchemy.sql import or_, and_, text
from typing import List
from sqlalchemy.ext.asyncio import  create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction , Status
from src.services.fee_service import get_taoshi_values
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import get_live_price, push_to_redis_queue
from src.utils.websocket_manager import websocket_manager
from src.schemas.redis_position import RedisPosition
from src.services.trade_service import close_transaction_sync, update_transaction_sync
from src.services.notification_service import NotificationService
from src.schemas.notification import NotificationCreate
from src.services.user_service import get_firebase_user_by_trader_id
from src.config import DATABASE_URL

logger = logging.getLogger(__name__)


def open_position(db, position, current_price, entry_price):
   
    try:
        
        asyncio.run( websocket_manager.submit_trade(position.trader_id, position.trade_pair, position.order_type,
                                           position.leverage))
        
        #Creating a position immediately with status PROCESSING
        update_transaction_sync(db, position.order_id, position.trader_id, entry_price= current_price,old_status=position.status
                                , status=Status.processing)

        logger.info(f"Save notification called for  redis profit_loss: id : {position.order_id}  redis entry price: {current_price} , position entry price {entry_price} - upward {position.upward}")
        save_notification(db, position , f" {position.trader_id} - {position.trade_pair} Opened @ market: {current_price}, limit: {entry_price} - upward: {position.upward}"  )

    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Opening Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while opening position {position.position_id}: {e}")


def close_position( db , position : Transaction, redis_position : RedisPosition):

    try:

        asyncio.run( websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
 
        #Closing a position immediately with status CLOSE_PROCESSING
        close_transaction_sync(db, position.order_id, position.trader_id, redis_position.price, profit_loss=redis_position.profit_loss,
                                old_status=position.status, profit_loss_without_fee=redis_position.profit_loss_without_fee,
                                taoshi_profit_loss=redis_position.taoshi_profit_loss, status=Status.close,
                                taoshi_profit_loss_without_fee=redis_position.taoshi_profit_loss_without_fee, order_level=redis_position.len_order,
                                average_entry_price=redis_position.average_entry_price)

        save_notification(db, position , f"{position.trader_id} - {position.trade_pair} Closed @ pl:{ round(redis_position.profit_loss, 6)} , position SL {position.stop_loss} - TP {position.take_profit}"  )
                
    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Closing Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred while closing position {position.position_id}: {e}")



def save_notification(db, position : Transaction , message :str):
    
    try:
        user =  get_firebase_user_by_trader_id(db , position.trader_id)
     
    
        NotificationService.create_notification(db, NotificationCreate( 
            trader_id= position.trader_id,
            trader_pair = position.trade_pair,
            message = message ,
            type = 'position-monitor-sync-challenge'
            ) , user = user )

    except Exception as e:
        print(f"An error occurred while saving notification :{e} {message}")




def check_take_profit(trailing, take_profit, profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected profit
    profit_loss should be > 0
    take_profit should be > 0
    """
    # if profit_loss < 0 it means there is no profit so return False
    if trailing or profit_loss <= 0 or take_profit <= 0:
        return False
    if profit_loss >= take_profit:
        return True
    return False


def check_stop_loss(trailing, stop_loss, profit_loss) -> bool:
    """
    Position should be closed if it reaches the expected loss
    """
    # if profit_loss > 0 it means there is no loss so return False
    if trailing or profit_loss > 0 or stop_loss <= 0:
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


def check_pending_trailing_position(db , position, current_price):
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
        open_position(db, position, current_price, entry_price=True)

def check_pending_position(db, position, current_price):
    """
    For Pending Position to be Opened
    """
    opened = any([  
        (position.upward == 0 and current_price >= position.entry_price),
        (position.upward == 1 and current_price <= position.entry_price)
    ])
    

    
    if opened:
        open_position(db, position, current_price , position.entry_price )

def check_open_position(db, position):
    """
    For Open Position to be Closed
    """
    # get values from taoshi platform
    redis_array = get_taoshi_values(
        position.trader_id,
        position.trade_pair,
        position_uuid=position.uuid,
        challenge=position.source,
        closed=True
    )
    logger.info(redis_array)
    redis_position = RedisPosition.from_redis_array(redis_array)
    
    #If position doesnt exits in redis (taoshi) it can mean anything, so we shouldnt process
    if redis_position.price == 0 or redis_position.closed:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Checking Open Position {position.trader_id}-{position.trade_pair}-{position.order_id} - Price is Zero in Redis Queue or Trades in Queue for pair are stale and closed",
            queue_name=ERROR_QUEUE_NAME
        )
        return False
     
    logger.info(f"Comparing Position Core Logic:{position.uuid} - profit:{redis_position.profit_loss} SL-{position.cumulative_stop_loss} TP-{position.cumulative_take_profit}")

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

        # ---------------------------- OPENED POSITION ---------------------------------
        if position.status in [Status.open , Status.adjust_processing]:
            logger.info(f"Processing Opened Position: trade-pair:{position.trade_pair} {position.trader_id}")
            return check_open_position(db , position)

        # ---------------------------- PENDING POSITION --------------------------------
        
        if position.status in [Status.pending]:
            current_price = get_live_price(position.trade_pair)
            if not current_price:
                return
            logger.info(f"Processing Pending Position: Trader:{position.trader_id} trade-pair:{position.trade_pair} current-price:{current_price} ask-price {position.entry_price}")
            # if it is not a trailing pending position
            
            return check_pending_position(db, position, current_price)
            # else:  # trailing pending position
            #     position = update_position_prices(db, position, current_price)
            #     check_pending_trailing_position(position, current_price)

    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Monitoring Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while monitoring position {position.position_id} in SL/TP task: {e}")


def get_monitored_positions(db: Session) -> List[Transaction]:
    """Get all monitored positions with proper async handling"""
    try:
        logger.info("Fetching monitored positions from database")
         # Base query for all statuses
        base_query = select(Transaction)
        
        # Combine conditions using OR for different status types
        status_conditions = or_(
      
                and_(
                    Transaction.status.in_([Status.open, Status.adjust_processing]),
                    
                    or_(    
                        and_(    Transaction.cumulative_take_profit.isnot(None),
                                Transaction.cumulative_take_profit != 0),
                        
                        and_(
                                Transaction.cumulative_stop_loss.isnot(None),
                                Transaction.cumulative_stop_loss != 0),
                        )
                  
                ),
                # For PENDING, no additional conditions needed
                Transaction.status == Status.pending
            )
        
        # Apply the combined conditions
        query = base_query.where(status_conditions)
        
        result = db.execute(query)
        positions = result.scalars().unique().all()
        return positions
            
    except Exception as e:
        logger.error(f"An error occurred while fetching new bug fix monitored positions: {e}")
        push_to_redis_queue(
            data=f"**Monitor Positions** Database Error - {e}", 
            queue_name=ERROR_QUEUE_NAME
        )
        return []


def monitor_positions_sync():
    """Monitor positions with proper async session handling"""
    try:
        logger.info("Starting monitor_positions_sync")
        
        # First get all positions in one transaction
        with TaskSessionLocal_() as db:
            positions =  get_monitored_positions(db)
            
            # Process each position with a new session
            for position in positions:
                logger.info(f"Processing position {position.trader_id} {position.position_id}: {position.status}: {position.take_profit} {position.stop_loss} ")
                monitor_position(db, position)
                    
        logger.info("Finished monitor_positions_sync")
    except Exception as e:
        logger.error(f"An error occurred in monitor_positions_sync: {e}")
        push_to_redis_queue(
            data=f"**Monitor Positions** Celery Task - {e}", 
            queue_name=ERROR_QUEUE_NAME
        )


@celery_app.task(name='src.tasks.position_monitor_sync.monitor_positions')
def monitor_positions():
    
    logger.info("Starting monitor_positions task")
    try:
        monitor_positions_sync() 
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise