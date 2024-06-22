from pydantic import BaseModel

class MonitoredPositionCreate(BaseModel):
    position_id: int
    order_id: int
    trader_id: int
    trade_pair: str
    cumulative_leverage: float
    cumulative_order_type: str
    cumulative_stop_loss: float
    cumulative_take_profit: float
    asset_type: str
    entry_price: float