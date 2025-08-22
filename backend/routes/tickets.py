import os, uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from ..database import sb
from ..services.pdf_service import make_ticket_pdf


load_dotenv()
TICKETS_DIR = os.getenv("TICKETS_DIR", "tickets")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/download/{ticket_uuid}")
async def download_ticket(ticket_uuid: str):
    # Lookup ticket by UUID
    supabase = sb()
    res = supabase.table("tickets").select("*", count="exact").eq("ticket_uuid", ticket_uuid).execute()
    rows = res.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Ticket not found")


    pdf_path = rows[0]["pdf_path"]
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found on server")


    filename = os.path.basename(pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)