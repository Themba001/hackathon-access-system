import os
import supabase
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

def main():
    res = supabase_client.table("participants").select("*").execute()
    participants = res.data
    print(f"🔍 Found {len(participants)} participants to check")

    fixes = 0
    for p in participants:
        email = p.get("email", "")
        full_name = p.get("full_name", "")
        pid = p.get("participant_id")

        if not pid or not email:
            continue

        # Case: duplicated domain like xxx@mynwu.ac.za@mynwu.ac.za
        if "@mynwu.ac.za@mynwu.ac.za" in email:
            fixed_email = email.replace("@mynwu.ac.za@mynwu.ac.za", "@mynwu.ac.za")
            fixed_name = pid  # student number as name placeholder if full_name is wrong

            supabase_client.table("participants").update({
                "email": fixed_email,
                "full_name": full_name if full_name and full_name != pid else pid
            }).eq("id", p["id"]).execute()

            print(f"✅ Fixed participant {pid}: {email} → {fixed_email}")
            fixes += 1

    print(f"🎉 Migration complete, fixed {fixes} records")

if __name__ == "__main__":
    main()
