import asyncio
import json
from typing import List

import websockets
from throttler import Throttler

from src.config import POLYGON_API_KEY
from src.utils.constants import forex_pairs, crypto_pairs, indices_pairs, stocks_pairs
from src.utils.logging import setup_logging
from src.utils.redis_manager import set_live_price

# Set the rate limit: max 10 requests per second
throttler = Throttler(rate_limit=10, period=1.0)

logger = setup_logging()


class WebSocketManager:
    def __init__(self, asset_type, pair_key):
        self.websocket = None
        self.asset_type = asset_type
        self.reconnect_interval = 5  # seconds
        self.trade_pairs = []
        self.pair_key = pair_key

    async def connect(self):
        websocket_url = f"wss://socket.polygon.io/{self.asset_type}"
        try:
            self.websocket = await websockets.connect(websocket_url)
            await self.authenticate()
            return self.websocket
        except Exception as e:
            logger.error(f"Connection failed: {e}. Retrying in {self.reconnect_interval} seconds...")
            await asyncio.sleep(self.reconnect_interval)

    async def listen_for_prices_multiple(self):
        print(self.trade_pairs, self.asset_type, self.websocket)
        print("Listening for prices multiple inside fubnc   ")
        if not self.trade_pairs or not self.asset_type:
            logger.error(
                "WebSocket, trade pairs, or asset type is not set. Please set them before calling this method.")
            return
        try:
            logger.info(f"Starting to listen for prices multiple {self.asset_type}...")
            await self.connect()
            await self.subscribe_multiple(self.trade_pairs)
            await self.receive_and_log()
        except Exception as e:
            print(f"WebSocket error: {e}. Reconnecting...")
            await asyncio.sleep(5)

    async def authenticate(self):
        logger.info("Authenticating WebSocket connection...")
        async with throttler:
            print("Authenticating WebSocket connection {}")
            await self.websocket.send(json.dumps({"action": "auth", "params": POLYGON_API_KEY}))
        response = await self.websocket.recv()
        logger.info(f"Authentication response: {response}")

        data = json.loads(response)
        if isinstance(data, list) and any(item.get("status") == "connected" for item in data):
            logger.info("WebSocket authenticated successfully")
        else:
            raise Exception("WebSocket authentication failed")

    async def subscribe_multiple(self, trade_pairs: List[str]):
        subscribe_message = {
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

                    if item.get("ev") not in ["CAS", "XAS", "A"]:
                        print(f"Skipping non-CAS event: {item}")
                        continue
                    print(item)
                    trade_pair = item.pop(self.pair_key, None)
                    item.pop("ev", None)

                    try:
                        trade_pair = trade_pair.replace("-", "").replace("/", "") if ("-" in trade_pair or "/" in
                                                                                      trade_pair) else trade_pair
                        set_live_price(trade_pair, item)
                    except Exception as e:
                        print(f"Failed to add to Redis: {e}")
            except Exception as e:
                print("WebSocket connection closed. Reconnecting...")
                await self.close()
                await asyncio.sleep(self.reconnect_interval)
                await self.listen_for_prices_multiple()

    async def unsubscribe_multiple(self):
        unsubscribe_message = {
            "action": "unsubscribe",
            "params": ",".join(self.trade_pairs)
        }
        async with throttler:
            await self.websocket.send(json.dumps(unsubscribe_message))
        response = await self.websocket.recv()
        logger.info(f"Unsubscription response: {response}")

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None


class ForexWebSocketManager(WebSocketManager):
    def __init__(self):
        super().__init__("forex", 'pair')
        self.trade_pairs = [f"CAS.{pair[:-3]}/{pair[-3:]}" for pair in forex_pairs]


class CryptoWebSocketManager(WebSocketManager):
    def __init__(self):
        super().__init__("crypto", 'pair')
        self.trade_pairs = [f"XAS.{pair[:-3]}-{pair[-3:]}" for pair in crypto_pairs]


class IndicesWebSocketManager(WebSocketManager):
    def __init__(self):
        super().__init__("indices", 'pair')
        self.trade_pairs = [f"A.{pair}" for pair in indices_pairs]


class StocksWebSocketManager(WebSocketManager):
    def __init__(self):
        super().__init__("stocks", 'sym')
        self.trade_pairs = [f"A.{pair}" for pair in stocks_pairs]


forex_websocket_manager = ForexWebSocketManager()
crypto_websocket_manager = CryptoWebSocketManager()
stocks_websocket_manager = StocksWebSocketManager()
