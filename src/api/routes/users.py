from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.user_service import get_firebase_user, create_firebase_user, create_or_update_challenges
from src.database_tasks import TaskSessionLocal_
from src.models.firebase_user import FirebaseUser
from src.schemas.user import FirebaseUserRead, FirebaseUserCreate, FirebaseUserUpdate
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


# Dependency
def get_db():
    db = TaskSessionLocal_()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=FirebaseUserRead)
def create_user(user_data: FirebaseUserCreate, db: Session = Depends(get_db)):
    logger.info(f"Create User for trader_id={user_data.firebase_id}")

    existing_user = get_firebase_user(db, user_data.firebase_id)
    if existing_user:
        logger.error("A user already exists for this firebase_id")
        raise HTTPException(status_code=400, detail="A user already exists for this firebase_id")

    try:
        new_user = create_firebase_user(db, user_data)
        logger.info(f"User created successfully with firebase id {user_data.firebase_id}")
        return new_user

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[FirebaseUserRead])
def get_users(db: Session = Depends(get_db)):
    logger.info("Fetching Firebase Users")
    return db.query(FirebaseUser).all()


@router.get("/{firebase_id}", response_model=FirebaseUserRead)
def get_user(firebase_id: str, db: Session = Depends(get_db)):
    user = get_firebase_user(db, firebase_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User Not Found!")
    return user


@router.put("/{firebase_id}", response_model=FirebaseUserRead)
def update_user(firebase_id: str, user_data: FirebaseUserUpdate, db: Session = Depends(get_db)):
    logger.info(f"Create User for trader_id={firebase_id}")

    user = get_firebase_user(db, firebase_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User Not Found!")

    if user_data.firebase_id:
        user = get_firebase_user(db, user_data.firebase_id)
        if user:
            raise HTTPException(status_code=400, detail="User with this firebase_id already exist!")
        user.firebase_id = user_data.firebase_id
        db.commit()
        db.refresh(user)

    if not user_data.challenges:
        return user

    user = create_or_update_challenges(db, user, user_data.challenges)
    logger.info(f"User updated successfully with firebase_id={user_data.firebase_id}")
    return user
