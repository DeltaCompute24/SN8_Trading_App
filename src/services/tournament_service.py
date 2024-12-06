import threading

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.models.tournament import Tournament
from src.schemas.tournament import TournamentCreate, TournamentUpdate
from src.services.email_service import send_mail
from src.services.payment_service import create_challenge, register_and_update_challenge, create_payment_entry
from src.services.user_service import get_firebase_user


def create_tournament(db: Session, tournament_data: TournamentCreate):
    tournament = Tournament(
        name=tournament_data.name,
        start_time=tournament_data.start_time,
        end_time=tournament_data.end_time,
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
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if tournament:
        tournament.name = tournament_data.name or tournament.name
        tournament.start_time = tournament_data.start_time or tournament.start_time
        tournament.end_time = tournament_data.end_time or tournament.end_time
        db.commit()
        db.refresh(tournament)
    return tournament


def delete_tournament(db: Session, tournament_id: int):
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if tournament:
        db.delete(tournament)
        db.commit()
    return tournament


def register_payment(db, tournament_id, firebase_id, amount, referral_code):
    # Validate Firebase User
    firebase_user = get_firebase_user(db, firebase_id)
    if not firebase_user or not firebase_user.username:
        raise HTTPException(status_code=400, detail="Invalid Firebase user data")

    # Fetch Tournament
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament Not Found")

    # Prepare Payment Data
    payment_data = {
        "amount": amount,
        "referral_code": referral_code,
        "step": 2,
        "phase": 1,
        "firebase_id": firebase_id,
    }

    # Create Challenge and Associate with Tournament
    new_challenge = create_challenge(
        db,
        payment_data=payment_data,
        network="test",
        user=firebase_user,
        challenge_status="Tournament",
        step=2,
        phase=1,
        tournament_id=tournament_id
    )

    # Thread to handle challenge updates
    thread = threading.Thread(target=register_and_update_challenge,
                              args=(new_challenge.id, "Tournament", tournament_id))
    thread.start()

    # Create Payment Entry
    new_payment = create_payment_entry(db, payment_data, new_challenge)

    # Send Confirmation Email
    send_mail(
        receiver=firebase_user.email,
        template_name="EmailTemplate.html",
        subject="Tournament Registration Confirmed",
        content=f"You are successfully registered in the tournament{tournament.name}",
        context={
            "username": firebase_user.username,
            "tournament": tournament.name,
        },
    )

    return {"message": f"Tournament Payment Registered Successfully"}
