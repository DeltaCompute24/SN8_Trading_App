import asyncio
import json
from typing import List
import aiohttp
import redis
from redis import asyncio as aioredis

import websockets
from throttler import Throttler
from src.utils.constants import forex_pairs
from src.config import POLYGON_API_KEY, SIGNAL_API_KEY, SIGNAL_API_BASE_URL
from src.utils.logging import setup_logging
import os



# Set the rate limit: max 10 requests per second
throttler = Throttler(rate_limit=10, period=1.0)
# Use the REDIS_URL from environment variables
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
redis_client = aioredis.from_url(redis_url, decode_responses=True)
logger = setup_logging()


class WebSocketManager:
    def __init__(self):
        
        self.websocket = None
        self.asset_type = None
        self.trade_pair = None
        self.current_prices = {}  # Store current prices
        self.reconnect_interval = 5  # seconds
        self._recv_lock = asyncio.Lock()  # Lock to ensure single access to recv
        self.trade_pairs =  [self.format_pair_updated(pair['value']) for pair in forex_pairs]
    
    async def connect(self, asset_type):
        self.asset_type = asset_type
        self.websocket_url = f"wss://socket.polygon.io/{self.asset_type}"
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            await self.authenticate()
            return self.websocket
        except Exception as e:
            logger.error(f"Connection failed: {e}. Retrying in {self.reconnect_interval} seconds...")
            await asyncio.sleep(self.reconnect_interval)


    async def listen_for_prices_multiple(self):
        asset_type = "forex"
        try:
            logger.info("Starting to listen for prices multiple...")
            await self.connect(asset_type)
            await self.subscribe_multiple(self.trade_pairs)
            await self.receive_and_log()
        except Exception as e:
            print(f"WebSocket error: {e}. Reconnecting...")
            await asyncio.sleep(5)
                
                
    async def authenticate(self):
        logger.info("Authenticating WebSocket connection...")
        async with throttler:
            await self.websocket.send(json.dumps({"action": "auth", "params": POLYGON_API_KEY}))
        response = await self.websocket.recv()
        logger.info(f"Authentication response: {response}")

        data = json.loads(response)
        if isinstance(data, list) and any(item.get("status") == "connected" for item in data):
            logger.info("WebSocket authenticated successfully")
        else:
            raise Exception("WebSocket authentication failed")

    async def subscribe_multiple(self, trade_pairs: List[str]):
        subscribe_message= {
            "action": "subscribe",
            "params": ",".join(trade_pairs)
        }
        async with throttler:
            await self.websocket.send(json.dumps(subscribe_message))
        response = await self.websocket.recv()
        logger.info(f"Subscription response: {response}")

    async def receive_and_log(self):
        print("Displaying prices for all trade pairs...")
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
  
                for item in data:
                   
                    if item.get("ev") != "CAS": 
                        print(f"Skipping non-CAS event: {item}")
                        continue
                    trade_pair = item.get("pair")
                    item.pop("ev", None)
                   
                    try:
                        serialized_item = json.dumps(item)
                        await redis_client.hset('live_prices', trade_pair, serialized_item)
                       
                    except Exception as e:
                        print(f"Failed to add to Redis: {e}")
            except websockets.ConnectionClosed:
                print("WebSocket connection closed. Reconnecting...")
                await self.connect("forex")
                await self.subscribe_multiple(self.trade_pairs)
            except Exception as e:
                print(f"Unexpected error in receive_and_log: {e}")
    
    async def unsubscribe_multiple(self):
        unsubscribe_message = {
            "action": "unsubscribe",
            "params": ",".join(self.trade_pairs)
        }
        async with throttler:
            await self.websocket.send(json.dumps(unsubscribe_message))
        response = await self.websocket.recv()
        logger.info(f"Unsubscription response: {response}")
       
    
    async def subscribe(self, trade_pair):
        if not self.websocket or self.websocket.closed:
            raise Exception("WebSocket is not connected")
        self.trade_pair = trade_pair
        logger.info(f"Subscribing to trade pair: {self.trade_pair}")
        params = self.format_pair(trade_pair)
        async with throttler:
            await self.websocket.send(json.dumps({"action": "subscribe", "params": params}))
        response = await self.websocket.recv()
        logger.info(f"Subscription response: {response}")
        return response

    async def unsubscribe(self, trade_pair):
        if self.websocket and self.websocket.open:
            logger.info(f"Unsubscribing from trade pair: {trade_pair}")
            params = self.format_pair(trade_pair)
            async with throttler:
                await self.websocket.send(json.dumps({"action": "unsubscribe", "params": params}))
            response = await self.websocket.recv()
            logger.info(f"Unsubscription response: {response}")
            return response

    async def listen_for_price(self, trade_pair, asset_type):
        logger.info(f"Listening for price updates for {trade_pair}")
        last_log_time = None

        while True:
            async with self._recv_lock:
                async with throttler:
                    try:
                        message = await self.websocket.recv()
                        data = json.loads(message)
                        event_code = self.get_event_code(asset_type)
                        if isinstance(data, list) and len(data) > 0 and data[0].get('ev') == event_code:
                            pair = data[0]['pair']
                            trade_pair = pair.replace("-", "").replace("/", "")
                            price = float(data[0]['c'])
                            self.current_prices[trade_pair] = price
                            await redis_client.hset('current_prices', trade_pair, data[0]['c'])
                            current_time = asyncio.get_event_loop().time()
                            if last_log_time is None or current_time - last_log_time >= 1:
                                logger.info(f"Current price for {trade_pair}: {price}")
                                # self.current_prices[trade_pair] = price
                                # await redis_client.hset('current_prices', trade_pair, data[0]['c'])
                                last_log_time = current_time
                            await asyncio.sleep(1)  # Adjust sleep duration as necessary
                    except websockets.ConnectionClosedError as e:
                        logger.error(f"Connection closed: {e}. Reconnecting...")
                        await self.connect(asset_type)
                        await self.subscribe(trade_pair)

    async def listen_for_initial_price(self):
        logger.info(f"Listening for price updates for {self.trade_pair}")
        log_count = 0
        last_log_time = None
        price = None

        while log_count < 1:
            async with self._recv_lock:
                async with throttler:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    event_code = self.get_event_code(self.asset_type)
                    if isinstance(data, list) and len(data) > 0 and data[0].get('ev') == event_code:
                        pair = data[0]['pair']
                        price = float(data[0]['c'])
                        current_time = asyncio.get_event_loop().time()
                        if last_log_time is None or current_time - last_log_time >= 1:
                            logger.info(f"Current price for {self.trade_pair}: {price}")
                            last_log_time = current_time
                            log_count += 1
                        await asyncio.sleep(1)  # Adjust sleep duration as necessary

        logger.info("Closing WebSocket connection after logging price.")
        await self.websocket.close()
        return price

    async def submit_trade(self, trader_id, trade_pair, order_type, leverage):
        signal_api_url = SIGNAL_API_BASE_URL.format(id=trader_id)
        params = {
            "api_key": SIGNAL_API_KEY,
            "trade_pair": trade_pair,
            "order_type": order_type,
            "leverage": leverage
        }
        async with aiohttp.ClientSession() as session:
            async with throttler:
                async with session.post(signal_api_url, json=params) as response:
                    response_text = await response.text()
                    logger.info(f"Submit trade signal sent. Response: {response_text}")
                    return response.status == 200

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    def get_event_code(self, asset_type):
        return "CAS" if asset_type == "forex" else "XAS"

    # def format_pair(self, pair):
    #     separator = '/' if self.asset_type == "forex" else '-'
    #     base = pair[:-3]
    #     quote = pair[-3:]
    #     return f"{base}{separator}{quote}"

    def format_pair(self, pair):
        ev = "CAS" if self.asset_type == "forex" else "XAS"
        separator = '/' if self.asset_type == "forex" else '-'

        if pair in ["SPX", "DJI", "FTSE", "GDAXI"]:
            formatted_pair = pair
        else:
            formatted_pair = f"{pair[:-3]}{separator}{pair[-3:]}"
        return f"{ev}.{formatted_pair}"

    
    def format_pair_updated(self, pair , asset_type = "forex"):
        prefix = "CAS." if asset_type == "forex" else "XAS."

        if pair in ["SPX", "DJI", "FTSE", "GDAXI"]:
            formatted_pair = pair
        else:
            formatted_pair = f"{pair[:-3]}-{pair[-3:]}"
        return f"{prefix}{formatted_pair}"

websocket_manager = WebSocketManager()
