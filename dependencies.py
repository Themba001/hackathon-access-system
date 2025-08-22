import os
from fastapi import Depends, HTTPException, status
from supabase import create_client, Client
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta

# ENV
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Supabase client
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="facilitators/login")

# Token utils
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Current facilitator validation
def get_current_facilitator(
    token: str = Depends(oauth2_scheme),
    supabase: Client = Depends(get_supabase)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate facilitator credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = supabase.table("profiles").select("email, role").eq("email", email).single().execute()
    if not result.data or result.data["role"] != "facilitator":
        raise credentials_exception

    return result.data
