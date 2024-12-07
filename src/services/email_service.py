import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader

from src.config import EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, SUPPORT_EMAIL
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue


def render_to_string(template_name, context=None):
    """
    Render the template with the context and return as a string
    """
    templates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    env = Environment(loader=FileSystemLoader(searchpath=templates_path))
    template = env.get_template(template_name)
    return template.render(context or {})


def send_mail(
        receiver,
        subject,
        content="",
        attachment=None,
        template_name='PaymentConfirmed.html',
        context=None,
):
    """
    Send an email with a subject and body content to the specified receiver.
    """
    if not receiver:
        return
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
        message["Bcc"] = SUPPORT_EMAIL

        # Attach the template body
        if template_name:
            if not context:
                context = {'email': receiver, 'text': content}
            html_content = render_to_string(template_name=template_name, context=context)
            message.attach(MIMEText(html_content, 'html'))  # HTML version

        # Attach the PDF file
        if attachment:
            pdf_file = attachment.get("path")
            with open(pdf_file, 'rb') as f:
                file = MIMEApplication(f.read(), _subtype="pdf")
                file.add_header('Content-Disposition', 'attachment', filename=attachment.get("name"))
                message.attach(file)

        # Log the email contents to ensure they're correct
        print(f"Email details: \nFrom: {EMAIL_HOST_USER}\nTo: {receiver}\nSubject: {subject}\nContent: {content}")

        # Convert the message to a string and send
        text = message.as_string()
        recipients = [receiver, SUPPORT_EMAIL]
        server.sendmail(EMAIL_HOST_USER, recipients, text)

    except Exception as exp:
        print(f"ERROR: {exp}")
        push_to_redis_queue(data=f"**SEND EMAIL ERROR** => {exp}", queue_name=ERROR_QUEUE_NAME)
    finally:
        # Close the server connection
        if server:
            server.quit()

def send_support_email(subject, content):
    send_mail(
        receiver=SUPPORT_EMAIL,
        subject=subject,
        content=content,
        template_name="EmailTemplate.html",
    )
