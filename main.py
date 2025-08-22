# main.py
from fastapi import FastAPI, Depends, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
import os, uuid, qrcode, smtplib
from email.message import EmailMessage
from PIL import Image, ImageDraw, ImageFont

from dependencies import supabase, pwd_context, create_access_token, get_current_facilitator

app = FastAPI(title="NWU Hackathon Access System")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Email Setup ----------------
SMTP_EMAIL = os.getenv("EMAIL_USER")
SMTP_PASSWORD = os.getenv("EMAIL_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT") or 587)

def send_email(to_email: str, subject: str, body: str, attachment_path: Optional[str] = None):
    if not (SMTP_EMAIL and SMTP_PASSWORD):
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    msg.set_content(body)
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="octet-stream",
                               filename=os.path.basename(attachment_path))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)

# ---------------- Ticket Generation ----------------
def generate_ticket(name: str, email: str, participant_type: str, event_code: str) -> str:
    qr_data = f"{name}|{email}|{participant_type}|{event_code}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    w, h = 600, 400
    ticket = Image.new("RGB", (w, h), "white")
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
    ticket.paste(qr_img, (w - 220, h - 220))

    os.makedirs("tickets", exist_ok=True)
    safe_email = email.replace("@", "_at_")
    path = os.path.join("tickets", f"{name}_{safe_email}.png")
    ticket.save(path)
    return path

# ---------------- Models ----------------
class FacilitatorSignup(BaseModel):
    email: EmailStr
    password: str

class FacilitatorLogin(BaseModel):
    email: EmailStr
    password: str

class Participant(BaseModel):
    name: str
    email: EmailStr
    participant_type: Optional[str] = "Participant"

class QRData(BaseModel):
    qr_code: str

# ---------------- Auth Endpoints ----------------
@app.post("/facilitators/signup")
def facilitator_signup(data: FacilitatorSignup):
    res = supabase.table("profiles").select("*").eq("email", data.email).eq("role", "facilitator").execute()
    profile = res.data[0] if res.data else None
    if profile and profile.get("password_hash"):
        raise HTTPException(status_code=400, detail="Password already set. Please log in.")

    password_hash = pwd_context.hash(data.password)
    if profile:
        supabase.table("profiles").update({"password_hash": password_hash}).eq("email", data.email).eq("role", "facilitator").execute()
    else:
        supabase.table("profiles").insert({"email": data.email, "role": "facilitator", "password_hash": password_hash}).execute()
    return {"message": "Facilitator account ready."}

@app.post("/facilitators/login")
def facilitator_login(data: FacilitatorLogin):
    res = supabase.table("profiles").select("*").eq("email", data.email).eq("role", "facilitator").execute()
    profile = res.data[0] if res.data else None
    if not profile or not profile.get("password_hash") or not pwd_context.verify(data.password, profile["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": profile["email"], "role": profile["role"]})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/facilitators/me")
def whoami(current=Depends(get_current_facilitator)):
    return {"email": current.get("sub"), "role": current.get("role")}

# ---------------- Participant Helpers ----------------
@app.get("/participant-id")
def get_participant_id(email: str = Query(...), _=Depends(get_current_facilitator)):
    pres = supabase.table("participants").select("participant_id").eq("email", email).execute()
    participant = pres.data[0] if pres.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    return {"participant_id": participant["participant_id"]}

# ---------------- Participant Management ----------------
@app.post("/participants")
def add_participant(data: Participant, _=Depends(get_current_facilitator)):
    new_id = str(uuid.uuid4())
    ticket_path = generate_ticket(data.name, data.email, data.participant_type, new_id)

    supabase.table("participants").insert({
        "participant_id": new_id,
        "full_name": data.name,
        "email": data.email,
        "registration_status": "Registered"
    }).execute()

    supabase.table("tickets").insert({
        "participant_id": new_id,
        "ticket_uuid": str(uuid.uuid4()),
        "pdf_path": ticket_path
    }).execute()

    send_email(data.email, f"Your {os.getenv('EVENT_NAME','NWU Hackathon')} Ticket", "Here is your ticket.", ticket_path)
    return {"message": "Participant added and ticket emailed.", "participant_id": new_id}

