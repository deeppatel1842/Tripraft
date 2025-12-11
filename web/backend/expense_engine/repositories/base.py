"""
Base Repository
Common patterns for Firestore data access with caching

Phase 6: Enhanced operation logging integration
Phase 17: Request-scoped document caching
"""

from typing import Optional, List, Dict, Any, TypeVar, Generic
from abc import ABC, abstractmethod
import logging
import time

# Import Firestore operation counter for performance tracking (legacy)
try:
    from expense_engine.firestore_counter import record_read, record_write, record_delete
    TRACKING_ENABLED = True
except ImportError:
    TRACKING_ENABLED = False
    def record_read(count=1, collection=None): pass
    def record_write(count=1, collection=None): pass
    def record_delete(count=1, collection=None): pass

# Import enhanced operation logger
try:
    from expense_engine.utils.operation_logger import (
        log_firestore_read,
        log_firestore_write,
        log_firestore_delete,
        log_firestore_query
    )
    OPERATION_LOGGING_ENABLED = True
except ImportError:
    OPERATION_LOGGING_ENABLED = False
    def log_firestore_read(collection, doc_id=None, count=1, duration_ms=0): pass
    def log_firestore_write(collection, doc_id=None, count=1, duration_ms=0, operation="set"): pass
    def log_firestore_delete(collection, doc_id=None, count=1, duration_ms=0): pass
    def log_firestore_query(collection, result_count=0, duration_ms=0, filters=None): pass

# Import request-scoped cache (Phase 17)
try:
    from expense_engine.utils.request_cache import (
        get_request_cache,
        invalidate_cached_document,
        update_cached_document
    )
    REQUEST_CACHE_ENABLED = True
except ImportError:
    REQUEST_CACHE_ENABLED = False
    def get_request_cache(): return None
    def invalidate_cached_document(collection, doc_id): pass
    def update_cached_document(collection, doc_id, data): pass

T = TypeVar('T')

logger = logging.getLogger(__name__)


