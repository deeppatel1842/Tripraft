"""
Input sanitization for user-provided text content.
Strips HTML/script tags to prevent stored XSS.
"""

import bleach

# Allowed tags for rich-text itinerary content
_ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'br', 'p', 'ul', 'ol', 'li', 'h1', 'h2', 'h3']
_ALLOWED_ATTRS = {}


def sanitize_text(text: str) -> str:
    """Strip all HTML tags from plain text fields (names, options, checklist items)."""
    if not text:
        return text
    return bleach.clean(text, tags=[], attributes={}, strip=True).strip()


def sanitize_rich_text(text: str) -> str:
    """Allow safe formatting tags for itinerary/document content."""
    if not text:
        return text
    return bleach.clean(text, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)
