import os, io, re, uuid, qrcode
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
QR_BUCKET = os.getenv("QR_BUCKET", "qr-codes")
EVENT_CODE = os.getenv("EVENT_CODE", "HACK25")

def supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def normalize_email(email: str) -> str:
    return email.strip().lower()

def generate_participant_id() -> str:
    # short, non-guessable token
    token = uuid.uuid4().hex[:6].upper()
    return f"{EVENT_CODE}-{token}"

def make_qr_png_bytes(payload: str) -> bytes:
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def upload_qr_to_storage(supabase: Client, filename: str, png_bytes: bytes) -> str:
    """
    Uploads QR PNG bytes to Supabase Storage bucket and returns public URL.
    """
    try:
        path = f"{filename}"
        # Use string "true" for upsert to avoid TypeError
        supabase.storage.from_(QR_BUCKET).upload(
            path=path,
            file=png_bytes,
            file_options={"content-type": "image/png", "upsert": "true"}
        )
        # Return public URL
        pub = supabase.storage.from_(QR_BUCKET).get_public_url(path)
        return pub
    except Exception as e:
        print(f"[ERROR] Failed to upload {filename} to storage: {e}")
        return ""


def parse_participants_line(line: str):
    """
    Accepts:
    Name,Email
    Name,Email,StudentNumber
    Name,Email,StudentNumber,Role
    """
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 3:  # require student number
        return None

    full_name = parts[2]  # what appears on certificate
    student_number = parts[1]  # student number
    role = parts[3].lower() if len(parts) >= 4 and parts[3] else "participant"
    if role not in ("participant","judge"): role = "participant"

    # Proper NWU email
    email = f"{student_number}@mynwu.ac.za"

    return {
        "full_name": full_name,
        "email": email,
        "student_number": student_number,
        "role": role
    }
