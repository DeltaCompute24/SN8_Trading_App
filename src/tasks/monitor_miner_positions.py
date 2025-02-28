import logging
from datetime import datetime, timedelta
from collections import defaultdict
from heapq import heappush, heappop
from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.services.api_service import call_main_net
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import set_hash_data, set_hash_value, push_to_redis_queue, delete_hash_value
from src.validations.time_validations import convert_timestamp_to_datetime
from src.services.trade_service import get_user_hotkey_map
from src.schemas.trader import HotKeyMap , UserDetails
from src.utils.constants import TOP_TRADERS
logger = logging.getLogger(__name__)
import json



def update_position_in_redis(position , trader_id, trade_pair , hot_key):
         
        key = f"{trade_pair}-{trader_id}"
        current_time = datetime.utcnow() - timedelta(hours=1)
        close_time = convert_timestamp_to_datetime(position["close_ms"])

        if position["is_closed_position"] and current_time > close_time:
            delete_hash_value(key)
            return

        price, taoshi_profit_loss, taoshi_profit_loss_without_fee = position["orders"][-1]["price"], \
            position["return_at_close"], position["current_return"]
        profit_loss = (taoshi_profit_loss * 100) - 100
        profit_loss_without_fee = (taoshi_profit_loss_without_fee * 100) - 100
        position_uuid = position["position_uuid"]
        
        

        # Include additional data in the value
        value = [
            str(datetime.now()), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
            taoshi_profit_loss_without_fee, position_uuid, hot_key, len(position["orders"]),
            position["average_entry_price"], position["is_closed_position"]
        ]
        
        set_hash_value(key=key, value=value)
        
def add_top_trades_and_returns(trade_pair_counter : dict, k : int, trader_data : UserDetails , all_time_returns : int):
        
        top_k_pairs = trade_pair_counter
        if k < len(trade_pair_counter):
            
            store = []
            top_k_pairs = {}
            for key, value in trade_pair_counter.items():
                heappush(store, (-value, key))

            for _ in range(0,k):
                pair = heappop(store)
                top_k_pairs[pair[1]] = -pair[0]
                    
        trader_data.top_trader_pairs  = top_k_pairs
        trader_data.all_time_returns = all_time_returns
        

def populate_redis_positions(data, _type="Mainnet", top_k = 3):
      
    with TaskSessionLocal_() as db:
        challenges : HotKeyMap = get_user_hotkey_map(db)
        challenges = challenges.data
        
        logger.info('Challenges', challenges)
        
        trade_pair_counter = defaultdict(int)
                
        for hot_key, content in data.items():
            if not content:
                continue
            
            positions = content.get('positions')
            all_time_returns = content.get('all_time_returns')
            trader_data = UserDetails ( 
                                    name = '',
                                    email = '',
                                    trader_id = None,
                                    user_id = None,
                                    id = None
                            )
            for position in positions:
                trade_pair = position.get("trade_pair", [])[0]

                if hot_key in challenges:
                    trader_data : UserDetails = challenges[hot_key]
                    update_position_in_redis(position,  trader_data.trader_id, trade_pair, hot_key)
                    
                
                trade_pair_counter[trade_pair] += 1  # Increment the count for the currency pair
            
            logger.info(f'Counter {hot_key} {trade_pair_counter}')

            
            if _type == 'Mainnet':
                if not challenges.get(hot_key):
                    challenges[hot_key] = trader_data
                
                    
                add_top_trades_and_returns(trade_pair_counter, top_k, trader_data, all_time_returns )       
                
                logger.info(f'Top Trades {trader_data}')

                # Convert the model data to JSON strings before storing in Redis

                serialized_data = {k: json.dumps(v.model_dump()) for k, v in challenges.items() if v.top_trader_pairs}
                  
                set_hash_data(TOP_TRADERS, data=serialized_data)
                trade_pair_counter = defaultdict(int)
            


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

