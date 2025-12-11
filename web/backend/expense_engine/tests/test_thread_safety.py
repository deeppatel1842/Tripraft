"""
Unit Tests for Thread Safety Module
Phase 10: Thread Safety & Concurrency

Tests cover:
1. GroupLockManager - in-memory locking
2. OptimisticLockManager - version checking
3. RetryConfig - exponential backoff
4. Decorator functions - with_group_lock, with_retry
5. ThreadSafeBalanceManager - integrated thread-safe operations
"""

# pylint: disable=redefined-outer-name,unused-argument,protected-access

import pytest
import threading
import time
from decimal import Decimal
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestLockStats:
    """Tests for LockStats dataclass"""
    
    def test_initial_stats_are_zero(self):
        """Test that initial stats are all zero"""
        from expense_engine.utils.thread_safety import LockStats
        
        stats = LockStats()
        
        assert stats.acquisitions == 0
        assert stats.releases == 0
        assert stats.contentions == 0
        assert stats.timeouts == 0
        assert stats.total_wait_time_ms == 0.0
    
    def test_record_acquisition(self):
        """Test recording lock acquisition"""
        from expense_engine.utils.thread_safety import LockStats
        
        stats = LockStats()
        stats.record_acquisition(10.5)
        stats.record_acquisition(20.0)
        
        assert stats.acquisitions == 2
        assert stats.total_wait_time_ms == 30.5
    
    def test_record_release(self):
        """Test recording lock release"""
        from expense_engine.utils.thread_safety import LockStats
        
        stats = LockStats()
        stats.record_release()
        stats.record_release()
        
        assert stats.releases == 2
    
    def test_record_contention(self):
        """Test recording lock contention"""
        from expense_engine.utils.thread_safety import LockStats
        
        stats = LockStats()
        stats.record_contention()
        
        assert stats.contentions == 1
    
    def test_record_timeout(self):
        """Test recording lock timeout"""
        from expense_engine.utils.thread_safety import LockStats
        
        stats = LockStats()
        stats.record_timeout()
        
        assert stats.timeouts == 1
    
    def test_average_wait_time_calculation(self):
        """Test average wait time calculation"""
        from expense_engine.utils.thread_safety import LockStats
        
        stats = LockStats()
        stats.record_acquisition(10.0)
        stats.record_acquisition(20.0)
        stats.record_acquisition(30.0)
        
        assert stats.average_wait_time_ms == 20.0
    
    def test_average_wait_time_zero_acquisitions(self):
        """Test average wait time with zero acquisitions"""
        from expense_engine.utils.thread_safety import LockStats
        
        stats = LockStats()
        
        assert stats.average_wait_time_ms == 0.0


