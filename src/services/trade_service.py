from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import and_, or_, text
from sqlalchemy.sql import func
from fastapi import HTTPException, status
from src.models.transaction import Transaction, Status
from src.schemas.monitored_position import MonitoredPositionCreate
from src.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionUpdateDatabase,
    TransactionUpdateDatabaseGen,
)
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from src.schemas.trader import HotKeyMap


async def create_transaction(
    db: AsyncSession,
    transaction_data: TransactionCreate,
    entry_price: float,
    operation_type: str,
    initial_price: float,
    position_id: int = None,
    cumulative_leverage: float = None,
    cumulative_stop_loss: float = None,
    cumulative_take_profit: float = None,
    order_type: str = None,
    cumulative_order_type: str = None,
    status: str = "OPEN",
    old_status: str = "OPEN",
    close_time: datetime = None,
    close_price: float = None,
    profit_loss: float = 0,
    upward: float = -1,
    order_level: int = 0,
    modified_by: str = None,
    average_entry_price: float = None,
    entry_price_list: list = None,
    leverage_list: list = None,
    order_type_list: list = None,
    max_profit_loss: float = 0.0,
    profit_loss_without_fee: float = 0.0,
    taoshi_profit_loss: float = 0.0,
    taoshi_profit_loss_without_fee: float = 0.0,
    uuid: str = None,
    hot_key: str = None,
    source: str = "",
    limit_order: float = 0.0,
    open_time: datetime = None,
    adjust_time: datetime = None,
):
    if operation_type == "initiate":
        max_position_id = await db.scalar(
            select(func.max(Transaction.position_id)).filter(
                Transaction.trader_id == transaction_data.trader_id
            )
        )
        position_id = (max_position_id or 0) + 1
        trade_order = 1
        cumulative_leverage = transaction_data.leverage
        cumulative_stop_loss = transaction_data.stop_loss
        cumulative_take_profit = transaction_data.take_profit
        cumulative_order_type = order_type
    else:
        max_trade_order = await db.scalar(
            select(func.max(Transaction.trade_order)).filter(
                Transaction.position_id == position_id
            )
        )
        trade_order = (max_trade_order or 0) + 1
    if not open_time:
        open_time = datetime.now()
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


async def close_transaction_without_commit(
    db: AsyncSession,
    order_id,
    trader_id,
    close_price: float = None,
    profit_loss: float = None,
    old_status: str = "",
    operation_type="close",
    status="CLOSED",
):
    close_time = datetime.utcnow()
    statement = text(
        """
            UPDATE transactions
            SET operation_type = :operation_type, 
                status = :status, 
                old_status = :old_status,
                close_time = :close_time, 
                close_price = :close_price,
                profit_loss = :profit_loss,
                modified_by = :modified_by
            WHERE order_id = :order_id
        """
    )

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
        },
    )


async def close_transaction_with_commit(
    db: AsyncSession,
    order_id,
    trader_id,
    close_price: float = None,
    profit_loss: float = None,
    old_status: str = "",
    operation_type="close",
    status="CLOSED",
):
    close_time = datetime.utcnow()
    statement = text(
        """
            UPDATE transactions
            SET operation_type = :operation_type, 
                status = :status, 
                old_status = :old_status,
                close_time = :close_time, 
                close_price = :close_price,
                profit_loss = :profit_loss,
                modified_by = :modified_by
            WHERE order_id = :order_id
        """
    )

    result = await db.execute(
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
        },
    )

    await db.commit()


def close_transaction_sync(
    db: Session,
    order_id,
    trader_id,
    close_price: float = None,
    profit_loss: float = None,
    old_status: str = "",
    order_level: int = 0,
    profit_loss_without_fee: float = 0.0,
    taoshi_profit_loss: float = 0.0,
    taoshi_profit_loss_without_fee: float = 0.0,
    average_entry_price: float = 0.0,
    operation_type="close",
    status="CLOSED",
):
    close_time = datetime.utcnow()
    statement = text(
        """
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
        """
    )

    db.execute(
        statement,
        {
            "operation_type": operation_type,
            "status": status,
            "old_status": old_status,
            "close_time": close_time,
            "close_price": close_price,
            "profit_loss": profit_loss,
            "order_id": order_id,
            "modified_by": "monitor_position_sync",
            "order_level": order_level,
            "profit_loss_without_fee": profit_loss_without_fee,
            "taoshi_profit_loss": taoshi_profit_loss,
            "taoshi_profit_loss_without_fee": taoshi_profit_loss_without_fee,
            "average_entry_price": average_entry_price,
        },
    )
    db.commit()


def update_transaction_sync(
    db: Session,
    order_id: int,
    trader_id: int,
    entry_price: float,
    old_status: str,
    status: str,
):
    """
    Update a transaction record with processing status.

    Args:
        db: Session - database session
        order_id: int - ID of the order to update
        trader_id: int - ID of the trader
        entry_price: float - entry price for the position
        old_status: str - previous status of the transaction
        status: str - new status to set
    """
    open_time = datetime.utcnow()

    statement = text(
        """
            UPDATE transactions
            SET status = :status, 
                old_status = :old_status,
                open_time = :open_time, 
                entry_price = :entry_price,
                modified_by = :modified_by
            WHERE order_id = :order_id
            AND trader_id = :trader_id
        """
    )

    db.execute(
        statement,
        {
            "status": status,
            "old_status": old_status,
            "open_time": open_time,
            "entry_price": entry_price,
            "order_id": order_id,
            "trader_id": trader_id,
            "modified_by": "monitor_position_sync",
        },
    )
    db.commit()


async def update_transaction_async(
    db: Session, transaction: Transaction, updated_values: TransactionUpdateDatabase
):
    """
    Update a transaction record with provided values status.

    """
    for key, value in updated_values.model_dump(exclude_unset=True).items():
        setattr(transaction, key, value)

    try:
        await db.commit()
        await db.refresh(transaction)
        return transaction
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not update payout: {str(e)}",
        )


def update_transaction_sync_gen(
    db: Session, transaction: Transaction, updated_values: TransactionUpdateDatabaseGen
):
    """
    Update a transaction record with provided values status.

    """
    for key, value in updated_values.model_dump(exclude_unset=True).items():
        setattr(transaction, key, value)

    try:
        db.commit()
        db.refresh(transaction)
        return transaction
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not update payout: {str(e)}",
        )


async def update_monitored_positions(
    db: AsyncSession, position_data: MonitoredPositionCreate
):
    await db.execute(
        text(
            """
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
        """
        ),
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
            "entry_price": position_data.entry_price,
        },
    )
    await db.commit()


async def get_open_or_adjusted_position(
    db: AsyncSession, trader_id: int, trade_pair: str
):
    open_transaction = await db.scalar(
        select(Transaction)
        .where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                Transaction.status.in_([Status.open, Status.adjust_processing]),
            )
        )
        .order_by(Transaction.trade_order.desc())
    )
    return open_transaction


async def get_latest_position(
    db: AsyncSession, trader_id: int, trade_pair: str
) -> Transaction:
    latest_transaction = await db.scalar(
        select(Transaction)
        .where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                or_(
                    Transaction.status == Status.open,
                    Transaction.status == Status.pending,
                    Transaction.status == Status.adjust_processing,
                ),
            )
        )
        .order_by(Transaction.trade_order.desc())
    )
    return latest_transaction


async def get_non_closed_position(
    db: AsyncSession, trader_id: int, trade_pair: str
) -> Transaction:
    transaction = await db.scalar(
        select(Transaction)
        .where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                Transaction.status != "CLOSED",
            )
        )
        .order_by(Transaction.trade_order.desc())
    )
    return transaction


def get_SLTP_pending_positions(db: Session) -> List[Transaction]:
    """Get all SLTP_pending_positions positions with proper async handling"""

    # Base query for all statuses
    base_query = select(Transaction)

    # Combine conditions using OR for different status types
    status_conditions = or_(
        and_(
            Transaction.status.in_([Status.open, Status.adjust_processing]),
            or_(
                and_(
                    Transaction.cumulative_take_profit.isnot(None),
                    Transaction.cumulative_take_profit != 0,
                ),
                and_(
                    Transaction.cumulative_stop_loss.isnot(None),
                    Transaction.cumulative_stop_loss != 0,
                ),
            ),
        ),
        # For PENDING, no additional conditions needed
        Transaction.status == Status.pending,
    )

    # Apply the combined conditions
    query = base_query.where(status_conditions)

    result = db.execute(query)
    positions = result.scalars().unique().all()
    return positions


def get_user_hotkey_map(db: Session) -> HotKeyMap:
    """
    Get a mapping of hot_keys to user details from challenges and firebase_users tables.
    Returns:
        Dict[str, Any]: A dictionary with hot_keys as keys and user details as values
    """
    try:
        query = text(
            """
            SELECT 
                jsonb_object_agg(
                    c.hot_key,
                    jsonb_build_object(
                        'name', u.username,
                        'email', u.email,
                        'user_id', u.id,
                        'trader_id', c.trader_id,
                        'id', u.id  
                    )
                ) as user_hotkey_map
            FROM challenges c
            JOIN firebase_users u ON c.user_id = u.id
        """
        )

        result = db.execute(query)
        user_map = result.scalar()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB Error fetching user hotkey map: {str(e)}",
        )
    return HotKeyMap(data=user_map)


async def get_transaction_by_order_id(db: AsyncSession, order_id) -> Transaction:
    stmt = select(Transaction).where(Transaction.order_id == order_id)
    result = (await db.execute(stmt)).scalar_one_or_none()
    return result
