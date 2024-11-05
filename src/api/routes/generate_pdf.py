import os
import tempfile
from datetime import datetime

import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from weasyprint import HTML

from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from src.database import get_db
from src.schemas.user import GeneratePdfSchema
from src.services.email_service import render_to_string, send_mail
from src.services.user_service import get_firebase_user
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()

s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
bucket_name = "delta-prop-shop-certificates"


@router.post("/", response_model=dict)
async def generate_certificate(user_data: GeneratePdfSchema, db: Session = Depends(get_db)):
    logger.info(f"Generate PDF for user={user_data.firebase_id}")

    user = await get_firebase_user(db, user_data.firebase_id)
    if not user:
        raise HTTPException(status_code=400, detail="User doesn't exist for this firebase_id")

    certificate_name = f"{user_data.hot_key}/{user_data.phase}/{user_data.step}/certificate.pdf"

    try:
        # Check if the certificate exists in S3
        s3.head_object(Bucket=bucket_name, Key=certificate_name)

        # Certificate exists, so download it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf_path = tmp_pdf.name
            s3.download_file(Bucket=bucket_name, Key=certificate_name, Filename=tmp_pdf_path)
            file_message = "Certificate already exists in S3, and was downloaded for email."
    except s3.exceptions.ClientError:
        # Certificate does not exist, generate a new one
        date = datetime.today().strftime("%b %d, %Y")
        rendered_html = render_to_string("src/templates/certificate.html",
                                         {"phase_number": user_data.phase, "name": user.name, "date": date})

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf_path = tmp_pdf.name
            HTML(string=rendered_html).write_pdf(tmp_pdf_path)
            file_message = "Certificate created and uploaded to S3."

            # Upload the generated PDF to S3
            try:
                s3.upload_file(tmp_pdf_path, bucket_name, certificate_name)
            except (NoCredentialsError, PartialCredentialsError):
                raise HTTPException(status_code=500, detail="Error with AWS credentials")

    # Define the email subject, body, and recipient details
    subject = "Your Certificate"
    body = f"{file_message} Please find the certificate attached."

    # Send the email with the PDF attachment
    try:
        send_mail(
            receiver=user.email,
            subject=subject,
            content=body,
            attachment={"path": tmp_pdf_path, "name": certificate_name},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")
    finally:
        # Clean up the temporary PDF file
        if tmp_pdf_path and os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)

    # Return a message indicating the result
    return {"message": file_message}
