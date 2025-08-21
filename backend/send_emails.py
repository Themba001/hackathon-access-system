import os, smtplib, ssl, mimetypes
from email.message import EmailMessage
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "Hackathon Team")
EVENT_NAME = os.getenv("EVENT_NAME", "Internal Hackathon")
EVENT_DATE = os.getenv("EVENT_DATE", "")
QR_BUCKET = os.getenv("QR_BUCKET", "qr-codes")

def supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def build_email(full_name: str, email: str, participant_id: str, qr_url: str, role: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"{SENDER_NAME} <{SMTP_EMAIL}>"
    msg["To"] = email
    msg["Subject"] = f"{EVENT_NAME}: Your Entry QR Code ({participant_id})"

    # Friendly copy (adjust as needed)
    body = f"""Hi {full_name},

You're confirmed for the {EVENT_NAME} on {EVENT_DATE}.
Please bring this QR code (attached/linked) to:
 • 🚍 Bus boarding
 • 🏁 Registration (entry)
 • 🍔 Meal collection

Participant ID: {participant_id}
Role: {role.capitalize()}

If you lose the attachment, you can also open the QR here:
{qr_url}

See you there,
— {SENDER_NAME}
"""

    msg.set_content(body)

    # Optional: attach the PNG by downloading it (Storage is public)
    # For speed (and to avoid network in script), we can skip attaching and rely on the link.
    # If you want to attach, uncomment below (requires requests).
    # import requests
    # png = requests.get(qr_url, timeout=10).content
    # maintype, subtype = 'image', 'png'
    # msg.add_attachment(png, maintype=maintype, subtype=subtype, filename=f"{participant_id}.png")

    return msg

def send_all():
    sb = supabase_client()
    # Send to all newly inserted participants (or filter)
    resp = sb.table("participants").select("*").execute()
    rows = resp.data or []

    print(f"Sending emails to {len(rows)} recipients...")

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)

        for r in rows:
            msg = build_email(
                full_name=r["full_name"],
                email=r["email"],
                participant_id=r["participant_id"],
                qr_url=r["qr_code_url"],
                role=r["role"],
            )
            server.send_message(msg)
            print("Sent:", r["email"])

if __name__ == "__main__":
    send_all()
