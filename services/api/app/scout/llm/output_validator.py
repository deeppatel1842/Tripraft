# Purpose: LLM Output Validator — Sanitizes and validates all LLM-generated text before it is stored or shown to users.
"""
LLM Output Validator — Sanitizes and validates all LLM-generated text
before it is stored or shown to users.

Defense layers:
  1. Rejection patterns — detect prompt injection leakage
  2. Length enforcement — truncate to configured max
  3. HTML/XSS sanitization — strip all tags via bleach
  4. PII detection — reject outputs containing sensitive patterns
"""
import re
from typing import Tuple

import bleach
from app.core.config import Config

# Patterns that indicate prompt injection succeeded or PII leaked.
# Each is compiled once at module load for performance.
_REJECTION_PATTERNS = [
    re.compile(r'system\s*prompt', re.IGNORECASE),
    re.compile(r'my\s*instructions\s*are', re.IGNORECASE),
    re.compile(r'ignore\s*previous', re.IGNORECASE),
    re.compile(r'as\s+an?\s+ai\s+language', re.IGNORECASE),
    re.compile(r'<script', re.IGNORECASE),  # duplicate guard for XSS
    re.compile(r'<script', re.IGNORECASE),
    re.compile(r'password|credit.?card|ssn', re.IGNORECASE),
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # email
    re.compile(r'\b\d{10,}\b'),  # phone-like sequences
]

_FALLBACK_MESSAGE = "I couldn't generate a good response. Try rephrasing your question."


def validate_llm_output(output: str) -> Tuple[bool, str]:
    """
    Validate and sanitize LLM output.

    Returns:
        (is_valid, cleaned_output_or_fallback_message)
    """
    if not output or not output.strip():
        return False, _FALLBACK_MESSAGE

    # Check for injection / PII indicators
    for pattern in _REJECTION_PATTERNS:
        if pattern.search(output):
            return False, _FALLBACK_MESSAGE

    # Truncate only if truly over the limit (1500 chars default).
    # Prefer sentence boundaries so responses end cleanly, not mid-thought.
    max_chars = Config.SCOUT_MAX_RESPONSE_CHARS
    if len(output) > max_chars:
        candidate = output[:max_chars]
        # Try to end at the last complete sentence within the allowed chars
        last_sentence = max(
            candidate.rfind('. '),
            candidate.rfind('! '),
            candidate.rfind('? '),
        )
        if last_sentence > max_chars // 2:
            # Clean sentence boundary found in the second half — use it
            output = output[:last_sentence + 1]
        else:
            # No good sentence boundary — truncate at last word and append ellipsis
            truncated = candidate.rsplit(' ', 1)[0]
            output = (truncated + '...') if truncated else (candidate + '...')

    # Strip all HTML/JS
    output = bleach.clean(output, tags=[], strip=True)

    return True, output.strip()
