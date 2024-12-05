from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.models.tournament import Tournament
from src.schemas.tournament import TournamentCreate, TournamentUpdate


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
