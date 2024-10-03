import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import HTTPException

from src.config import EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD


def send_mail(receiver, subject, content):
    """
    Send an email with a subject and body content to the specified receiver.
    """
    server = None
    try:
        # Set up the server connection
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)

        # Create the email
        message = MIMEMultipart()
        message['From'] = EMAIL_HOST_USER
        message['To'] = receiver
        message['Subject'] = subject

        # Attach the email body
        message.attach(MIMEText(content, 'plain'))

        # Log the email contents to ensure they're correct
        print(f"Email details: \nFrom: {EMAIL_HOST_USER}\nTo: {receiver}\nSubject: {subject}\nContent: {content}")

        # Convert the message to a string and send
        text = message.as_string()
        server.sendmail(EMAIL_HOST_USER, receiver, text)

    except Exception as exp:
        raise HTTPException(status_code=400, detail=f"Email not sent successfully! Error: {str(exp)}")

    finally:
        # Close the server connection
        if server:
            server.quit()
