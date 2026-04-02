"""
Consent Gate — Enforces AI data access consent before any processing.

Checks per-user, per-group consent records in ai_consent table.
Supports multi-jurisdiction compliance (GDPR, DPDPA, CCPA).
Respects Global Privacy Control (GPC) browser signal for CCPA.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import Config
from app.domain.ai.models import (VALID_CONSENT_TYPES, VALID_JURISDICTIONS,
                                  AIConsent)

logger = logging.getLogger(__name__)


class ConsentResult:
    """Immutable result from consent check."""
    __slots__ = ('allowed', 'consented_user_ids', 'needs_prompt')

    def __init__(self, allowed: bool, consented_user_ids: list, needs_prompt: bool):
        self.allowed = allowed
        self.consented_user_ids = consented_user_ids
        self.needs_prompt = needs_prompt


class ConsentGate:
    """Checks and enforces AI consent before any data access."""

    @staticmethod
    def check(session, group_id: str, user_id: str) -> ConsentResult:
        """
        Check whether a user has granted AI consent in a group.

        Returns ConsentResult with:
          - allowed: True if sender has active consent
          - consented_user_ids: all members with active consent in this group
          - needs_prompt: True if sender has never been shown the consent card
        """
        sender_consent = session.query(AIConsent).filter_by(
            group_id=group_id,
            user_id=user_id,
            consent_type='chat_history_read',
        ).first()

        if not sender_consent:
            return ConsentResult(allowed=False, consented_user_ids=[], needs_prompt=True)

        if not sender_consent.granted or sender_consent.revoked_at is not None:
            return ConsentResult(allowed=False, consented_user_ids=[], needs_prompt=False)

        # Invalidate stale consent if consent version has changed
        if sender_consent.consent_version != Config.SCOUT_CONSENT_VERSION:
            return ConsentResult(allowed=False, consented_user_ids=[], needs_prompt=True)

        # Fetch all consented members in this group
        consented = session.query(AIConsent.user_id).filter_by(
            group_id=group_id,
            consent_type='chat_history_read',
            granted=True,
        ).filter(
            AIConsent.revoked_at.is_(None),
            AIConsent.consent_version == Config.SCOUT_CONSENT_VERSION,
        ).all()

        return ConsentResult(
            allowed=True,
            consented_user_ids=[str(c.user_id) for c in consented],
            needs_prompt=False,
        )

    @staticmethod
    def grant(
        session,
        group_id: str,
        user_id: str,
        jurisdiction: str,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> AIConsent:
        """Record consent grant. Upserts if a previous record exists."""
        now = datetime.now(timezone.utc)
        jurisdiction = jurisdiction if jurisdiction in VALID_JURISDICTIONS else 'GDPR'

        existing = session.query(AIConsent).filter_by(
            group_id=group_id,
            user_id=user_id,
            consent_type='chat_history_read',
        ).first()

        if existing:
            existing.granted = True
            existing.granted_at = now
            existing.revoked_at = None
            existing.consent_version = Config.SCOUT_CONSENT_VERSION
            existing.jurisdiction = jurisdiction
            existing.ip_address = ip_address
            existing.user_agent = user_agent
            existing.updated_at = now
            return existing

        consent = AIConsent(
            group_id=group_id,
            user_id=user_id,
            consent_type='chat_history_read',
            granted=True,
            consent_version=Config.SCOUT_CONSENT_VERSION,
            jurisdiction=jurisdiction,
            notice_shown_at=now,
            granted_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(consent)
        return consent

    @staticmethod
    def decline(
        session,
        group_id: str,
        user_id: str,
        jurisdiction: str,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> AIConsent:
        """Record consent decline."""
        now = datetime.now(timezone.utc)
        jurisdiction = jurisdiction if jurisdiction in VALID_JURISDICTIONS else 'GDPR'

        existing = session.query(AIConsent).filter_by(
            group_id=group_id,
            user_id=user_id,
            consent_type='chat_history_read',
        ).first()

        if existing:
            existing.granted = False
            existing.revoked_at = now
            existing.consent_version = Config.SCOUT_CONSENT_VERSION
            existing.jurisdiction = jurisdiction
            existing.ip_address = ip_address
            existing.user_agent = user_agent
            existing.updated_at = now
            return existing

        consent = AIConsent(
            group_id=group_id,
            user_id=user_id,
            consent_type='chat_history_read',
            granted=False,
            consent_version=Config.SCOUT_CONSENT_VERSION,
            jurisdiction=jurisdiction,
            notice_shown_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(consent)
        return consent

    @staticmethod
    def revoke(session, group_id: str, user_id: str) -> bool:
        """
        Revoke consent and delete associated preference data.
        Returns True if consent was found and revoked.
        """
        from app.domain.ai.models import AIPreferenceProfile

        consent = session.query(AIConsent).filter_by(
            group_id=group_id,
            user_id=user_id,
            consent_type='chat_history_read',
        ).first()

        if not consent:
            return False

        now = datetime.now(timezone.utc)
        consent.granted = False
        consent.revoked_at = now
        consent.updated_at = now

        # Delete preference profiles
        session.query(AIPreferenceProfile).filter_by(
            group_id=group_id,
            user_id=user_id,
        ).delete(synchronize_session='fetch')

        logger.info(
            'AI consent revoked: user=%s group=%s, preferences deleted',
            user_id, group_id,
        )
        return True

    @staticmethod
    def detect_jurisdiction(accept_language: str = '', gpc_signal: str = '0') -> str:
        """
        Detect user jurisdiction from request headers.

        Priority: GPC signal (CCPA) > Accept-Language > default GDPR.
        """
        if gpc_signal == '1':
            return 'CCPA'

        lang = accept_language.lower()
        if 'en-in' in lang or 'hi' in lang:
            return 'DPDPA'
        if 'en-us' in lang:
            return 'CCPA'

        # Default to strictest jurisdiction
        return 'GDPR'

    @staticmethod
    def should_auto_decline(gpc_signal: str, jurisdiction: str) -> bool:
        """Check if GPC signal requires automatic opt-out (CCPA compliance)."""
        return jurisdiction == 'CCPA' and gpc_signal == '1'
        return jurisdiction == 'CCPA' and gpc_signal == '1'
        return jurisdiction == 'CCPA' and gpc_signal == '1'
