# Purpose: AI Consent Routes — REST API for managing Scout agent consent. Endpoints:.
"""
AI Consent Routes — REST API for managing Scout agent consent.

Endpoints:
  GET    /groups/<group_id>/ai/consent       — Check current consent status
  POST   /groups/<group_id>/ai/consent       — Grant or decline consent
  DELETE /groups/<group_id>/ai/consent       — Revoke consent (forget me)
"""
import logging
from datetime import datetime, timezone

from app.core.apiutils.responses import error_response, success_response
from app.core.rate_limiter import limit_api
from app.auth.security.decorators import require_auth, require_group_role
from app.core.db.connection import get_db
from app.scout.services.consent_gate import ConsentGate
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

ai_consent_bp = Blueprint(
    'ai_consent',
    __name__,
    url_prefix='/api/v1/group-planner',
)


@ai_consent_bp.route('/groups/<group_id>/ai/consent', methods=['GET'])
@require_auth
@require_group_role('viewer')
@limit_api('read_light')
def get_consent_status(group_id):
    """Check whether the authenticated user has granted AI consent in this group."""
    with get_db() as session:
        result = ConsentGate.check(session, group_id, g.user_id)
        return success_response({
            'allowed': result.allowed,
            'needs_prompt': result.needs_prompt,
            'consented_member_count': len(result.consented_user_ids),
        })


@ai_consent_bp.route('/groups/<group_id>/ai/consent', methods=['POST'])
@require_auth
@require_group_role('member')
@limit_api('create')
def update_consent(group_id):
    """Grant or decline AI consent."""
    body = request.json or {}
    action = body.get('action')  # 'grant' or 'decline'

    if action not in ('grant', 'decline'):
        return error_response("action must be 'grant' or 'decline'", 400)

    ip_address = request.remote_addr or '0.0.0.0'
    user_agent = request.headers.get('User-Agent', '')
    accept_language = request.headers.get('Accept-Language', '')
    gpc_signal = request.headers.get('Sec-GPC', '0')
    jurisdiction = ConsentGate.detect_jurisdiction(accept_language, gpc_signal)

    # CCPA: GPC signal forces auto-decline
    if ConsentGate.should_auto_decline(gpc_signal, jurisdiction):
        action = 'decline'

    with get_db() as session:
        if action == 'grant':
            consent = ConsentGate.grant(
                session=session,
                group_id=group_id,
                user_id=g.user_id,
                jurisdiction=jurisdiction,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.commit()
            return success_response({
                'granted': True,
                'jurisdiction': jurisdiction,
                'message': 'Got it. I can now help with travel questions for this group.',
            })
        else:
            consent = ConsentGate.decline(
                session=session,
                group_id=group_id,
                user_id=g.user_id,
                jurisdiction=jurisdiction,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.commit()
            return success_response({
                'granted': False,
                'jurisdiction': jurisdiction,
                'message': "No problem. I won't read your data. You can change your mind anytime.",
            })


@ai_consent_bp.route('/groups/<group_id>/ai/consent', methods=['DELETE'])
@require_auth
@require_group_role('member')
@limit_api('delete')
def revoke_consent(group_id):
    """Revoke consent and delete the AI data held about the caller.

    Idempotent: it used to answer 404 when no AIConsent row existed, which
    made erasure unreachable for precisely the users who needed it, since a
    user who never saw a consent card could still have preference rows and
    agent logs written about them (audit P0-10, P1-35). Deletion is a
    request to end up with no data, and that is satisfiable either way.
    """
    with get_db() as session:
        ConsentGate.revoke(session, group_id, g.user_id)
        session.commit()

        return success_response({
            'revoked': True,
            # Claims only what revoke() does. The old copy promised
            # "summaries updated" while never touching a summary.
            'message': (
                'Done. Your saved preferences, your agent logs and this '
                "group's chat summaries have been deleted, and cached AI "
                'answers for the group were cleared.'
            ),
        })
