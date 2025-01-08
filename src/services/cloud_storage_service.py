import tempfile
from datetime import datetime

from fastapi import APIRouter, HTTPException
from google.cloud import storage
from weasyprint import HTML

from src.config import GCP_BUCKET, GCP_PROJECT
from src.services.email_service import render_to_string
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()

# Initialize GCP storage client and bucket
# Initialize the gcp from the terminal by this command ```gcloud auth application-default login```
client = storage.Client(project=GCP_PROJECT)
bucket = client.bucket(GCP_BUCKET)


def get_certificate_from_gcp(certificate_name):
    """
    Get the certificate from GCP if it exists and return the path to the downloaded certificate.
    """
    try:
        # Check if the certificate exists in GCP
        blob = bucket.blob(certificate_name)
        if not blob.exists():
            return None

        # Download the certificate to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf_path = tmp_pdf.name
            blob.download_to_filename(tmp_pdf_path)
            return tmp_pdf_path
    except Exception as e:
        logger.error(f"Error while downloading certificate from GCP: {e}")
        return None


def upload_certificate_to_gcp(certificate_name, name, phase):
    """
    Upload the certificate to GCP Cloud Storage.
    """
    # Generate certificate content
    date = datetime.today().strftime("%b %d, %Y")
    rendered_html = render_to_string(
        template_name="CongratulationsCertificate.html",
        context={"phase": phase, "name": name, "date": date},
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf_path = tmp_pdf.name
        HTML(string=rendered_html).write_pdf(tmp_pdf_path)

        # Upload the generated PDF to GCP
        try:
            blob = bucket.blob(certificate_name)
            blob.upload_from_filename(tmp_pdf_path)
            logger.info(f"Certificate {certificate_name} uploaded to GCP.")
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error uploading to GCP storage")
        return tmp_pdf_path


def get_certificate_gcp(certificate_name, name, phase):
    """
    Get the certificate from GCP Cloud Storage if it exists; otherwise, generate and upload a new one.
    """
    tmp_pdf_path = get_certificate_from_gcp(certificate_name)
    if not tmp_pdf_path:
        tmp_pdf_path = upload_certificate_to_gcp(certificate_name, name, phase)
    return tmp_pdf_path
