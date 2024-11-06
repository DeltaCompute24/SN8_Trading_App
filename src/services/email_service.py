import smtplib
import threading
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader

from src.config import EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD


def render_to_string(template_name, context=None):
    """
    Render the template with the context and return as a string
    """
    env = Environment(loader=FileSystemLoader(searchpath="./src/templates/"))
    template = env.get_template(template_name)
    return template.render(context)


def send_mail(receiver, subject, content, attachment=None):
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

        # Attach the email body
        context = {'email': receiver, 'text': content}
        html_content = render_to_string(template_name='email_template.html', context=context)
        message.attach(MIMEText(html_content, 'html'))  # HTML version

        # Attach the PDF file
        if attachment:
            pdf_file = attachment.get("path")
            with open(pdf_file, 'rb') as f:
                file = MIMEApplication(f.read(), _subtype="pdf")
                file.add_header('Content-Disposition', 'attachment', filename=attachment.get("name"))
                message.attach(file)

        # Attach the image
        image_path = 'src/templates/email_template_image.png'
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
            image = MIMEImage(img_data)
            image.add_header('Content-ID', '<email_template_image>')  # Content-ID to reference in the HTML
            image.add_header('Content-Disposition', 'inline', filename=image_path)
            message.attach(image)

        # Log the email contents to ensure they're correct
        print(f"Email details: \nFrom: {EMAIL_HOST_USER}\nTo: {receiver}\nSubject: {subject}\nContent: {content}")

        # Convert the message to a string and send
        text = message.as_string()
        server.sendmail(EMAIL_HOST_USER, receiver, text)

    except Exception as exp:
        print(f"ERROR: {exp}")
    finally:
        # Close the server connection
        if server:
            server.quit()


def send_mail_in_thread(receiver, subject, content):
    email_thread = threading.Thread(target=send_mail, args=(receiver, subject, content))
    email_thread.start()
