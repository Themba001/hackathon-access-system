import os
import re
import csv
import smtplib
import qrcode
from dotenv import load_dotenv
from email.message import EmailMessage
from fpdf import FPDF
from pathlib import Path
from io import BytesIO

# ✅ Try to import Supabase
try:
    import supabase
    SUPABASE_ENABLED = True
except ImportError:
    print("⚠️ Supabase not installed. Running without DB sync.")
    SUPABASE_ENABLED = False

# =========================
# Load Environment Variables
# =========================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("EMAIL_USER")
SMTP_PASS = os.getenv("EMAIL_PASS")
SENDER_NAME = os.getenv("SENDER_NAME", "Hackathon Team")

EVENT_NAME = os.getenv("EVENT_NAME", "Hackathon Event")
EVENT_DATE = os.getenv("EVENT_DATE", "TBD")
EVENT_CODE = os.getenv("EVENT_CODE", "HACK2025")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
TICKETS_DIR = Path(os.getenv("TICKETS_DIR", "tickets"))
TICKETS_DIR.mkdir(exist_ok=True)

PARTICIPANTS_FILE = Path("../data/participants.txt")

# ✅ Define A6 size (mm) for PDF ticket
A6_SIZE_MM = (105, 148)  # width x height in mm

# =========================
# Initialize Supabase Client
# =========================
if SUPABASE_ENABLED and SUPABASE_URL and SUPABASE_KEY:
    supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase_client = None
    SUPABASE_ENABLED = False

# =========================
# Helpers
# =========================

def normalize_student_number(raw: str) -> str:
    digits = re.sub(r"\D", "", str(raw or ""))
    return digits[:8] if len(digits) >= 8 else digits

def generate_qr(participant_id: str) -> bytes:
    qr_data = f"{BASE_URL}/checkin/{participant_id}"
    img = qrcode.make(qr_data)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def _pdf_to_bytes(pdf: FPDF) -> bytes:
    try:
        buf = BytesIO()
        pdf.output(buf)  # fpdf2 supports file-like output
        return buf.getvalue()
    except TypeError:
        out = pdf.output(dest="S")
        if isinstance(out, (bytes, bytearray)):
            return bytes(out)
        return str(out).encode("latin-1", errors="ignore")

def build_pdf_ticket(full_name: str, email: str, participant_id: str, role: str, qr_bytes: bytes) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format=A6_SIZE_MM)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    page_w, page_h = A6_SIZE_MM
    margin = 10
    gap = 6
    qr_size = 50
    left_w = page_w - (2 * margin) - qr_size - gap
    left_x = margin
    start_y = margin + 10

    pdf.set_font("Helvetica", size=12)

    def left_line(text: str, ln_height: float = 8):
        y = pdf.get_y() if pdf.get_y() > 0 else start_y
        pdf.set_xy(left_x, y)
        pdf.multi_cell(left_w, ln_height, text)

    pdf.set_xy(left_x, start_y)
    left_line(f"Name: {full_name}")
    left_line(f"Email: {email}")
    left_line(f"Participant Type: {role.capitalize()}")
    left_line(f"Event: {EVENT_NAME}")
    left_line(f"Date: {EVENT_DATE}")
    left_line(f"Event Code: {EVENT_CODE}")

    qr_x = page_w - margin - qr_size
    text_height_est = 6 * 8 + 4
    qr_y = start_y + max(0, (text_height_est - qr_size) / 2)

    qr_path = TICKETS_DIR / f"{participant_id}_qr.png"
    with open(qr_path, "wb") as f:
        f.write(qr_bytes)
    pdf.image(str(qr_path), x=qr_x, y=qr_y, w=qr_size)
    qr_path.unlink(missing_ok=True)

    return _pdf_to_bytes(pdf)

def build_email(full_name: str, recipient_email: str, participant_id: str, qr_bytes: bytes, role: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"{EVENT_NAME} Ticket"
    msg["From"] = f"{SENDER_NAME} <{SMTP_USER}>"
    msg["To"] = recipient_email
    msg.set_content(
        f"Hi {full_name},\n\n"
        f"Please find attached your ticket for {EVENT_NAME}.\n\n"
        f"See you there!"
    )

    # ✅ Correct order
    pdf_bytes = build_pdf_ticket(full_name, recipient_email, participant_id, role, qr_bytes)

    filename = f"{participant_id}_{full_name}.pdf"
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)
    return msg

def send_email(msg: EmailMessage):
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"✅ Email sent to {msg['To']}")
    except Exception as e:
        print(f"❌ Failed to send email to {msg['To']}: {e}")

# =========================
# File Loading
# =========================

def parse_row(parts):
    # Expected: email, studentNumber, fullName, role
    if len(parts) < 4:
        return None

    student_number = normalize_student_number(parts[1])
    full_name = parts[2].strip()
    role = parts[3].strip().lower()

    # ✅ Always generate email from student number
    email = f"{student_number}@mynwu.ac.za"

    return {
        "email": email,
        "student_number": student_number,
        "participant_id": student_number,
        "full_name": full_name,
        "role": role
    }

def load_participants_from_file():
    participants = []
    if not PARTICIPANTS_FILE.exists():
        print(f"⚠️ Participants file not found: {PARTICIPANTS_FILE}")
        return participants

    with open(PARTICIPANTS_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for raw in reader:
            if not raw or (len(raw) == 1 and raw[0].startswith("#")):
                continue
            parsed = parse_row(raw)
            if parsed:
                participants.append(parsed)
    return participants

def insert_new_participants(participants):
    if not SUPABASE_ENABLED:
        return 0

    inserted = 0
    for p in participants:
        try:
            existing = supabase_client.table("participants").select("participant_id").eq("participant_id", p["participant_id"]).execute()
            if existing.data:
                continue

            supabase_client.table("participants").insert(p).execute()
            inserted += 1
            print(f"🆕 Inserted participant {p['participant_id']} ({p['full_name']})")
        except Exception as e:
            print(f"❌ Failed to insert {p}: {e}")
    return inserted

# =========================
# Main
# =========================

def main():
    print("🚀 Starting ticket generation and email process...")

    participants_from_file = load_participants_from_file()
    if participants_from_file:
        insert_new_participants(participants_from_file)

    participants = []
    if SUPABASE_ENABLED:
        try:
            res = supabase_client.table("participants").select("*").execute()
            participants = res.data or []
        except Exception as e:
            print(f"❌ Error fetching participants: {e}")

    if not participants and participants_from_file:
        participants = participants_from_file

    if not participants:
        print("⚠️ No participants found.")
        return

    print(f"✅ Found {len(participants)} participants to process.\n")

    for rec in participants:
        pid = rec.get("participant_id")
        email = rec.get("email")
        full_name = rec.get("full_name", "Unknown")
        role = rec.get("role", "participant")

        if not pid or not email:
            print(f"❌ Skipping record with missing ID/email: {rec}")
            continue

        ticket_path = TICKETS_DIR / f"{pid}_{full_name}.pdf"
        if ticket_path.exists():
            print(f"⏩ Ticket already exists for {email} ({pid}), skipping.")
            continue

        print(f"📝 Generating ticket for {full_name} ({email})")
        try:
            qr_bytes = generate_qr(pid)
            msg = build_email(full_name, email, pid, qr_bytes, role)
            send_email(msg)

            with open(ticket_path, "wb") as f:
                f.write(msg.get_payload()[-1].get_payload(decode=True))
            print(f"💾 Ticket saved: {ticket_path}\n")
        except Exception as e:
            print(f"❌ Error processing {email}: {e}")

if __name__ == "__main__":
    main()
