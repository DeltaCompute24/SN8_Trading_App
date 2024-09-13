import gc
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import text

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal
from src.models.monitored_positions import MonitoredPosition
from src.services.trade_service import calculate_profit_loss, get_latest_position
from src.utils.async_utils import run_async_in_sync
from src.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


@celery_app.task(name='src.tasks.position_monitor.monitor_positions')
def monitor_positions():
    gc.disable()
    logger.info("Starting monitor_positions task")
    run_async_in_sync(monitor_positions_async)


async def get_monitored_positions():
    try:
        logger.info("Fetching monitored positions from database")
        db: AsyncSession = TaskSessionLocal()
        result = await db.execute(select(MonitoredPosition))
        positions = result.scalars().all()
        db.close()
        logger.info(f"Retrieved {len(positions)} monitored positions")
        return positions
    except Exception as e:
        logger.error(f"An error occurred while fetching monitored positions: {e}")
        return []


async def monitor_positions_async():
    try:
        logger.info("Starting monitor_positions_async")
        positions = await get_monitored_positions()
        for position in positions:
            logger.info(f"Processing position {position.position_id}")
            await monitor_position(position)
        logger.info("Finished monitor_positions_async")
    except Exception as e:
        logger.error(f"An error occurred in monitor_positions_async: {e}")


async def monitor_position(position):
    try:
        current_price = websocket_manager.current_prices.get(position.trade_pair)
        if current_price:
            profit_loss = calculate_profit_loss(position, current_price)
            if should_close_position(profit_loss, position):
                db: AsyncSession = TaskSessionLocal()
                await close_position(position)
                db.close()
        return True
    except Exception as e:
        logger.error(f"An error occurred while monitoring position {position.position_id}: {e}")


async def close_position(position):
    try:
        db: AsyncSession = TaskSessionLocal()
        open_position = await get_latest_position(db, position.trader_id, position.trade_pair)

        if open_position:
            close_submitted = await websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1)
            if close_submitted:
                await db.execute(
                    text("DELETE FROM monitored_positions WHERE position_id = :position_id"),
                    {"position_id": position.position_id}
                )
                await db.commit()
        db.close()
    except Exception as e:
        logger.error(f"An error occurred while closing position {position.position_id}: {e}")


def should_close_position(profit_loss, position):
    try:
        result = (
                (position.cumulative_order_type == "LONG" and profit_loss >= position.cumulative_take_profit) or
                (position.cumulative_order_type == "LONG" and profit_loss <= position.cumulative_stop_loss) or
                (position.cumulative_order_type == "SHORT" and profit_loss <= position.cumulative_take_profit) or
                (position.cumulative_order_type == "SHORT" and profit_loss >= position.cumulative_stop_loss)
        )
        logger.info(f"Determining whether to close position: {result}")
        # Enable the garbage collector
        gc.enable()
        return result
    except Exception as e:
        logger.error(f"An error occurred while determining if position should be closed: {e}")
        return False
