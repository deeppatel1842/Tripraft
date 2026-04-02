"""
SQLAlchemy ORM Models for AI Agent System
==========================================
Tables for consent management, preference profiles, and agent logging.

Supports the Scout (@scout) travel guide agent embedded in group chat.
All models follow project conventions: UUIDv7 PKs, timezone-aware timestamps,
explicit indexes, and bidirectional relationships.
"""

from app.infrastructure.db.base import Base
from app.infrastructure.db.uuid7 import CoercingUuid as Uuid
from app.infrastructure.db.uuid7 import uuid7
from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Fixed set of valid preference keys — no arbitrary keys allowed.
VALID_PREFERENCE_KEYS = frozenset({
    'food', 'budget', 'pace', 'interests', 'accommodation', 'transport_pref',
    'home_country', 'current_location',
})

# Fixed set of valid consent types.
VALID_CONSENT_TYPES = frozenset({
    'chat_history_read',
})

# Fixed set of valid preference sources.
VALID_PREFERENCE_SOURCES = frozenset({
    'chat_summary', 'poll_vote', 'place_vote', 'explicit',
})

# Fixed set of valid jurisdictions.
VALID_JURISDICTIONS = frozenset({
    'GDPR', 'DPDPA', 'CCPA',
})

# Fixed set of valid agent names.
VALID_AGENT_NAMES = frozenset({
    'scout', 'crew',
})


class AIConsent(Base):
    """
    Tracks per-user, per-group, per-consent-type AI data access consent.

    Multi-jurisdiction: GDPR (UK/EU), DPDPA (India), CCPA (California).
    Every row is an immutable audit record — revocation sets revoked_at
    rather than deleting the row.
    """
    __tablename__ = 'ai_consent'
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', 'consent_type', name='uq_ai_consent_group_user_type'),
        Index('idx_ai_consent_group', 'group_id', postgresql_where='granted = TRUE'),
        Index('idx_ai_consent_user', 'user_id'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    group_id = Column(Uuid, ForeignKey('travel_groups.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    consent_type = Column(String(30), nullable=False, default='chat_history_read')
    granted = Column(Boolean, nullable=False, default=False)
    consent_version = Column(String(10), nullable=False, default='1.0')
    jurisdiction = Column(String(10), nullable=False, default='GDPR')
    notice_shown_at = Column(DateTime(timezone=True), nullable=False)
    granted_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    ip_address = Column(String(45), nullable=False)  # IPv4/IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    group = relationship('TravelGroup', lazy='select')
    user = relationship('User', lazy='select')

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'group_id': str(self.group_id),
            'user_id': str(self.user_id),
            'consent_type': self.consent_type,
            'granted': self.granted,
            'consent_version': self.consent_version,
            'jurisdiction': self.jurisdiction,
            'notice_shown_at': self.notice_shown_at.isoformat() if self.notice_shown_at else None,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AIPreferenceProfile(Base):
    """
    Stores extracted travel preferences per user per group.

    Only populated from consented members' summarized chat data,
    poll votes, or explicit user input. Never from raw messages.

    preference_key is restricted to VALID_PREFERENCE_KEYS.
    """
    __tablename__ = 'ai_preference_profiles'
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', 'preference_key', name='uq_ai_prefs_group_user_key'),
        Index('idx_ai_prefs_group', 'group_id'),
        Index('idx_ai_prefs_user', 'user_id'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    group_id = Column(Uuid, ForeignKey('travel_groups.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    preference_key = Column(String(50), nullable=False)
    preference_value = Column(String(200), nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    source = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    group = relationship('TravelGroup', lazy='select')
    user = relationship('User', lazy='select')

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'group_id': str(self.group_id),
            'user_id': str(self.user_id),
            'preference_key': self.preference_key,
            'preference_value': self.preference_value,
            'confidence': self.confidence,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AIAgentLog(Base):
    """
    Audit log for every Scout/Crew agent interaction.

    query_text is sanitized (no PII, no raw messages).
    Retained for 90 days, then purged by Celery cleanup task.
    """
    __tablename__ = 'ai_agent_logs'
    __table_args__ = (
        Index('idx_agent_logs_group', 'group_id', 'created_at'),
        Index('idx_agent_logs_agent', 'agent', 'created_at'),
    )

    id = Column(Uuid, primary_key=True, default=uuid7)
    group_id = Column(Uuid, nullable=False)
    user_id = Column(Uuid, nullable=False)
    agent = Column(String(10), nullable=False)
    intent = Column(String(30), nullable=False)
    query_text = Column(Text, nullable=False)
    response_summary = Column(String(500))
    tokens_used = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False)
    cache_hit = Column(Boolean, nullable=False, default=False)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'group_id': str(self.group_id),
            'user_id': str(self.user_id),
            'agent': self.agent,
            'intent': self.intent,
            'query_text': self.query_text,
            'response_summary': self.response_summary,
            'tokens_used': self.tokens_used,
            'latency_ms': self.latency_ms,
            'cache_hit': self.cache_hit,
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
