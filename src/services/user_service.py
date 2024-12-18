import re

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.database_tasks import TaskSessionLocal_
from src.models import UsersBalance
from src.models.challenge import Challenge
from src.models.firebase_user import FirebaseUser
from src.models.users import Users
from src.schemas.user import UsersBase, FavoriteTradePairs
from src.services.email_service import send_mail
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


async def get_user_by_email(db: AsyncSession, email: str):
    user = await db.scalar(
        select(FirebaseUser).where(
            and_(
                FirebaseUser.email == email,
            )
        )
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found for id: {email}"
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


def create_firebase_user(db: Session, firebase_id: str, name: str = "", email: str = ""):
    if not firebase_id:
        raise HTTPException(status_code=400, detail="Firebase id can't be Empty!")
    firebase_user = get_firebase_user(db, firebase_id)
    username = construct_username(email)
    if not firebase_user:
        firebase_user = FirebaseUser(
            firebase_id=firebase_id,
            name=name,
            email=email,
            username=username,
        )
        db.add(firebase_user)
        # send email
        send_mail(
            email,
            subject="Welcome to Delta Prop Shop",
            template_name="WelcomeEmail.html",
            context={
                "name": name or "User",
            }
        )
    else:
        firebase_user.name = name
        firebase_user.email = email
        firebase_user.username = username
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


def bulk_update_challenges(db: Session, data):
    db.execute(
        update(Challenge),
        data,
    )
    db.commit()


# ---------------------- USER BALANCE ------------------------------

def get_user_balance(db: Session, hot_key: str):
    try:
        user_balance = db.scalar(
            select(UsersBalance).where(
                and_(
                    UsersBalance.hot_key == hot_key,
                )
            )
        )
        return user_balance
    except Exception as e:
        return None


def create_user_balance(db: Session, user_data):
    try:
        user_balance = UsersBalance(
            trader_id=user_data.trader_id,
            hot_key=user_data.hot_key,
            balance=user_data.balance,
            balance_as_on=user_data.balance_as_on,
        )
        db.add(user_balance)
        db.commit()
        db.refresh(user_balance)
        return user_balance
    except Exception as e:
        logger.error(f"Error creating user balance: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def add_to_favorites(db: Session, trade_pair_data: FavoriteTradePairs) -> FirebaseUser:
    user: FirebaseUser = await get_user_by_email(db, trade_pair_data.email)
    favorite_trade_pairs = list(user.favorite_trade_pairs or [])

    if trade_pair_data.trade_pair in favorite_trade_pairs:
        return user

    user.favorite_trade_pairs = favorite_trade_pairs + [trade_pair_data.trade_pair]
    await db.flush()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    print(f"Done")

    return user


async def remove_from_favorites(db: Session, trade_pair_data: FavoriteTradePairs) -> FirebaseUser:
    user: FirebaseUser = await get_user_by_email(db, trade_pair_data.email)

    if trade_pair_data.trade_pair not in user.favorite_trade_pairs:
        return user

    updated_pairs = list(user.favorite_trade_pairs)
    try:
        updated_pairs.remove(trade_pair_data.trade_pair)
    except Exception as ex:
        pass

    user.favorite_trade_pairs = updated_pairs

    await db.commit()
    await db.refresh(user)
    return user
