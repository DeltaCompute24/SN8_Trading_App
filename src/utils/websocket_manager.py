import asyncio
import websockets
import json
from datetime import datetime
from src.config import POLYGON_API_KEY, SIGNAL_API_KEY, SIGNAL_API_BASE_URL
from src.utils.logging import setup_logging
import aiohttp

logger = setup_logging()

class WebSocketManager:
    def __init__(self):
        self.websocket = None
        self.asset_type = None
        self.trade_pair = None

    async def connect(self, asset_type):
        self.asset_type = asset_type
        self.websocket_url = f"wss://socket.polygon.io/{self.asset_type}"
        self.websocket = await websockets.connect(self.websocket_url)
        await self.authenticate()
        return self.websocket

    async def authenticate(self):
        logger.info("Authenticating WebSocket connection...")
        await self.websocket.send(json.dumps({"action": "auth", "params": POLYGON_API_KEY}))
        response = await self.websocket.recv()
        logger.info(f"Authentication response: {response}")
        
        data = json.loads(response)
        if isinstance(data, list) and any(item.get("status") == "connected" for item in data):
            logger.info("WebSocket authenticated successfully")
        else:
            raise Exception("WebSocket authentication failed")

    async def subscribe(self, trade_pair):
        self.trade_pair = trade_pair
        logger.info(f"Subscribing to trade pair: {self.trade_pair}")
        formatted_pair = self.format_pair(self.trade_pair)
        event_code = self.get_event_code()
        params = f"{event_code}.{formatted_pair}"
        await self.websocket.send(json.dumps({"action": "subscribe", "params": params}))
        response = await self.websocket.recv()
        logger.info(f"Subscription response: {response}")
        return response

    async def listen_for_price(self):
        logger.info(f"Listening for price updates for {self.trade_pair}")
        log_count = 0
        last_log_time = None
        price = None

        while log_count < 1:
            message = await self.websocket.recv()
            data = json.loads(message)
            event_code = self.get_event_code()
            if isinstance(data, list) and len(data) > 0 and data[0].get('ev') == event_code:
                price = float(data[0]['c'])
                current_time = asyncio.get_event_loop().time()
                if last_log_time is None or current_time - last_log_time >= 1:
                    logger.info(f"Current price for {self.trade_pair}: {price}")
                    last_log_time = current_time
                    log_count += 1
            await asyncio.sleep(1)  # Adjust sleep duration as necessary

        logger.info("Closing WebSocket connection after logging price 3 times.")
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
            async with session.post(signal_api_url, json=params) as response:
                response_text = await response.text()
                logger.info(f"Submit trade signal sent. Response: {response_text}")
                return response.status == 200

    def get_event_code(self):
        return "CAS" if self.asset_type == "forex" else "XAS"

    def format_pair(self, pair):
        separator = '/' if self.asset_type == "forex" else '-'
        base = pair[:-3]
        quote = pair[-3:]
        return f"{base}{separator}{quote}"

websocket_manager = WebSocketManager()