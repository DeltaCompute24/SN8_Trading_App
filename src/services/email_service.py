import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader

from src.config import EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD


def render_to_string(template_name, context=None):
    # Set up the Jinja2 environment to look for templates in the current directory
    env = Environment(loader=FileSystemLoader(searchpath="./"))
    template = env.get_template(template_name)

    # Render the template with the context and return as a string
    return template.render(context)


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
        context = {'email': receiver, 'text': content}
        html_content = render_to_string('src/templates/email_template.html', context)
        message.attach(MIMEText(html_content, 'html'))  # HTML version

        image_path = 'src/templates/image1.png'
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
            image = MIMEImage(img_data)
            image.add_header('Content-ID', '<image1>')  # Content-ID to reference in the HTML
            image.add_header('Content-Disposition', 'inline', filename=image_path)
            message.attach(image)

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
