"""
Tests for Request-scoped Document Cache (Phase 17.1)

Tests verify:
1. Cache stores and retrieves documents correctly
2. Cache prevents duplicate Firestore reads within a request
3. Cache is properly scoped to the request lifecycle
4. Cache invalidation works correctly on writes
5. Statistics are tracked accurately
"""

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask

# Import the request cache module
from expense_engine.utils.request_cache import (
    RequestDocumentCache,
    get_request_cache,
    cache_document_read,
    cache_query_result,
    invalidate_cached_document,
    update_cached_document,
    log_request_cache_stats
)


class TestRequestDocumentCache:
    """Unit tests for RequestDocumentCache class"""
    
    def test_cache_initialization(self):
        """Cache initializes with empty state"""
        cache = RequestDocumentCache()
        
        assert len(cache) == 0
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['sets'] == 0
    
    def test_set_and_get_document(self):
        """Cache stores and retrieves documents correctly"""
        cache = RequestDocumentCache()
        doc_data = {'id': 'doc123', 'name': 'Test Document', 'amount': 100}
        
        # Set document
        cache.set('expense_groups', 'doc123', doc_data)
        
        # Get document
        result = cache.get('expense_groups', 'doc123')
        
        assert result == doc_data
        assert cache.get_stats()['sets'] == 1
        assert cache.get_stats()['hits'] == 1
    
    def test_get_nonexistent_document_returns_none(self):
        """Getting non-existent document returns None and counts as miss"""
        cache = RequestDocumentCache()
        
        result = cache.get('expense_groups', 'nonexistent')
        
        assert result is None
        assert cache.get_stats()['misses'] == 1
    
    def test_set_none_does_not_cache(self):
        """Setting None value does not store in cache"""
        cache = RequestDocumentCache()
        
        cache.set('expense_groups', 'doc123', None)
        
        assert len(cache) == 0
        assert cache.get_stats()['sets'] == 0
    
    def test_delete_removes_document(self):
        """Delete removes document from cache"""
        cache = RequestDocumentCache()
        doc_data = {'id': 'doc123', 'name': 'Test'}
        
        cache.set('expense_groups', 'doc123', doc_data)
        assert len(cache) == 1
        
        result = cache.delete('expense_groups', 'doc123')
        
        assert result is True
        assert len(cache) == 0
        assert cache.get('expense_groups', 'doc123') is None
    
    def test_delete_nonexistent_returns_false(self):
        """Delete of non-existent document returns False"""
        cache = RequestDocumentCache()
        
        result = cache.delete('expense_groups', 'nonexistent')
        
        assert result is False
    
    def test_clear_removes_all_documents(self):
        """Clear removes all cached documents"""
        cache = RequestDocumentCache()
        
        cache.set('expense_groups', 'doc1', {'id': 'doc1'})
        cache.set('expense_groups', 'doc2', {'id': 'doc2'})
        cache.set('expenses', 'exp1', {'id': 'exp1'})
        assert len(cache) == 3
        
        cache.clear()
        
        assert len(cache) == 0
    
    def test_hit_rate_calculation(self):
        """Hit rate is calculated correctly"""
        cache = RequestDocumentCache()
        
        # Set a document
        cache.set('expense_groups', 'doc1', {'id': 'doc1'})
        
        # 2 hits
        cache.get('expense_groups', 'doc1')
        cache.get('expense_groups', 'doc1')
        
        # 2 misses
        cache.get('expense_groups', 'doc2')
        cache.get('expense_groups', 'doc3')
        
        # 2 hits + 2 misses = 50% hit rate
        assert cache.get_hit_rate() == 50.0
    
    def test_hit_rate_zero_when_no_lookups(self):
        """Hit rate is 0 when no lookups have been made"""
        cache = RequestDocumentCache()
        
        assert cache.get_hit_rate() == 0.0
    
    def test_contains_check(self):
        """Contains check works correctly"""
        cache = RequestDocumentCache()
        
        cache.set('expense_groups', 'doc1', {'id': 'doc1'})
        
        assert 'expense_groups/doc1' in cache
        assert 'expense_groups/doc2' not in cache
    
    def test_different_collections_isolated(self):
        """Documents in different collections are isolated"""
        cache = RequestDocumentCache()
        
        cache.set('expense_groups', 'doc1', {'collection': 'groups'})
        cache.set('expenses', 'doc1', {'collection': 'expenses'})
        
        assert cache.get('expense_groups', 'doc1')['collection'] == 'groups'
        assert cache.get('expenses', 'doc1')['collection'] == 'expenses'


