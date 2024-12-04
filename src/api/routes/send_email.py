from fastapi import APIRouter, HTTPException

from src.schemas.user import EmailInput
from src.services.email_service import send_mail
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.post("/", response_model=dict)
async def send_welcome_email(email_input: EmailInput):
    email = email_input.email
    _type = email_input.type.lower()

    if _type not in ["payment-confirmed", "setup-completed"]:
        raise HTTPException(status_code=400,
                            detail="Invalid email type. Please enter 'payment-confirmed' or 'setup-completed'")

    logger.info(f"Send Welcome Email to User: {email}")

    try:
        send_mail(
            receiver=email,
            subject=f"User, {_type.replace('-', ' ').title()}",
            context={"name": "User"}
        )
        return {
            "detail": "Email sent Successfully!"
        }

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=str(e))
