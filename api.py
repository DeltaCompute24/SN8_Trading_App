from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
import asyncio
from fastapi import BackgroundTasks
from src.utils import setup_logging


from src.monitorapi import TradeMonitor  # Ensure this is correctly imported
logger = setup_logging()

app = FastAPI()

class TradeInput(BaseModel):
    trader_id: int
    trade_pair: str
    order_type: str
    leverage: float
    asset_type: str
    stop_loss: float
    take_profit: float
    test_mode: bool

class TradeSession:
    def __init__(self, monitor):
        self.monitor = monitor
        self.session_id = str(uuid4())
        self.is_trade_active = False

sessions = {}

@app.post("/trades/")
async def start_trade(trade_input: TradeInput, background_tasks: BackgroundTasks):
    args = {
        "self.trader_id" : trade_input.trader_id,
        "trade_pair": trade_input.trade_pair,
        "order_type": trade_input.order_type,
        "leverage": trade_input.leverage,
        "asset_type": trade_input.asset_type,
        "stop_loss": trade_input.stop_loss,
        "take_profit": trade_input.take_profit,
        "test_mode": trade_input.test_mode,
    }
    monitor = TradeMonitor(args)
    session = TradeSession(monitor)
    sessions[session.session_id] = session

    # Move connection to background task
    background_tasks.add_task(monitor.connect_to_websocket)
    session.is_trade_active = True  # Make sure this is set after the monitor starts successfully
    return {"session_id": session.session_id, "message": "Initiating trade"}

@app.get("/trades/{session_id}")
async def get_trade_status(session_id: str):
    logger.info(f"Requested session_id: {session_id}")
    logger.info(f"Available sessions: {list(sessions.keys())}")
    clean_session_id = session_id.strip('"')
    
    session = sessions.get(clean_session_id)
    if not session or not session.is_trade_active:
        raise HTTPException(status_code=404, detail="Session not found or trade not active")
    
    monitor = session.monitor
    trade_status = {
        "Trade Open Time": str(monitor.trade_open_time),
        "Trade Pair": monitor.trade_pair,
        "Asset Type": monitor.asset_type.capitalize(),
        "Order Type": monitor.order_type,
        "Leverage": f"{monitor.leverage:.2f}x",
        "Entry Price": f"{monitor.entry_price:.2f}",
        "Current Price": f"{monitor.current_price:.2f}",
        "Profit/Loss": f"{monitor.calculate_profit_loss():.2f}% ({monitor.calculate_absolute_profit_loss():.2f})",
        "Fee Deducted": f"{monitor.calculate_fee():.6f}",
        "Take Profit": f"{monitor.take_profit_level:.2f}%",
        "Stop Loss": f"{monitor.stop_loss_level:.2f}%",
    }
    return trade_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