@app.get("/tickets/{email}")
def download_ticket(email: EmailStr, _=Depends(get_current_facilitator)):
    pres = supabase.table("participants").select("*").eq("email", email).execute()
    participant = pres.data[0] if pres.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    tres = supabase.table("tickets").select("pdf_path").eq("participant_id", participant["participant_id"]).execute()
    ticket = tres.data[0] if tres.data else None
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    path = ticket["pdf_path"]
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Ticket file missing on server")
    return FileResponse(path, media_type="image/png")

@app.post("/tickets/resend")
def resend_ticket(email: EmailStr = Body(..., embed=True), _=Depends(get_current_facilitator)):
    pres = supabase.table("participants").select("*").eq("email", email).execute()
    participant = pres.data[0] if pres.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    tres = supabase.table("tickets").select("pdf_path").eq("participant_id", participant["participant_id"]).execute()
    ticket = tres.data[0] if tres.data else None
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    send_email(email, "Your Hackathon Ticket", "Resending your ticket.", ticket["pdf_path"])
    return {"message": "Ticket resent."}

# ---------------- QR Utilities ----------------
def extract_email_from_qr(qr_code: str) -> str:
    try:
        _, email, _, _ = [s.strip() for s in qr_code.split("|")]
        return email
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid QR code format")

def log_attendance(participant_id: str, event_type: str):
    try:
        supabase.table("attendance_logs").insert({
            "participant_id": participant_id,
            "event_type": event_type,
            "status": True,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
    except Exception:
        pass  # Non-critical, just log

# ---------------- QR Endpoints ----------------
@app.post("/checkin")
def checkin(data: QRData, _=Depends(get_current_facilitator)):
    email = extract_email_from_qr(data.qr_code)
    pres = supabase.table("participants").select("*").eq("email", email).execute()
    participant = pres.data[0] if pres.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    supabase.table("participants").update({
        "checkin_status": True,
        "checkin_timestamp": datetime.utcnow().isoformat()
    }).eq("participant_id", participant["participant_id"]).execute()
    log_attendance(participant["participant_id"], "checkin")

    return {"message": f"{participant['full_name']} checked in."}

@app.post("/boarding")
def boarding_qr(data: QRData, _=Depends(get_current_facilitator)):
    email = extract_email_from_qr(data.qr_code)
    pres = supabase.table("participants").select("participant_id","full_name").eq("email", email).execute()
    participant = pres.data[0] if pres.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    supabase.table("participants").update({
        "transport_status": True,
        "transport_timestamp": datetime.utcnow().isoformat()
    }).eq("participant_id", participant["participant_id"]).execute()
    log_attendance(participant["participant_id"], "boarding")

    return {"message": f"{participant['full_name']} boarded the bus."}

@app.post("/meals")
def meals_qr(data: QRData, _=Depends(get_current_facilitator)):
    email = extract_email_from_qr(data.qr_code)
    pres = supabase.table("participants").select("participant_id","full_name").eq("email", email).execute()
    participant = pres.data[0] if pres.data else None
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    supabase.table("participants").update({
        "meal_status": True,
        "meal_timestamp": datetime.utcnow().isoformat()
    }).eq("participant_id", participant["participant_id"]).execute()
    log_attendance(participant["participant_id"], "meal")

    return {"message": f"{participant['full_name']} collected a meal."}

# ---------------- DEV / DEBUG ----------------
@app.post("/dev/create_facilitator")
def dev_create_facilitator(email: EmailStr, password: str):
    password_hash = pwd_context.hash(password)
    supabase.table("profiles").insert({
        "email": email,
        "role": "facilitator",
        "password_hash": password_hash
    }).execute()
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}

@app.get("/")
def root():
    return {"message": "API is running"}
