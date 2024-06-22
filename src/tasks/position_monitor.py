from asgiref.sync import async_to_sync
from src.database_tasks import get_task_db
from src.models.monitored_positions import MonitoredPosition
from src.services.trade_service import calculate_profit_loss, get_open_position
from src.utils.websocket_manager import websocket_manager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import text
from src.core.celery_app import celery_app
from src.utils.async_utils import run_async_in_sync

@celery_app.task(name='src.tasks.position_monitor.monitor_positions')
def monitor_positions():
    run_async_in_sync(monitor_positions_async)

async def monitor_positions_async():
    async for db in get_task_db():
        positions = await get_monitored_positions(db)
        for position in positions:
            await monitor_position(position, db)

async def get_monitored_positions(db: AsyncSession):
    result = await db.execute(select(MonitoredPosition))
    positions = result.scalars().all()
    return positions

async def monitor_position(position, db: AsyncSession):
    current_price = websocket_manager.current_prices.get(position.trade_pair)
    if current_price:
        profit_loss = calculate_profit_loss(
            position.entry_price, 
            current_price, 
            position.cumulative_leverage, 
            position.cumulative_order_type, 
            position.asset_type
        )
        if should_close_position(profit_loss, position):
            await close_position(position, db)

async def close_position(position, db: AsyncSession):
    open_position = await get_open_position(db, position.trader_id, position.trade_pair)
    if open_position:
        close_submitted = await websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1)
        if close_submitted:
            await db.execute(
                text("DELETE FROM monitored_positions WHERE position_id = :position_id"),
                {"position_id": position.position_id}
            )
            await db.commit()

def should_close_position(profit_loss, position):
    return (
        (position.cumulative_order_type == "LONG" and profit_loss >= position.cumulative_take_profit) or 
        (position.cumulative_order_type == "LONG" and profit_loss <= position.cumulative_stop_loss) or
        (position.cumulative_order_type == "SHORT" and profit_loss <= position.cumulative_take_profit) or
        (position.cumulative_order_type == "SHORT" and profit_loss >= position.cumulative_stop_loss)
    )
