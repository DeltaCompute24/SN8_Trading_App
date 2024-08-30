import asyncio
import json

import aiohttp
import redis
import websockets
from throttler import Throttler

from src.config import POLYGON_API_KEY, SIGNAL_API_KEY, SIGNAL_API_BASE_URL
from src.utils.logging import setup_logging

logger = setup_logging()

# Set the rate limit: max 10 requests per second
throttler = Throttler(rate_limit=10, period=1.0)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


class WebSocketManager:
    def __init__(self):
        self.websocket = None
        self.asset_type = None
        self.trade_pair = None
        self.current_prices = {}  # Store current prices
        self.reconnect_interval = 5  # seconds
        self._recv_lock = asyncio.Lock()  # Lock to ensure single access to recv

    async def connect(self, asset_type):
        self.asset_type = asset_type
        self.websocket_url = f"wss://socket.polygon.io/{self.asset_type}"
        while True:
            try:
                self.websocket = await websockets.connect(self.websocket_url)
                await self.authenticate()
                return self.websocket
            except Exception as e:
                logger.error(f"Connection failed: {e}. Retrying in {self.reconnect_interval} seconds...")
                await asyncio.sleep(self.reconnect_interval)

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
                            current_time = asyncio.get_event_loop().time()
                            if last_log_time is None or current_time - last_log_time >= 1:
                                logger.info(f"Current price for {trade_pair}: {price}")
                                self.current_prices[trade_pair] = price
                                await redis_client.hset('current_prices', trade_pair, data[0]['c'])
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


websocket_manager = WebSocketManager()
