from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.user import GeneratePdfSchema
from src.services.s3_services import send_certificate_email
from src.services.user_service import get_firebase_user
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.post("/", response_model=dict)
async def generate_certificate(user_data: GeneratePdfSchema, db: Session = Depends(get_db)):
    logger.info(f"Generate PDF for user={user_data.firebase_id}")

    user = await get_firebase_user(db, user_data.firebase_id)
    if not user:
        raise HTTPException(status_code=400, detail="User doesn't exist for this firebase_id")

    send_certificate_email(user.email, user.name, user_data)

    # Return a message indicating the result
    return {"message": "Certificate Generated!"}
