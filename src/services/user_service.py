import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge
from src.models.firebase_user import FirebaseUser
from src.models.users import Users
from src.schemas.user import UsersBase
from src.utils.logging import setup_logging

logger = setup_logging()
ambassadors = {}


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


def get_user_by_id(db: Session, id: int):
    user = db.scalar(
        select(FirebaseUser).where(
            and_(
                FirebaseUser.id == id,
            )
        )
    )
    return user


def create_firebase_user(db: Session, firebase_id: str, name: str, email: str):
    firebase_user = get_firebase_user(db, firebase_id)
    if not firebase_user:
        username = construct_username(email)
        firebase_user = FirebaseUser(
            firebase_id=firebase_id,
            name=name,
            email=email,
            username=username,
        )
        db.add(firebase_user)
        db.commit()
        db.refresh(firebase_user)

    return firebase_user


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


def construct_username(email):
    base_username = email.split('@')[0].lower()
    return re.sub(r'[^a-z0-9]', '_', base_username)


def get_challenge(trader_id: int, source=False):
    with TaskSessionLocal_() as db:
        challenge = db.scalar(
            select(Challenge).where(
                and_(Challenge.trader_id == trader_id, )
            )
        )
        if not challenge:
            return
        if source:
            return challenge.challenge
        return challenge


def get_challenge_by_id(db: Session, challenge_id: int):
    challenge = db.scalar(
        select(Challenge).where(
            and_(
                Challenge.id == challenge_id,
            )
        )
    )
    return challenge


def get_challenge_for_hotkey(hot_key):
    with TaskSessionLocal_() as db:
        challenge = db.scalar(
            select(Challenge).where(
                and_(Challenge.hot_key == hot_key, )
            )
        )
        return challenge


def populate_ambassadors():
    global ambassadors
    with TaskSessionLocal_() as db:
        challenges = db.query(Challenge).all()
        for challenge in challenges:
            ambassadors[challenge.trader_id] = challenge.hot_key


def get_hot_key(trader_id: int):
    global ambassadors
    hot_key = ambassadors.get(trader_id)
    if not hot_key:
        populate_ambassadors()
        hot_key = ambassadors.get(trader_id)
    return hot_key
