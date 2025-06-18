from datetime import datetime, timedelta, timezone # Added timezone explicitly
from typing import Optional, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel # For TokenData schema

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None # Added user_id to token data


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)}) # Add issued_at time
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decodes the access token. Returns TokenData if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub") # Standard claim for subject (username)
        user_id: Optional[int] = payload.get("id")   # Custom claim for user_id

        if username is None and user_id is None: # Require at least one identifier
            return None
        return TokenData(username=username, user_id=user_id)
    except JWTError: # Catches expired tokens, invalid signature, etc.
        return None
