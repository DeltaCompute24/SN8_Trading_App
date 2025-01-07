import os
import tempfile
from datetime import datetime

import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from fastapi import APIRouter, HTTPException
from weasyprint import HTML

from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, BUCKET_NAME
from src.services.cloud_storage_service import get_certificate_gcp
from src.services.email_service import render_to_string, send_mail
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()

s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)


def get_certificate_from_s3(certificate_name):
    """
    Get the certificate from S3 if it exists and return the path to the downloaded certificate
    """
    try:
        # Check if the certificate exists in S3
        s3.head_object(Bucket=BUCKET_NAME, Key=certificate_name)

        # Certificate exists, so download it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf_path = tmp_pdf.name
            s3.download_file(Bucket=BUCKET_NAME, Key=certificate_name, Filename=tmp_pdf_path)
            return tmp_pdf_path
    except s3.exceptions.ClientError:
        return None


def upload_certificate_to_s3(certificate_name, name, phase):
    """
    Upload the certificate to S3
    """
    # Certificate does not exist, generate a new one
    date = datetime.today().strftime("%b %d, %Y")
    rendered_html = render_to_string(template_name="CongratulationsCertificate.html",
                                     context={"phase": phase, "name": name, "date": date})

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf_path = tmp_pdf.name
        HTML(string=rendered_html).write_pdf(tmp_pdf_path)

        # Upload the generated PDF to S3
        try:
            s3.upload_file(tmp_pdf_path, BUCKET_NAME, certificate_name)
        except (NoCredentialsError, PartialCredentialsError):
            raise HTTPException(status_code=500, detail="Error with AWS credentials")
        return tmp_pdf_path


def get_certificate(certificate_name, name, phase):
    """
    Get the certificate from S3 if it exists and return the path to the downloaded certificate
    """
    tmp_pdf_path = get_certificate_from_s3(certificate_name)
    if not tmp_pdf_path:
        tmp_pdf_path = upload_certificate_to_s3(certificate_name, name, phase)
    return tmp_pdf_path


def send_certificate_email(email, name, data, celery_task=False):
    """
    Send the certificate email to the user
    """
    certificate_name = f"{data.hot_key}/{data.phase}/{data.step}/certificate.pdf"
    tmp_pdf_path = get_certificate_gcp(certificate_name, name, data.phase)

    attachment = {
        "path": tmp_pdf_path,
        "name": "certificate.pdf",
    }
    if celery_task:
        return attachment
    # Define the email subject, body, and recipient details
    subject = f"Phase {data.phase} Certificate"
    body = "You have successfully Passed. Please find the certificate attached."

    # Send the email with the PDF attachment
    try:
        send_mail(
            receiver=email,
            subject=subject,
            content=body,
            template_name="",
            attachment=attachment,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")
    finally:
        # Clean up the temporary PDF file
        if tmp_pdf_path and os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)
