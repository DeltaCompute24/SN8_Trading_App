import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import and_, text
from sqlalchemy.sql import func

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_3
from src.models.monitored_positions import MonitoredPosition
from src.models.transaction import Transaction
from src.services.trade_service import calculate_profit_loss
from src.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


def get_open_position(db: AsyncSession, trader_id: int, trade_pair: str):
    latest_position_id = db.scalar(
        select(func.max(Transaction.position_id)).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair
            )
        )
    )

    if not latest_position_id:
        return None

    latest_transaction = db.scalar(
        select(Transaction).where(
            and_(
                Transaction.position_id == latest_position_id,
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair
            )
        ).order_by(Transaction.trade_order.desc())
    )

    if latest_transaction and latest_transaction.status == "OPEN":
        return latest_transaction

    return None


@celery_app.task(name='src.tasks.position_monitor_sync.monitor_positions')
def monitor_positions():
    logger.info("Starting monitor_positions task")
    monitor_positions_sync()


def get_monitored_positions():
    try:
        logger.info("Fetching monitored positions from database")
        db: AsyncSession = TaskSessionLocal_3()
        result = db.execute(select(MonitoredPosition))
        positions = result.scalars().all()
        db.close()
        logger.info(f"Retrieved {len(positions)} monitored positions")
        return positions
    except Exception as e:
        logger.error(f"An error occurred while fetching monitored positions: {e}")
        return []


def monitor_positions_sync():
    try:
        logger.info("Starting monitor_positions_sync")
        positions = get_monitored_positions()
        for position in positions:
            logger.info(f"Processing position {position.position_id}")
            monitor_position(position)
        logger.info("Finished monitor_positions_sync")
    except Exception as e:
        logger.error(f"An error occurred in monitor_positions_sync: {e}")


def monitor_position(position):
    try:
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
                db: AsyncSession = TaskSessionLocal_3()
                close_position(position)
                db.close()
        return True
    except Exception as e:
        logger.error(f"An error occurred while monitoring position {position.position_id}: {e}")


def close_position(position):
    try:
        db: AsyncSession = TaskSessionLocal_3()
        open_position = get_open_position(db, position.trader_id, position.trade_pair)

        if open_position:
            close_submitted = websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1)
            if close_submitted:
                db.execute(
                    text("DELETE FROM monitored_positions WHERE position_id = :position_id"),
                    {"position_id": position.position_id}
                )
                db.commit()
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
        return result
    except Exception as e:
        logger.error(f"An error occurred while determining if position should be closed: {e}")
        return False