class BaseRepository(ABC, Generic[T]):
    """
    Base repository with common Firestore operations
    Provides CRUD operations and transaction support
    """
    
    def __init__(self, db=None):
        """
        Initialize repository
        
        Args:
            db: Firestore client instance (optional, will create if None)
        """
        if db is None:
            from firebase_admin import firestore as admin_firestore
            self.db = admin_firestore.client()
        else:
            self.db = db
    
    @abstractmethod
    def get_collection_name(self) -> str:
        """Return Firestore collection name"""
        raise NotImplementedError("Subclasses must implement get_collection_name")
    
    def get_collection(self):
        """Get collection reference"""
        return self.db.collection(self.get_collection_name())
    
    @property
    def collection(self):
        """Property alias for get_collection() for convenience"""
        return self.get_collection()
    
    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID with request-level caching
        
        Phase 17: Uses request cache to avoid duplicate reads within same request.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        collection_name = self.get_collection_name()
        
        # Phase 17: Check request cache first
        if REQUEST_CACHE_ENABLED:
            cache = get_request_cache()
            if cache is not None:
                cached_data = cache.get(collection_name, doc_id)
                if cached_data is not None:
                    logger.debug("[REQUEST_CACHE] HIT: %s/%s", collection_name, doc_id)
                    return cached_data
        
        start_time = time.time()
        try:
            doc = self.get_collection().document(doc_id).get()
            duration_ms = (time.time() - start_time) * 1000
            
            record_read(1, collection_name)  # Track Firestore read (legacy)
            log_firestore_read(collection_name, doc_id, 1, duration_ms)  # Enhanced logging
            
            if doc.exists:
                data = doc.to_dict()
                if data:
                    data['id'] = doc.id  # Include document ID
                    
                    # Phase 17: Store in request cache for reuse
                    if REQUEST_CACHE_ENABLED:
                        cache = get_request_cache()
                        if cache is not None:
                            cache.set(collection_name, doc_id, data)
                    
                return data
            return None
        except Exception as exc:
            logger.error("Error getting document %s: %s", doc_id, str(exc))
            raise
    
    def create(self, doc_id: str, data: Dict[str, Any]) -> str:
        """
        Create new document with cache update
        
        Phase 17: Stores created document in request cache to avoid re-read.
        
        Args:
            doc_id: Document ID
            data: Document data
            
        Returns:
            Created document ID
        """
        collection_name = self.get_collection_name()
        start_time = time.time()
        try:
            self.get_collection().document(doc_id).set(data)
            duration_ms = (time.time() - start_time) * 1000
            
            record_write(1, collection_name)  # Track Firestore write (legacy)
            log_firestore_write(collection_name, doc_id, 1, duration_ms, "create")  # Enhanced logging
            
            # Phase 17: Store in request cache (write-through pattern)
            if REQUEST_CACHE_ENABLED:
                cached_data = {**data, 'id': doc_id}
                update_cached_document(collection_name, doc_id, cached_data)
            
            logger.info("Created document: %s/%s", collection_name, doc_id)
            return doc_id
        except Exception as exc:
            logger.error("Error creating document %s: %s", doc_id, str(exc))
            raise
    
    def update(self, doc_id: str, data: Dict[str, Any]) -> None:
        """
        Update existing document with cache invalidation
        
        Phase 17: Invalidates request cache entry after update.
        
        Args:
            doc_id: Document ID
            data: Partial document data to update
        """
        collection_name = self.get_collection_name()
        start_time = time.time()
        try:
            self.get_collection().document(doc_id).update(data)
            duration_ms = (time.time() - start_time) * 1000
            
            record_write(1, collection_name)  # Track Firestore write (legacy)
            log_firestore_write(collection_name, doc_id, 1, duration_ms, "update")  # Enhanced logging
            
            # Phase 17: Invalidate request cache (can't merge partial updates easily)
            if REQUEST_CACHE_ENABLED:
                invalidate_cached_document(collection_name, doc_id)
            
            logger.info("Updated document: %s/%s", collection_name, doc_id)
        except Exception as exc:
            logger.error("Error updating document %s: %s", doc_id, str(exc))
            raise

    def upsert(self, doc_id: str, data: Dict[str, Any]) -> None:
        """
        Update document if exists, create if not (merge operation)
        
        Uses Firestore set() with merge=True to handle both cases.
        This is safer than update() when document may not exist.
        
        Phase 17: Invalidates request cache after upsert.
        
        Args:
            doc_id: Document ID
            data: Document data to merge
        """
        collection_name = self.get_collection_name()
        start_time = time.time()
        try:
            self.get_collection().document(doc_id).set(data, merge=True)
            duration_ms = (time.time() - start_time) * 1000
            
            record_write(1, collection_name)
            log_firestore_write(collection_name, doc_id, 1, duration_ms, "upsert")
            
            # Phase 17: Invalidate cache (merge creates partial state we can't track)
            if REQUEST_CACHE_ENABLED:
                invalidate_cached_document(collection_name, doc_id)
            
            logger.info("Upserted document: %s/%s", collection_name, doc_id)
        except Exception as exc:
            logger.error("Error upserting document %s: %s", doc_id, str(exc))
            raise
    
    def delete(self, doc_id: str) -> None:
        """
        Delete document with cache invalidation
        
        Phase 17: Removes document from request cache.
        
        Args:
            doc_id: Document ID
        """
        collection_name = self.get_collection_name()
        start_time = time.time()
        try:
            self.get_collection().document(doc_id).delete()
            duration_ms = (time.time() - start_time) * 1000
            
            record_delete(1, collection_name)  # Track Firestore delete (legacy)
            log_firestore_delete(collection_name, doc_id, 1, duration_ms)  # Enhanced logging
            
            # Phase 17: Remove from request cache
            if REQUEST_CACHE_ENABLED:
                invalidate_cached_document(collection_name, doc_id)
            
            logger.info("Deleted document: %s/%s", collection_name, doc_id)
        except Exception as exc:
            logger.error("Error deleting document %s: %s", doc_id, str(exc))
            raise
    
    def query(
        self,
        filters: Optional[List[tuple]] = None,
        order_by: Optional[tuple] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query documents with filters
        
        Args:
            filters: List of (field, operator, value) tuples
            order_by: Tuple of (field, direction) e.g. ('created_at', 'DESCENDING')
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching documents
        """
        start_time = time.time()
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            query = self.get_collection()
            
            # Build filter descriptions for logging
            filter_strs = []
            
            # Apply filters using FieldFilter (recommended pattern to avoid deprecation warning)
            if filters:
                for field, operator, value in filters:
                    query = query.where(filter=FieldFilter(field, operator, value))
                    filter_strs.append(f"{field}{operator}{value}")
            
            # Apply ordering
            if order_by:
                field, direction = order_by
                query = query.order_by(field, direction=direction)
            
            # Apply offset
            if offset:
                query = query.offset(offset)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            
            results = []
            for doc in docs:
                data = doc.to_dict()
                if data:
                    data['id'] = doc.id
                    results.append(data)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Track reads (1 per document returned, minimum 1 for the query itself)
            record_read(max(1, len(results)), self.get_collection_name())  # Legacy
            log_firestore_query(self.get_collection_name(), len(results), duration_ms, filter_strs)  # Enhanced
            
            return results
            
        except Exception as exc:
            logger.error("Error querying collection %s: %s", self.get_collection_name(), str(exc))
            raise
    
    def exists(self, doc_id: str) -> bool:
        """
        Check if document exists
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if document exists
        """
        try:
            doc = self.get_collection().document(doc_id).get()
            record_read(1, self.get_collection_name())  # Track read
            return doc.exists
        except Exception as exc:
            logger.error("Error checking existence of %s: %s", doc_id, str(exc))
            raise
    
    def count(self, filters: Optional[List[tuple]] = None) -> int:
        """
        Count documents matching filters
        
        Args:
            filters: List of (field, operator, value) tuples
            
        Returns:
            Number of matching documents
        """
        results = self.query(filters=filters)
        return len(results)
    
    def batch_create(self, documents: Dict[str, Dict[str, Any]]) -> None:
        """
        Create multiple documents in a batch
        
        Args:
            documents: Map of doc_id -> data
        """
        try:
            batch = self.db.batch()
            for doc_id, data in documents.items():
                doc_ref = self.get_collection().document(doc_id)
                batch.set(doc_ref, data)
            batch.commit()
            logger.info("Batch created %d documents in %s", len(documents), self.get_collection_name())
        except Exception as exc:
            logger.error("Error in batch create: %s", str(exc))
            raise
    
    def transaction_update(
        self,
        transaction,
        doc_id: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Update document within a transaction
        
        Args:
            transaction: Firestore transaction
            doc_id: Document ID
            data: Data to update
        """
        doc_ref = self.get_collection().document(doc_id)
        transaction.update(doc_ref, data)
    
    def batch_update(self, updates: Dict[str, Dict[str, Any]]) -> None:
        """
        Update multiple documents in a batch
        
        Args:
            updates: Map of doc_id -> data to update
        """
        try:
            batch = self.db.batch()
            for doc_id, data in updates.items():
                doc_ref = self.get_collection().document(doc_id)
                batch.update(doc_ref, data)
            batch.commit()
            logger.info("Batch updated %d documents in %s", len(updates), self.get_collection_name())
        except Exception as exc:
            logger.error("Error in batch update: %s", str(exc))
            raise
    
    def batch_delete(self, doc_ids: List[str]) -> None:
        """
        Delete multiple documents in a batch
        
        Args:
            doc_ids: List of document IDs to delete
        """
        try:
            batch = self.db.batch()
            for doc_id in doc_ids:
                doc_ref = self.get_collection().document(doc_id)
                batch.delete(doc_ref)
            batch.commit()
            logger.info("Batch deleted %d documents from %s", len(doc_ids), self.get_collection_name())
        except Exception as exc:
            logger.error("Error in batch delete: %s", str(exc))
            raise
    
    def query_with_cursor(
        self,
        filters: Optional[List[tuple]] = None,
        order_by: Optional[tuple] = None,
        limit: int = 20,
        start_after: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Query documents with cursor-based pagination
        More efficient than offset for large datasets
        
        Args:
            filters: List of (field, operator, value) tuples
            order_by: Tuple of (field, direction) e.g. ('created_at', 'DESCENDING')
            limit: Maximum number of results
            start_after: Document snapshot or field value to start after
            
        Returns:
            Dict with documents, has_more flag, and next_cursor
        """
        try:
            query = self.get_collection()
            
            # Apply filters
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            # Apply ordering (required for cursor pagination)
            if order_by:
                field, direction = order_by
                query = query.order_by(field, direction=direction)
            
            # Apply cursor
            if start_after:
                query = query.start_after(start_after)
            
            # Request one extra to check if more exist
            query = query.limit(limit + 1)
            
            # Execute query
            docs = list(query.stream())
            
            # Check if there are more results
            has_more = len(docs) > limit
            if has_more:
                docs = docs[:limit]  # Remove the extra document
            
            results = []
            last_doc = None
            for doc in docs:
                data = doc.to_dict()
                if data:
                    data['id'] = doc.id
                    results.append(data)
                    last_doc = doc
            
            return {
                'documents': results,
                'has_more': has_more,
                'next_cursor': last_doc.id if last_doc and has_more else None
            }
            
        except Exception as exc:
            logger.error("Error in cursor query %s: %s", self.get_collection_name(), str(exc))
            raise
    
    def soft_delete(self, doc_id: str, deleted_at_field: str = 'deleted_at', 
                    is_deleted_field: str = 'is_deleted') -> None:
        """
        Soft delete a document (mark as deleted without removing)
        
        Args:
            doc_id: Document ID
            deleted_at_field: Name of timestamp field
            is_deleted_field: Name of boolean deleted flag field
        """
        from datetime import datetime
        try:
            self.update(doc_id, {
                is_deleted_field: True,
                deleted_at_field: datetime.utcnow()
            })
            logger.info("Soft deleted document: %s/%s", self.get_collection_name(), doc_id)
        except Exception as exc:
            logger.error("Error soft deleting document %s: %s", doc_id, str(exc))
            raise
    
    def restore(self, doc_id: str, deleted_at_field: str = 'deleted_at',
                is_deleted_field: str = 'is_deleted') -> None:
        """
        Restore a soft-deleted document
        
        Args:
            doc_id: Document ID
            deleted_at_field: Name of timestamp field
            is_deleted_field: Name of boolean deleted flag field
        """
        try:
            self.update(doc_id, {
                is_deleted_field: False,
                deleted_at_field: None
            })
            logger.info("Restored document: %s/%s", self.get_collection_name(), doc_id)
        except Exception as exc:
            logger.error("Error restoring document %s: %s", doc_id, str(exc))
            raise
