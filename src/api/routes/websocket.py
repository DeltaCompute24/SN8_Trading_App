import ast
import asyncio
import json
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.utils.constants import POSITIONS_TABLE, REDIS_LIVE_PRICES_TABLE
from src.utils.redis_manager import get_hash_values, get_hash_value

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.broadcast_tasks = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        if len(self.active_connections) == 1:
            # Start broadcasting when the first client connects
            self.broadcast_tasks.append(asyncio.create_task(self.broadcast_prices()))
            self.broadcast_tasks.append(asyncio.create_task(self.broadcast_positions()))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if not self.active_connections and self.broadcast_tasks:
            # Stop broadcasting when the last client disconnects
            for task in self.broadcast_tasks:
                task.cancel()
            self.broadcast_tasks = []

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            self.active_connections.remove(conn)

    async def broadcast_prices(self):
        while True:
            if not self.active_connections:
                # No active connections, stop broadcasting
                break
            try:
                current_prices = get_hash_value(key="0", hash_name=REDIS_LIVE_PRICES_TABLE)
                current_prices = json.loads(current_prices)
                await self.broadcast(json.dumps({"type": "prices", "data": current_prices}))
            except Exception as e:
                print(f"Error fetching prices: {e}")
            await asyncio.sleep(1)

    async def broadcast_positions(self):
        while True:
            if not self.active_connections:
                # No active connections, stop broadcasting
                break
            try:
                positions = get_hash_values(POSITIONS_TABLE)
                positions_dict = {}
                for key, value in positions.items():

                    value = ast.literal_eval(value)

                    trade_pair, trader_id = key.split("-")
                    if trader_id not in positions_dict:
                        positions_dict[trader_id] = {}
                    positions_dict[trader_id][trade_pair] = {
                        "time": value[0],
                        "price": value[1],
                        "profit_loss": value[2],
                        "profit_loss_without_fee": value[3],
                    }
                await self.broadcast(json.dumps({"type": "positions", "data": positions_dict}))
            except Exception as e:
                print(f"Error fetching positions: {e}")
            await asyncio.sleep(1)


manager = ConnectionManager()


@router.websocket("/delta")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
