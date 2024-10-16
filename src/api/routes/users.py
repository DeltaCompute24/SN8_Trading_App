from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database_tasks import TaskSessionLocal_
from src.models.firebase_user import FirebaseUser
from src.schemas.user import ChallengeRead, ChallengeUpdate
from src.schemas.user import FirebaseUserRead, FirebaseUserCreate, FirebaseUserUpdate
from src.services.email_service import send_mail_in_thread
from src.services.user_service import get_firebase_user, create_firebase_user, create_or_update_challenges, \
    get_challenge_by_id, construct_username, get_user_by_id
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
    try:
        new_user = create_firebase_user(db, user_data.firebase_id, user_data.name, user_data.email)
        new_user = create_or_update_challenges(db, new_user, user_data.challenges)
        return new_user
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[FirebaseUserRead])
def get_users(db: Session = Depends(get_db)):
    logger.info("Fetching Firebase Users")
    users = db.query(FirebaseUser).all()
    return users


@router.get("/{firebase_id}", response_model=FirebaseUserRead)
def get_user(firebase_id: str, db: Session = Depends(get_db)):
    user = get_firebase_user(db, firebase_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User Not Found!")
    return user


@router.put("/{user_id}", response_model=FirebaseUserRead)
def update_user(user_id: int, user_data: FirebaseUserUpdate, db: Session = Depends(get_db)):
    logger.info(f"Create User for user_id={user_id}")

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User Not Found!")
    if user_data.firebase_id:
        existing_user = get_firebase_user(db, user_data.firebase_id)
        if existing_user and existing_user != user:
            raise HTTPException(status_code=400, detail="User with this firebase_id already exists!")
        user.firebase_id = user_data.firebase_id
    if user_data.name:
        user.name = user_data.name
    if user_data.email:
        user.email = user_data.email
        user.username = construct_username(user_data.email)
    db.commit()
    db.refresh(user)

    if not user_data.challenges:
        return user

    user = create_or_update_challenges(db, user, user_data.challenges)
    logger.info(f"User updated successfully with firebase_id={user_data.firebase_id}")
    return user


@router.put("/challenge/{challenge_id}", response_model=ChallengeRead)
def update_challenge(
        challenge_id: int,
        challenge_data: ChallengeUpdate,
        db: Session = Depends(get_db),
):
    try:
        challenge = get_challenge_by_id(db, challenge_id)
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge Not Found!")

        challenge.hot_key = challenge_data.hot_key
        challenge.trader_id = challenge_data.trader_id
        challenge.active = "1"
        challenge.status = "In Challenge"

        db.commit()
        db.refresh(challenge)
        if challenge.user.email:
            send_mail_in_thread(challenge.user.email, "Issuance of trader_id and hot_key",
                                "Congratulations! Your trader_id and hot_key is ready. Now, you can use your system.")
        return challenge
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
