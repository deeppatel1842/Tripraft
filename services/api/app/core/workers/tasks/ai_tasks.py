# Purpose: AI Background Tasks — Celery tasks for Scout agent processing. Tasks:.
"""
AI Background Tasks — Celery tasks for Scout agent processing.

Tasks:
  - process_scout_mention: Handle @scout mentions asynchronously
  - generate_chat_summary: Extract preferences from anonymized chat batches
  - cleanup_agent_logs: Purge logs older than retention period
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from app.core.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name='app.core.workers.tasks.ai_tasks.process_scout_mention',
    max_retries=1,
    soft_time_limit=30,
    default_retry_delay=5,
)
def process_scout_mention(
    self,
    group_id: str,
    sender_id: str,
    message_content: str,
    consent_context: dict | None = None,
):
    """
    Process a @scout mention detected in group chat.

    Called asynchronously from ChatService.send_message() when @scout
    is detected. Posts the response as an AI-type message back to the group.
    """
    from app.core.config import Config
    from app.core.cache.redis import redis_client
    from app.core.db.connection import get_db
    from app.trips.services.chat_service import ChatService
    from app.scout.services.consent_gate import ConsentGate
    from app.scout.services.scout_agent_service import ScoutAgentService

    if not Config.FF_SCOUT_AGENT:
        logger.info('Scout agent disabled, skipping mention in group=%s', group_id)
        return {'status': 'disabled'}

    scout = ScoutAgentService()
    redis = redis_client if redis_client.available else None

    try:
        with get_db() as session:
            # Check for opt-in/opt-out commands first
            opt_result = ScoutAgentService._handle_opt_commands(message_content)
            if opt_result and opt_result.get('response_type') == 'consent_action':
                return _handle_consent_action(
                    session, group_id, sender_id, opt_result['intent'], consent_context,
                )

            success, result = scout.process(
                session=session,
                group_id=group_id,
                sender_id=sender_id,
                message_content=message_content,
                redis_client=redis,
            )

            if success and result.get('response'):
                response_type = result.get('response_type', 'text')
                msg_type = 'text'
                if response_type == 'place_suggestion':
                    msg_type = 'place_suggestion'
                elif response_type == 'consent_card':
                    msg_type = 'system'

                ChatService.send_message(
                    group_id=group_id,
                    sender_id=None,
                    sender_type='ai',
                    content=result['response'],
                    msg_type=msg_type,
                    metadata_json={'agent': 'scout', 'intent': result.get('intent', 'unknown')},
                )

            session.commit()
            return {'status': 'processed', 'intent': result.get('intent', 'unknown')}

    except Exception as exc:
        logger.error('process_scout_mention failed: group=%s error=%s', group_id, exc)
        raise self.retry(exc=exc)
    finally:
        try:
            from app.trips.realtime.events import emit_to_group
            emit_to_group(group_id, 'chat:typing_stop', {'user_id': 'scout'})
        except Exception:
            logger.debug('Could not clear Scout typing indicator', exc_info=True)


def _handle_consent_action(
    session,
    group_id: str,
    sender_id: str,
    intent: str,
    consent_context: dict | None = None,
) -> dict:
    """Handle opt-in/opt-out within the Celery task context."""
    from app.trips.services.chat_service import ChatService
    from app.scout.services.consent_gate import ConsentGate
    consent_context = consent_context or {}
    ip_address = consent_context.get('ip_address') or '0.0.0.0'
    jurisdiction = ConsentGate.detect_jurisdiction(
        accept_language=consent_context.get('jurisdiction', ''),
        gpc_signal=consent_context.get('gpc_signal', '0'),
    )

    if intent == 'opt_in':
        ConsentGate.grant(
            session=session,
            group_id=group_id,
            user_id=sender_id,
            jurisdiction=jurisdiction,
            ip_address=ip_address,
            user_agent=consent_context.get('user_agent'),
        )
        response = 'Got it. I can now help with travel questions for this group.'
    else:
        ConsentGate.revoke(session, group_id, sender_id)
        response = (
            "Done. I've deleted your saved preferences and everything I had "
            "logged about you in this group, and I won't use your data again "
            "unless you say '@scout opt in'."
        )

    session.commit()

    ChatService.send_message(
        group_id=group_id,
        sender_id=None,
        sender_type='ai',
        content=response,
        msg_type='text',
        metadata_json={'agent': 'scout', 'intent': intent},
    )

    return {'status': 'consent_updated', 'intent': intent}


@celery_app.task(
    bind=True,
    name='app.core.workers.tasks.ai_tasks.generate_chat_summary',
    max_retries=2,
    soft_time_limit=120,
    default_retry_delay=30,
)
def generate_chat_summary(self, group_id: str):
    """
    Generate an AI summary from the last batch of chat messages.

    Triggered every CHAT_SUMMARY_TRIGGER messages in a group.
    Only processes messages from consented members.
    Extracts preferences into ai_preference_profiles.
    """
    from app.core.config import Config
    from app.scout.models import (VALID_PREFERENCE_KEYS, AIConsent,
                                      AIPreferenceProfile)
    from app.trips.models import ChatMessage, ChatSummary
    from app.core.db.connection import get_db
    from app.scout.llm.ollama_client import (OllamaClient,
                                                      OllamaUnavailable)
    from app.scout.llm.prompt_templates import \
        summary_extraction_prompt

    if not Config.FF_SCOUT_AGENT:
        return {'status': 'disabled'}

    ollama = OllamaClient()

    try:
        with get_db() as session:
            # 1. Get consented user IDs.
            # The consent_version predicate matters: ConsentGate.check
            # requires it, so without it here a member whose consent predates
            # a consent-text change was still being summarised after the
            # text they agreed to had changed (audit P1-36).
            consented_ids = [
                str(c.user_id) for c in session.query(AIConsent.user_id).filter_by(
                    group_id=group_id,
                    consent_type='chat_history_read',
                    granted=True,
                ).filter(
                    AIConsent.revoked_at.is_(None),
                    AIConsent.consent_version == Config.SCOUT_CONSENT_VERSION,
                ).all()
            ]

            if not consented_ids:
                return {'status': 'no_consent'}

            # 2. Get last summary marker
            last_summary = session.query(ChatSummary).filter_by(
                group_id=group_id,
            ).order_by(ChatSummary.created_at.desc()).first()

            from_id = last_summary.to_message_id if last_summary else None

            # 3. Fetch messages from consented members only
            query = session.query(ChatMessage).filter(
                ChatMessage.group_id == group_id,
                ChatMessage.sender_id.in_(consented_ids),
                ChatMessage.is_deleted.is_(False),
                ChatMessage.is_archived.is_(False),
                ChatMessage.sender_type == 'user',
            )
            if from_id:
                query = query.filter(ChatMessage.id > from_id)

            messages = query.order_by(ChatMessage.id).limit(
                Config.CHAT_SUMMARY_TRIGGER,
            ).all()

            if len(messages) < 10:
                return {'status': 'insufficient_messages', 'count': len(messages)}

            # 4. Anonymize messages for LLM
            member_aliases = {}
            alias_counter = 0
            anonymized_lines = []
            for msg in messages:
                sid = str(msg.sender_id)
                if sid not in member_aliases:
                    alias_counter += 1
                    member_aliases[sid] = f"Member {chr(64 + alias_counter)}"
                anonymized_lines.append(f"{member_aliases[sid]}: {msg.content}")

            # 5. Send to LLM for extraction
            prompt = summary_extraction_prompt('\n'.join(anonymized_lines))

            try:
                raw_response = ollama.generate(
                    prompt=prompt,
                    model=Config.OLLAMA_MODEL_LIGHT,
                    temperature=0.1,
                    max_tokens=500,
                )
            except OllamaUnavailable as exc:
                logger.warning('Ollama unavailable for summary: %s', exc)
                raise self.retry(exc=exc)

            # 6. Parse JSON response
            try:
                parsed = json.loads(raw_response)
            except json.JSONDecodeError:
                logger.warning('Invalid JSON from LLM summary: %s', raw_response[:200])
                return {'status': 'parse_error'}

            # 7. UPSERT preferences
            alias_to_id = {v: k for k, v in member_aliases.items()}
            for pref in parsed.get('preferences', []):
                user_id = alias_to_id.get(pref.get('alias'))
                key = pref.get('key', '')
                value = pref.get('value', '')

                if not user_id or key not in VALID_PREFERENCE_KEYS or not value:
                    continue

                existing = session.query(AIPreferenceProfile).filter_by(
                    group_id=group_id,
                    user_id=user_id,
                    preference_key=key,
                ).first()

                if existing:
                    existing.preference_value = str(value)[:200]
                    existing.source = 'chat_summary'
                    existing.confidence = min(existing.confidence + 0.1, 1.0)
                else:
                    session.add(AIPreferenceProfile(
                        group_id=group_id,
                        user_id=user_id,
                        preference_key=key,
                        preference_value=str(value)[:200],
                        confidence=0.5,
                        source='chat_summary',
                    ))

            # 8. Store summary
            summary = ChatSummary(
                group_id=group_id,
                from_message_id=messages[0].id,
                to_message_id=messages[-1].id,
                summary_text=str(parsed.get('summary', ''))[:2000],
                topic_tags=parsed.get('topics', []),
                extra_metadata={
                    'member_count': len(member_aliases),
                    'message_count': len(messages),
                },
            )
            session.add(summary)
            session.commit()

            logger.info(
                'Chat summary generated: group=%s messages=%d prefs=%d',
                group_id, len(messages), len(parsed.get('preferences', [])),
            )
            return {
                'status': 'success',
                'messages_processed': len(messages),
                'preferences_extracted': len(parsed.get('preferences', [])),
            }

    except OllamaUnavailable:
        raise
    except Exception as exc:
        logger.error('generate_chat_summary failed: group=%s error=%s', group_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(name='app.core.workers.tasks.ai_tasks.cleanup_agent_logs')
def cleanup_agent_logs():
    """
    Purge ai_agent_logs older than AGENT_LOG_RETENTION_DAYS.
    Scheduled via Celery Beat daily.
    """
    from app.core.config import Config
    from app.scout.models import AIAgentLog
    from app.core.db.connection import get_db

    retention_days = Config.AGENT_LOG_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    try:
        with get_db() as session:
            count = session.query(AIAgentLog).filter(
                AIAgentLog.created_at < cutoff,
            ).delete(synchronize_session='fetch')
            session.commit()
            logger.info('Cleaned up %d agent logs older than %d days', count, retention_days)
            return {'deleted': count}
    except Exception as exc:
        logger.error('cleanup_agent_logs failed: %s', exc)
        raise
