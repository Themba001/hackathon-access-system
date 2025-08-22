# main.py
from fastapi import FastAPI, Depends, HTTPException, status, Body, Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import os
import uuid
import qrcode
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from supabase import Client, create_client
from passlib.context import CryptContext
from jose import JWTError, jwt
from typing import Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware



# --------------------------------------------------
# App Initialization
# --------------------------------------------------
app = FastAPI(title="NWU Hackathon Access System")


origins = [
    "https://has-access.netlify.app",  # replace with your actual Netlify URL
    "http://localhost:5173"  # optional, for local testing
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://has-access.netlify.app"],  # your Netlify URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# CORS so your browser-based frontend can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your domain(s) in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in environment.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SMTP_EMAIL = os.getenv("EMAIL_USER")
SMTP_PASSWORD = os.getenv("EMAIL_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT") or 587)

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_change_me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --------------------------------------------------
# Password Hashing
# --------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --------------------------------------------------
# JWT Helpers
# --------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


    


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/facilitators/login")

def get_current_facilitator(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = verify_access_token(token)
    if not payload or payload.get("role") != "facilitator":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

# --------------------------------------------------
# Models
# --------------------------------------------------
class Participant(BaseModel):
    name: str
    email: EmailStr
    participant_type: str  # "Participant", "Judge", "Organizer"

class CheckInData(BaseModel):
    qr_data: str

class TaskData(BaseModel):
    participant_id: str
    task_type: str  # e.g., "transport", "meal"  (must match columns: transport_status, meal_status)

class FacilitatorSignup(BaseModel):
    email: EmailStr
    password: str

class FacilitatorLogin(BaseModel):
    email: EmailStr
    password: str

# --------------------------------------------------
# Utility Functions
# --------------------------------------------------
def generate_ticket(name: str, email: str, participant_type: str, event_code: str) -> str:
    qr_data = f"{name}|{email}|{participant_type}|{event_code}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    ticket_width, ticket_height = 600, 400
    ticket = Image.new("RGB", (ticket_width, ticket_height), "white")
    draw = ImageDraw.Draw(ticket)

    try:
        font = ImageFont.truetype("arial.ttf", size=24)
    except Exception:
        font = ImageFont.load_default()

    draw.text((20, 20), f"Name: {name}", fill="black", font=font)
    draw.text((20, 60), f"Email: {email}", fill="black", font=font)
    draw.text((20, 100), f"Type: {participant_type}", fill="black", font=font)
    draw.text((20, 140), f"Event: {os.getenv('EVENT_NAME','NWU Hackathon')}", fill="black", font=font)
    draw.text((20, 180), f"Date: {os.getenv('EVENT_DATE','2025-01-01')}", fill="black", font=font)
    draw.text((20, 220), f"Code: {event_code}", fill="black", font=font)

    qr_img = qr_img.resize((200, 200))
    ticket.paste(qr_img, (ticket_width - 220, ticket_height - 220))

    tickets_dir = "tickets"
    os.makedirs(tickets_dir, exist_ok=True)
    safe_email = email.replace("@", "_at_")
    ticket_file = os.path.join(tickets_dir, f"{name}_{safe_email}.png")
    ticket.save(ticket_file)

    return ticket_file

def send_email(to_email: str, subject: str, body: str, attachment_path: Optional[str] = None) -> None:
    if not (SMTP_EMAIL and SMTP_PASSWORD and SMTP_SERVER and SMTP_PORT):
        # silently skip in dev if mail not configured
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    msg.set_content(body)

    if attachment_path:
        with open(attachment_path, "rb") as f:
            file_data = f.read()
            file_name = os.path.basename(attachment_path)
        msg.add_attachment(
            file_data,
            maintype="application",
            subtype="octet-stream",
            filename=file_name,
        )

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)

# --------------------------------------------------
# Health
# --------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}


@app.get("/")
def read_root():
    return {"message": "Hello! Your API is running."}

