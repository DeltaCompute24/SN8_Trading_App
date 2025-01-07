import asyncio

import websockets

from src.config import TESTNET_CHECKPOINT_URL
from src.utils.constants import TESTNET_TABLE
from src.utils.logging import setup_logging
from src.utils.redis_manager import set_hash_value

logger = setup_logging()


class TestnetWebSocketManager:
    def __init__(self):
        self.websocket = None
        self.reconnect_interval = 5  # seconds
        self._recv_lock = asyncio.Lock()  # Lock to ensure single access to recv

    async def run_testnet(self):
        try:
            self.websocket = await websockets.connect(TESTNET_CHECKPOINT_URL)
            await self.receive_and_log()
        except Exception as e:
            logger.error(f"Testnet Connection Failed: {e}. Retrying in {self.reconnect_interval} seconds...")
            await asyncio.sleep(self.reconnect_interval)

    async def receive_and_log(self):
        while True:
            try:
                message = await self.websocket.recv()
                set_hash_value(key="0", value=message, hash_name=TESTNET_TABLE)
            except Exception as e:
                print("Testnet WebSocket Connection Closed. Reconnecting...")
                await self.close()
                await asyncio.sleep(self.reconnect_interval)
                await self.run_testnet()

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None


testnet_websocket_manager = TestnetWebSocketManager()
