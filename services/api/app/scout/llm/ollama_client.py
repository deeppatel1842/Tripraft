# Purpose: Ollama HTTP Client — with circuit breaker, timeouts, and graceful fallback. Talks to the Ollama REST API running on an internal Docker network.
"""
Ollama HTTP Client — with circuit breaker, timeouts, and graceful fallback.

Talks to the Ollama REST API running on an internal Docker network.
No authentication (Ollama has none) — relies on network isolation.
"""
import hashlib
import json
import logging
from typing import Optional

import pybreaker
import requests
from app.core.config import Config

logger = logging.getLogger(__name__)


class OllamaUnavailable(Exception):
    """Raised when Ollama is unreachable or circuit breaker is open."""


# ---------------------------------------------------------------------------
# Circuit breaker (pybreaker — same pattern as core/resilience.py)
# ---------------------------------------------------------------------------
class _OllamaBreakListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning("Ollama circuit breaker: %s -> %s", old_state.name, new_state.name)

    def failure(self, cb, exc):
        logger.debug("Ollama circuit breaker recorded failure: %s", exc)


ollama_breaker = pybreaker.CircuitBreaker(
    fail_max=Config.SCOUT_CB_FAIL_MAX,
    reset_timeout=Config.SCOUT_CB_RECOVERY_TIMEOUT,
    name='ollama',
    listeners=[_OllamaBreakListener()],
)


class OllamaClient:
    """
    Stateless HTTP client for Ollama /api/generate.

    All config pulled from Config class — nothing hardcoded.
    Thread-safe: no mutable instance state.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self._base_url = (base_url or Config.OLLAMA_BASE_URL).rstrip('/')
        self._timeout = timeout or Config.OLLAMA_REQUEST_TIMEOUT

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a prompt to Ollama and return the generated text.

        Raises OllamaUnavailable on timeout, connection error, or HTTP error.
        Circuit breaker opens after SCOUT_CB_FAIL_MAX consecutive failures.
        """
        try:
            return self._generate_with_breaker(prompt, model, temperature, max_tokens)
        except pybreaker.CircuitBreakerError:
            raise OllamaUnavailable('Ollama circuit breaker is open. Try again later.')

    @ollama_breaker
    def _generate_with_breaker(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Inner method wrapped by circuit breaker."""
        model = model or Config.OLLAMA_MODEL_LIGHT
        temperature = temperature if temperature is not None else Config.OLLAMA_TEMPERATURE
        max_tokens = max_tokens or Config.OLLAMA_MAX_TOKENS

        payload = {
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            },
        }

        try:
            resp = requests.post(
                f'{self._base_url}/api/generate',
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json().get('response', '')

        except (requests.Timeout, requests.ConnectionError) as exc:
            raise OllamaUnavailable(f'Ollama connection failed: {exc}') from exc
        except requests.HTTPError as exc:
            raise OllamaUnavailable(f'Ollama HTTP error: {exc}') from exc

    def select_model(self, intent: str) -> str:
        """Route to light or heavy model based on intent complexity."""
        light_intents = frozenset({
            'chat_summary', 'preference_extract', 'simple_qa', 'format_response',
            'place_search', 'weather', 'visa', 'flight_range', 'hotel_range',
            'transport', 'budget_advice', 'preference_summary', 'off_topic',
            'redirect_crew',
        })
        if intent in light_intents:
            return Config.OLLAMA_MODEL_LIGHT
        return Config.OLLAMA_MODEL_HEAVY

    def health_check(self) -> bool:
        """Quick ping to verify Ollama is reachable."""
        try:
            resp = requests.get(
                f'{self._base_url}/api/tags',
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def cache_key(
        group_id: str,
        query: str,
        sender_id: str = '',
        consented_user_ids: Optional[list[str]] = None,
    ) -> str:
        """Generate a cache key bound to the consent context.

        Responses that use preference summaries are not interchangeable
        between senders or between different sets of consented members.
        Include both, plus the consent-text version, so revocation and a
        policy-version change cannot replay a response made under old data.
        """
        normalized = query.strip().lower()
        query_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        consent_scope = ','.join(sorted(str(uid) for uid in (consented_user_ids or [])))
        context = '\x00'.join((str(sender_id), consent_scope, Config.SCOUT_CONSENT_VERSION))
        context_hash = hashlib.sha256(context.encode()).hexdigest()[:16]
        return f'ai_cache:{group_id}:{query_hash}:{context_hash}'
