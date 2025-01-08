import threading
from datetime import datetime

import pytz
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.models.tournament import Tournament
from src.schemas.tournament import TournamentCreate, TournamentUpdate
from src.schemas.user import PaymentCreate
from src.services.email_service import send_mail
from src.services.payment_service import create_challenge, create_payment_entry, register_and_update_challenge
from src.services.user_service import get_firebase_user
from src.validations.time_validations import convert_to_etc


def create_tournament(db: Session, tournament_data: TournamentCreate):
    tournament_data.start_time = tournament_data.start_time.replace(second=0, microsecond=0)
    tournament_data.end_time = tournament_data.end_time.replace(second=0, microsecond=0)

    tournament = Tournament(
        **tournament_data.model_dump()
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return tournament


def get_tournament_by_id(db: Session, tournament_id: int):
    tournament = db.scalar(
        select(Tournament).where(
            and_(
                Tournament.id == tournament_id
            )
        )
    )
    return tournament


def update_tournament(db: Session, tournament_id: int, tournament_data: TournamentUpdate):
    tournament = get_tournament_by_id(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament Not Found!")

    if tournament_data.name:
        tournament.name = tournament_data.name
    if tournament_data.start_time:
        tournament.start_time = tournament_data.start_time.replace(second=0, microsecond=0)
    if tournament_data.end_time:
        tournament.end_time = tournament_data.end_time.replace(second=0, microsecond=0)
    if tournament_data.active is not None:
        tournament.active = tournament_data.active
    if tournament_data.prize:
        tournament.prize = tournament_data.prize
    if tournament_data.cost:
        tournament.cost = tournament_data.cost

    db.commit()
    db.refresh(tournament)
    return tournament


def delete_tournament(db: Session, tournament_id: int):
    tournament = get_tournament_by_id(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament Not Found!")

    db.delete(tournament)
    db.commit()
    return tournament


def register_tournament_payment(db, tournament_id, firebase_id, amount, referral_code):
    # Validate Firebase User
    firebase_user = get_firebase_user(db, firebase_id)
    if not firebase_user or not firebase_user.username:
        raise HTTPException(status_code=400, detail="Invalid Firebase user data")

    # Fetch Tournament
    tournament = get_tournament_by_id(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament Not Found")

    now = datetime.now(pytz.utc).replace(second=0, microsecond=0).replace(tzinfo=None)
    if tournament.end_time <= now:
        raise HTTPException(status_code=404, detail="Tournament has ended!")

    # Prepare Payment Data
    payment_data = PaymentCreate(
        amount=amount,
        referral_code=referral_code,
        step=2,
        firebase_id=firebase_id,
    )

    # Create Challenge
    new_challenge = create_challenge(
        db,
        payment_data=payment_data,
        network="test",
        phase=1,
        user=firebase_user,
        challenge_status="Tournament",
    )

    # Associate Challenge with Tournament
    new_challenge.tournament_id = tournament.id
    tournament.challenges.append(new_challenge)
    db.add(new_challenge)
    db.commit()
    db.refresh(new_challenge)

    context = {
        "name": firebase_user.name or "User",
        "tournament": tournament,
        "start_time": convert_to_etc(tournament.start_time),
        "end_time": convert_to_etc(tournament.end_time),
    }

    # Thread to handle challenge updates
    thread = threading.Thread(
        target=register_and_update_challenge,
        args=(
            new_challenge.id,
            "Tournament",
            tournament.name,
            "TournamentDetail.html",
            context,
        ),
    )
    thread.start()

    # Create Payment Entry
    create_payment_entry(db, payment_data, 1, new_challenge)

    # Send Confirmation Email
    send_mail(
        receiver=firebase_user.email,
        template_name="TournamentRegistrationDetails.html",
        subject="Tournament Registration Confirmed",
        context=context,
    )

    return {"message": f"Tournament Payment Registered Successfully"}


async def get_tournament(db: AsyncSession, tournament_id: int):
    """
    Fetch a tournament by its ID using AsyncSession.

    Args:
        db: The asynchronous database session.
        tournament_id: The ID of the tournament to fetch.

    Returns:
        The Tournament object or None if not found.
    """
    result = await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    return result.scalars().first()


def update_tournament_object(db: Session, tournament, data):
    for key, value in data.items():
        setattr(tournament, key, value)

    db.commit()
    db.refresh(tournament)
    return tournament
