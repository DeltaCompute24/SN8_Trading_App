from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import and_
from src.models.transaction import Transaction
from src.schemas.transaction import TransactionCreate
from datetime import datetime
from sqlalchemy.sql import func

async def create_transaction(db: AsyncSession, transaction_data: TransactionCreate, entry_price: float, operation_type: str,
                             position_id: int = None, trade_order: int = None, cumulative_leverage: float = None,
                             cumulative_stop_loss: float = None, cumulative_take_profit: float = None,
                             cumulative_order_type: str = None, status: str = "OPEN", close_time: datetime = None,
                             close_price: float = None, profit_loss: float = None):
    if operation_type == "initiate":
        max_position_id = await db.scalar(select(func.max(Transaction.position_id)).filter(Transaction.trader_id == transaction_data.trader_id))
        position_id = (max_position_id or 0) + 1
        trade_order = 1
        cumulative_leverage = transaction_data.leverage
        cumulative_stop_loss = transaction_data.stop_loss
        cumulative_take_profit = transaction_data.take_profit
        cumulative_order_type = transaction_data.order_type
    else:
        max_trade_order = await db.scalar(select(func.max(Transaction.trade_order)).filter(Transaction.position_id == position_id))
        trade_order = (max_trade_order or 0) + 1

    new_transaction = Transaction(
        trader_id=transaction_data.trader_id,
        trade_pair=transaction_data.trade_pair,
        open_time=datetime.utcnow(),
        entry_price=entry_price,
        leverage=transaction_data.leverage,
        stop_loss=transaction_data.stop_loss,
        take_profit=transaction_data.take_profit,
        order_type=transaction_data.order_type,
        asset_type=transaction_data.asset_type,
        operation_type=operation_type,
        cumulative_leverage=cumulative_leverage,
        cumulative_stop_loss=cumulative_stop_loss,
        cumulative_take_profit=cumulative_take_profit,
        cumulative_order_type=cumulative_order_type,
        status=status,
        close_time=close_time,
        close_price=close_price,
        profit_loss=profit_loss,
        position_id=position_id,
        trade_order=trade_order
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)
    return new_transaction

async def get_open_position(db: AsyncSession, trader_id: int, trade_pair: str) -> Transaction:
    # Get the latest position_id for the given trader_id and trade_pair
    latest_position_id = await db.scalar(
        select(func.max(Transaction.position_id)).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair
            )
        )
    )

    if not latest_position_id:
        return None

    # Get the transaction with the latest trade_order for the latest position_id
    latest_transaction = await db.scalar(
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

async def get_latest_position(db: AsyncSession, trader_id: int, trade_pair: str) -> Transaction:
    latest_position_id = await db.scalar(
        select(func.max(Transaction.position_id)).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair
            )
        )
    )

    if not latest_position_id:
        return None

    result = await db.execute(select(Transaction).where(
        and_(
            Transaction.position_id == latest_position_id,
            Transaction.trader_id == trader_id,
            Transaction.trade_pair == trade_pair
        )
    ).order_by(Transaction.trade_order.desc()))
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
