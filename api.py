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

@app.post("/initiate-trade/")
async def initiate_trade(trade_input: TradeInput, background_tasks: BackgroundTasks):
    args = trade_input.dict()
    monitor = TradeMonitor(args)
    session = TradeSession(monitor)
    sessions[session.session_id] = session
    background_tasks.add_task(monitor.connect_to_websocket)
    session.is_trade_active = True
    return {"session_id": session.session_id, "message": "Trade initiated successfully"}

@app.get("/check-trade-status/{session_id}")
async def check_trade_status(session_id: str):
    session = sessions.get(session_id.strip('"'))
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

@app.post("/adjust-trade/{session_id}")
async def adjust_trade(session_id: str, trade_input: TradeInput):
    session = sessions.get(session_id.strip('"'))
    if not session or not session.is_trade_active:
        raise HTTPException(status_code=404, detail="Session not found or trade not active")

    monitor = session.monitor

    # Determine if the new trade is the same type (LONG/SHORT) as the existing trade
    if (monitor.order_type == 'LONG' and trade_input.order_type.upper() == 'LONG') or \
       (monitor.order_type == 'SHORT' and trade_input.order_type.upper() == 'SHORT'):
        new_leverage = monitor.leverage + trade_input.leverage
    else:
        new_leverage = monitor.leverage - trade_input.leverage

    # Update the order type based on the resulting leverage
    if new_leverage == 0:
        monitor.order_type = 'FLAT'  # Assuming 'FLAT' means no open position
        monitor.leverage = 0
    elif new_leverage < 0:
        monitor.order_type = 'SHORT'
        monitor.leverage = abs(new_leverage)
    else:  # new_leverage > 0
        monitor.order_type = 'LONG'
        monitor.leverage = new_leverage

    # Update stop loss and take profit based on the latest trade input
    monitor.stop_loss_level = trade_input.stop_loss
    monitor.take_profit_level = trade_input.take_profit

    logger.info(f"Trade parameters updated: Order Type - {monitor.order_type}, Leverage - {monitor.leverage}")
    return {"message": "Trade parameters updated successfully", "session_id": session_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
