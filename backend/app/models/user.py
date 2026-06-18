"""User Pydantic models for authentication."""
from pydantic import BaseModel


class User(BaseModel):
    """User schema from users.json."""
    name: str
    password: str


class LoginRequest(BaseModel):
    name: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
