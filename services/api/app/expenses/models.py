# Purpose: SQLAlchemy ORM Models for Expense Engine Base, User, and UserSession are imported from shared_db (single source of truth).
"""
SQLAlchemy ORM Models for Expense Engine
=========================================
Base, User, and UserSession are imported from shared_db (single source of truth).
All expense-specific models (Group, Expense, Settlement, etc.) are defined here.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.auth.models import User, UserSession
# Import shared Base, User, UserSession — single source of truth
from app.core.db.base import Base
from app.core.db.uuid7 import CoercingUuid as Uuid
from app.core.db.uuid7 import uuid7
from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, ForeignKey,
                        Index, Integer, Numeric, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


_MONEY_QUANTUM = Decimal('0.01')


def money_to_json(value):
    """Render a persisted Decimal at the JSON boundary without float noise.

    JSON has no Decimal number type, while the existing browser contract uses
    numeric amounts. Quantizing immediately before that boundary guarantees a
    two-decimal representation instead of exposing binary calculation noise.
    """
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP))


class Group(Base):
    """Expense group model"""
    __tablename__ = 'groups'

    id = Column(Uuid, primary_key=True, default=uuid7)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    currency = Column(String(3), default='USD')
    created_by = Column(Uuid, ForeignKey('users.id'), nullable=False)
    group_code = Column(String(20), unique=True)
    category = Column(String(50))  # trip, home, couple, friends, etc.
    image_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())  # pyright: ignore
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # pyright: ignore

    # Relationships
    owner = relationship('User', back_populates='groups_owned', foreign_keys=[created_by])
    members = relationship('GroupMember', back_populates='group', cascade='all, delete-orphan')
    expenses = relationship('Expense', back_populates='group', cascade='all, delete-orphan')
    settlements = relationship('Settlement', back_populates='group', cascade='all, delete-orphan')
    balances = relationship('GroupBalance', back_populates='group', cascade='all, delete-orphan')
    invitations = relationship('Invitation', back_populates='group', cascade='all, delete-orphan')

    def to_dict(self, include_members=False):
        """Convert to dictionary"""
        data = {
            'id': str(self.id),
            'group_id': str(self.id),  # Frontend expects group_id as well
            'name': self.name,
            'description': self.description,
            'currency': self.currency,
            'created_by': str(self.created_by),
            'created_by_name': self.owner.display_name if self.owner else None,  # Include owner name
            'group_code': self.group_code,
            'category': self.category,
            'image_url': self.image_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,  # type: ignore
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None,  # type: ignore
            'member_count': len([m for m in self.members if m.is_active]) if self.members else 0
        }
        if include_members:
            data['members'] = [m.to_dict() for m in self.members if m.is_active]
        return data


class GroupMember(Base):
    """Group membership model"""
    __tablename__ = 'group_members'
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_member'),
        Index('idx_group_members_user', 'user_id', 'is_active'),
        Index('idx_group_members_group', 'group_id', 'is_active'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    group_id = Column(Uuid, ForeignKey('groups.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False)
    role = Column(String(20), default='member')  # owner, admin, member
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=func.now())  # pyright: ignore
    removed_at = Column(DateTime)
    removed_by = Column(Uuid, ForeignKey('users.id'))

    # Relationships
    group = relationship('Group', back_populates='members')
    user = relationship('User', back_populates='memberships', foreign_keys=[user_id])

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'group_id': str(self.group_id),
            'user_id': str(self.user_id),
            'role': self.role,
            'is_active': self.is_active,
            'joined_at': self.joined_at.isoformat() if self.joined_at is not None else None,  # type: ignore
            'user': self.user.to_dict() if self.user else None
        }


class Expense(Base):
    """Expense model"""
    __tablename__ = 'expenses'
    __table_args__ = (
        Index('idx_expenses_group', 'group_id', 'is_deleted', 'expense_date'),
        Index('idx_expenses_paid_by', 'paid_by'),
        Index('idx_expenses_paid_by_date', 'paid_by', 'created_at'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    group_id = Column(Uuid, ForeignKey('groups.id', ondelete='CASCADE'), nullable=True)  # Nullable for personal expenses
    description = Column(String(500), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default='USD')
    paid_by = Column(Uuid, ForeignKey('users.id'), nullable=False)
    split_type = Column(String(20), default='equal')  # equal, exact, percentage, shares, none
    category = Column(String(50))
    notes = Column(Text)
    expense_date = Column(Date, default=date.today)
    receipt_url = Column(Text)
    is_deleted = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    created_by = Column(Uuid, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=func.now())  # pyright: ignore
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # pyright: ignore
    deleted_at = Column(DateTime)
    deleted_by = Column(Uuid, ForeignKey('users.id'), nullable=True)  # User who deleted the expense

    # Relationships
    group = relationship('Group', back_populates='expenses')
    payer = relationship('User', back_populates='expenses_paid', foreign_keys=[paid_by])
    creator = relationship('User', back_populates='expenses_created', foreign_keys=[created_by])
    splits = relationship('ExpenseSplit', back_populates='expense', cascade='all, delete-orphan')
    history = relationship('ExpenseHistory', back_populates='expense', cascade='all, delete-orphan')

    def to_dict(self, include_splits=True):
        """Convert to dictionary"""
        data = {
            'id': str(self.id),
            'group_id': str(self.group_id) if self.group_id else None,
            'description': self.description,
            'amount': money_to_json(self.amount),
            'currency': self.currency,
            'paid_by': str(self.paid_by),
            'paid_by_name': self.payer.display_name if self.payer else None,
            'split_type': self.split_type,
            'category': self.category,
            'notes': self.notes,
            'expense_date': self.expense_date.isoformat() if self.expense_date is not None else None,  # type: ignore
            'receipt_url': self.receipt_url,
            'is_deleted': self.is_deleted,
            'is_edited': self.is_edited,
            'created_by': str(self.created_by),
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,  # type: ignore
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None  # type: ignore
        }
        if include_splits and self.splits:
            data['splits'] = [s.to_dict() for s in self.splits]
        return data


class ExpenseSplit(Base):
    """Expense split model - who owes what"""
    __tablename__ = 'expense_splits'
    __table_args__ = (
        UniqueConstraint('expense_id', 'user_id', name='uq_expense_split'),
        Index('idx_expense_splits_user', 'user_id'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    expense_id = Column(Uuid, ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    percentage = Column(Numeric(5, 2))
    shares = Column(Integer)

    # Relationships
    expense = relationship('Expense', back_populates='splits')
    user = relationship('User')

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'expense_id': str(self.expense_id),
            'user_id': str(self.user_id),
            'user_name': self.user.display_name if self.user else None,
            'amount': money_to_json(self.amount),
            'percentage': money_to_json(self.percentage),
            'shares': self.shares
        }


class Settlement(Base):
    """Settlement/payment model"""
    __tablename__ = 'settlements'
    __table_args__ = (
        Index('idx_settlements_group', 'group_id', 'is_deleted'),
        Index('idx_settlements_users', 'from_user_id', 'to_user_id'),
        Index('idx_settlements_group_date', 'group_id', 'settlement_date'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    group_id = Column(Uuid, ForeignKey('groups.id', ondelete='CASCADE'), nullable=False)
    from_user_id = Column(Uuid, ForeignKey('users.id'), nullable=False)
    to_user_id = Column(Uuid, ForeignKey('users.id'), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default='USD')
    method = Column(String(50), default='cash')
    notes = Column(Text)
    proof_url = Column(Text)
    recorded_by = Column(Uuid, ForeignKey('users.id'), nullable=False)
    settlement_date = Column(Date, default=date.today)
    is_deleted = Column(Boolean, default=False)
    # Soft-deletion metadata is part of the persisted audit trail.  These
    # fields must be real mapped columns; assigning unmapped attributes is
    # silently discarded by SQLAlchemy on commit.
    deleted_at = Column(DateTime)
    deleted_by = Column(Uuid, ForeignKey('users.id', name='fk_settlements_deleted_by_user'), nullable=True)
    created_at = Column(DateTime, default=func.now())  # pyright: ignore

    # Relationships
    group = relationship('Group', back_populates='settlements')
    from_user = relationship('User', foreign_keys=[from_user_id])
    to_user = relationship('User', foreign_keys=[to_user_id])
    recorder = relationship('User', foreign_keys=[recorded_by])
    deleter = relationship('User', foreign_keys=[deleted_by])

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'group_id': str(self.group_id),
            'from_user_id': str(self.from_user_id),
            'from_user_name': self.from_user.display_name if self.from_user else None,
            'to_user_id': str(self.to_user_id),
            'to_user_name': self.to_user.display_name if self.to_user else None,
            'amount': money_to_json(self.amount),
            'currency': self.currency,
            'method': self.method,
            'notes': self.notes,
            'proof_url': self.proof_url,
            'recorded_by': str(self.recorded_by),
            'settlement_date': self.settlement_date.isoformat() if self.settlement_date is not None else None,  # type: ignore
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at is not None else None,
            'deleted_by': str(self.deleted_by) if self.deleted_by is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None  # type: ignore
        }


class GroupBalance(Base):
    """Denormalized balance for performance"""
    __tablename__ = 'group_balances'
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_balance'),
        Index('idx_balances_group', 'group_id'),
        Index('idx_balances_user', 'user_id'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    group_id = Column(Uuid, ForeignKey('groups.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False)
    balance = Column(Numeric(12, 2), default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # pyright: ignore

    # Relationships
    group = relationship('Group', back_populates='balances')
    user = relationship('User')

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'user_id': str(self.user_id),
            'user_name': self.user.display_name if self.user else None,
            'balance': money_to_json(self.balance),
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None  # type: ignore
        }


class Invitation(Base):
    """Group invitation model"""
    __tablename__ = 'invitations'
    __table_args__ = (
        UniqueConstraint('group_id', 'invitee_email', name='uq_invitation'),
        Index('idx_invitations_email', 'invitee_email', 'status'),
        Index('idx_invitations_group', 'group_id', 'status'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    group_id = Column(Uuid, ForeignKey('groups.id', ondelete='CASCADE'), nullable=False)
    invitee_email = Column(String(255), nullable=False)
    invitee_user_id = Column(Uuid, ForeignKey('users.id'))
    invited_by = Column(Uuid, ForeignKey('users.id'), nullable=False)
    status = Column(String(20), default='pending')  # pending, accepted, declined, expired
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())  # pyright: ignore
    responded_at = Column(DateTime)

    # Relationships
    group = relationship('Group', back_populates='invitations')
    invitee = relationship('User', foreign_keys=[invitee_user_id])
    inviter = relationship('User', foreign_keys=[invited_by])

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'invitation_id': str(self.id),  # Frontend expects invitation_id
            'group_id': str(self.group_id),
            'group_name': self.group.name if self.group else None,
            'invitee_email': self.invitee_email,
            'invited_email': self.invitee_email,  # Also include as invited_email for compatibility
            'invitee_user_id': str(self.invitee_user_id) if self.invitee_user_id else None,
            'invited_by': str(self.invited_by),
            'invited_by_name': self.inviter.display_name if self.inviter else None,
            'status': self.status,
            'expires_at': self.expires_at.isoformat() if self.expires_at is not None else None,  # type: ignore
            'created_at': self.created_at.isoformat() if self.created_at is not None else None  # type: ignore
        }


class ExpenseHistory(Base):
    """Expense edit history for audit trail"""
    __tablename__ = 'expense_history'
    __table_args__ = (
        Index('idx_expense_history_expense', 'expense_id', 'created_at'),
        Index('idx_expense_history_user', 'changed_by', 'created_at'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    expense_id = Column(Uuid, ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(Uuid, ForeignKey('groups.id'), nullable=True)  # Nullable for personal expenses
    action = Column(String(20), nullable=False)  # created, updated, deleted, restored
    changed_by = Column(Uuid, ForeignKey('users.id'), nullable=False)
    changes_json = Column(JSON)  # Field changes
    before_snapshot = Column(JSON)  # Expense before change
    after_snapshot = Column(JSON)  # Expense after change
    created_at = Column(DateTime, default=func.now())  # pyright: ignore

    # Relationships
    expense = relationship('Expense', back_populates='history')
    changer = relationship('User')

    def to_dict(self):
        """Convert to dictionary"""
        # Parse changes_json if it's a string
        changes = self.changes_json
        if isinstance(changes, str):
            import json
            try:
                changes = json.loads(changes)
            except (json.JSONDecodeError, ValueError):
                changes = []

        return {
            'id': str(self.id),
            'expense_id': str(self.expense_id),
            'group_id': str(self.group_id) if self.group_id else None,
            'action': self.action,
            'changed_by': str(self.changed_by),
            'changed_by_name': self.changer.display_name if self.changer else None,
            'changes': changes,
            'before_snapshot': self.before_snapshot,
            'after_snapshot': self.after_snapshot,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,  # type: ignore
            'changed_at': self.created_at.isoformat() if self.created_at is not None else None  # type: ignore
        }

# UserSession is imported from shared_db.models (see top of file)
# UserSession is imported from shared_db.models (see top of file)
# UserSession is imported from shared_db.models (see top of file)
# UserSession is imported from shared_db.models (see top of file)
