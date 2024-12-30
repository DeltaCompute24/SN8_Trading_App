import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from src.database_tasks import TaskSessionLocal_
from src.models import Tournament
from src.schemas.tournament import TournamentCreate, TournamentRegister, TournamentUpdate, TournamentRead, TournamentScore
from src.services.tournament_service import (
    create_tournament,
    get_tournament_by_id,
    update_tournament,
    delete_tournament,
    register_tournament_payment,
)
from src.utils.constants import TOURNAMENT
from src.utils.logging import setup_logging
from src.utils.redis_manager import get_hash_value

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
        logger.info(f"Tournament created successfully with tournament_id={tournament.id}")
        return tournament
    except Exception as e:
        logger.info(f"Error creating tournament: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[TournamentRead])
def get_all_tournaments_endpoint(db: Session = Depends(get_db)):
    logger.info("Fetching all tournaments")
    return db.query(Tournament).options(joinedload(Tournament.challenges)).all()


@router.get("/score", response_model= TournamentScore)
def participants_score(db: Session = Depends(get_db), tournament_id: int = None):
    logger.info("Return Tournaments Participants Score")
    try:
        scores = get_hash_value(key="0", hash_name=TOURNAMENT)
        scores_list = json.loads(scores) if scores else []
        if not tournament_id:
            return { "statistic" :  scores_list}
        try:
            tournament = db.query(Tournament).options(joinedload(Tournament.challenges)).filter(Tournament.id == tournament_id).first()
            if not tournament:
                raise HTTPException(status_code=404, detail="Tournament not found")
            for tournament_scores in scores_list:
                if tournament_scores["tournament"] == tournament.name:
                    return { "statistic" :  tournament_scores  ,  "tournament" :  tournament}
            return { "statistic" :  []  ,  "tournament" :  tournament}
        finally:
            db.close()
    except Exception as e:
        logger.info(f"Error during fetching score: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error as {e}")


@router.get("/{tournament_id}", response_model=TournamentRead)
def get_tournament_by_id_endpoint(tournament_id: int, db: Session = Depends(get_db)):
    tournament = get_tournament_by_id(db, tournament_id)
    if not tournament:
        logger.info(f"Tournament with id={tournament_id} not found")
        raise HTTPException(status_code=404, detail="Tournament Not Found")
    return tournament


@router.put("/{tournament_id}", response_model=TournamentRead)
def update_tournament_endpoint(tournament_id: int, tournament_data: TournamentUpdate, db: Session = Depends(get_db)):
    tournament = update_tournament(db, tournament_id, tournament_data)
    if not tournament:
        logger.info(f"Tournament with id={tournament_id} not found")
        raise HTTPException(status_code=404, detail="Tournament Not Found")
    return tournament


# @router.delete("/{tournament_id}")
def delete_tournament_endpoint(tournament_id: int, db: Session = Depends(get_db)):
    tournament = delete_tournament(db, tournament_id)
    if not tournament:
        logger.info(f"Tournament with id={tournament_id} not found")
        raise HTTPException(status_code=404, detail="Tournament Not Found")
    return {"message": "Tournament deleted successfully"}


@router.post("/register-payment")
def register_tournament_endpoint(
        tournament_register: TournamentRegister,
        db: Session = Depends(get_db)):
    logger.info(
        f"Registering for tournament {tournament_register.tournament_id} with firebase_id={tournament_register.firebase_id}")
    try:
        # Create Challenge and Associate with Tournament
        message = register_tournament_payment(db, tournament_register.tournament_id, tournament_register.firebase_id,
                                              tournament_register.amount, tournament_register.referral_code)
        return message
    except Exception as e:
        logger.info(f"Error during registration: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error as {e}")
