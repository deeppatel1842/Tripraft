"""
Idempotency Manager - Prevents Duplicate Operations
Ensures that repeated API calls with the same idempotency key don't create duplicate resources
"""

import logging
import json
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class IdempotencyManager:
    """
    Manages idempotency keys to prevent duplicate operations
    
    Use Cases:
    - Prevent duplicate expense creation (network retry)
    - Prevent duplicate group creation (double-click)
    - Prevent duplicate payment processing
    
    TTL: 24 hours (operations older than 24h can be retried)
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.prefix = "idempotency:"
        self.ttl = 86400  # 24 hours
    
    def generate_key(self, operation: str, user_id: str, data: Dict) -> str:
        """
        Generate idempotency key from operation parameters
        
        Args:
            operation: Operation type (create_expense, create_group, etc.)
            user_id: User performing the operation
            data: Operation data (for hashing)
        
        Returns:
            Idempotency key string
        """
        import hashlib
        
        # Create deterministic hash from operation data
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        
        return f"{operation}:{user_id}:{data_hash}"
    
    def check_and_store(self, idempotency_key: str, result: Dict) -> Optional[Dict]:
        """
        Check if operation was already performed, store if new
        
        Args:
            idempotency_key: Unique key for this operation
            result: Operation result to store
        
        Returns:
            Existing result if operation already performed, None if new operation
        """
        if not self.redis_client:
            return None  # Redis unavailable, allow operation
            
        try:
            key = f"{self.prefix}{idempotency_key}"
            
            # Check if key exists
            existing = self.redis_client.get(key)
            if existing:
                logger.info(f"🔁 Idempotent request detected: {idempotency_key}")
                return json.loads(existing)
            
            # Store new result
            result_with_meta = {
                'result': result,
                'timestamp': datetime.utcnow().isoformat(),
                'idempotency_key': idempotency_key
            }
            
            self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(result_with_meta, default=str)
            )
            
            logger.info(f"✅ Stored idempotency key: {idempotency_key}")
            return None
            
        except Exception as e:
            logger.error(f"Idempotency check failed: {e}")
            # Fail open: allow operation if cache check fails
            return None
    
    def get_result(self, idempotency_key: str) -> Optional[Dict]:
        """Get stored result for idempotency key"""
        if not self.redis_client:
            return None  # Redis unavailable
            
        try:
            key = f"{self.prefix}{idempotency_key}"
            existing = self.redis_client.get(key)
            if existing:
                data = json.loads(existing)
                return data.get('result')
            return None
        except Exception as e:
            logger.error(f"Error getting idempotent result: {e}")
            return None
    
    def invalidate(self, idempotency_key: str):
        """Remove idempotency key (for testing/rollback)"""
        if not self.redis_client:
            return  # Redis unavailable
            
        try:
            key = f"{self.prefix}{idempotency_key}"
            self.redis_client.delete(key)
            logger.info(f"🗑️ Invalidated idempotency key: {idempotency_key}")
        except Exception as e:
            logger.error(f"Error invalidating idempotency key: {e}")
    
    def cleanup_expired(self):
        """Clean up expired idempotency keys (runs periodically)"""
        if not self.redis_client:
            return  # Redis unavailable
            
        try:
            pattern = f"{self.prefix}*"
            keys = self.redis_client.keys(pattern)
            
            cleaned = 0
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -1:  # No expiry set
                    self.redis_client.expire(key, self.ttl)
                elif ttl == -2:  # Key doesn't exist
                    cleaned += 1
            
            if cleaned > 0:
                logger.info(f"🧹 Cleaned up {cleaned} expired idempotency keys")
        except Exception as e:
            logger.error(f"Error cleaning up idempotency keys: {e}")


class IdempotencyDecorator:
    """
    Decorator for idempotent operations
    
    Usage:
        @idempotent_operation(operation_type='create_expense')
        def create_expense(self, user_id, data):
            # Your code here
            pass
    """
    
    def __init__(self, idempotency_manager: IdempotencyManager, operation_type: str):
        self.manager = idempotency_manager
        self.operation_type = operation_type
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # Extract user_id and data from function arguments
            # This is a simplified version - adjust based on your function signatures
            user_id = kwargs.get('user_id') or (args[1] if len(args) > 1 else None)
            data = kwargs.get('data') or (args[2] if len(args) > 2 else {})
            
            if not user_id:
                # No user_id, can't create idempotency key
                return func(*args, **kwargs)
            
            # Generate idempotency key
            idem_key = self.manager.generate_key(self.operation_type, user_id, data)
            
            # Check if already performed
            existing_result = self.manager.get_result(idem_key)
            if existing_result:
                logger.info(f"🔁 Returning cached idempotent result for {self.operation_type}")
                return existing_result
            
            # Perform operation
            result = func(*args, **kwargs)
            
            # Store result
            self.manager.check_and_store(idem_key, result)
            
            return result
        
        return wrapper


def idempotent_operation(operation_type: str):
    """
    Decorator factory for idempotent operations
    
    Usage:
        @idempotent_operation('create_expense')
        def create_expense(self, user_id, data):
            pass
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Check if idempotency manager exists
            if not hasattr(self, 'idempotency_manager'):
                # No idempotency manager, just call function
                return func(self, *args, **kwargs)
            
            # Extract parameters based on operation type
            if operation_type == 'create_expense':
                user_id = kwargs.get('paid_by') or args[0] if args else None
                data = {
                    'description': kwargs.get('description', ''),
                    'amount': kwargs.get('amount', 0),
                    'category': kwargs.get('category', ''),
                    'group_id': kwargs.get('group_id', '')
                }
            elif operation_type == 'create_group':
                user_id = kwargs.get('created_by') or args[0] if args else None
                data = {
                    'name': kwargs.get('name', ''),
                    'description': kwargs.get('description', ''),
                    'currency': kwargs.get('currency', 'USD')
                }
            else:
                # Unknown operation type, skip idempotency
                return func(self, *args, **kwargs)
            
            if not user_id:
                return func(self, *args, **kwargs)
            
            # Generate idempotency key
            idem_key = self.idempotency_manager.generate_key(operation_type, user_id, data)
            
            # Check if already performed
            existing_result = self.idempotency_manager.get_result(idem_key)
            if existing_result:
                logger.info(f"🔁 Idempotent request: returning cached result for {operation_type}")
                return existing_result
            
            # Perform operation
            result = func(self, *args, **kwargs)
            
            # Store result (if successful)
            if result:
                self.idempotency_manager.check_and_store(idem_key, result)
            
            return result
        
        return wrapper
    return decorator
