# generate_and_email_beast.py
import os, ssl, smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from supabase import create_client
import qrcode
from io import BytesIO
from utils import generate_participant_id, upload_qr_to_storage

load_dotenv()

# Supabase + email config
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

DATA_FILE = os.path.join("data", "participants.txt")
OUT_DIR = os.path.join("data", "qrcodes")
os.makedirs(OUT_DIR, exist_ok=True)

def supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def make_qr_png_bytes(participant_id: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(participant_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def build_email(full_name: str, email: str, participant_id: str, qr_url: str, role: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"{SENDER_NAME} <{SMTP_EMAIL}>"
    msg["To"] = email
    msg["Subject"] = f"{EVENT_NAME}: Your Entry QR Code ({participant_id})"
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
    return msg

def main():
    sb = supabase_client()
    # Fetch existing participants (by email + student_number)
    existing = sb.table("participants").select("email,student_number").execute()
    existing_set = {(r["email"], r["student_number"]) for r in (existing.data or [])}

    to_insert = []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            parts = [p.strip() for p in raw.split(",")]
            if len(parts) < 4:
                print(f"Skipped invalid line: {raw}")
                continue
            email, student_number, full_name, role = parts
            role = role.lower()
            if role not in ("participant", "judge"):
                print(f"Skipped unknown role: {role}")
                continue

            if (email, student_number) in existing_set:
                print(f"Skipping existing participant: {full_name} ({email})")
                continue

            participant_id = generate_participant_id()
            qr_png = make_qr_png_bytes(participant_id)

            # Save locally (optional)
            local_path = os.path.join(OUT_DIR, f"{participant_id}.png")
            with open(local_path, "wb") as imgf:
                imgf.write(qr_png)

            # Upload to Supabase Storage
            qr_url = upload_qr_to_storage(sb, f"{participant_id}.png", qr_png)

            rec = {
                "participant_id": participant_id,
                "role": role,
                "full_name": full_name,
                "email": email,
                "student_number": student_number,
                "year_of_study": None,
                "registration_status": "Registered",
                "confirmation_status": "Confirmed",
                "admission_status": "Granted",
                "qr_code_url": qr_url
            }
            to_insert.append(rec)

    if not to_insert:
        print("No new participants to insert.")
        return

    # Insert new participants
    sb.table("participants").insert(to_insert).execute()
    print(f"Inserted and queued {len(to_insert)} new participants.")

    # Send emails only to new participants
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        for r in to_insert:
            msg = build_email(
                full_name=r["full_name"],
                email=r["email"],
                participant_id=r["participant_id"],
                qr_url=r["qr_code_url"],
                role=r["role"]
            )
            server.send_message(msg)
            print("Sent:", r["email"])

if __name__ == "__main__":
    main()
