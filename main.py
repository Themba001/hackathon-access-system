from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os
import qrcode
from email.message import EmailMessage
import smtplib
from pydantic import BaseModel
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont


load_dotenv()  # must be before accessing os.getenv

SMTP_EMAIL = os.getenv("EMAIL_USER")
SMTP_PASSWORD = os.getenv("EMAIL_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
if SMTP_PORT is None:
    SMTP_PORT = 587
else:
    SMTP_PORT = int(SMTP_PORT)


def generate_ticket(name: str, email: str, participant_type: str, event_code: str, event_name: str, event_date: str):
    # --- Create QR code ---
    qr_data = f"{name} | {email} | {participant_type} | {event_code}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # --- Create ticket canvas ---
    ticket_width = 600
    ticket_height = 400
    ticket = Image.new("RGB", (ticket_width, ticket_height), "white")
    draw = ImageDraw.Draw(ticket)

    # Optional: Add font (you can use a TTF file)
    font_path = "arial.ttf"  # Make sure this exists or use default
    try:
        font = ImageFont.truetype(font_path, size=24)
    except:
        font = ImageFont.load_default()

    # --- Write ticket details ---
    draw.text((20, 20), f"Name: {name}", fill="black", font=font)
    draw.text((20, 60), f"Email: {email}", fill="black", font=font)
    draw.text((20, 100), f"Participant Type: {participant_type}", fill="black", font=font)
    draw.text((20, 140), f"Event: {event_name}", fill="black", font=font)
    draw.text((20, 180), f"Date: {event_date}", fill="black", font=font)
    draw.text((20, 220), f"Event Code: {event_code}", fill="black", font=font)

    # --- Paste QR code on the ticket ---
    qr_img = qr_img.resize((200, 200))
    ticket.paste(qr_img, (ticket_width - 220, ticket_height - 220))

    # --- Save ticket ---
    tickets_dir = "tickets"
    if not os.path.exists(tickets_dir):
        os.makedirs(tickets_dir)
    ticket_file = os.path.join(tickets_dir, f"{name}_{email}.png")
    ticket.save(ticket_file)
    return ticket_file


app = FastAPI(title="NWU Hackathon Access System")

class Participant(BaseModel):
    name: str
    email: str
    participant_type: str  # e.g. "Participant", "Judge", "Organizer"

participants = []


# --- Email function ---
def send_email(to_email: str, subject: str, body: str, attachment_path=None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = to_email
    msg.set_content(body)

    # attach file if provided
    if attachment_path:
        with open(attachment_path, "rb") as f:
            file_data = f.read()
            file_name = os.path.basename(attachment_path)
        msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)

    with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        server.send_message(msg)


# --- GET participants ---
@app.get("/participants")
def get_participants():
    return participants


# --- POST participant ---
@app.post("/participants")
def add_participant(participant: Participant):
    if not participant.name or not participant.email:
        raise HTTPException(status_code=400, detail="Name and email are required.")

    # --- Generate ticket ---
    ticket_file = generate_ticket(
        name=participant.name,
        email=participant.email,
        participant_type=participant.participant_type,
        event_code=os.getenv("EVENT_CODE"),
        event_name=os.getenv("EVENT_NAME"),
        event_date=os.getenv("EVENT_DATE")
    )

    # Add participant to list
    participant_data = {
        "name": participant.name,
        "email": participant.email,
        "participant_type": participant.participant_type
    }
    participants.append(participant_data)

    # --- Send welcome email with ticket ---
    subject = f"Welcome to {os.getenv('EVENT_NAME')}!"
    body = (
        f"Hi {participant.name},\n\n"
        f"You are registered as a {participant.participant_type} "
        f"for {os.getenv('EVENT_NAME')} on {os.getenv('EVENT_DATE')}.\n"
        f"Your ticket is attached.\n\nSee you there!"
    )
    send_email(participant.email, subject, body, ticket_file)

    return {"message": "Participant added and email sent!", "participant": participant_data}


# --- GET ticket by email ---
@app.get("/tickets/{email}")
def get_ticket(email: str):
    # Look up participant
    participant = next((p for p in participants if p["email"] == email), None)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")

    # Ticket path
    ticket_file = os.path.join("tickets", f"{participant['name']}_{participant['email']}.png")
    if not os.path.exists(ticket_file):
        raise HTTPException(status_code=404, detail="Ticket not found. Try re-registering.")

    return FileResponse(ticket_file, media_type="image/png", filename=f"{participant['name']}_ticket.png")