# --------------------------------------------------
# Auth: Facilitators
# --------------------------------------------------
@app.post("/facilitators/signup")
def facilitator_signup(data: FacilitatorSignup):
    """
    Create a facilitator if none exists for this email, or set the password
    if a facilitator row exists without a password.
    Email must follow studentNumber@mynwu.ac.za (validated on frontend ideally).
    """
    # Try find existing facilitator record
    result = (
        supabase.table("profiles")
        .select("*")
        .eq("email", data.email)
        .eq("role", "facilitator")
        .execute()
    )
    profile = result.data[0] if result.data else None

    # If already has password, block re-signup
    if profile and profile.get("password_hash"):
        raise HTTPException(status_code=400, detail="Password already set. Please log in instead.")

    password_hash = pwd_context.hash(data.password)

    if not profile:
        # Create new facilitator profile
        insert_res = supabase.table("profiles").insert({
            "email": data.email,
            "role": "facilitator",
            "password_hash": password_hash
        }).execute()
        if not insert_res.data:
            raise HTTPException(status_code=500, detail="Could not create facilitator.")
    else:
        # Update existing missing password
        supabase.table("profiles").update({"password_hash": password_hash}).eq("email", data.email).eq("role", "facilitator").execute()

    return {"message": "Facilitator account ready. You can now log in."}

@app.post("/facilitators/login")
def facilitator_login(data: FacilitatorLogin):
    res = (
        supabase.table("profiles")
        .select("*")
        .eq("email", data.email)
        .eq("role", "facilitator")
        .execute()
    )
    profile = res.data[0] if res.data else None
    if not profile or not profile.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not pwd_context.verify(data.password, profile["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": profile["email"], "role": profile["role"]})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/facilitators/me")
def whoami(current=Depends(get_current_facilitator)):
    return {"email": current.get("sub"), "role": current.get("role")}

# --------------------------------------------------
# 1) Task Management
# --------------------------------------------------
@app.post("/task")
def perform_task(
    data: TaskData,
    _current=Depends(get_current_facilitator)
):
    # Expect task_type like "transport" or "meal"
    valid_task_fields = {"transport", "meal"}
    if data.task_type not in valid_task_fields:
        raise HTTPException(status_code=400, detail=f"task_type must be one of {sorted(valid_task_fields)}")

    part_res = (
        supabase.table("participants")
        .select("*")
        .eq("participant_id", data.participant_id)
        .execute()
    )
    participant = part_res.data[0] if part_res.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Columns in your schema are *_status and *_timestamp
    update_payload = {
        f"{data.task_type}_status": True,
        f"{data.task_type}_timestamp": datetime.utcnow().isoformat()
    }
    supabase.table("participants").update(update_payload).eq("participant_id", data.participant_id).execute()

    return {"message": f"{participant['full_name']} completed {data.task_type} successfully!"}

# --------------------------------------------------
# 2) Participant Management
# --------------------------------------------------
@app.get("/participants")
def get_participants(_current=Depends(get_current_facilitator)):
    response = supabase.table("participants").select("*").order("created_at", desc=True).execute()
    return response.data or []

@app.post("/participants")
def add_participant(participant: Participant, _current=Depends(get_current_facilitator)):
    new_id = str(uuid.uuid4())
    ticket_file = generate_ticket(participant.name, participant.email, participant.participant_type, new_id)

    supabase.table("participants").insert({
        "participant_id": new_id,
        "full_name": participant.name,
        "email": participant.email,
        "participant_type": participant.participant_type,
        "registration_status": "Registered"
    }).execute()

    supabase.table("tickets").insert({
        "participant_id": new_id,
        "ticket_uuid": str(uuid.uuid4()),
        "pdf_path": ticket_file
    }).execute()

    send_email(
        participant.email,
        f"Your {os.getenv('EVENT_NAME','NWU Hackathon')} Ticket",
        "Here is your ticket.",
        ticket_file
    )

    return {"message": "Participant added and ticket emailed.", "participant_id": new_id}

