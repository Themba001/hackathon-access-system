from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
import os
import uuid
import qrcode
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from supabase import Client, create_client
from passlib.context import CryptContext

# --------------------------------------------------
# App Initialization
# --------------------------------------------------
app = FastAPI(title="NWU Hackathon Access System")

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SMTP_EMAIL = os.getenv("EMAIL_USER")
SMTP_PASSWORD = os.getenv("EMAIL_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT") or 587)

# --------------------------------------------------
# Password Hashing
# --------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --------------------------------------------------
# Authentication
# --------------------------------------------------
security = HTTPBasic()

def get_current_facilitator(
    credentials: HTTPBasicCredentials = Depends(security)
):
    result = supabase.table("profiles")\
        .select("*")\
        .eq("email", credentials.username)\
        .eq("role", "facilitator")\
        .single().execute()

    profile = result.data

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # TODO: add password check here (bcrypt), right now it’s just email
    return profile


# --------------------------------------------------
# Models
# --------------------------------------------------
class Participant(BaseModel):
    name: str
    email: str
    participant_type: str  # "Participant", "Judge", "Organizer"

class CheckInData(BaseModel):
    qr_data: str

class TaskData(BaseModel):
    participant_id: str
    task_type: str  # e.g., "bus_boarding", "meal_collection"

class AdminSignup(BaseModel):
    email: str
    password: str

# --------------------------------------------------
# Utility Functions
# --------------------------------------------------
def generate_ticket(name: str, email: str, participant_type: str, event_code: str):
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
    except:
        font = ImageFont.load_default()

    draw.text((20, 20), f"Name: {name}", fill="black", font=font)
    draw.text((20, 60), f"Email: {email}", fill="black", font=font)
    draw.text((20, 100), f"Type: {participant_type}", fill="black", font=font)
    draw.text((20, 140), f"Event: {os.getenv('EVENT_NAME')}", fill="black", font=font)
    draw.text((20, 180), f"Date: {os.getenv('EVENT_DATE')}", fill="black", font=font)
    draw.text((20, 220), f"Code: {event_code}", fill="black", font=font)

    qr_img = qr_img.resize((200, 200))
    ticket.paste(qr_img, (ticket_width - 220, ticket_height - 220))

    tickets_dir = "tickets"
    os.makedirs(tickets_dir, exist_ok=True)
    ticket_file = os.path.join(tickets_dir, f"{name}_{email}.png")
    ticket.save(ticket_file)

    return ticket_file

def send_email(to_email: str, subject: str, body: str, attachment_path=None):
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
# Routes
# --------------------------------------------------

## Admin signup (set password first time)
@app.post("/admins/signup")
def admin_signup(data: AdminSignup):
    existing = (
        supabase.table("profiles")
        .select("*")
        .eq("email", data.email)
        .eq("role", "admin")
        .single()
        .execute()
    )
    profile = existing.data

    if not profile:
        raise HTTPException(status_code=404, detail="No admin account found for this email")

    if profile.get("password_hash"):
        raise HTTPException(status_code=400, detail="Password already set. Please log in instead.")

    password_hash = pwd_context.hash(data.password)
    supabase.table("profiles").update({"password_hash": password_hash}).eq("email", data.email).execute()

    return {"message": "Password set successfully. You can now log in."}

## 1️⃣ Task Management
@app.post("/task", dependencies=[Depends(get_current_admin)])
def perform_task(data: TaskData):
    participant = (
        supabase.table("participants")
        .select("*")
        .eq("participant_id", data.participant_id)
        .single()
        .execute()
        .data
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    supabase.table("participants").update({
        f"{data.task_type}_status": True,
        f"{data.task_type}_time": datetime.now().isoformat()
    }).eq("participant_id", data.participant_id).execute()

    return {"message": f"{participant['full_name']} completed {data.task_type} successfully!"}

## 2️⃣ Participant Management
@app.get("/participants", dependencies=[Depends(get_current_admin)])
def get_participants():
    response = supabase.table("participants").select("*").execute()
    return response.data or []

@app.post("/participants", dependencies=[Depends(get_current_admin)])
def add_participant(participant: Participant):
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

    send_email(participant.email, f"Your {os.getenv('EVENT_NAME')} Ticket", "Here is your ticket.", ticket_file)

    return {"message": "Participant added and ticket emailed.", "participant_id": new_id}

@app.put("/participants/{participant_id}", dependencies=[Depends(get_current_admin)])
def edit_participant(participant_id: str, participant: Participant):
    supabase.table("participants").update({
        "full_name": participant.name,
        "email": participant.email,
        "participant_type": participant.participant_type
    }).eq("participant_id", participant_id).execute()
    return {"message": "Participant updated."}

@app.delete("/participants/{participant_id}", dependencies=[Depends(get_current_admin)])
def delete_participant(participant_id: str):
    supabase.table("participants").delete().eq("participant_id", participant_id).execute()
    supabase.table("tickets").delete().eq("participant_id", participant_id).execute()
    return {"message": "Participant deleted."}

## 3️⃣ Ticket Management
@app.get("/tickets/{email}", dependencies=[Depends(get_current_admin)])
def download_ticket(email: str):
    participant = (
        supabase.table("participants")
        .select("*")
        .eq("email", email)
        .single()
        .execute()
        .data
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    ticket = (
        supabase.table("tickets")
        .select("pdf_path")
        .eq("participant_id", participant["participant_id"])
        .single()
        .execute()
        .data
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return FileResponse(ticket["pdf_path"], media_type="image/png")

@app.post("/tickets/resend", dependencies=[Depends(get_current_admin)])
def resend_ticket(email: str):
    participant = (
        supabase.table("participants")
        .select("*")
        .eq("email", email)
        .single()
        .execute()
        .data
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    ticket = (
        supabase.table("tickets")
        .select("pdf_path")
        .eq("participant_id", participant["participant_id"])
        .single()
        .execute()
        .data
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    send_email(email, "Your Hackathon Ticket", "Resending your ticket.", ticket["pdf_path"])
    return {"message": "Ticket resent."}

## 4️⃣ Check-in
@app.post("/checkin", dependencies=[Depends(get_current_admin)])
def checkin_participant(data: CheckInData):
    try:
        name, email, ptype, code = data.qr_data.split("|")
    except:
        raise HTTPException(status_code=400, detail="Invalid QR code format")

    participant = (
        supabase.table("participants")
        .select("*")
        .eq("email", email)
        .single()
        .execute()
        .data
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    supabase.table("participants").update({
        "checkin_status": True,
        "checkin_time": datetime.now().isoformat()
    }).eq("participant_id", participant["participant_id"]).execute()

    return {"message": f"{name} checked in successfully."}

## 5️⃣ Analytics
@app.get("/analytics/summary", dependencies=[Depends(get_current_admin)])
def analytics_summary():
    participants = supabase.table("participants").select("*").execute().data or []
    total_registered = len(participants)
    total_checked_in = len([p for p in participants if p.get("checkin_status")])
    breakdown = {}
    for p in participants:
        breakdown[p["participant_type"]] = breakdown.get(p["participant_type"], 0) + 1
    return {
        "total_registered": total_registered,
        "total_checked_in": total_checked_in,
        "by_type": breakdown
    }
