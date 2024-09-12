from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import and_, text
from sqlalchemy.sql import func

from src.models.transaction import Transaction
from src.schemas.monitored_position import MonitoredPositionCreate
from src.schemas.transaction import TransactionCreate


async def create_transaction(db: AsyncSession, transaction_data: TransactionCreate, entry_price: float,
                             operation_type: str, initial_price: float, position_id: int = None,
                             cumulative_leverage: float = None, cumulative_stop_loss: float = None,
                             cumulative_take_profit: float = None,
                             cumulative_order_type: str = None, status: str = "OPEN", old_status: str = "OPEN",
                             close_time: datetime = None, close_price: float = None, profit_loss: float = None,
                             upward: float = -1, challenge_level: str = None, modified_by: str = None,
                             average_entry_price: float = None):
    if operation_type == "initiate":
        max_position_id = await db.scalar(
            select(func.max(Transaction.position_id)).filter(Transaction.trader_id == transaction_data.trader_id))
        position_id = (max_position_id or 0) + 1
        trade_order = 1
        cumulative_leverage = transaction_data.leverage
        cumulative_stop_loss = transaction_data.stop_loss
        cumulative_take_profit = transaction_data.take_profit
        cumulative_order_type = transaction_data.order_type
    else:
        max_trade_order = await db.scalar(
            select(func.max(Transaction.trade_order)).filter(Transaction.position_id == position_id))
        trade_order = (max_trade_order or 0) + 1

    new_transaction = Transaction(
        trader_id=transaction_data.trader_id,
        trade_pair=transaction_data.trade_pair,
        open_time=datetime.utcnow(),
        entry_price=entry_price,
        initial_price=initial_price,
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
        average_entry_price=average_entry_price,
        status=status,
        old_status=old_status,
        close_time=close_time,
        close_price=close_price,
        profit_loss=profit_loss,
        position_id=position_id,
        trade_order=trade_order,
        upward=upward,
        challenge_level=challenge_level,
        modified_by=modified_by,
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)
    return new_transaction


async def close_transaction(db: AsyncSession, order_id, trader_id, close_price: float = None,
                            profit_loss: float = None, old_status: str = None, challenge_level: str = None):
    close_time = datetime.utcnow()
    statement = text("""
            UPDATE transactions
            SET operation_type = :operation_type, 
                status = :status, 
                old_status = :old_status,
                close_time = :close_time, 
                close_price = :close_price,
                profit_loss = :profit_loss,
                leverage = :leverage,
                stop_loss = :stop_loss,
                take_profit = :take_profit,
                order_type = :order_type,
                modified_by = :modified_by,
                challenge_level = :challenge_level
            WHERE order_id = :order_id
        """)

    await db.execute(
        statement,
        {
            "operation_type": "close",
            "status": "CLOSED",
            "old_status": old_status,
            "close_time": close_time,
            "close_price": close_price,
            "profit_loss": profit_loss,
            "leverage": 1,
            "stop_loss": None,
            "take_profit": None,
            "order_type": "FLAT",
            "order_id": order_id,
            "modified_by": str(trader_id),
            "challenge_level": challenge_level
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
                Transaction.status != "CLOSED"
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return open_transaction


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


def calculate_profit_loss(entry_price: float, current_price: float, leverage: float, order_type: str,
                          asset_type: str) -> float:
    # broker fee or commission
    fee = calculate_fee(leverage, asset_type)
    # if long which means user bet that the price will increase i.e. current_price > entry_price => it's a profit
    if order_type == "LONG":
        price_difference = (current_price - entry_price)
    # if long which means user bet that the price will increase i.e. current_price > entry_price => it's a profit
    elif order_type == "SHORT":
        price_difference = (entry_price - current_price)
    else:
        price_difference = 0.00
    net_profit = price_difference - fee
    if (entry_price * leverage) == 0:
        return 0.00

    profit_loss_percent = ((net_profit / entry_price) * leverage) * 100
    return profit_loss_percent


def calculate_fee(leverage: float, asset_type: str) -> float:
    return (0.00007 * leverage) if asset_type == 'forex' else (0.002 * leverage)


def calculate_unrealized_pnl(current_price, position):
    if position.entry_price == 0 or position.average_entry_price is None:
        return 1

    gain = (
            (current_price - position.average_entry_price)
            * position.cumulative_leverage
            / position.entry_price
    )
    # Check if liquidated
    if gain <= -1.0:
        return 0
    net_return = 1 + gain
    return net_return


def calculate_return_with_fees(current_return_no_fees, position):
    fee = calculate_fee(leverage=position.cumulative_leverage, asset_type=position.asset_type)
    return current_return_no_fees * fee


def get_open_position_return_with_fees(realtime_price, position):
    current_return = calculate_unrealized_pnl(realtime_price, position)
    return calculate_return_with_fees(current_return, position)
