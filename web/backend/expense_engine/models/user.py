"""
User Models
User profile and preferences
"""

from typing import Optional
from pydantic import Field

from .base import BaseModel
from ..constants import Currency


class UserProfile(BaseModel):
    """User profile information"""
    
    uid: str = Field(..., min_length=1, description="Firebase user ID")
    email: str = Field(..., description="User email address")
    name: Optional[str] = Field(None, max_length=100, description="Display name")
    picture: Optional[str] = Field(None, description="Profile picture URL")
    email_verified: bool = Field(default=False, description="Email verification status")
    
    # Preferences
    default_currency: Currency = Field(default=Currency.USD, description="Preferred currency")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    
    # Metadata
    is_active: bool = Field(default=True, description="Account active status")
    last_login: Optional[str] = Field(None, description="Last login timestamp")


class UserPreferences(BaseModel):
    """User preferences for expense management"""
    
    uid: str = Field(..., min_length=1)
    
    # Currency settings
    default_currency: Currency = Field(default=Currency.USD)
    
    # Notification settings
    email_notifications: bool = Field(default=True)
    push_notifications: bool = Field(default=True)
    
    # Display settings
    theme: str = Field(default="light", pattern="^(light|dark|auto)$")
    language: str = Field(default="en", max_length=5)
