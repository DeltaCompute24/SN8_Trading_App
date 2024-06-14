from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from src.models.position import Position
from src.schemas.position import PositionCreate
from datetime import datetime

async def create_position(db: AsyncSession, position_data: PositionCreate, entry_price: float, operation_type: str, 
                          cumulative_leverage: float, cumulative_stop_loss: float, cumulative_take_profit: float, 
                          cumulative_order_type: str, close_time: datetime = None, close_price: float = None, profit_loss: float = None):
    position = Position(
        trader_id=position_data.trader_id,
        trade_pair=position_data.trade_pair,
        leverage=position_data.leverage,
        entry_price=entry_price,
        asset_type=position_data.asset_type,
        stop_loss=position_data.stop_loss,
        take_profit=position_data.take_profit,
        open_time=datetime.utcnow(),
        status="OPEN" if operation_type != "close" else "CLOSED",
        order_type=position_data.order_type,
        cumulative_leverage=cumulative_leverage,
        cumulative_stop_loss=cumulative_stop_loss,
        cumulative_take_profit=cumulative_take_profit,
        cumulative_order_type=cumulative_order_type,
        operation_type=operation_type,
        close_time=close_time,
        close_price=close_price,
        profit_loss=profit_loss
    )
    db.add(position)
    await db.commit()
    await db.refresh(position)
    return position

async def get_open_position(db: AsyncSession, trader_id: int, trade_pair: str) -> Position:
    result = await db.execute(select(Position).where(
        and_(
            Position.trader_id == trader_id,
            Position.trade_pair == trade_pair,
            Position.status == "OPEN"
        )
    ))
    return result.scalars().first()

async def get_latest_position(db: AsyncSession, trader_id: int, trade_pair: str) -> Position:
    result = await db.execute(select(Position).where(
        and_(
            Position.trader_id == trader_id,
            Position.trade_pair == trade_pair
        )
    ).order_by(Position.open_time.desc()))
    return result.scalars().first()

def calculate_profit_loss(entry_price: float, current_price: float, leverage: float, order_type: str, asset_type: str) -> float:
    fee = calculate_fee(leverage, asset_type)
    if order_type == "LONG":
        price_difference = (current_price - entry_price) * leverage
    elif order_type == "SHORT":
        price_difference = (entry_price - current_price) * leverage
    net_profit = price_difference - fee
    profit_loss_percent = (net_profit / (entry_price * leverage)) * 100
    return profit_loss_percent

def calculate_fee(leverage: float, asset_type: str) -> float:
    return (0.00007 * leverage) if asset_type == 'forex' else (0.002 * leverage)
