"""
Invitation Models
Group invitation system
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import Field, field_validator

from .base import BaseModel
from ..constants import InvitationStatus


class Invitation(BaseModel):
    """Group invitation model"""
    
    invitation_id: Optional[str] = None
    group_id: str = Field(..., min_length=1)
    group_name: Optional[str] = Field(None, max_length=100)  # Denormalized
    
    # Invitee info
    email: str = Field(..., description="Email address of invitee")
    invited_user_id: Optional[str] = Field(None, description="User ID if already registered")
    
    # Inviter info
    invited_by: str = Field(..., min_length=1, description="User ID of inviter")
    invited_by_name: Optional[str] = Field(None, max_length=100)  # Denormalized
    
    # Invitation details
    message: Optional[str] = Field(None, max_length=500, description="Personal message")
    status: InvitationStatus = Field(default=InvitationStatus.PENDING)
    
    # Timestamps
    invited_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=7),
        description="Invitation expiry date"
    )
    responded_at: Optional[datetime] = None
    
    # Response
    response_message: Optional[str] = Field(None, max_length=200)
    
    @field_validator('status')
    @classmethod
    def validate_status_transition(cls, v: InvitationStatus, values) -> InvitationStatus:
        """Validate status transitions"""
        # Once accepted/declined, cannot change
        if 'status' in values.data:
            old_status = values.data.get('status')
            if old_status in [InvitationStatus.ACCEPTED, InvitationStatus.DECLINED]:
                if v != old_status:
                    raise ValueError(f"Cannot change status from {old_status} to {v}")
        return v
    
    def to_dict(self) -> dict:
        """
        Convert model to dictionary for Firestore
        Adds invited_email alias for frontend compatibility
        """
        data = super().to_dict()
        # Add invited_email alias for frontend compatibility
        data['invited_email'] = data.get('email')
        return data
    
    def is_expired(self) -> bool:
        """Check if invitation has expired"""
        return datetime.utcnow() > self.expires_at
    
    def can_accept(self) -> bool:
        """Check if invitation can be accepted"""
        return (
            self.status == InvitationStatus.PENDING and
            not self.is_expired()
        )
    
    def accept(self) -> None:
        """Mark invitation as accepted"""
        if not self.can_accept():
            raise ValueError("Cannot accept invitation")
        self.status = InvitationStatus.ACCEPTED
        self.responded_at = datetime.utcnow()
    
    def decline(self, message: Optional[str] = None) -> None:
        """Mark invitation as declined"""
        if self.status != InvitationStatus.PENDING:
            raise ValueError("Can only decline pending invitations")
        self.status = InvitationStatus.DECLINED
        self.responded_at = datetime.utcnow()
        if message:
            self.response_message = message
