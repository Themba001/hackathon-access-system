# dependencies.py
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from supabase import Client, create_client
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

# ---- env & clients ----
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SECRET_KEY = os.getenv("SECRET_KEY", "change_me_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# This is only used by Swagger to show the lock icon; we still accept JSON at /facilitators/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/facilitators/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def get_current_facilitator(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = verify_access_token(token)
    if not payload or payload.get("role") != "facilitator":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload
