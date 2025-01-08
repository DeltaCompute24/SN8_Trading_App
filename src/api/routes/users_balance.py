from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database_tasks import get_sync_db
from src.models import UsersBalance
from src.schemas.user import CreateUserBalanceSchema, UserBalanceSchema
from src.services.user_service import create_user_balance, get_user_balance
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.post("/", response_model=UserBalanceSchema)
def create_balance(user_data: CreateUserBalanceSchema, db: Session = Depends(get_sync_db)):
    logger.info(f"Create User Balance for trader_id={user_data.trader_id}")
    try:
        return create_user_balance(db, user_data)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[UserBalanceSchema])
def get_user_balances(db: Session = Depends(get_sync_db)):
    logger.info("Fetching Users Balances")
    return db.query(UsersBalance).all()


@router.put("/", response_model=UserBalanceSchema)
def update_user_balance(user_data: CreateUserBalanceSchema, db: Session = Depends(get_sync_db)):
    user = get_user_balance(db, user_data.hot_key)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User Balance for this hotkey {user_data.hot_key} Not Found!")
    try:
        if user_data.trader_id:
            user.trader_id = user_data.trader_id
        if user_data.balance:
            user.balance = user_data.balance
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