class TestGetRequestCache:
    """Tests for get_request_cache function"""
    
    def test_returns_cache_outside_request_context(self):
        """Returns a new cache instance outside Flask request context"""
        cache = get_request_cache()
        
        assert isinstance(cache, RequestDocumentCache)
    
    def test_returns_same_cache_within_request(self):
        """Returns the same cache instance within a Flask request"""
        app = Flask(__name__)
        
        with app.test_request_context():
            cache1 = get_request_cache()
            cache1.set('test', 'doc1', {'data': 'value'})
            
            cache2 = get_request_cache()
            
            # Should be the same instance
            assert cache2.get('test', 'doc1') == {'data': 'value'}
    
    def test_new_cache_for_each_request(self):
        """Each request gets a fresh cache"""
        app = Flask(__name__)
        
        with app.test_request_context():
            cache1 = get_request_cache()
            cache1.set('test', 'doc1', {'data': 'request1'})
        
        with app.test_request_context():
            cache2 = get_request_cache()
            # New request should not have previous request's data
            assert cache2.get('test', 'doc1') is None


class TestCacheDocumentReadDecorator:
    """Tests for cache_document_read decorator"""
    
    def test_decorator_caches_result(self):
        """Decorator caches the result of get_by_id"""
        app = Flask(__name__)
        
        class MockRepository:
            _collection_name = 'test_collection'
            
            def __init__(self):
                self.call_count = 0
            
            @cache_document_read
            def get_by_id(self, doc_id: str):
                self.call_count += 1
                return {'id': doc_id, 'data': 'test'}
        
        with app.test_request_context():
            repo = MockRepository()
            
            # First call - should hit the actual method
            result1 = repo.get_by_id('doc123')
            assert result1 == {'id': 'doc123', 'data': 'test'}
            assert repo.call_count == 1
            
            # Second call - should return cached value
            result2 = repo.get_by_id('doc123')
            assert result2 == {'id': 'doc123', 'data': 'test'}
            assert repo.call_count == 1  # No additional call
    
    def test_decorator_does_not_cache_none(self):
        """Decorator does not cache None results"""
        app = Flask(__name__)
        
        class MockRepository:
            _collection_name = 'test_collection'
            
            def __init__(self):
                self.call_count = 0
            
            @cache_document_read
            def get_by_id(self, doc_id: str):
                self.call_count += 1
                return None
        
        with app.test_request_context():
            repo = MockRepository()
            
            # First call
            result1 = repo.get_by_id('nonexistent')
            assert result1 is None
            assert repo.call_count == 1
            
            # Second call - should still hit method since None wasn't cached
            result2 = repo.get_by_id('nonexistent')
            assert result2 is None
            assert repo.call_count == 2
    
    def test_decorator_different_doc_ids_cached_separately(self):
        """Different doc IDs are cached separately"""
        app = Flask(__name__)
        
        class MockRepository:
            _collection_name = 'test_collection'
            
            @cache_document_read
            def get_by_id(self, doc_id: str):
                return {'id': doc_id}
        
        with app.test_request_context():
            repo = MockRepository()
            
            result1 = repo.get_by_id('doc1')
            result2 = repo.get_by_id('doc2')
            
            assert result1['id'] == 'doc1'
            assert result2['id'] == 'doc2'


