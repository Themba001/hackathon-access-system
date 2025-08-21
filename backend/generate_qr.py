import os, csv
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from utils import (
    supabase_client, parse_participants_line, generate_participant_id,
    make_qr_png_bytes, upload_qr_to_storage
)

load_dotenv()
DATA_FILE = os.path.join("data", "participants.txt")
OUT_DIR = os.path.join("data", "qrcodes")
os.makedirs(OUT_DIR, exist_ok=True)

def main():
    sb = supabase_client()
    to_insert = []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            p = parse_participants_line(raw)
            if not p:
                print(f"Skipped invalid line: {raw}")
                continue

            # create participant_id + QR
            participant_id = generate_participant_id()
            qr_png = make_qr_png_bytes(participant_id)

            # local copy (optional)
            local_path = os.path.join(OUT_DIR, f"{participant_id}.png")
            with open(local_path, "wb") as imgf:
                imgf.write(qr_png)

            # upload to Storage
            qr_url = upload_qr_to_storage(sb, f"{participant_id}.png", qr_png)

            # “Granted” only if they made your final list file:
            admission_status = "Granted"

            rec = {
                "participant_id": participant_id,
                "role": p["role"],
                "full_name": p["full_name"],
                "email": p["email"],
                "student_number": p["student_number"],
                "year_of_study": None,
                "registration_status": "Registered",
                "confirmation_status": "Confirmed",
                "admission_status": admission_status,
                "qr_code_url": qr_url
            }
            to_insert.append(rec)

    if not to_insert:
        print("No participants to insert.")
        return

    # Insert via SERVICE ROLE (bypasses client insert policy)
    res = sb.table("participants").insert(to_insert).execute()
    print(f"Inserted {len(to_insert)} participants.")

if __name__ == "__main__":
    main()
