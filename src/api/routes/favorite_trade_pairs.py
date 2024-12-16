from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.user import FirebaseUserBase, FavoriteTradePairs
from src.services.user_service import add_to_favorites, remove_from_favorites
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()



@router.post("/", response_model=FirebaseUserBase)
async def add_pair(trade_pair_data: FavoriteTradePairs,  db: Session = Depends(get_db)):
    user = await add_to_favorites( db, trade_pair_data )
    return user

@router.delete("/", response_model=FirebaseUserBase)
async def delete_pair(trade_pair_data: FavoriteTradePairs, db : Session = Depends(get_db)):
    user = await remove_from_favorites( db, trade_pair_data )
    return user
