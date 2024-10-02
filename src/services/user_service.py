from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.models.firebase_user import FirebaseUser
from src.models.users import Users
from src.schemas.user import UsersBase, FirebaseUserCreate


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
        hot_key=user_data.hot_key,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


# ---------------------- FIREBASE USER ------------------------------

def get_firebase_user(db: Session, firebase_id: str):
    user = db.scalar(
        select(FirebaseUser).where(
            and_(
                FirebaseUser.firebase_id == firebase_id,
            )
        )
    )
    return user


def create_firebase_user(db: Session, user_data: FirebaseUserCreate):
    new_user = FirebaseUser(
        firebase_id=user_data.firebase_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if user_data.challenges:
        for challenge_data in user_data.challenges:
            challenge = Challenge(
                trader_id=challenge_data.trader_id,
                hot_key=challenge_data.hot_key,
                status=challenge_data.status,
                active=challenge_data.active,
                challenge=challenge_data.challenge,
                user_id=new_user.id
            )
            db.add(challenge)
        db.commit()
    db.refresh(new_user)

    return new_user


def create_or_update_challenges(db: Session, user, challenges):
    for challenge_data in challenges:
        existing_challenge = db.scalar(
            select(Challenge).where(
                and_(
                    Challenge.trader_id == challenge_data.trader_id,
                    Challenge.user_id == user.id
                )
            )
        )
        if existing_challenge:
            existing_challenge.hot_key = challenge_data.hot_key
            existing_challenge.status = challenge_data.status
            existing_challenge.active = challenge_data.active
            existing_challenge.challenge = challenge_data.challenge
        else:
            new_challenge = Challenge(
                trader_id=challenge_data.trader_id,
                hot_key=challenge_data.hot_key,
                status=challenge_data.status,
                active=challenge_data.active,
                challenge=challenge_data.challenge,
                user_id=user.id
            )
            db.add(new_challenge)

        db.commit()
        db.refresh(user)

    return user


def get_challenge(trader_id: int):
    with TaskSessionLocal_() as db:
        challenge = db.scalar(
            select(Challenge).where(
                and_(
                    Challenge.trader_id == trader_id,
                )
            )
        )
        if not challenge:
            return True

        if challenge.challenge == "main":
            return True
        return False