class TestGroupLockManager:
    """Tests for GroupLockManager"""
    
    def test_acquire_and_release_lock(self):
        """Test basic lock acquire and release"""
        from expense_engine.utils.thread_safety import GroupLockManager
        
        manager = GroupLockManager()
        group_id = "test_group_1"
        
        with manager.acquire_group_lock(group_id):
            # Lock should be held here
            assert group_id in manager._locks
        
        # Lock should be released
        stats = manager.get_stats(group_id)
        assert stats is not None
        assert stats.acquisitions == 1
        assert stats.releases == 1
    
    def test_reentrant_lock(self):
        """Test that locks are reentrant (same thread can acquire twice)"""
        from expense_engine.utils.thread_safety import GroupLockManager
        
        manager = GroupLockManager()
        group_id = "test_group_2"
        
        with manager.acquire_group_lock(group_id):
            # Nested acquisition should work (RLock)
            with manager.acquire_group_lock(group_id):
                pass
        
        stats = manager.get_stats(group_id)
        assert stats.acquisitions == 2
        assert stats.releases == 2
    
    def test_lock_timeout(self):
        """Test that lock times out when held by another thread"""
        from expense_engine.utils.thread_safety import GroupLockManager
        
        manager = GroupLockManager()
        group_id = "test_group_3"
        lock_acquired = threading.Event()
        timeout_occurred = threading.Event()
        
        def hold_lock():
            with manager.acquire_group_lock(group_id, timeout=5.0):
                lock_acquired.set()
                time.sleep(1.0)  # Hold lock for 1 second
        
        def try_acquire():
            lock_acquired.wait()  # Wait until first thread has lock
            try:
                with manager.acquire_group_lock(group_id, timeout=0.1):
                    pass  # Should not reach here
            except TimeoutError:
                timeout_occurred.set()
        
        thread1 = threading.Thread(target=hold_lock)
        thread2 = threading.Thread(target=try_acquire)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        assert timeout_occurred.is_set()
        stats = manager.get_stats(group_id)
        assert stats.timeouts == 1
    
    def test_concurrent_access_different_groups(self):
        """Test concurrent access to different groups"""
        from expense_engine.utils.thread_safety import GroupLockManager
        
        manager = GroupLockManager()
        results = []
        
        def access_group(group_id: str, value: int):
            with manager.acquire_group_lock(group_id):
                time.sleep(0.05)  # Simulate work
                results.append((group_id, value))
        
        threads = []
        for i in range(10):
            group_id = f"group_{i % 3}"  # 3 different groups
            thread = threading.Thread(target=access_group, args=(group_id, i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All 10 operations should complete
        assert len(results) == 10
    
    def test_get_all_stats(self):
        """Test getting stats for all groups"""
        from expense_engine.utils.thread_safety import GroupLockManager
        
        manager = GroupLockManager()
        
        with manager.acquire_group_lock("group_a"):
            pass
        with manager.acquire_group_lock("group_b"):
            pass
        with manager.acquire_group_lock("group_a"):
            pass
        
        all_stats = manager.get_all_stats()
        
        assert "group_a" in all_stats
        assert "group_b" in all_stats
        assert all_stats["group_a"].acquisitions == 2
        assert all_stats["group_b"].acquisitions == 1
    
    def test_clear_stats(self):
        """Test clearing statistics"""
        from expense_engine.utils.thread_safety import GroupLockManager
        
        manager = GroupLockManager()
        
        with manager.acquire_group_lock("group_x"):
            pass
        
        manager.clear_stats()
        
        stats = manager.get_stats("group_x")
        assert stats.acquisitions == 0


class TestOptimisticLockManager:
    """Tests for OptimisticLockManager"""
    
    def test_check_version_success(self):
        """Test version check passes when versions match"""
        from expense_engine.utils.thread_safety import OptimisticLockManager
        
        # Should not raise
        OptimisticLockManager.check_version("group_1", 5, 5)
    
    def test_check_version_failure(self):
        """Test version check fails when versions don't match"""
        from expense_engine.utils.thread_safety import (
            OptimisticLockManager,
            OptimisticLockError
        )
        
        with pytest.raises(OptimisticLockError) as exc_info:
            OptimisticLockManager.check_version("group_1", 5, 6)
        
        assert exc_info.value.expected_version == 5
        assert exc_info.value.actual_version == 6
        assert exc_info.value.group_id == "group_1"
    
    def test_increment_version_from_none(self):
        """Test version increment from None"""
        from expense_engine.utils.thread_safety import OptimisticLockManager
        
        result = OptimisticLockManager.increment_version(None)
        assert result == 1
    
    def test_increment_version_from_number(self):
        """Test version increment from existing number"""
        from expense_engine.utils.thread_safety import OptimisticLockManager
        
        result = OptimisticLockManager.increment_version(5)
        assert result == 6
    
    def test_optimistic_lock_error_str(self):
        """Test OptimisticLockError string representation"""
        from expense_engine.utils.thread_safety import OptimisticLockError
        
        error = OptimisticLockError(
            expected_version=5,
            actual_version=6,
            group_id="test_group"
        )
        
        error_str = str(error)
        assert "test_group" in error_str
        assert "5" in error_str
        assert "6" in error_str


class TestRetryConfig:
    """Tests for RetryConfig"""
    
    def test_default_configuration(self):
        """Test default retry configuration"""
        from expense_engine.utils.thread_safety import RetryConfig
        
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay_ms == 100.0
        assert config.max_delay_ms == 5000.0
        assert config.exponential_base == 2.0
    
    def test_custom_configuration(self):
        """Test custom retry configuration"""
        from expense_engine.utils.thread_safety import RetryConfig
        
        config = RetryConfig(
            max_retries=5,
            base_delay_ms=50.0,
            max_delay_ms=1000.0,
            exponential_base=1.5
        )
        
        assert config.max_retries == 5
        assert config.base_delay_ms == 50.0
    
    def test_get_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation"""
        from expense_engine.utils.thread_safety import RetryConfig
        
        config = RetryConfig(
            base_delay_ms=100.0,
            exponential_base=2.0,
            max_delay_ms=10000.0
        )
        
        assert config.get_delay_ms(0) == 100.0    # 100 * 2^0 = 100
        assert config.get_delay_ms(1) == 200.0    # 100 * 2^1 = 200
        assert config.get_delay_ms(2) == 400.0    # 100 * 2^2 = 400
        assert config.get_delay_ms(3) == 800.0    # 100 * 2^3 = 800
    
    def test_get_delay_respects_max(self):
        """Test that delay respects maximum"""
        from expense_engine.utils.thread_safety import RetryConfig
        
        config = RetryConfig(
            base_delay_ms=100.0,
            exponential_base=2.0,
            max_delay_ms=500.0
        )
        
        # 100 * 2^10 = 102400, but should be capped at 500
        assert config.get_delay_ms(10) == 500.0


class TestWithRetryDecorator:
    """Tests for with_retry decorator"""
    
    def test_success_on_first_try(self):
        """Test function succeeds on first try"""
        from expense_engine.utils.thread_safety import with_retry, RetryConfig
        
        call_count = 0
        
        @with_retry(config=RetryConfig(max_retries=3))
        def always_succeeds():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = always_succeeds()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_specified_exception(self):
        """Test retry on specified exception"""
        from expense_engine.utils.thread_safety import (
            with_retry,
            RetryConfig,
            OptimisticLockError
        )
        
        call_count = 0
        
        @with_retry(
            config=RetryConfig(max_retries=3, base_delay_ms=1.0),
            retry_exceptions=(OptimisticLockError,)
        )
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OptimisticLockError(
                    expected_version=1,
                    actual_version=2,
                    group_id="test"
                )
            return "success"
        
        result = fails_twice()
        
        assert result == "success"
        assert call_count == 3
    
    def test_raises_after_max_retries(self):
        """Test exception raised after max retries"""
        from expense_engine.utils.thread_safety import (
            with_retry,
            RetryConfig,
            OptimisticLockError
        )
        
        call_count = 0
        
        @with_retry(
            config=RetryConfig(max_retries=2, base_delay_ms=1.0),
            retry_exceptions=(OptimisticLockError,)
        )
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise OptimisticLockError(
                expected_version=1,
                actual_version=2,
                group_id="test"
            )
        
        with pytest.raises(OptimisticLockError):
            always_fails()
        
        # Initial try + 2 retries = 3 calls
        assert call_count == 3
    
    def test_no_retry_on_unspecified_exception(self):
        """Test no retry on exception not in retry_exceptions"""
        from expense_engine.utils.thread_safety import (
            with_retry,
            RetryConfig,
            OptimisticLockError
        )
        
        call_count = 0
        
        @with_retry(
            config=RetryConfig(max_retries=3, base_delay_ms=1.0),
            retry_exceptions=(OptimisticLockError,)
        )
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a retry exception")
        
        with pytest.raises(ValueError):
            raises_value_error()
        
        # Should only be called once (no retry)
        assert call_count == 1


class TestWithGroupLockDecorator:
    """Tests for with_group_lock decorator"""
    
    def test_decorator_acquires_lock_from_kwargs(self):
        """Test decorator extracts group_id from kwargs"""
        from expense_engine.utils.thread_safety import (
            with_group_lock,
            get_group_lock_manager
        )
        
        @with_group_lock(group_id_param="group_id")
        def my_function(group_id: str, data: str) -> str:
            return f"{group_id}:{data}"
        
        result = my_function(group_id="test_group", data="test_data")
        
        assert result == "test_group:test_data"
        
        # Verify lock was used
        manager = get_group_lock_manager()
        stats = manager.get_stats("test_group")
        assert stats is not None
        assert stats.acquisitions > 0
    
    def test_decorator_acquires_lock_from_positional(self):
        """Test decorator extracts group_id from positional args"""
        from expense_engine.utils.thread_safety import with_group_lock
        
        @with_group_lock(group_id_param="group_id")
        def my_function(group_id: str, value: int) -> int:
            return value * 2
        
        result = my_function("my_group", 5)
        
        assert result == 10
    
    def test_decorator_raises_on_missing_group_id(self):
        """Test decorator raises when group_id not found"""
        from expense_engine.utils.thread_safety import with_group_lock
        
        @with_group_lock(group_id_param="group_id")
        def my_function(other_param: str) -> str:
            return other_param
        
        with pytest.raises(ValueError) as exc_info:
            my_function(other_param="value")
        
        assert "group_id" in str(exc_info.value)


class TestThreadSafeBalanceManager:
    """Tests for ThreadSafeBalanceManager"""
    
    @pytest.fixture
    def mock_firestore(self):
        """Create mock Firestore client"""
        with patch('firebase_admin.firestore.client') as mock_client:
            # Setup mock document
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {
                'group_id': 'test_group',
                'balances': {'user_1': 50.0, 'user_2': -50.0},
                'version': 1
            }
            
            # Setup mock collection
            mock_collection = MagicMock()
            mock_collection.document.return_value.get.return_value = mock_doc
            
            # Setup mock transaction
            mock_transaction = MagicMock()
            mock_client.return_value.collection.return_value = mock_collection
            mock_client.return_value.transaction.return_value = mock_transaction
            
            yield mock_client
    
    @pytest.fixture
    def mock_balance_service(self):
        """Create mock balance service"""
        service = MagicMock()
        service.calculate_expense_deltas.return_value = {
            'user_1': Decimal('50.00'),
            'user_2': Decimal('-50.00')
        }
        return service
    
    def test_get_balances_with_version(self, mock_firestore):
        """Test getting balances with version"""
        from expense_engine.utils.thread_safe_balance import ThreadSafeBalanceManager
        
        manager = ThreadSafeBalanceManager()
        result = manager.get_balances_with_version("test_group")
        
        assert result['group_id'] == "test_group"
        assert 'balances' in result
        assert 'version' in result
    
    def test_get_lock_stats(self, mock_firestore):
        """Test getting lock statistics"""
        from expense_engine.utils.thread_safe_balance import ThreadSafeBalanceManager
        
        manager = ThreadSafeBalanceManager()
        
        # First, create some lock activity
        with manager.lock_manager.acquire_group_lock("stats_test_group"):
            pass
        
        stats = manager.get_lock_stats("stats_test_group")
        
        assert stats is not None
        assert stats['group_id'] == "stats_test_group"
        assert stats['acquisitions'] == 1
    
    def test_get_lock_stats_no_activity(self, mock_firestore):
        """Test getting lock stats for group with no activity"""
        from expense_engine.utils.thread_safe_balance import ThreadSafeBalanceManager
        
        manager = ThreadSafeBalanceManager()
        stats = manager.get_lock_stats("nonexistent_group")
        
        assert stats is None


class TestConcurrentBalanceUpdates:
    """Integration tests for concurrent balance updates"""
    
    def test_concurrent_expense_additions(self):
        """Test multiple threads adding expenses don't corrupt balances"""
        from expense_engine.utils.thread_safety import GroupLockManager
        
        manager = GroupLockManager()
        group_id = "concurrent_test_group"
        
        # Simulated balance state
        balance = {'total': 0}
        
        def add_expense(amount: int):
            with manager.acquire_group_lock(group_id):
                # Simulate read-modify-write
                current = balance['total']
                time.sleep(0.01)  # Simulate processing time
                balance['total'] = current + amount
        
        # Run 100 concurrent additions of $1 each
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(add_expense, 1) for _ in range(100)]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions
        
        # Without proper locking, this would likely be less than 100
        assert balance['total'] == 100
    
    def test_no_deadlock_with_multiple_groups(self):
        """Test that accessing multiple groups doesn't cause deadlock"""
        from expense_engine.utils.thread_safety import GroupLockManager
        
        manager = GroupLockManager()
        results = []
        
        def access_groups(thread_id: int):
            # Each thread accesses groups in different order
            groups = [f"group_{i}" for i in range(5)]
            if thread_id % 2 == 0:
                groups = reversed(groups)
            
            for group_id in groups:
                with manager.acquire_group_lock(group_id, timeout=5.0):
                    time.sleep(0.01)
                    results.append((thread_id, group_id))
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=access_groups, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait with timeout to detect deadlock
        for thread in threads:
            thread.join(timeout=10.0)
            assert not thread.is_alive(), "Thread did not complete - possible deadlock"
        
        # All operations should complete
        assert len(results) == 50  # 10 threads * 5 groups each


class TestGlobalSingletons:
    """Tests for global singleton instances"""
    
    def test_get_group_lock_manager_singleton(self):
        """Test that get_group_lock_manager returns singleton"""
        from expense_engine.utils.thread_safety import get_group_lock_manager
        
        manager1 = get_group_lock_manager()
        manager2 = get_group_lock_manager()
        
        assert manager1 is manager2
    
    def test_get_thread_safe_balance_manager_singleton(self):
        """Test that get_thread_safe_balance_manager returns singleton"""
        from expense_engine.utils.thread_safe_balance import (
            get_thread_safe_balance_manager,
            _thread_safe_balance_manager
        )
        
        # Reset singleton for clean test
        import expense_engine.utils.thread_safe_balance as module
        module._thread_safe_balance_manager = None
        
        with patch('firebase_admin.firestore.client'):
            manager1 = get_thread_safe_balance_manager()
            manager2 = get_thread_safe_balance_manager()
            
            assert manager1 is manager2
