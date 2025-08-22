# facilitator_routes.py

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from datetime import datetime
from typing import Dict

from .dependencies import get_supabase, get_current_facilitator

router = APIRouter(
    prefix="/facilitator",
    tags=["Facilitator Tasks"]
)

def update_participant_event(
    supabase: Client,
    participant_id: str,
    update_fields: Dict,
    event_type: str
):
    # Update participant record
    result = supabase.table("participants").update(update_fields).eq("participant_id", participant_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Insert attendance log
    supabase.table("attendance_logs").insert({
        "participant_id": participant_id,
        "event_type": event_type,
        "status": True,
        "timestamp": datetime.utcnow()
    }).execute()

    return {"message": f"{event_type.capitalize()} recorded for {participant_id}"}


@router.post("/checkin")
def checkin_participant(
    participant_id: str,
    facilitator=Depends(get_current_facilitator),
    supabase: Client = Depends(get_supabase)
):
    return update_participant_event(
        supabase,
        participant_id,
        {"checkin_status": True, "checkin_timestamp": datetime.utcnow()},
        "checkin"
    )


@router.post("/boarding")
def board_bus(
    participant_id: str,
    facilitator=Depends(get_current_facilitator),
    supabase: Client = Depends(get_supabase)
):
    return update_participant_event(
        supabase,
        participant_id,
        {"transport_status": True, "transport_timestamp": datetime.utcnow()},
        "boarding"
    )


@router.post("/meal")
def collect_meal(
    participant_id: str,
    facilitator=Depends(get_current_facilitator),
    supabase: Client = Depends(get_supabase)
):
    return update_participant_event(
        supabase,
        participant_id,
        {"meal_status": True, "meal_timestamp": datetime.utcnow()},
        "meal"
    )
