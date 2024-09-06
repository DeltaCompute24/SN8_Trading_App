from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import and_

from src.schemas.user import UsersBase
from src.models.users import Users


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
