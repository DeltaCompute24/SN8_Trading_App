import smtplib
import ssl
from email.message import EmailMessage

from src.config import EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS
from src.templates.email_template import welcome_template


def setup_server():
    """
    Setup Server to send email using TLS
    """
    context = ssl.create_default_context()
    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)

    if EMAIL_USE_TLS:
        server.starttls(context=context)

    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    return server


def send_mail(receiver, subject, content):
    """
    - call setup_server to get server object
    - ready the email message
    - send email using server
    """
    server = None
    try:
        server = setup_server()
        msg = EmailMessage()
        msg['From'] = EMAIL_HOST_USER
        msg['To'] = receiver
        msg['Subject'] = subject
        msg.set_content(content, subtype='html')

        server.send_message(msg)
        print('Successfully sent mail')
    except Exception as exp:
        print(f'Exception Raised: {exp}')
    finally:
        if server:
            server.quit()


def send_welcome_email(email):
    """
    - generate otp
    - store otp in model
    - call send_mail function
    """
    subject = 'Welcome Email'
    content = welcome_template(email)
    send_mail(email, subject, content)