class TestCacheQueryResultDecorator:
    """Tests for cache_query_result decorator"""
    
    def test_decorator_caches_query_result(self):
        """Decorator caches query results"""
        app = Flask(__name__)
        
        class MockRepository:
            def __init__(self):
                self.call_count = 0
            
            @cache_query_result('expense_groups', 'user_groups')
            def get_user_groups(self, user_id: str):
                self.call_count += 1
                return [{'id': 'group1'}, {'id': 'group2'}]
        
        with app.test_request_context():
            repo = MockRepository()
            
            # First call
            result1 = repo.get_user_groups('user123')
            assert len(result1) == 2
            assert repo.call_count == 1
            
            # Second call - should be cached
            result2 = repo.get_user_groups('user123')
            assert len(result2) == 2
            assert repo.call_count == 1  # No additional call
    
    def test_decorator_different_args_cached_separately(self):
        """Different arguments are cached separately"""
        app = Flask(__name__)
        
        class MockRepository:
            call_count = 0
            
            @cache_query_result('expense_groups', 'user_groups')
            def get_user_groups(self, user_id: str):
                MockRepository.call_count += 1
                return [{'user': user_id}]
        
        with app.test_request_context():
            repo = MockRepository()
            
            result1 = repo.get_user_groups('user1')
            result2 = repo.get_user_groups('user2')
            
            assert result1[0]['user'] == 'user1'
            assert result2[0]['user'] == 'user2'
            assert MockRepository.call_count == 2


class TestCacheInvalidation:
    """Tests for cache invalidation functions"""
    
    def test_invalidate_cached_document(self):
        """invalidate_cached_document removes document from cache"""
        app = Flask(__name__)
        
        with app.test_request_context():
            cache = get_request_cache()
            cache.set('expense_groups', 'doc1', {'id': 'doc1'})
            
            invalidate_cached_document('expense_groups', 'doc1')
            
            assert cache.get('expense_groups', 'doc1') is None
    
    def test_update_cached_document(self):
        """update_cached_document updates cache with new data"""
        app = Flask(__name__)
        
        with app.test_request_context():
            cache = get_request_cache()
            cache.set('expense_groups', 'doc1', {'id': 'doc1', 'version': 1})
            
            update_cached_document('expense_groups', 'doc1', {'id': 'doc1', 'version': 2})
            
            result = cache.get('expense_groups', 'doc1')
            assert result['version'] == 2


class TestLogRequestCacheStats:
    """Tests for log_request_cache_stats function"""
    
    def test_returns_stats_dict(self):
        """Function returns stats dictionary"""
        app = Flask(__name__)
        
        with app.test_request_context():
            cache = get_request_cache()
            cache.set('test', 'doc1', {'id': 'doc1'})
            cache.get('test', 'doc1')  # Hit
            cache.get('test', 'doc2')  # Miss
            
            stats = log_request_cache_stats()
            
            assert 'hits' in stats
            assert 'misses' in stats
            assert 'sets' in stats
            assert 'hit_rate' in stats
            assert 'cached_docs' in stats
            assert stats['hits'] == 1
            assert stats['misses'] == 1


class TestIntegrationWithBaseRepository:
    """Integration tests with BaseRepository"""
    
    def test_base_repository_uses_request_cache(self):
        """BaseRepository.get_by_id uses request cache"""
        app = Flask(__name__)
        
        with app.test_request_context():
            # Force reimport to ensure REQUEST_CACHE_ENABLED is True
            import importlib
            from expense_engine.repositories import base
            importlib.reload(base)
            
            # Mock Firestore document
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.id = 'test123'
            mock_doc.to_dict.return_value = {'name': 'Test Group'}
            
            mock_collection = MagicMock()
            mock_collection.document.return_value.get.return_value = mock_doc
            
            mock_db = MagicMock()
            mock_db.collection.return_value = mock_collection
            
            # Create repository using reloaded module
            class TestRepository(base.BaseRepository):
                def get_collection_name(self) -> str:
                    return 'test_collection'
            
            repo = TestRepository(db=mock_db)
            
            # First call - should hit Firestore
            result1 = repo.get_by_id('test123')
            assert result1['name'] == 'Test Group'
            assert mock_collection.document.call_count == 1
            
            # Second call - should hit cache, not Firestore
            result2 = repo.get_by_id('test123')
            assert result2['name'] == 'Test Group'
            assert mock_collection.document.call_count == 1  # No additional call
    
    def test_base_repository_create_updates_cache(self):
        """BaseRepository.create stores document in request cache"""
        app = Flask(__name__)
        
        with app.test_request_context():
            # Force reimport to ensure REQUEST_CACHE_ENABLED is True
            import importlib
            from expense_engine.repositories import base
            importlib.reload(base)
            
            mock_collection = MagicMock()
            mock_db = MagicMock()
            mock_db.collection.return_value = mock_collection
            
            class TestRepository(base.BaseRepository):
                def get_collection_name(self) -> str:
                    return 'test_collection'
            
            repo = TestRepository(db=mock_db)
            
            # Create document
            repo.create('new_doc', {'name': 'New Document'})
            
            # Check cache has the document
            cache = get_request_cache()
            cached = cache.get('test_collection', 'new_doc')
            assert cached is not None
            assert cached['name'] == 'New Document'
            assert cached['id'] == 'new_doc'
    
    def test_base_repository_delete_invalidates_cache(self):
        """BaseRepository.delete removes document from request cache"""
        app = Flask(__name__)
        
        with app.test_request_context():
            # Force reimport to ensure REQUEST_CACHE_ENABLED is True
            import importlib
            from expense_engine.repositories import base
            importlib.reload(base)
            
            mock_collection = MagicMock()
            mock_db = MagicMock()
            mock_db.collection.return_value = mock_collection
            
            class TestRepository(base.BaseRepository):
                def get_collection_name(self) -> str:
                    return 'test_collection'
            
            repo = TestRepository(db=mock_db)
            
            # Pre-populate cache
            cache = get_request_cache()
            cache.set('test_collection', 'doc_to_delete', {'id': 'doc_to_delete'})
            
            # Delete document
            repo.delete('doc_to_delete')
            
            # Cache should be cleared
            assert cache.get('test_collection', 'doc_to_delete') is None


