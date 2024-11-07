import asyncio
import json
from typing import List

import aiohttp
import websockets
from throttler import Throttler

from src.config import POLYGON_API_KEY, SIGNAL_API_KEY, SIGNAL_API_BASE_URL
from src.utils.constants import forex_pairs, crypto_pairs, indices_pairs
from src.utils.logging import setup_logging
from src.utils.redis_manager import set_live_price

# Set the rate limit: max 10 requests per second
throttler = Throttler(rate_limit=10, period=1.0)
# Use the REDIS_URL from environment variables

logger = setup_logging()


class WebSocketManager:
    def __init__(self, asset_type):
        self.websocket = None
        self.asset_type = asset_type
        self.trade_pair = None
        self.reconnect_interval = 5  # seconds
        self._recv_lock = asyncio.Lock()  # Lock to ensure single access to recv
        self.trade_pairs = []

    async def connect(self):
        self.websocket_url = f"wss://socket.polygon.io/{self.asset_type}"
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            await self.authenticate()
            return self.websocket
        except Exception as e:
            logger.error(f"Connection failed: {e}. Retrying in {self.reconnect_interval} seconds...")
            await asyncio.sleep(self.reconnect_interval)

    async def listen_for_prices_multiple(self):
        print(self.trade_pairs, self.asset_type, self.websocket)
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
                    trade_pair = item.pop("pair", None)
                    item.pop("ev", None)

                    try:
                        trade_pair = trade_pair.replace("-", "").replace("/", "")
                        set_live_price(trade_pair, item)
                    except Exception as e:
                        print(f"Failed to add to Redis: {e}")
            except websockets.ConnectionClosed:
                print("WebSocket connection closed. Reconnecting...")
                await self.connect()
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

    def format_pair_updated(self, pair):
        prefix = "CAS." if self.asset_type == "forex" else "XAS."
        separator = '/' if self.asset_type == "forex" else '-'

        if pair in ["SPX", "DJI", "FTSE", "GDAXI"]:
            formatted_pair = pair
        else:
            formatted_pair = f"{pair[:-3]}{separator}{pair[-3:]}"
        return f"{prefix}{formatted_pair}"


class ForexWebSocketManager(WebSocketManager):
    def __init__(self):
        super().__init__("forex")
        self.trade_pairs = [self.format_pair_updated(pair) for pair in forex_pairs]

    def format_pair_updated(self, pair):
        return f"CAS.{pair[:-3]}/{pair[-3:]}"


class CryptoWebSocketManager(WebSocketManager):
    def __init__(self):
        super().__init__("crypto")
        self.trade_pairs = [self.format_pair_updated(pair) for pair in crypto_pairs]

    def format_pair_updated(self, pair):
        return f"XAS.{pair[:-3]}-{pair[-3:]}"


class IndicesWebSocketManager(WebSocketManager):
    def __init__(self):
        super().__init__("indices")
        self.trade_pairs = [self.format_pair_updated(pair) for pair in indices_pairs]

    def format_pair_updated(self, pair):
        prefix = "A."
        if pair in ["SPX", "DJI", "FTSE", "GDAXI", "VIX", "NDX"]:
            formatted_pair = pair
        else:
            formatted_pair = f"{pair[:-3]}-{pair[-3:]}"
        return f"{prefix}{formatted_pair}"


websocket_manager = WebSocketManager("forex")

forex_websocket_manager = ForexWebSocketManager()
crypto_websocket_manager = CryptoWebSocketManager()
# indices_websocket_manager = IndicesWebSocketManager()
