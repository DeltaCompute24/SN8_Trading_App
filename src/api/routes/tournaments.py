from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database_tasks import TaskSessionLocal_
from src.models import Tournament
from src.schemas.tournament import TournamentCreate, TournamentUpdate, TournamentRead
from src.services.tournament_service import (
    create_tournament,
    get_tournament_by_id,
    update_tournament,
    delete_tournament,
)
from src.utils.logging import setup_logging

router = APIRouter()
logger = setup_logging()


def get_db():
    db = TaskSessionLocal_()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=TournamentRead)
def create_tournament_endpoint(tournament_data: TournamentCreate, db: Session = Depends(get_db)):
    try:
        tournament = create_tournament(db, tournament_data)
        logger.error(f"Tournament created successfully with tournament_id={tournament.id}")
        return tournament
    except Exception as e:
        logger.error(f"Error creating tournament: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[TournamentRead])
def get_all_tournaments_endpoint(db: Session = Depends(get_db)):
    logger.info("Fetching all tournaments")
    return db.query(Tournament).all()


@router.get("/{tournament_id}", response_model=TournamentRead)
def get_tournament_by_id_endpoint(tournament_id: int, db: Session = Depends(get_db)):
    tournament = get_tournament_by_id(db, tournament_id)
    if not tournament:
        logger.error(f"Tournament with id={tournament_id} not found")
        raise HTTPException(status_code=404, detail="Tournament Not Found")
    return tournament


@router.put("/{tournament_id}", response_model=TournamentRead)
def update_tournament_endpoint(tournament_id: int, tournament_data: TournamentUpdate, db: Session = Depends(get_db)):
    tournament = update_tournament(db, tournament_id, tournament_data)
    if not tournament:
        logger.error(f"Tournament with id={tournament_id} not found")
        raise HTTPException(status_code=404, detail="Tournament Not Found")
    return tournament


@router.delete("/{tournament_id}")
def delete_tournament_endpoint(tournament_id: int, db: Session = Depends(get_db)):
    tournament = delete_tournament(db, tournament_id)
    if not tournament:
        logger.warning(f"Tournament with id={tournament_id} not found")
        raise HTTPException(status_code=404, detail="Tournament Not Found")
    return {"message": "Tournament deleted successfully"}
