import os
from dotenv import load_dotenv

load_dotenv()
print(os.getenv("SUPABASE_URL"))
print(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
