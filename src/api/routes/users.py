from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database_tasks import get_sync_db
from src.models.firebase_user import FirebaseUser
from src.schemas.user import FirebaseUserRead, FirebaseUserCreate, FirebaseUserUpdate
from src.services.user_service import get_firebase_user, create_firebase_user, construct_username
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.post("/", response_model=FirebaseUserRead)
def create_user(user_data: FirebaseUserCreate, db: Session = Depends(get_sync_db)):
    logger.info(f"Create User for trader_id={user_data.firebase_id}")
    if not user_data.firebase_id or not user_data.name or not user_data.email:
        raise HTTPException(status_code=400, detail="Firebase id, Name or Email can't be Empty!")
    try:
        return create_firebase_user(db, user_data.firebase_id, user_data.name, user_data.email)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[FirebaseUserRead])
def get_users(db: Session = Depends(get_sync_db)):
    logger.info("Fetching Firebase Users")
    users = db.query(FirebaseUser).all()
    return users


@router.get("/{firebase_id}", response_model=FirebaseUserRead)
def get_user(firebase_id: str, db: Session = Depends(get_sync_db)):
    user = get_firebase_user(db, firebase_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User Not Found!")
    return user


@router.put("/{firebase_id}", response_model=FirebaseUserRead)
def update_user(firebase_id: str, user_data: FirebaseUserUpdate, db: Session = Depends(get_sync_db)):
    user = get_firebase_user(db, firebase_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User Not Found!")
    if user_data.name:
        user.name = user_data.name
    if user_data.email:
        user.email = user_data.email
        user.username = construct_username(user_data.email)
    db.commit()
    db.refresh(user)
    logger.info(f"User updated successfully with firebase_id={firebase_id}")
    return user
