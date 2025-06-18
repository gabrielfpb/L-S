from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # For the /token endpoint
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core import security # security.py
from ...services import user_service # user_service.py
from ..schemas import user_schemas # user_schemas.py (Token, UserCreate, UserResponse)
from ..dependencies import get_current_active_user # For /users/me

router = APIRouter()

@router.post("/token", response_model=user_schemas.Token)
async def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends() # username and password from form
):
    user = user_service.authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = security.create_access_token(
        data={"sub": user.username, "id": user.id} # "sub" is standard for subject (username)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/register", response_model=user_schemas.UserCreateResponse, status_code=status.HTTP_201_CREATED)
def register_new_user(
    user_in: user_schemas.UserCreate,
    db: Session = Depends(get_db)
):
    db_user_by_username = user_service.get_user_by_username(db, username=user_in.username)
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    db_user_by_email = user_service.get_user_by_email(db, email=user_in.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    created_user = user_service.create_user(db=db, user_data=user_in)
    # UserCreateResponse is designed to be compatible with the User model via orm_mode=True
    return created_user


# Example of a protected route to get current user's info
@router.get("/users/me", response_model=user_schemas.UserResponse)
async def read_users_me(current_user: user_schemas.UserResponse = Depends(get_current_active_user)):
    # The dependency `get_current_active_user` returns an SQLAlchemy User model instance.
    # FastAPI, with orm_mode=True in Pydantic schema (UserResponse), handles the conversion.
    return current_user
