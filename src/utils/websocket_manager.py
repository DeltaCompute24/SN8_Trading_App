import asyncio
import json

import aiohttp
import websockets
from throttler import Throttler

from src.config import SIGNAL_API_KEY, SIGNAL_API_BASE_URL, POLYGON_WEBSOCKET
from src.utils.logging import setup_logging
from src.utils.redis_manager import set_live_prices

# Set the rate limit: max 10 requests per second
throttler = Throttler(rate_limit=10, period=1.0)

logger = setup_logging()


class WebSocketManager:
    def __init__(self):
        self.websocket = None
        self.reconnect_interval = 5  # seconds
        self._recv_lock = asyncio.Lock()  # Lock to ensure single access to recv

    async def connect(self):
        try:
            self.websocket = await websockets.connect(POLYGON_WEBSOCKET)
            await self.receive_and_log()
        except Exception as e:
            logger.error(f"Testnet Connection Failed: {e}. Retrying in {self.reconnect_interval} seconds...")
            await asyncio.sleep(self.reconnect_interval)

    async def receive_and_log(self):
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                set_live_prices(key="0", value=data.get("data"))
            except Exception as e:
                print("Testnet WebSocket Connection Closed. Reconnecting...")
                await self.close()
                await asyncio.sleep(self.reconnect_interval)
                await self.connect()

    async def submit_trade(self, trader_id, trade_pair, order_type, leverage):
        signal_api_url = SIGNAL_API_BASE_URL.format(id=trader_id)
        params = {
            "api_key": SIGNAL_API_KEY,
            "trade_pair": trade_pair,
            "order_type": order_type,
            "leverage": leverage
        }
        print("SIGNAL API REQUEST", params)
        async with aiohttp.ClientSession() as session:
            async with throttler:
                async with session.post(signal_api_url, json=params) as response:
                    print("SIGNAL API RESPONSE", response)
                    response_text = await response.text()
                    print("SIGNAL API RESPONSE TEXT", response_text)
                    logger.info(f"Submit trade signal sent. Response: {response_text}")
                    return response.status == 200

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None


websocket_manager = WebSocketManager()
