"""
User Domain Models
===================
User, UserSession, and AuditLog models for authentication, session management,
and security audit trail.
"""
from app.infrastructure.db.base import Base
from app.infrastructure.db.uuid7 import CoercingUuid as Uuid
from app.infrastructure.db.uuid7 import uuid7
from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Index,
                        Integer, String, Text)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class User(Base):
    """
    Unified User Model.
    Shared between Expense Engine and Group Planner.
    """
    __tablename__ = 'users'

    id = Column(Uuid, primary_key=True, default=uuid7)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100))
    photo_url = Column(Text)
    phone = Column(String(20))
    default_currency = Column(String(3), default='USD')
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)

    # Relationships
    sessions = relationship(
        'UserSession',
        back_populates='user',
        cascade='all, delete-orphan'
    )
    groups_owned = relationship(
        'Group',
        back_populates='owner',
        foreign_keys='Group.created_by'
    )
    memberships = relationship(
        'GroupMember',
        back_populates='user',
        foreign_keys='GroupMember.user_id'
    )
    expenses_paid = relationship(
        'Expense',
        back_populates='payer',
        foreign_keys='Expense.paid_by'
    )
    expenses_created = relationship(
        'Expense',
        back_populates='creator',
        foreign_keys='Expense.created_by'
    )

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary for API responses."""
        data = {
            'id': str(self.id),
            'user_id': str(self.id),
            'email': self.email,
            'display_name': self.display_name,
            'photo_url': self.photo_url,
            'phone': self.phone,
            'default_currency': self.default_currency,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
        if include_sensitive:
            data['password_hash'] = self.password_hash
        return data

    def __repr__(self) -> str:
        return f'<User {self.email}>'


class UserSession(Base):
    """User session for refresh token management."""
    __tablename__ = 'user_sessions'
    __table_args__ = (
        Index('idx_user_sessions_token', 'refresh_token'),
        Index('idx_user_sessions_user', 'user_id'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    user_id = Column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    refresh_token = Column(String(500), nullable=False, index=True)
    device_info = Column(Text)
    ip_address = Column(String(45))
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime)

    # Relationships
    user = relationship('User', back_populates='sessions')

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'device_info': self.device_info,
            'ip_address': self.ip_address,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
        }

    def __repr__(self) -> str:
        return f'<UserSession user_id={self.user_id}>'


class AuditLog(Base):
    """
    Security audit trail for destructive and sensitive operations.

    Every delete, password change, login failure, and admin action is recorded
    with the full before-state snapshot, IP address, and user agent.
    """
    __tablename__ = 'audit_log'
    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_action', 'action', 'created_at'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Uuid)
    old_data = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=func.now())

    user = relationship('User')

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': str(self.resource_id) if self.resource_id else None,
            'old_data': self.old_data,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f'<AuditLog {self.action} {self.resource_type}:{self.resource_id}>'
        return f'<AuditLog {self.action} {self.resource_type}:{self.resource_id}>'
        return f'<AuditLog {self.action} {self.resource_type}:{self.resource_id}>'
        return f'<AuditLog {self.action} {self.resource_type}:{self.resource_id}>'
