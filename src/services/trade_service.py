from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from src.models.position import Position
from src.schemas.position import PositionCreate
from datetime import datetime

async def create_position(db: AsyncSession, position_data: PositionCreate, entry_price: float, operation_type: str) -> Position:
    position = Position(
        trader_id=position_data.trader_id,
        trade_pair=position_data.trade_pair,
        leverage=position_data.leverage,
        asset_type=position_data.asset_type,
        stop_loss=position_data.stop_loss,
        take_profit=position_data.take_profit,
        open_time=datetime.utcnow(),
        status="OPEN",
        order_type=position_data.order_type,
        entry_price=entry_price,
        cumulative_leverage=position_data.leverage,
        cumulative_stop_loss=position_data.stop_loss,
        cumulative_take_profit=position_data.take_profit,
        cumulative_order_type=position_data.order_type,
        operation_type=operation_type
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

async def calculate_profit_loss(db: AsyncSession, trader_id: int, trade_pair: str) -> float:
    position = await get_open_position(db, trader_id, trade_pair)
    if not position:
        return None

    # Here you can add your logic to calculate profit/loss based on the current price
    # For demonstration, let's assume we have a simple difference calculation
    if position.entry_price is not None and position.current_price is not None:
        return (position.current_price - position.entry_price) * position.leverage

    return None

async def adjust_position(db: AsyncSession, trader_id: int, trade_pair: str, leverage: float, stop_loss: float, take_profit: float, order_type: str) -> Position:
    position = await get_open_position(db, trader_id, trade_pair)
    if not position:
        return None

    # Adjust leverage and potentially change order type
    if position.order_type == order_type.upper():
        position.leverage += leverage
    else:
        position.leverage -= leverage

    if position.leverage == 0:
        position.order_type = 'FLAT'
    elif position.leverage < 0:
        position.order_type = 'SHORT'
        position.leverage = abs(position.leverage)
    else:
        position.order_type = 'LONG'

    # Update cumulative columns
    position.cumulative_leverage += leverage
    position.cumulative_stop_loss = stop_loss
    position.cumulative_take_profit = take_profit
    position.cumulative_order_type = order_type

    await db.commit()
    await db.refresh(position)
    return position