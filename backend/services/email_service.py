import os, ssl, smtplib
from email.message import EmailMessage
from dotenv import load_dotenv


load_dotenv()
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "Hackathon Team")
EVENT_NAME = os.getenv("EVENT_NAME", "Internal Hackathon")




def send_download_link(to_email: str, full_name: str, url: str):
    msg = EmailMessage()
    msg["From"] = f"{SENDER_NAME} <{SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = f"Your {EVENT_NAME} Ticket"


    body = f"""Hi {full_name},


    Your ticket for the {EVENT_NAME} is ready.
    Please download it here (keep it safe and bring it on the day):
    {url}


    See you there!
    — {SENDER_NAME}
    """
    msg.set_content(body)


    ctx = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls(context=ctx)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)