import asyncio
import json
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.utils.redis_manager import get_hash_values

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

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if not self.active_connections and self.broadcast_tasks:
            # Stop broadcasting when the last client disconnects
            for task in self.broadcast_tasks:
                task.cancel()
            self.broadcast_tasks = []

    async def broadcast(self, message: dict):
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
                prices_dict = {k: json.loads(v) for k, v in current_prices.items()}
                await self.broadcast(json.dumps(prices_dict))
            except Exception as e:
                print(f"Error fetching prices: {e}")
            await asyncio.sleep(1)


manager = ConnectionManager()


@router.websocket("/live-prices")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
