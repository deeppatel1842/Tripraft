"""
SQLAlchemy ORM Models for Group Planner
=========================================
All database tables for collaborative travel planning.

Base and User are imported from shared_db (single source of truth).
All Group Planner-specific models (TravelGroup, Place, Poll, etc.) are defined here.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

# Import shared Base and User — single source of truth
from app.infrastructure.db.base import Base
from app.domain.users.models import User, UserSession
from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Float,
                        ForeignKey, Index, Integer, Numeric, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class TravelGroup(Base):
    """Travel group model for collaborative trip planning"""
    __tablename__ = 'travel_groups'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    destination = Column(String(255))
    destination_lat = Column(Float)  # Latitude for map centering
    destination_lng = Column(Float)  # Longitude for map centering
    destination_type = Column(String(20))  # 'country', 'state', or 'city'
    destination_id = Column(String(50))  # Reference to locations database
    group_code = Column(String(20), unique=True, index=True)
    group_image = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)  # References shared users table
    
    # Trip dates
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Budget
    estimated_budget = Column(Numeric(12, 2))
    budget_currency = Column(String(3), default='USD')
    
    # Expense engine integration
    expense_group_id = Column(Integer)  # Link to expense_engine group
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships - Note: User relationships defined via backref in expense_engine
    owner = relationship('User', foreign_keys=[created_by])
    members = relationship('TripMember', back_populates='group', cascade='all, delete-orphan')
    places = relationship('Place', back_populates='group', cascade='all, delete-orphan')
    polls = relationship('Poll', back_populates='group', cascade='all, delete-orphan')
    invitations = relationship('TripInvitation', back_populates='group', cascade='all, delete-orphan')
    checklist_items = relationship('ChecklistItem', back_populates='group', cascade='all, delete-orphan')
    itinerary = relationship('ItineraryDocument', back_populates='group', uselist=False, cascade='all, delete-orphan')
    activities = relationship('GroupActivity', back_populates='group', cascade='all, delete-orphan')
    
    def to_dict(self, include_members=False, include_places=False, include_polls=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'group_id': str(self.id),  # Frontend expects string group_id
            'name': self.name,
            'description': self.description,
            'destination': self.destination,
            'destination_lat': self.destination_lat,
            'destination_lng': self.destination_lng,
            'destination_type': self.destination_type,
            'destination_id': self.destination_id,
            'destination_coordinates': {
                'lat': self.destination_lat,
                'lng': self.destination_lng
            } if self.destination_lat and self.destination_lng else None,
            'group_code': self.group_code,
            'group_image': self.group_image,
            'created_by': self.created_by,
            'created_by_name': self.owner.display_name if self.owner else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'estimated_budget': float(self.estimated_budget) if self.estimated_budget else None,
            'budget_currency': self.budget_currency,
            'expense_group_id': self.expense_group_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'member_count': len([m for m in self.members if m.is_active]) if self.members else 0
        }
        
        if include_members and self.members:
            # Return member data with user info and role info merged
            members_data = []
            for m in self.members:
                if m.is_active and m.user:
                    member_dict = {
                        'id': m.user.id,
                        'user_id': m.user.id,
                        'email': m.user.email,
                        'display_name': m.user.display_name,
                        'photo_url': m.user.photo_url,
                        'role': m.role,
                        'is_creator': m.role == 'creator',
                        'joined_at': m.joined_at.isoformat() if m.joined_at else None
                    }
                    members_data.append(member_dict)
            data['members'] = members_data
            data['member_details'] = [m.to_dict() for m in self.members if m.is_active]
        
        if include_places and self.places:
            data['places'] = [p.to_dict() for p in self.places if not p.is_deleted]
        
        if include_polls and self.polls:
            data['polls'] = [p.to_dict() for p in self.polls if not p.is_deleted]
        
        return data


class TripMember(Base):
    """Trip/Group membership model for Group Planner
    Note: Named TripMember to avoid conflict with expense_engine GroupMember
    Table name is gp_group_members (Group Planner specific)
    """
    __tablename__ = 'gp_group_members'
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_gp_group_member'),
        Index('idx_gp_group_members_user', 'user_id', 'is_active'),
        Index('idx_gp_group_members_group', 'group_id', 'is_active'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('travel_groups.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # References shared users table
    role = Column(String(20), default='member')  # creator, admin, member
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=func.now())
    removed_at = Column(DateTime)
    removed_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    group = relationship('TravelGroup', back_populates='members')
    user = relationship('User', foreign_keys=[user_id])
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'user_id': self.user_id,
            'role': self.role,
            'is_active': self.is_active,
            'is_creator': self.role == 'creator',
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'display_name': self.user.display_name if self.user else None,
            'email': self.user.email if self.user else None,
            'photo_url': self.user.photo_url if self.user else None
        }


class Place(Base):
    """Place to visit model"""
    __tablename__ = 'gp_places'
    __table_args__ = (
        Index('idx_gp_places_group', 'group_id', 'is_deleted'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('travel_groups.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    category = Column(String(50))  # restaurant, attraction, hotel, activity, etc.
    
    # Planning details
    visit_date = Column(Date)
    suggested_duration = Column(String(50))
    remarks = Column(Text)
    
    # Additional info
    photo_url = Column(Text)
    website = Column(Text)
    rating = Column(Float)
    
    # Metadata
    added_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    group = relationship('TravelGroup', back_populates='places')
    adder = relationship('User', foreign_keys=[added_by])
    votes = relationship('PlaceVote', back_populates='place', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        vote_user_ids = [v.user_id for v in self.votes] if self.votes else []
        return {
            'id': str(self.id),
            'group_id': self.group_id,
            'name': self.name,
            'description': self.description,
            'address': self.address,
            'coordinates': [self.latitude, self.longitude] if self.latitude and self.longitude else None,
            'category': self.category,
            'visit_date': self.visit_date.isoformat() if self.visit_date else None,
            'suggested_duration': self.suggested_duration,
            'remarks': self.remarks,
            'photo_url': self.photo_url,
            'website': self.website,
            'rating': self.rating,
            'added_by': self.added_by,
            'added_by_name': self.adder.display_name if self.adder else None,
            'votes': vote_user_ids,
            'vote_count': len(vote_user_ids),
            'added_at': self.created_at.isoformat() if self.created_at else None
        }


class PlaceVote(Base):
    """Place vote model - tracks who voted for which place"""
    __tablename__ = 'gp_place_votes'
    __table_args__ = (
        UniqueConstraint('place_id', 'user_id', name='uq_gp_place_vote'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(Integer, ForeignKey('gp_places.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    place = relationship('Place', back_populates='votes')
    user = relationship('User')


class Poll(Base):
    """Poll model for group voting"""
    __tablename__ = 'gp_polls'
    __table_args__ = (
        Index('idx_gp_polls_group', 'group_id', 'is_deleted'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('travel_groups.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    options = Column(JSON, nullable=False)  # List of option strings
    is_multiple_choice = Column(Boolean, default=False)
    expires_at = Column(DateTime)
    
    # Metadata
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    group = relationship('TravelGroup', back_populates='polls')
    creator = relationship('User', foreign_keys=[created_by])
    votes = relationship('PollVote', back_populates='poll', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        # Calculate vote counts per option
        vote_counts = {}
        votes_detail = {}
        voted_by = []
        
        for option in self.options:
            vote_counts[option] = 0
            votes_detail[option] = []
        
        if self.votes:
            for vote in self.votes:
                option = vote.option
                if option in vote_counts:
                    vote_counts[option] += 1
                    votes_detail[option].append(vote.user_id)
                if vote.user_id not in voted_by:
                    voted_by.append(vote.user_id)
        
        return {
            'id': str(self.id),
            'group_id': self.group_id,
            'name': self.name,
            'options': self.options,
            'votes': vote_counts,
            'votes_detail': votes_detail,
            'voted_by': voted_by,
            'is_multiple_choice': self.is_multiple_choice,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_by': self.created_by,
            'created_by_name': self.creator.display_name if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PollVote(Base):
    """Poll vote model"""
    __tablename__ = 'gp_poll_votes'
    __table_args__ = (
        UniqueConstraint('poll_id', 'user_id', 'option', name='uq_gp_poll_vote'),
        Index('idx_gp_poll_votes', 'poll_id', 'user_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(Integer, ForeignKey('gp_polls.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    option = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    poll = relationship('Poll', back_populates='votes')
    user = relationship('User')


class TripInvitation(Base):
    """Group invitation model for trip planning
    Note: Named TripInvitation to avoid conflict with expense_engine Invitation
    Table name is gp_invitations (Group Planner specific)
    """
    __tablename__ = 'gp_invitations'
    __table_args__ = (
        UniqueConstraint('group_id', 'invitee_email', name='uq_gp_invitation'),
        Index('idx_gp_invitations_email', 'invitee_email', 'status'),
        Index('idx_gp_invitations_group', 'group_id', 'status'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('travel_groups.id', ondelete='CASCADE'), nullable=False)
    invitee_email = Column(String(255), nullable=False)
    invitee_user_id = Column(Integer, ForeignKey('users.id'))
    invited_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String(20), default='pending')  # pending, accepted, declined, expired
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    responded_at = Column(DateTime)
    
    # Relationships
    group = relationship('TravelGroup', back_populates='invitations')
    invitee = relationship('User', foreign_keys=[invitee_user_id])
    inviter = relationship('User', foreign_keys=[invited_by])
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'invitation_id': str(self.id),
            'group_id': str(self.group_id),
            'group_name': self.group.name if self.group else None,
            'invitee_email': self.invitee_email,
            'invited_email': self.invitee_email,
            'invitee_user_id': self.invitee_user_id,
            'invited_by': self.invited_by,
            'invited_by_name': self.inviter.display_name if self.inviter else None,
            'status': self.status,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None
        }


class ChecklistItem(Base):
    """Checklist item model for trip preparation"""
    __tablename__ = 'gp_checklist_items'
    __table_args__ = (
        Index('idx_gp_checklist_group', 'group_id', 'is_deleted'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('travel_groups.id', ondelete='CASCADE'), nullable=False)
    item = Column(String(500), nullable=False)
    completed = Column(Boolean, default=False)
    completed_by = Column(Integer, ForeignKey('users.id'))
    completed_at = Column(DateTime)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    group = relationship('TravelGroup', back_populates='checklist_items')
    author = relationship('User', foreign_keys=[author_id])
    completer = relationship('User', foreign_keys=[completed_by])
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'group_id': self.group_id,
            'item': self.item,
            'completed': self.completed,
            'completed_by': self.completed_by,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'authorId': self.author_id,
            'author_name': self.author.display_name if self.author else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ItineraryDocument(Base):
    """Itinerary document model for collaborative trip planning"""
    __tablename__ = 'gp_itinerary_documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('travel_groups.id', ondelete='CASCADE'), nullable=False, unique=True)
    content = Column(Text, default='')  # Markdown content
    last_edited_by = Column(Integer, ForeignKey('users.id'))
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    group = relationship('TravelGroup', back_populates='itinerary')
    editor = relationship('User', foreign_keys=[last_edited_by])
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'content': self.content,
            'last_edited_by': self.last_edited_by,
            'last_edited_by_name': self.editor.display_name if self.editor else None,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class GroupActivity(Base):
    """Activity log for group changes (real-time updates)"""
    __tablename__ = 'gp_group_activities'
    __table_args__ = (
        Index('idx_gp_activities_group', 'group_id', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('travel_groups.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(50), nullable=False)  # place_added, poll_created, member_joined, etc.
    entity_type = Column(String(50))  # place, poll, member, checklist, etc.
    entity_id = Column(Integer)
    details = Column(JSON)  # Additional details about the action
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    group = relationship('TravelGroup', back_populates='activities')
    user = relationship('User')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'user_id': self.user_id,
            'user_name': self.user.display_name if self.user else None,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
