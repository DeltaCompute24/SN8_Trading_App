from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.user import UsersSchema, UsersBase
from src.services.user_service import get_user, create_user
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.post("/create-user/", response_model=UsersSchema)
async def initiate_position(user_data: UsersBase, db: AsyncSession = Depends(get_db)):
    logger.info(f"Create User for trader_id={user_data.trader_id}")

    existing_user = await get_user(db, user_data.trader_id)
    if existing_user:
        logger.error("A user already exists for this trader_id")
        raise HTTPException(status_code=400, detail="A user already exists for this trader_id")

    try:
        # Create the user
        new_user = await create_user(db, user_data)
        logger.info(f"User initiated successfully with trader id {user_data.trader_id}")
        return new_user

    except Exception as e:
        logger.error(f"Error initiating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