class TestPerformanceScenarios:
    """Performance scenario tests"""
    
    def test_multiple_reads_same_document(self):
        """Multiple reads of same document only hit Firestore once"""
        app = Flask(__name__)
        
        with app.test_request_context():
            call_count = 0
            
            def mock_get_by_id(doc_id):
                nonlocal call_count
                call_count += 1
                return {'id': doc_id, 'data': 'test'}
            
            cache = get_request_cache()
            collection = 'expense_groups'
            doc_id = 'group123'
            
            # Simulate 5 reads of same document
            for _ in range(5):
                cached = cache.get(collection, doc_id)
                if cached is None:
                    result = mock_get_by_id(doc_id)
                    cache.set(collection, doc_id, result)
            
            # Should only call Firestore once
            assert call_count == 1
            
            stats = cache.get_stats()
            assert stats['hits'] == 4  # 4 cache hits
            assert stats['misses'] == 1  # 1 cache miss (first read)
            assert stats['sets'] == 1  # 1 cache set
    
    def test_expense_creation_workflow(self):
        """Simulates expense creation workflow with cache"""
        app = Flask(__name__)
        
        with app.test_request_context():
            cache = get_request_cache()
            
            # Simulate workflow:
            # 1. Read group (verify user is member)
            # 2. Read group again (get settings)
            # 3. Read group again (calculate balances)
            # 4. Create expense
            # 5. Read expense (verify creation) - should use cache
            
            group_reads = 0
            expense_reads = 0
            
            def read_group(group_id):
                nonlocal group_reads
                cached = cache.get('expense_groups', group_id)
                if cached:
                    return cached
                group_reads += 1
                data = {'id': group_id, 'name': 'Test Group'}
                cache.set('expense_groups', group_id, data)
                return data
            
            def create_expense(expense_id, data):
                full_data = {**data, 'id': expense_id}
                cache.set('expenses', expense_id, full_data)
                return expense_id
            
            def read_expense(expense_id):
                nonlocal expense_reads
                cached = cache.get('expenses', expense_id)
                if cached:
                    return cached
                expense_reads += 1
                return {'id': expense_id}
            
            # Execute workflow
            read_group('group1')  # Miss - 1 Firestore read
            read_group('group1')  # Hit
            read_group('group1')  # Hit
            
            create_expense('exp1', {'amount': 100, 'group_id': 'group1'})
            
            read_expense('exp1')  # Hit (from create cache)
            
            assert group_reads == 1  # Only 1 Firestore read for group
            assert expense_reads == 0  # 0 Firestore reads for expense (cached from create)
            
            stats = cache.get_stats()
            # 2 group hits + 1 expense hit = 3 total hits
            assert stats['hits'] == 3
            # 1 group miss = 1 miss
            assert stats['misses'] == 1
