"""
Audit Logging Middleware
Compliance-grade mutation logging for all data changes

Features:
- Logs all create, update, delete operations
- Captures before/after state for updates
- Includes user context, timestamp, IP address
- Stores in Firestore audit_logs collection
- Non-blocking (async) to avoid impacting request latency
"""

from functools import wraps
from flask import request, g
from datetime import datetime
from typing import Optional, Dict, Any, Callable
import logging
import threading
import json

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Audit logger for compliance-grade mutation tracking
    """
    
    COLLECTION_NAME = 'audit_logs'
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Lazy initialization of Firestore client"""
        if self._db is None:
            from firebase_admin import firestore
            self._db = firestore.client()
        return self._db
    
    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        user_email: Optional[str] = None,
        group_id: Optional[str] = None,
        before_data: Optional[Dict[str, Any]] = None,
        after_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log an audit event (non-blocking)
        
        Args:
            action: Action type (create, update, delete, read)
            resource_type: Type of resource (expense, group, settlement, etc.)
            resource_id: ID of the resource
            user_id: User who performed the action
            user_email: User's email (optional)
            group_id: Associated group ID (optional)
            before_data: State before change (for updates/deletes)
            after_data: State after change (for creates/updates)
            metadata: Additional context
            ip_address: Client IP address
            user_agent: Client user agent
        """
        # Run in background thread to avoid blocking
        thread = threading.Thread(
            target=self._write_audit_log,
            args=(
                action, resource_type, resource_id, user_id, user_email,
                group_id, before_data, after_data, metadata, ip_address, user_agent
            ),
            daemon=True
        )
        thread.start()
    
    def _write_audit_log(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        user_email: Optional[str],
        group_id: Optional[str],
        before_data: Optional[Dict[str, Any]],
        after_data: Optional[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> None:
        """
        Write audit log to Firestore (runs in background thread)
        """
        try:
            timestamp = datetime.utcnow()
            
            # Sanitize data - remove sensitive fields and convert to JSON-serializable
            safe_before = self._sanitize_data(before_data) if before_data else None
            safe_after = self._sanitize_data(after_data) if after_data else None
            
            audit_entry = {
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'user_id': user_id,
                'user_email': user_email,
                'group_id': group_id,
                'before_data': safe_before,
                'after_data': safe_after,
                'metadata': metadata or {},
                'ip_address': ip_address,
                'user_agent': user_agent,
                'timestamp': timestamp.isoformat(),
                'created_at': timestamp
            }
            
            # Write to Firestore
            self.db.collection(self.COLLECTION_NAME).add(audit_entry)
            
            logger.debug(
                "Audit log: %s %s/%s by %s",
                action, resource_type, resource_id, user_id
            )
            
        except Exception as exc:
            # Don't fail the request if audit logging fails
            logger.error("Failed to write audit log: %s", str(exc))
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize data for storage - remove sensitive fields, convert types
        
        Args:
            data: Raw data dict
            
        Returns:
            Sanitized data dict
        """
        if not data:
            return {}
        
        # Fields to exclude from audit logs
        sensitive_fields = {
            'password', 'token', 'secret', 'api_key', 'auth_token',
            'access_token', 'refresh_token', 'private_key'
        }
        
        sanitized = {}
        for key, value in data.items():
            # Skip sensitive fields
            if key.lower() in sensitive_fields:
                sanitized[key] = '[REDACTED]'
                continue
            
            # Convert datetime objects to ISO strings
            if isinstance(value, datetime):
                sanitized[key] = value.isoformat()
            # Convert Decimal to float
            elif hasattr(value, '__float__'):
                sanitized[key] = float(value)
            # Handle nested dicts
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            # Handle lists
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def log_sync(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        **kwargs
    ) -> None:
        """
        Synchronous audit log (for critical operations)
        """
        self._write_audit_log(
            action, resource_type, resource_id, user_id,
            kwargs.get('user_email'),
            kwargs.get('group_id'),
            kwargs.get('before_data'),
            kwargs.get('after_data'),
            kwargs.get('metadata'),
            kwargs.get('ip_address'),
            kwargs.get('user_agent')
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def audit_action(
    action: str,
    resource_type: str,
    resource_id_param: str = 'id',
    group_id_param: Optional[str] = 'group_id',
    capture_before: bool = False,
    capture_after: bool = False
):
    """
    Decorator to automatically log audit events for route functions
    
    Args:
        action: Action type (create, update, delete)
        resource_type: Type of resource
        resource_id_param: Parameter name for resource ID
        group_id_param: Parameter name for group ID
        capture_before: Whether to capture before state (for updates/deletes)
        capture_after: Whether to capture after state (for creates/updates)
    
    Usage:
        @require_auth
        @audit_action('delete', 'expense', 'expense_id', capture_before=True)
        def delete_expense(expense_id):
            # Delete expense
            pass
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from .auth import get_current_user
            
            audit_logger = get_audit_logger()
            current_user = get_current_user()
            
            # Get resource ID
            resource_id = (
                kwargs.get(resource_id_param) or
                (request.view_args.get(resource_id_param) if request.view_args else None) or
                'unknown'
            )
            
            # Get group ID
            group_id = None
            if group_id_param:
                group_id = (
                    kwargs.get(group_id_param) or
                    (request.view_args.get(group_id_param) if request.view_args else None) or
                    (request.json.get(group_id_param) if request.is_json and request.json else None)
                )
            
            # Get client info
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')[:500]  # Truncate
            
            # Capture before state if requested
            before_data = None
            if capture_before:
                before_data = getattr(g, 'audit_before_data', None)
            
            # Execute the function
            result = f(*args, **kwargs)
            
            # Capture after state if requested
            after_data = None
            if capture_after:
                after_data = getattr(g, 'audit_after_data', None)
            
            # Get request body for creates
            if action == 'create' and request.is_json and not after_data:
                after_data = request.json
            
            # Log the audit event
            audit_logger.log_action(
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                user_id=current_user['uid'],
                user_email=current_user.get('email'),
                group_id=group_id,
                before_data=before_data,
                after_data=after_data,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return result
        
        return decorated_function
    return decorator


def set_audit_before_data(data: Dict[str, Any]) -> None:
    """
    Set the 'before' state for audit logging
    Call this before making changes to capture previous state
    
    Args:
        data: Current state of the resource
    """
    g.audit_before_data = data


def set_audit_after_data(data: Dict[str, Any]) -> None:
    """
    Set the 'after' state for audit logging
    Call this after making changes to capture new state
    
    Args:
        data: New state of the resource
    """
    g.audit_after_data = data
