"""
Group Models
Group, GroupMember, and GroupSettings
"""

from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator

from .base import BaseModel
from ..constants import GroupRole, Currency
from ..config import business_rules


class GroupSettings(BaseModel):
    """Group settings and preferences"""
    
    default_currency: Currency = Field(default=Currency.USD)
    allow_guests: bool = Field(default=False)
    require_approval_for_expenses: bool = Field(default=False)
    max_expense_amount: float = Field(default=business_rules.MAX_EXPENSE_AMOUNT)


class Group(BaseModel):
    """Expense group model"""
    
    group_id: Optional[str] = Field(None, description="Firestore document ID")
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=business_rules.MAX_GROUP_NAME_LENGTH,
        description="Group name"
    )
    description: Optional[str] = Field(
        None, 
        max_length=business_rules.MAX_DESCRIPTION_LENGTH,
        description="Group description"
    )
    
    # Owner
    created_by: str = Field(..., min_length=1, description="Creator user ID")
    
    # Members array (list of user IDs) - CRITICAL for queries
    members: List[str] = Field(default_factory=list, description="List of member user IDs")
    
    # Member details map (user_id -> details)
    member_details: Dict[str, Any] = Field(default_factory=dict, description="Member details keyed by user_id")
    
    # Group invite code
    group_code: Optional[str] = Field(None, max_length=20, description="Unique invite code")
    
    # Settings
    currency: Currency = Field(default=Currency.USD)
    settings: GroupSettings = Field(default_factory=GroupSettings)
    
    # Metadata
    is_active: bool = Field(default=True)
    member_count: int = Field(default=1, ge=1)
    total_expenses: int = Field(default=0, ge=0)
    
    # Group image
    image_url: Optional[str] = None
    
    @field_validator('member_count')
    @classmethod
    def validate_member_count(cls, v: int) -> int:
        """Validate member count doesn't exceed maximum"""
        if v > business_rules.MAX_GROUP_MEMBERS:
            raise ValueError(f"Group cannot have more than {business_rules.MAX_GROUP_MEMBERS} members")
        return v


class GroupMember(BaseModel):
    """
    Group membership model with soft-delete support (Phase 15)
    
    Soft-delete preserves member info for transaction history.
    Removed members show their name in past expenses but can't be 
    added to new expenses unless they rejoin.
    """
    
    membership_id: Optional[str] = Field(None, description="Format: {group_id}_{user_id}")
    group_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    
    # Role and permissions
    role: GroupRole = Field(default=GroupRole.MEMBER)
    
    # User info (denormalized for quick access)
    user_name: Optional[str] = Field(None, max_length=100)
    user_email: Optional[str] = None
    user_picture: Optional[str] = None
    
    # Phase 15: Cached user info (survives user account deletion)
    cached_display_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="Preserved display name for transaction history"
    )
    cached_email: Optional[str] = Field(
        None,
        description="Preserved email for transaction history"
    )
    
    # Membership status
    is_active: bool = Field(default=True, description="False = soft-deleted/removed")
    joined_at: Optional[str] = None
    
    # Phase 15: Soft-delete fields
    removed_at: Optional[str] = Field(
        None,
        description="Timestamp when member was removed from group"
    )
    removed_by: Optional[str] = Field(
        None,
        description="User ID who removed this member"
    )
    removal_reason: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional reason for removal (left, kicked, etc.)"
    )
    
    # Balance tracking
    net_balance: float = Field(default=0.0, description="User's net balance in group")
    
    def generate_membership_id(self) -> str:
        """Generate membership ID from group_id and user_id"""
        return f"{self.group_id}_{self.user_id}"
    
    def get_display_name(self) -> str:
        """
        Get best available display name for this member.
        Falls back to cached name if user_name is not available.
        """
        return self.user_name or self.cached_display_name or self.user_email or self.user_id


class GroupCreate(BaseModel):
    """Model for creating a new group"""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=business_rules.MAX_GROUP_NAME_LENGTH
    )
    description: Optional[str] = Field(
        None,
        max_length=business_rules.MAX_DESCRIPTION_LENGTH
    )
    currency: Currency = Field(default=Currency.USD)
    category: Optional[str] = Field(None, max_length=50)


class GroupUpdate(BaseModel):
    """Model for updating a group"""
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=business_rules.MAX_GROUP_NAME_LENGTH
    )
    description: Optional[str] = Field(
        None,
        max_length=business_rules.MAX_DESCRIPTION_LENGTH
    )
    category: Optional[str] = Field(None, max_length=50)
    is_archived: Optional[bool] = None


class GroupSummary(BaseModel):
    """
    Group summary with members and balances
    Used for efficient group detail page loading
    """
    
    group: Group
    members: List[GroupMember] = Field(default_factory=list)
    recent_expense_count: int = Field(default=0)
    
    # Quick stats
    total_spent: float = Field(default=0.0)
    unsettled_amount: float = Field(default=0.0)
