"""
User Schemas
=============
Pydantic models for request/response validation.
"""
from datetime import datetime
from typing import Optional

from app.core.config import Config
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Request schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=Config.PASSWORD_MIN_LENGTH, max_length=Config.PASSWORD_MAX_LENGTH)
    display_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserLoginRequest(BaseModel):
    """Request schema for user login."""
    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    """Request schema for profile updates."""
    display_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    photo_url: Optional[str] = None
    default_currency: Optional[str] = Field(None, min_length=3, max_length=3)


class PasswordChangeRequest(BaseModel):
    """Request schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=Config.PASSWORD_MIN_LENGTH, max_length=Config.PASSWORD_MAX_LENGTH)


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""
    refresh_token: str


class UserResponse(BaseModel):
    """Response schema for user data."""
    id: int
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    phone: Optional[str] = None
    default_currency: str = Config.DEFAULT_CURRENCY
    is_active: bool = True
    email_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Response schema for authentication endpoints."""
    success: bool = True
    user: UserResponse
    access_token: str
    refresh_token: str


class TokenResponse(BaseModel):
    """Response schema for token refresh."""
    success: bool = True
    access_token: str
    refresh_token: str


class MessageResponse(BaseModel):
    """Generic message response."""
    success: bool = True
    message: str
