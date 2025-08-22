from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dependencies import get_supabase, create_access_token, get_current_facilitator
from supabase import Client
from datetime import timedelta

app = FastAPI(title="Hackathon Access System")

# ✅ CORS so Netlify frontend can talk to Render backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["has-access.netlify.app"],  # change to ["https://your-netlify.app"] in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Models --------
class LoginRequest(BaseModel):
    email: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class QRRequest(BaseModel):
    participant_id: str

# -------- Facilitator Login --------
@app.post("/facilitators/login", response_model=TokenResponse)
def facilitator_login(request: LoginRequest, supabase: Client = Depends(get_supabase)):
    result = supabase.table("profiles").select("email, role").eq("email", request.email).single().execute()
    if not result.data or result.data["role"] != "facilitator":
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = create_access_token({"sub": request.email}, expires_delta=timedelta(minutes=60))
    return {"access_token": token, "token_type": "bearer"}

# -------- Boarding Endpoint --------
@app.post("/boarding")
def board_bus(
    qr: QRRequest,
    supabase: Client = Depends(get_supabase),
    facilitator=Depends(get_current_facilitator)
):
    participant_id = qr.participant_id

    result = supabase.table("participants").update({
        "transport_status": True,
        "transport_timestamp": "now()"
    }).eq("participant_id", participant_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Participant not found")

    supabase.table("attendance_logs").insert({
        "participant_id": participant_id,
        "event_type": "boarding",
        "status": True
    }).execute()

    return {"message": f"Participant {participant_id} boarded successfully"}

# -------- Meal Collection Endpoint --------
@app.post("/meals")
def collect_meal(
    qr: QRRequest,
    supabase: Client = Depends(get_supabase),
    facilitator=Depends(get_current_facilitator)
):
    participant_id = qr.participant_id

    result = supabase.table("participants").update({
        "meal_status": True,
        "meal_timestamp": "now()"
    }).eq("participant_id", participant_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Participant not found")

    supabase.table("attendance_logs").insert({
        "participant_id": participant_id,
        "event_type": "meal",
        "status": True
    }).execute()

    return {"message": f"Meal collected for {participant_id}"}