@app.put("/participants/{participant_id}")
def edit_participant(participant_id: str, participant: Participant, _current=Depends(get_current_facilitator)):
    supabase.table("participants").update({
        "full_name": participant.name,
        "email": participant.email,
        "participant_type": participant.participant_type
    }).eq("participant_id", participant_id).execute()
    return {"message": "Participant updated."}

@app.delete("/participants/{participant_id}")
def delete_participant(participant_id: str, _current=Depends(get_current_facilitator)):
    supabase.table("tickets").delete().eq("participant_id", participant_id).execute()
    supabase.table("participants").delete().eq("participant_id", participant_id).execute()
    return {"message": "Participant deleted."}

# --------------------------------------------------
# 3) Ticket Management
# --------------------------------------------------
@app.get("/tickets/{email}")
def download_ticket(email: EmailStr, _current=Depends(get_current_facilitator)):
    pres = (
        supabase.table("participants")
        .select("*")
        .eq("email", email)
        .execute()
    )
    participant = pres.data[0] if pres.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    tres = (
        supabase.table("tickets")
        .select("pdf_path")
        .eq("participant_id", participant["participant_id"])
        .execute()
    )
    ticket = tres.data[0] if tres.data else None
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    path = ticket["pdf_path"]
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Ticket file missing on server")

    return FileResponse(path, media_type="image/png")

@app.post("/tickets/resend")
def resend_ticket(email: EmailStr = Body(..., embed=True), _current=Depends(get_current_facilitator)):
    pres = (
        supabase.table("participants")
        .select("*")
        .eq("email", email)
        .execute()
    )
    participant = pres.data[0] if pres.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    tres = (
        supabase.table("tickets")
        .select("pdf_path")
        .eq("participant_id", participant["participant_id"])
        .execute()
    )
    ticket = tres.data[0] if tres.data else None
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    send_email(email, "Your Hackathon Ticket", "Resending your ticket.", ticket["pdf_path"])
    return {"message": "Ticket resent."}

# --------------------------------------------------
# 4) Check-in
# --------------------------------------------------
@app.post("/checkin")
def checkin_participant(data: CheckInData, _current=Depends(get_current_facilitator)):
    try:
        name, email, ptype, code = data.qr_data.split("|")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid QR code format")

    pres = (
        supabase.table("participants")
        .select("*")
        .eq("email", email)
        .execute()
    )
    participant = pres.data[0] if pres.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    supabase.table("participants").update({
        "checkin_status": True,
        "checkin_timestamp": datetime.utcnow().isoformat()
    }).eq("participant_id", participant["participant_id"]).execute()

    # Optional: record attendance log
    try:
        supabase.table("attendance_logs").insert({
            "participant_id": participant["participant_id"],
            "event_type": "checkin",
            "status": True,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
    except Exception:
        pass

    return {"message": f"{name} checked in successfully."}

# --------------------------------------------------
# 5) Analytics
# --------------------------------------------------
@app.get("/analytics/summary")
def analytics_summary(_current=Depends(get_current_facilitator)):
    participants = supabase.table("participants").select("*").execute().data or []
    total_registered = len(participants)
    total_checked_in = len([p for p in participants if p.get("checkin_status")])
    breakdown: Dict[str, int] = {}
    for p in participants:
        ptype = p.get("participant_type") or "Unknown"
        breakdown[ptype] = breakdown.get(ptype, 0) + 1
    return {
        "total_registered": total_registered,
        "total_checked_in": total_checked_in,
        "by_type": breakdown
    }

# --------------------------------------------------
# Convenience: preload a facilitator via query (DEV ONLY)
# --------------------------------------------------
@app.post("/dev/create_facilitator")
def dev_create_facilitator(
    email: EmailStr = Query(...),
    password: str = Query(...),
):
    password_hash = pwd_context.hash(password)
    supabase.table("profiles").insert({
        "email": email,
        "role": "facilitator",
        "password_hash": password_hash
    }).execute()
    return {"ok": True}
