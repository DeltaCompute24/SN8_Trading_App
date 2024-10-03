import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import HTTPException

from src.config import EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD


def send_mail(receiver, subject, content):
    """
    - call setup_server to get server object
    - ready the email message
    - send email using server
    """
    server = None
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)

        message = MIMEMultipart()
        message['From'] = EMAIL_HOST_USER
        message['To'] = receiver
        message['Subject'] = subject
        text = message.as_string()

        # Add body to email
        message.attach(MIMEText(content, 'plain'))
        server.sendmail(EMAIL_HOST, receiver, text)
    except Exception as exp:
        raise HTTPException(status_code=400, detail="Email is not sent Successfully!")
    finally:
        # Close the server
        if server:
            server.quit()
