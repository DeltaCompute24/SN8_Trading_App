from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import and_

from src.models.users import Users
from src.schemas.user import UsersBase


async def get_user(db: AsyncSession, trader_id: int):
    user = await db.scalar(
        select(Users).where(
            and_(
                Users.trader_id == trader_id,
            )
        )
    )
    return user


async def create_user(db: AsyncSession, user_data: UsersBase):
    new_user = Users(
        trader_id=user_data.trader_id,
        current_challenge_level=user_data.current_challenge_level,
        hot_key=user_data.hot_key,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def get_user_challenge_level(db: AsyncSession, trader_id: int):
    user = await get_user(db, trader_id)
    if not user:
        return ""
    return user.current_challenge_level
