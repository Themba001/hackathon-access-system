import os, uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime
from supabase import Client


from .database import sb
from .routes.tickets import router as tickets_router
from .services.pdf_service import make_ticket_pdf


load_dotenv()
TICKETS_DIR = os.getenv("TICKETS_DIR", "tickets")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


app = FastAPI(title="Hackathon Access Backend")
app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
app.include_router(tickets_router)


@app.get("/")
def root():
    return {"ok": True, "service": "hackathon-access"}


# Utility endpoint (optional) to (re)issue a ticket for a participant
@app.post("/issue-ticket/{participant_id}")
def issue_ticket(participant_id: str):
    # Fetch participant info from Supabase
    participant = sb.table("participants").select("*").eq("id", participant_id).single().execute()

    if not participant.data:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Generate unique ticket ID
    ticket_id = str(uuid.uuid4())

    # Create ticket PDF
    filename = f"{ticket_id}.pdf"
    filepath = os.path.join(TICKETS_DIR, filename)

    make_ticket_pdf(
        participant=participant.data,
        ticket_id=ticket_id,
        filepath=filepath,
    )

    # Construct download URL
    download_url = f"{BASE_URL}/tickets/{filename}"

    # Optionally: store ticket info in Supabase
    sb.table("tickets").insert({
        "id": ticket_id,
        "participant_id": participant_id,
        "issued_at": datetime.utcnow().isoformat(),
        "file_url": download_url,
    }).execute()

    return {
        "ok": True,
        "ticket_id": ticket_id,
        "download_url": download_url,
    }