import logging
import asyncio
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction , Status, OrderType 
from src.services.fee_service import get_taoshi_values
from src.utils.constants import ERROR_QUEUE_NAME, STOP_LOSS_POSITIONS_TABLE
from src.utils.redis_manager import set_hash_value, push_to_redis_queue , get_bid_ask_price
from src.utils.websocket_manager import websocket_manager
from src.schemas.redis_position import RedisPosition 
from src.services.trade_service import get_SLTP_pending_positions , close_transaction_sync, update_transaction_sync , update_transaction_sync_gen
from src.services.notification_service import NotificationService
from src.schemas.transaction import TransactionUpdateDatabaseGen

logger = logging.getLogger(__name__)


def open_position(db, position : Transaction, current_price : float):
   
    try:
        
        asyncio.run( websocket_manager.submit_trade(position.trader_id, position.trade_pair, position.order_type,
                                           position.leverage))
        
        #Creating a position immediately with status PROCESSING
        update_transaction_sync(db, position.order_id, position.trader_id, entry_price= current_price,old_status=position.status
                                , status=Status.processing)

        logger.info(f"Save notification called for  redis profit_loss: id : {position.order_id}  redis entry price: {current_price} , position entry price {position.entry_price} - upward {position.upward}")
        NotificationService.save_notification(db, position , f" {position.trader_id} - {position.trade_pair} Opened @ market: {current_price}, limit: {position.entry_price} - Order: {position.order_type}"  )

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

        NotificationService.save_notification(db, position , f"{position.trader_id} - {position.trade_pair} Closed @ pl:{ round(redis_position.profit_loss, 6)} , position SL {position.stop_loss} - TP {position.take_profit}"  )
                
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


def update_stop_loss(db , new_trailing_stop_loss : float , position : Transaction , new_entry_price : float):
        print(f"{new_trailing_stop_loss} {position.entry_price} {new_entry_price}")
        new_trailing_stop_loss_percent = (new_trailing_stop_loss / position.entry_price) * 100
        position.stop_loss = new_trailing_stop_loss_percent
        position.cumulative_stop_loss =  position.stop_loss
        
        set_hash_value(f'{position.trade_pair}-{position.trader_id}',new_trailing_stop_loss_percent ,STOP_LOSS_POSITIONS_TABLE  )
        update_transaction_gen(db , position , { "stop_loss" : new_trailing_stop_loss_percent , 
                                                "cumulative_stop_loss" : new_trailing_stop_loss_percent,
                                                "entry_price" : new_entry_price
                                                })


def update_trailing_stop_loss(db , position : Transaction) -> bool:
    """
    Position should be closed if it reaches the expected trailing loss
    """
    
    quotes = get_bid_ask_price(position.trade_pair)
    if quotes.ap == 0.0 or quotes.bp == 0.0 : return
    logger.info(f"Trade-Pair {position.trade_pair} bp {quotes.ap} ap: {quotes.bp}  ")
    
    if position.trailing and position.stop_loss > 0:
        buy_price = quotes.bp
        sell_price = quotes.ap  
        
        if position.order_type == OrderType.buy:
            
            if buy_price > position.entry_price:
                #Stop Loss Moves Up
                new_trailing_stop_loss =  (buy_price * (position.stop_loss / 100)) 
                logger.info(f" BUY - {buy_price} {position.entry_price} - New Trailing SL {new_trailing_stop_loss}   ")
                update_stop_loss(db , new_trailing_stop_loss , position, buy_price)
                 
        
        elif position.order_type == OrderType.sell:
            
            if sell_price < position.entry_price:
                #Stop Loss moves down
                new_trailing_stop_loss =  (sell_price * (position.stop_loss / 100)) 
                logger.info(f" SELL  - {sell_price} {position.entry_price}- New Trailing SL {new_trailing_stop_loss}   ")
                update_stop_loss(db ,new_trailing_stop_loss , position , sell_price)

                
    

