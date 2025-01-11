from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import and_, or_, text
from sqlalchemy.sql import func

from src.models.transaction import Transaction
from src.schemas.monitored_position import MonitoredPositionCreate
from src.schemas.transaction import TransactionCreate


async def create_transaction(db: AsyncSession, transaction_data: TransactionCreate, entry_price: float,
                             operation_type: str, initial_price: float, position_id: int = None,
                             cumulative_leverage: float = None, cumulative_stop_loss: float = None,
                             cumulative_take_profit: float = None, order_type: str = None,
                             cumulative_order_type: str = None, status: str = "OPEN", old_status: str = "OPEN",
                             close_time: datetime = None, close_price: float = None, profit_loss: float = 0,
                             upward: float = -1, order_level: int = 0, modified_by: str = None,
                             average_entry_price: float = None, entry_price_list: list = None,
                             leverage_list: list = None, order_type_list: list = None, max_profit_loss: float = 0.0,
                             profit_loss_without_fee: float = 0.0, taoshi_profit_loss: float = 0.0,
                             taoshi_profit_loss_without_fee: float = 0.0, uuid: str = None, hot_key: str = None,
                             source: str = "", limit_order: float = 0.0, open_time: datetime = None,
                             adjust_time: datetime = None,
                             ):
    if operation_type == "initiate":
        max_position_id = await db.scalar(
            select(func.max(Transaction.position_id)).filter(Transaction.trader_id == transaction_data.trader_id))
        position_id = (max_position_id or 0) + 1
        trade_order = 1
        cumulative_leverage = transaction_data.leverage
        cumulative_stop_loss = transaction_data.stop_loss
        cumulative_take_profit = transaction_data.take_profit
        cumulative_order_type = order_type
    else:
        max_trade_order = await db.scalar(
            select(func.max(Transaction.trade_order)).filter(Transaction.position_id == position_id))
        trade_order = (max_trade_order or 0) + 1
    if not open_time:
        open_time = datetime.utcnow()
    new_transaction = Transaction(
        trader_id=transaction_data.trader_id,
        trade_pair=transaction_data.trade_pair,
        open_time=open_time,
        adjust_time=adjust_time,
        entry_price=entry_price,
        initial_price=initial_price,
        min_price=initial_price,
        max_price=initial_price,
        limit_order=limit_order,
        leverage=transaction_data.leverage,
        trailing=transaction_data.trailing,
        stop_loss=transaction_data.stop_loss,
        take_profit=transaction_data.take_profit,
        order_type=order_type,
        asset_type=transaction_data.asset_type,
        operation_type=operation_type,
        cumulative_leverage=cumulative_leverage,
        cumulative_stop_loss=cumulative_stop_loss,
        cumulative_take_profit=cumulative_take_profit,
        cumulative_order_type=cumulative_order_type,
        average_entry_price=average_entry_price,
        status=status,
        old_status=old_status,
        close_time=close_time,
        close_price=close_price,
        profit_loss=profit_loss,
        max_profit_loss=max_profit_loss,
        profit_loss_without_fee=profit_loss_without_fee,
        position_id=position_id,
        trade_order=trade_order,
        upward=upward,
        order_level=order_level,
        entry_price_list=entry_price_list,
        leverage_list=leverage_list,
        order_type_list=order_type_list,
        modified_by=modified_by,
        taoshi_profit_loss=taoshi_profit_loss,
        taoshi_profit_loss_without_fee=taoshi_profit_loss_without_fee,
        uuid=uuid,
        hot_key=hot_key,
        source=source,
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)
    return new_transaction


async def close_transaction(
        db: AsyncSession, order_id, trader_id, close_price: float = None,
        profit_loss: float = None, old_status: str = "", order_level: int = 0,
        profit_loss_without_fee: float = 0.0, taoshi_profit_loss: float = 0.0,
        taoshi_profit_loss_without_fee: float = 0.0, average_entry_price: float = 0.0,
        operation_type="close", status="CLOSED",
):
    close_time = datetime.utcnow()
    statement = text("""
            UPDATE transactions
            SET operation_type = :operation_type, 
                status = :status, 
                old_status = :old_status,
                close_time = :close_time, 
                close_price = :close_price,
                profit_loss = :profit_loss,
                modified_by = :modified_by,
                order_level = :order_level,
                profit_loss_without_fee = :profit_loss_without_fee,
                taoshi_profit_loss = :taoshi_profit_loss,
                taoshi_profit_loss_without_fee = :taoshi_profit_loss_without_fee,
                average_entry_price = :average_entry_price
            WHERE order_id = :order_id
        """)

    await db.execute(
        statement,
        {
            "operation_type": operation_type,
            "status": status,
            "old_status": old_status,
            "close_time": close_time,
            "close_price": close_price,
            "profit_loss": profit_loss,
            "order_id": order_id,
            "modified_by": str(trader_id),
            "order_level": order_level,
            "profit_loss_without_fee": profit_loss_without_fee,
            "taoshi_profit_loss": taoshi_profit_loss,
            "taoshi_profit_loss_without_fee": taoshi_profit_loss_without_fee,
            "average_entry_price": average_entry_price,
        }
    )
    await db.commit()


async def update_monitored_positions(db: AsyncSession, position_data: MonitoredPositionCreate):
    await db.execute(
        text("""
        INSERT INTO monitored_positions (
            position_id, order_id, trader_id, trade_pair, cumulative_leverage, cumulative_order_type, 
            cumulative_stop_loss, cumulative_take_profit, asset_type, entry_price
        ) VALUES (
            :position_id, :order_id, :trader_id, :trade_pair, :cumulative_leverage, :cumulative_order_type, 
            :cumulative_stop_loss, :cumulative_take_profit, :asset_type, :entry_price
        ) ON CONFLICT (position_id, order_id) DO UPDATE SET
            cumulative_leverage = EXCLUDED.cumulative_leverage,
            cumulative_order_type = EXCLUDED.cumulative_order_type,
            cumulative_stop_loss = EXCLUDED.cumulative_stop_loss,
            cumulative_take_profit = EXCLUDED.cumulative_take_profit,
            asset_type = EXCLUDED.asset_type,
            entry_price = EXCLUDED.entry_price
        """),
        {
            "position_id": position_data.position_id,
            "order_id": position_data.order_id,
            "trader_id": position_data.trader_id,
            "trade_pair": position_data.trade_pair,
            "cumulative_leverage": position_data.cumulative_leverage,
            "cumulative_order_type": position_data.cumulative_order_type,
            "cumulative_stop_loss": position_data.cumulative_stop_loss,
            "cumulative_take_profit": position_data.cumulative_take_profit,
            "asset_type": position_data.asset_type,
            "entry_price": position_data.entry_price
        }
    )
    await db.commit()


async def get_open_position(db: AsyncSession, trader_id: int, trade_pair: str):
    open_transaction = await db.scalar(
        select(Transaction).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                Transaction.status == "OPEN"
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return open_transaction


async def get_latest_position(db: AsyncSession, trader_id: int, trade_pair: str) -> Transaction:
    latest_transaction = await db.scalar(
        select(Transaction).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                or_(
                    Transaction.status == "OPEN",
                    Transaction.status == "PENDING",
                )
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return latest_transaction


async def get_non_closed_position(db: AsyncSession, trader_id: int, trade_pair: str) -> Transaction:
    transaction = await db.scalar(
        select(Transaction).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                Transaction.status != "CLOSED",
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return transaction
