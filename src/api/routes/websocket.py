import ast
import asyncio
import json
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.utils.constants import POSITIONS_TABLE
from src.utils.redis_manager import get_hash_values

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.broadcast_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        if len(self.active_connections) == 1:
            # Start broadcasting when the first client connects
            self.broadcast_task = asyncio.create_task(self.broadcast_prices())

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if not self.active_connections and self.broadcast_task:
            # Stop broadcasting when the last client disconnects
            self.broadcast_task.cancel()
            self.broadcast_task = None

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
                current_prices = get_hash_values()
                # prices_dict = {k : json.loads(v) for k, v in current_prices.items()}
                prices_dict = {k: float(v) for k, v in current_prices.items()}
                await self.broadcast(json.dumps(prices_dict))
            except Exception as e:
                print(f"Error fetching prices: {e}")
            await asyncio.sleep(1)


class PConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.broadcast_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        if len(self.active_connections) == 1:
            # Start broadcasting when the first client connects
            self.broadcast_task = asyncio.create_task(self.broadcast_prices())

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if not self.active_connections and self.broadcast_task:
            # Stop broadcasting when the last client disconnects
            self.broadcast_task.cancel()
            self.broadcast_task = None

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

                await self.broadcast(json.dumps(positions_dict))
            except Exception as e:
                print(f"Error fetching prices: {e}")
            await asyncio.sleep(1)


manager = ConnectionManager()
p_manager = PConnectionManager()


@router.websocket("/positions")
async def position_websocket_endpoint(websocket: WebSocket):
    await p_manager.connect(websocket)
    try:
        while True:
            # Wait for any message from the client to keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        p_manager.disconnect(websocket)


@router.websocket("/live-prices")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for any message from the client to keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
