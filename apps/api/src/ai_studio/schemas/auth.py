from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(default="", max_length=200)
    password: str = Field(min_length=8, max_length=200)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class CurrentUser(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
