from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from ..core import security # security.py
from ..core.database import get_db
from ..services import user_service # user_service.py
from ..models.models import User # SQLAlchemy User model
from ..api.schemas.user_schemas import UserResponse # Pydantic User schema for response type hint

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token") # Matches the token endpoint URL

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User: # Returns SQLAlchemy User model
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = security.decode_access_token(token)
    if token_data is None or token_data.user_id is None: # Ensure user_id is in token
        raise credentials_exception

    user = user_service.get_user_by_id(db, user_id=token_data.user_id)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User: # Returns SQLAlchemy User model
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# Optional: Dependency for superuser
def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges"
        )
    return current_user
