from fastapi import APIRouter, HTTPException

from src.schemas.user import EmailInput
from src.services.email_service import send_mail
from src.templates.email_template import welcome_template
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.post("/", response_model=dict)
async def send_welcome_email(email_input: EmailInput):
    email = email_input.email

    logger.info(f"Send Welcome Email to User {email}")

    try:
        subject = 'Welcome Email'
        content = welcome_template(email)
        send_mail(email, subject, content)
        logger.info(f"Email sent Successfully!")

        return {
            "detail": "Email sent Successfully!"
        }

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=str(e))
