"""
Circuit breakers for external service calls.
Wraps Ticketmaster, Nominatim, and SMTP with pybreaker to prevent
cascading failures when external services are down.
"""

import logging

import pybreaker

from app.core.config import get_config

logger = logging.getLogger(__name__)

_config = get_config()

# Circuit breaker settings from config (with sane defaults)
_FAIL_MAX = getattr(_config, 'CIRCUIT_BREAKER_FAIL_MAX', 5)
_RESET_TIMEOUT = getattr(_config, 'CIRCUIT_BREAKER_RESET_TIMEOUT', 30)


class _LogListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning("Circuit breaker '%s': %s -> %s", cb.name, old_state.name, new_state.name)

    def failure(self, cb, exc):
        logger.debug("Circuit breaker '%s' recorded failure: %s", cb.name, exc)


_listener = _LogListener()

ticketmaster_breaker = pybreaker.CircuitBreaker(
    fail_max=_FAIL_MAX,
    reset_timeout=_RESET_TIMEOUT,
    name="ticketmaster",
    listeners=[_listener],
)

nominatim_breaker = pybreaker.CircuitBreaker(
    fail_max=_FAIL_MAX,
    reset_timeout=_RESET_TIMEOUT,
    name="nominatim",
    listeners=[_listener],
)

smtp_breaker = pybreaker.CircuitBreaker(
    fail_max=_FAIL_MAX,
    reset_timeout=_RESET_TIMEOUT,
    name="smtp",
    listeners=[_listener],
)
