from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None
    is_superuser: bool = False

class TokenCreate(BaseModel):
    email: str = Field(..., description="User's email")
    password: str = Field(..., description="User's password")