def should_close_position(redis_position : RedisPosition , position : Transaction) -> bool:
    """
     This function should run for OPEN or ADJUST_PROCESSING positions.
     So check before it.
    """
    try:
        #Cumulatives are set in create_transaction , all set, need to check in DB
        take_profit = position.cumulative_take_profit
        stop_loss = position.cumulative_stop_loss        
        trailing = position.trailing
        
       

        close_result = any([
            check_stop_loss(trailing, stop_loss, redis_position.profit_loss),
            check_take_profit(trailing, take_profit, redis_position.profit_loss)
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




def update_transaction_gen(db, position: int, update_values: dict):
    """
    Update transaction with provided values using dictionary unpacking
    """
    print(update_values)
    update_transaction_sync_gen(
        db, 
        position, 
        TransactionUpdateDatabaseGen(**update_values)
    )


def update_trailing_limit(db, position : Transaction , buy_price : float , sell_price : float):
    
    if position.order_type == OrderType.buy:
        
        #Market Moves in favorable direction
        if buy_price < position.initial_price:
            #Trailing Percent Moves Up
            entry_price_decrement = (buy_price * position.limit_order)
            entry_price_decrement_percent = (entry_price_decrement / position.initial_price)
            new_entry_price = buy_price -  entry_price_decrement
            update_transaction_gen(db , position , { "entry_price" : new_entry_price , "initial_price" : buy_price , 'limit_order' : entry_price_decrement_percent })
                
    
    elif position.order_type == OrderType.sell:
        
        #Market Moves in favorable direction
        if sell_price > position.initial_price:
            #Stop Loss moves down
            entry_price_increment = (sell_price * position.limit_order)
            entry_price_increment_percent = (entry_price_increment / position.initial_price)
            new_entry_price = sell_price  +  entry_price_increment
            update_transaction_gen(db , position , { "entry_price" : new_entry_price , "initial_price" : sell_price,  "limit_order" : entry_price_increment_percent  })
    
    

def check_pending_position(db, position : Transaction , buy_price : float, sell_price : float):
    """
    For Pending Position to be Opened
    """
    
    opened = any([  
        (position.order_type == OrderType.buy and buy_price <= position.entry_price),
        (position.order_type == OrderType.sell and sell_price >= position.entry_price)
    ])
    
    logger.info(f"Processing Pending Position:{position.trader_id} {position.trade_pair} order:{position.order_type} quote-price ap {sell_price} bp {buy_price}")

    
    if opened:
        open_position(db, position, buy_price if position.order_type == OrderType.buy else sell_price )

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
    
    redis_position = RedisPosition.from_redis_array(redis_array)
    
    #If position doesnt exits in redis (taoshi) it can mean anything, so we shouldnt process
    if redis_position.price == 0 or redis_position.closed:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Checking Open Position {position.trader_id}-{position.trade_pair}-{position.order_id} - Price is Zero in Redis Queue or Trades in Queue for pair are stale and closed",
            queue_name=ERROR_QUEUE_NAME
        )
        return False
     
    logger.info(f"Comparing Position Core Logic:{position.uuid} - profit:{redis_position.profit_loss} SL-{position.cumulative_stop_loss} TP-{position.cumulative_take_profit}")

    if should_close_position(redis_position , position):
        logger.info(f"Position should be closed: {position.position_id}: {position.trader_id}: {position.trade_pair}")
        close_position(db, position, redis_position)
        return True


def monitor_position(db, position : Transaction):
    """
    Monitor a single position

    if status is OPEN then check if it meets the criteria to CLOSE the position
    if status is PENDING then check if it meets the criteria to OPEN the position
    """
   
    try:

        # ---------------------------- OPENED POSITION ---------------------------------
        if position.status in [Status.open , Status.adjust_processing]:
            logger.info(f"Processing Opened Position: trade-pair:{position.trade_pair} {position.trader_id}")
            if position.trailing and position.stop_loss != 0:
                update_trailing_stop_loss(db ,position)
            return check_open_position(db , position)

        # ---------------------------- PENDING POSITION --------------------------------
        
        if position.status in [Status.pending]:
            quotes = get_bid_ask_price(position.trade_pair)
            if quotes.ap == 0.0 or quotes.bp == 0.0 : 
                logger.error("BUY SELL in Redis is 0, cannot process pending orders")
                return
            if position.trailing and position.limit_order and position.initial_price:
                logger.error("UPDATE TRAILING LIMIT CALLED")

                # update_trailing_limit(db, position , quotes.bp , quotes.ap)
            return check_pending_position(db, position , quotes.bp , quotes.ap)


    except Exception as e:
        push_to_redis_queue(
            data=f"**Monitor Positions** While Monitoring Position {position.trader_id}-{position.trade_pair}-{position.order_id} - {e}",
            queue_name=ERROR_QUEUE_NAME
        )
        logger.error(f"An error occurred while monitoring position {position.position_id} in SL/TP task: {e}")



def monitor_positions_sync():
    """Monitor positions with proper async session handling"""

    logger.info("Starting monitor_positions_sync")
    
    # First get all positions in one transaction
    with TaskSessionLocal_() as db:
        positions =  get_SLTP_pending_positions(db)
        
        # Process each position with a new session
        for position in positions:
            logger.info(f"Processing position {position.trader_id} {position.position_id}: {position.status}: {position.take_profit} {position.stop_loss} ")
            monitor_position(db, position)
                
    logger.info("Finished monitor_positions_sync")



@celery_app.task(name='src.tasks.position_monitor_sync.monitor_positions')
def monitor_positions():
    logger.info("Starting monitor_positions task")
    monitor_positions_sync() 
   