"""
Group Planner Models
Data models for collaborative travel planning system
Following expense engine architecture patterns
"""

import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum


class GroupRole(Enum):
    """Member roles in travel groups"""
    CREATOR = "creator"
    ADMIN = "admin" 
    MEMBER = "member"


class InvitationStatus(Enum):
    """Group invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PlaceCategory(Enum):
    """Categories for places to visit"""
    RESTAURANT = "restaurant"
    ATTRACTION = "attraction"
    HOTEL = "hotel"
    ACTIVITY = "activity"
    SHOPPING = "shopping"
    TRANSPORT = "transport"
    OTHER = "other"


@dataclass
class TravelGroup:
    """Travel group data model"""
    group_id: str
    name: str
    description: str
    created_by: str
    created_at: datetime
    members: List[str]
    destination: Optional[str] = None
    trip_dates: Optional[Dict] = None
    budget_range: Optional[Dict] = None
    group_image: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        data = asdict(self)
        # Convert datetime to ISO string for Firebase
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TravelGroup':
        """Create from dictionary (Firebase data)"""
        # Convert ISO string back to datetime
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class GroupMember:
    """Group member data model"""
    user_id: str
    group_id: str
    role: str  # GroupRole enum value
    joined_at: datetime
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        data = asdict(self)
        data['joined_at'] = self.joined_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroupMember':
        """Create from dictionary (Firebase data)"""
        if isinstance(data['joined_at'], str):
            data['joined_at'] = datetime.fromisoformat(data['joined_at'])
        return cls(**data)


@dataclass
class Place:
    """Place to visit data model"""
    place_id: str
    group_id: str
    name: str
    description: str
    coordinates: Optional[List[float]]  # [lat, lng]
    address: Optional[str]
    category: str  # PlaceCategory enum value
    added_by: str
    added_at: datetime
    votes: List[str]  # List of user IDs who voted
    vote_count: int
    remarks: List[Dict]  # List of {user_id, text, timestamp}
    photo_url: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        data = asdict(self)
        data['added_at'] = self.added_at.isoformat()
        # Convert remark timestamps to ISO strings
        for remark in data['remarks']:
            if isinstance(remark.get('timestamp'), datetime):
                remark['timestamp'] = remark['timestamp'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Place':
        """Create from dictionary (Firebase data)"""
        if isinstance(data['added_at'], str):
            data['added_at'] = datetime.fromisoformat(data['added_at'])
        # Convert remark timestamps back to datetime
        for remark in data['remarks']:
            if isinstance(remark.get('timestamp'), str):
                remark['timestamp'] = datetime.fromisoformat(remark['timestamp'])
        return cls(**data)


@dataclass
class TravelPoll:
    """Travel poll data model"""
    poll_id: str
    group_id: str
    question: str
    options: List[str]
    votes: Dict[str, str]  # user_id -> option
    created_by: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_multiple_choice: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TravelPoll':
        """Create from dictionary (Firebase data)"""
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('expires_at') and isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


@dataclass
class GroupInvitation:
    """Group invitation data model"""
    invitation_id: str
    group_id: str
    invited_by: str
    invited_email: str
    invited_user: Optional[str]  # Set if user already exists
    status: str  # InvitationStatus enum value
    created_at: datetime
    expires_at: datetime
    responded_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        if self.responded_at:
            data['responded_at'] = self.responded_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroupInvitation':
        """Create from dictionary (Firebase data)"""
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        if data.get('responded_at') and isinstance(data['responded_at'], str):
            data['responded_at'] = datetime.fromisoformat(data['responded_at'])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if invitation has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_pending(self) -> bool:
        """Check if invitation is still pending"""
        return self.status == InvitationStatus.PENDING.value and not self.is_expired()


@dataclass
class TripDocument:
    """Trip planning document data model"""
    document_id: str
    group_id: str
    title: str
    content: str  # Markdown content
    last_edited_by: str
    last_edited_at: datetime
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        data = asdict(self)
        data['last_edited_at'] = self.last_edited_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TripDocument':
        """Create from dictionary (Firebase data)"""
        if isinstance(data['last_edited_at'], str):
            data['last_edited_at'] = datetime.fromisoformat(data['last_edited_at'])
        return cls(**data)


@dataclass
class User:
    """User data model (for group planner context)"""
    uid: str
    email: str
    display_name: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create from dictionary (Firebase data)"""
        if data.get('created_at') and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


# Utility functions for model creation
def create_group_id() -> str:
    """Generate unique group ID"""
    return str(uuid.uuid4())


def create_place_id() -> str:
    """Generate unique place ID"""
    return str(uuid.uuid4())


def create_poll_id() -> str:
    """Generate unique poll ID"""
    return str(uuid.uuid4())


def create_invitation_id() -> str:
    """Generate unique invitation ID"""
    return str(uuid.uuid4())


def create_document_id() -> str:
    """Generate unique document ID"""
    return str(uuid.uuid4())


# Model validation functions
def validate_coordinates(coords: List[float]) -> bool:
    """Validate latitude and longitude coordinates"""
    if not coords or len(coords) != 2:
        return False
    lat, lng = coords
    return -90 <= lat <= 90 and -180 <= lng <= 180


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
