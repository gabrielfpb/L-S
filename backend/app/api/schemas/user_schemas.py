from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    # is_active: Optional[bool] = True # Default in model
    # is_superuser: Optional[bool] = False # Default in model

class UserCreate(UserBase):
    password: str

class UserCreateResponse(UserBase): # For response after user creation
    id: int
    is_active: bool # Show the default
    is_superuser: bool
    created_at: datetime.datetime
    class Config:
        orm_mode = True


class UserUpdate(BaseModel): # More focused update schema
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None # For password changes
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserResponse(UserBase): # For general user info response
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime.datetime
    # updated_at: Optional[datetime.datetime] = None # Add if in model and needed

    class Config:
        orm_mode = True

# Schemas for Token
class Token(BaseModel):
    access_token: str
    token_type: str

# TokenData is already in security.py, but can be here too if preferred for schema organization
# class TokenData(BaseModel):
#     username: Optional[str] = None
#     user_id: Optional[int] = None
