"""
Audit Logging System
Tracks all sensitive operations for compliance and security
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any
from flask import request, g
import json

logger = logging.getLogger(__name__)


class AuditAction:
    """Standard audit action types"""
    
    # Group actions
    CREATE_GROUP = "create_group"
    UPDATE_GROUP = "update_group"
    DELETE_GROUP = "delete_group"
    INVITE_USER = "invite_user"
    REMOVE_MEMBER = "remove_member"
    
    # Expense actions
    CREATE_EXPENSE = "create_expense"
    UPDATE_EXPENSE = "update_expense"
    DELETE_EXPENSE = "delete_expense"
    
    # Settlement actions
    CREATE_SETTLEMENT = "create_settlement"
    APPROVE_SETTLEMENT = "approve_settlement"
    REJECT_SETTLEMENT = "reject_settlement"
    
    # Admin actions
    VIEW_ANALYTICS = "view_analytics"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MODIFY_USER = "modify_user"
    
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"


class AuditLogger:
    """
    Audit logging system for tracking sensitive operations
    
    Features:
    - Logs all CREATE, UPDATE, DELETE operations
    - Captures user context (IP, user agent, timestamp)
    - Stores in Firestore for compliance
    - Supports querying and filtering
    """
    
    def __init__(self, firestore_db=None):
        """
        Initialize audit logger
        
        Args:
            firestore_db: Firestore database instance
        """
        self.db = firestore_db
        self.collection_name = "audit_logs"
        
        if not self.db:
            logger.warning("⚠️ Audit logger initialized without Firestore - logs will be written to file only")
    
    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ):
        """
        Log an audit event
        
        Args:
            action: Action performed (use AuditAction constants)
            resource_type: Type of resource (group, expense, settlement, etc.)
            resource_id: ID of the resource
            user_id: User who performed the action
            details: Additional details about the action
            status: Action status (success, failed, denied)
        """
        try:
            # Build audit entry
            audit_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'user_id': user_id or (g.user_id if hasattr(g, 'user_id') else 'anonymous'),
                'status': status,
                'details': details or {},
                
                # Request context
                'ip_address': request.remote_addr if request else None,
                'user_agent': request.user_agent.string if request and request.user_agent else None,
                'method': request.method if request else None,
                'endpoint': request.endpoint if request else None,
            }
            
            # Log to application logs
            logger.info(f"🔒 AUDIT: {action} on {resource_type}/{resource_id} by {audit_entry['user_id']} - {status}")
            
            # Store in Firestore if available
            if self.db:
                try:
                    self.db.collection(self.collection_name).add(audit_entry)
                except Exception as e:
                    logger.error(f"❌ Failed to write audit log to Firestore: {e}")
            
            # Fallback: Write to file
            self._write_to_file(audit_entry)
            
        except Exception as e:
            logger.error(f"❌ Error creating audit log: {e}")
    
    def _write_to_file(self, audit_entry: Dict):
        """
        Write audit entry to local file (fallback/backup)
        
        Args:
            audit_entry: Audit log entry
        """
        try:
            with open('audit_logs.jsonl', 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
        except Exception as e:
            logger.error(f"❌ Failed to write audit log to file: {e}")
    
    def get_user_actions(
        self,
        user_id: str,
        limit: int = 100,
        action_filter: Optional[str] = None
    ) -> list:
        """
        Get audit logs for a specific user
        
        Args:
            user_id: User ID
            limit: Maximum number of logs to return
            action_filter: Optional action type filter
            
        Returns:
            List of audit log entries
        """
        if not self.db:
            return []
        
        try:
            query = self.db.collection(self.collection_name).where('user_id', '==', user_id)
            
            if action_filter:
                query = query.where('action', '==', action_filter)
            
            query = query.order_by('timestamp', direction='DESCENDING').limit(limit)
            
            docs = query.stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
            
        except Exception as e:
            logger.error(f"❌ Error querying audit logs: {e}")
            return []
    
    def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50
    ) -> list:
        """
        Get audit history for a specific resource
        
        Args:
            resource_type: Type of resource
            resource_id: Resource ID
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log entries
        """
        if not self.db:
            return []
        
        try:
            query = self.db.collection(self.collection_name) \
                .where('resource_type', '==', resource_type) \
                .where('resource_id', '==', resource_id) \
                .order_by('timestamp', direction='DESCENDING') \
                .limit(limit)
            
            docs = query.stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
            
        except Exception as e:
            logger.error(f"❌ Error querying resource history: {e}")
            return []
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """
        Get recent audit logs (admin only)
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of recent audit log entries
        """
        if not self.db:
            return []
        
        try:
            query = self.db.collection(self.collection_name) \
                .order_by('timestamp', direction='DESCENDING') \
                .limit(limit)
            
            docs = query.stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
            
        except Exception as e:
            logger.error(f"❌ Error querying recent logs: {e}")
            return []


# Singleton instance
_audit_logger = None


def get_audit_logger(firestore_db=None):
    """
    Get or create audit logger instance
    
    Args:
        firestore_db: Firestore database instance
        
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    
    if _audit_logger is None:
        _audit_logger = AuditLogger(firestore_db)
    
    return _audit_logger
