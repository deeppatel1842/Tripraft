"""
Invitation Token Utility
Phase 20.1: JWT-based invitation tokens to eliminate lookup reads

Instead of reading invitation document on accept, encode all needed data
in a signed JWT token. This eliminates 4 Firestore reads per invitation accept.

Security:
- HMAC-SHA256 signed tokens
- 7-day expiry (matches business rule)
- Contains: group_id, group_name, inviter details, invitee email
"""

import os
import hmac
import hashlib
import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Secret key for signing tokens (should be in environment)
# Falls back to a default for development only
INVITATION_SECRET = os.getenv('INVITATION_TOKEN_SECRET', os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'))


class InvitationTokenError(Exception):
    """Base exception for invitation token errors"""
    pass


class TokenExpiredError(InvitationTokenError):
    """Token has expired"""
    pass


class TokenInvalidError(InvitationTokenError):
    """Token signature is invalid or corrupted"""
    pass


def _encode_base64url(data: bytes) -> str:
    """URL-safe base64 encoding without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _decode_base64url(data: str) -> bytes:
    """URL-safe base64 decoding with padding restoration"""
    # Add back padding
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data.encode('utf-8'))


def _sign_payload(payload: str) -> str:
    """Create HMAC-SHA256 signature for payload"""
    signature = hmac.new(
        INVITATION_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return _encode_base64url(signature)


def _verify_signature(payload: str, signature: str) -> bool:
    """Verify HMAC-SHA256 signature"""
    expected_sig = _sign_payload(payload)
    return hmac.compare_digest(expected_sig, signature)


def create_invitation_token(
    invitation_id: str,
    group_id: str,
    group_name: str,
    inviter_id: str,
    inviter_name: str,
    invitee_email: str,
    role: str = 'member',
    expiry_days: int = 7
) -> str:
    """
    Create a signed invitation token containing all needed data.
    
    This allows accepting an invitation WITHOUT reading the invitation document,
    eliminating 1-4 Firestore reads per acceptance.
    
    Args:
        invitation_id: The Firestore invitation document ID (for status update)
        group_id: Target group ID
        group_name: Group name for display
        inviter_id: User ID who sent invitation
        inviter_name: Display name of inviter
        invitee_email: Email of person being invited
        role: Role to assign (admin/member)
        expiry_days: Token validity period
        
    Returns:
        Signed JWT-like token string (base64url encoded)
    """
    # Calculate expiry timestamp
    expires_at = datetime.utcnow() + timedelta(days=expiry_days)
    
    # Build payload with all needed data
    payload = {
        'inv': invitation_id,      # Invitation ID for status update
        'gid': group_id,           # Group ID
        'gnm': group_name,         # Group name
        'iid': inviter_id,         # Inviter user ID
        'inm': inviter_name,       # Inviter name
        'eml': invitee_email,      # Invitee email
        'rol': role,               # Role to assign
        'exp': int(expires_at.timestamp()),  # Expiry timestamp
        'iat': int(datetime.utcnow().timestamp())  # Issued at
    }
    
    # Encode payload
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = _encode_base64url(payload_json.encode('utf-8'))
    
    # Sign it
    signature = _sign_payload(payload_b64)
    
    # Return token: payload.signature
    token = f"{payload_b64}.{signature}"
    
    logger.debug(
        "[TOKEN] Created invitation token for %s to group %s (expires: %s)",
        invitee_email, group_id, expires_at.isoformat()
    )
    
    return token


def decode_invitation_token(token: str) -> Dict:
    """
    Decode and verify an invitation token.
    
    Args:
        token: The signed token string
        
    Returns:
        Dict with invitation data:
        - invitation_id: Firestore document ID
        - group_id: Target group
        - group_name: Group name
        - inviter_id: Who sent it
        - inviter_name: Inviter display name
        - invitee_email: Who it's for
        - role: Role to assign
        - expires_at: Expiry datetime
        - issued_at: Creation datetime
        
    Raises:
        TokenExpiredError: If token has expired
        TokenInvalidError: If signature is invalid or token is malformed
    """
    try:
        # Split token
        parts = token.split('.')
        if len(parts) != 2:
            raise TokenInvalidError("Invalid token format")
        
        payload_b64, signature = parts
        
        # Verify signature FIRST (before decoding payload)
        if not _verify_signature(payload_b64, signature):
            logger.warning("[TOKEN] Invalid signature for token")
            raise TokenInvalidError("Invalid token signature")
        
        # Decode payload
        payload_json = _decode_base64url(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        
        # Check expiry
        exp_timestamp = payload.get('exp', 0)
        if datetime.utcnow().timestamp() > exp_timestamp:
            logger.info("[TOKEN] Token expired at %s", datetime.fromtimestamp(exp_timestamp).isoformat())
            raise TokenExpiredError("Invitation token has expired")
        
        # Return decoded data with full field names
        return {
            'invitation_id': payload.get('inv'),
            'group_id': payload.get('gid'),
            'group_name': payload.get('gnm'),
            'inviter_id': payload.get('iid'),
            'inviter_name': payload.get('inm'),
            'invitee_email': payload.get('eml'),
            'role': payload.get('rol', 'member'),
            'expires_at': datetime.fromtimestamp(exp_timestamp),
            'issued_at': datetime.fromtimestamp(payload.get('iat', 0))
        }
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("[TOKEN] Failed to decode token: %s", str(e))
        raise TokenInvalidError(f"Malformed token: {str(e)}")


def is_token_valid(token: str) -> bool:
    """
    Quick check if token is valid without raising exceptions.
    
    Args:
        token: The token to validate
        
    Returns:
        True if valid and not expired, False otherwise
    """
    try:
        decode_invitation_token(token)
        return True
    except InvitationTokenError:
        return False


# Export for easy access
__all__ = [
    'create_invitation_token',
    'decode_invitation_token',
    'is_token_valid',
    'InvitationTokenError',
    'TokenExpiredError',
    'TokenInvalidError'
]
