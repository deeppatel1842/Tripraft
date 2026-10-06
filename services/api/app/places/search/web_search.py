# Purpose: Web Search Client — DuckDuckGo (DDGS) with SearXNG fallback. Provides a unified web search interface for Scout agent queries when.
"""
Web Search Client — DuckDuckGo (DDGS) with SearXNG fallback.

Provides a unified web search interface for Scout agent queries when
the TripRaft DB does not have enough results.

Primary:  duckduckgo-search (DDGS) — actual web search, no API key, free.
Fallback: SearXNG self-hosted — used in production Docker environments.

The previous DDG Instant Answer API returned HTTP 202 with empty body for
most travel queries (it only covers Wikipedia-style knowledge panels).
DDGS performs a real web search and returns full result pages.
"""
import logging
from typing import Dict, List, Optional

import pybreaker
import requests
from app.core.config import Config
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException

logger = logging.getLogger(__name__)


class WebSearchUnavailable(Exception):
    """Raised when all search backends are down or circuit-broken."""


class _LogListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning("Search CB '%s': %s -> %s", cb.name, old_state.name, new_state.name)

    def failure(self, cb, exc):
        logger.debug("Search CB '%s' failure: %s", cb.name, exc)


_listener = _LogListener()

searxng_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=120,
    name='searxng',
    listeners=[_listener],
)

ddg_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=300,
    name='duckduckgo',
    listeners=[_listener],
)


class WebSearchClient:
    """
    Unified web search with cascade:
      1. DuckDuckGo DDGS (real web search, free, no auth required)
      2. SearXNG (self-hosted, Docker environments only)
    """

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search the web for travel-related results.

        Returns a list of dicts: [{'title': str, 'url': str, 'snippet': str}, ...]
        Raises WebSearchUnavailable if both backends fail.
        """
        results = self._try_duckduckgo(query, max_results)
        if results:
            return results

        results = self._try_searxng(query, max_results)
        if results:
            return results

        raise WebSearchUnavailable('All search backends unavailable')

    @ddg_breaker
    def _try_duckduckgo(self, query: str, max_results: int) -> Optional[List[Dict]]:
        """
        Real web search via duckduckgo-search library.

        Unlike the DDG Instant Answer API (which returns 202 empty for most queries),
        DDGS performs an actual search and returns result pages for any query.
        """
        try:
            raw = DDGS().text(query, max_results=max_results)
            if not raw:
                logger.debug('DDGS returned no results for: %s', query)
                return None

            results = []
            for item in raw:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('href', ''),
                    'snippet': item.get('body', '')[:400],
                    'source': 'duckduckgo',
                })
            logger.debug('DDGS returned %d results for: %s', len(results), query)
            return results if results else None

        except RatelimitException:
            logger.warning('DuckDuckGo rate-limited — backing off')
            raise
        except DDGSException as exc:
            logger.warning('DuckDuckGo search error: %s', exc)
            raise
        except pybreaker.CircuitBreakerError:
            raise
        except Exception as exc:
            logger.warning('DuckDuckGo search failed: %s', exc)
            raise

    @searxng_breaker
    def _try_searxng(self, query: str, max_results: int) -> Optional[List[Dict]]:
        """
        Query self-hosted SearXNG instance (production Docker only).
        Timeout is kept short (1s) so local dev fails fast without blocking Scout.
        """
        base_url = Config.SEARXNG_BASE_URL
        # Use a short timeout: if SearXNG hostname is not reachable (local dev),
        # we want to fail fast rather than block Scout's response for 3+ seconds.
        timeout = min(Config.SEARXNG_TIMEOUT, 1)

        try:
            resp = requests.get(
                f'{base_url}/search',
                params={
                    'q': query,
                    'format': 'json',
                    'categories': 'general',
                    'language': 'en',
                    'safesearch': 1,
                    'pageno': 1,
                },
                timeout=timeout,
                headers={'Accept': 'application/json'},
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get('results', [])[:max_results]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('content', '')[:400],
                    'source': 'searxng',
                })
            return results if results else None

        except pybreaker.CircuitBreakerError:
            raise
        except Exception as exc:
            logger.warning('SearXNG search failed: %s', exc)
            raise
