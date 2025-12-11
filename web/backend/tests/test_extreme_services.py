"""
Unit Tests for Phase 21 Extreme Services
==========================================

Tests for the 10-operation architecture:
- ExtremeDashboardService
- ExtremeGroupService
- ExtremeExpenseService
- ExtremeSettlementService

Target: Verify each operation achieves 0 reads and 1 batch write.
"""

import pytest
from unittest.mock import MagicMock


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock Firestore database"""
    db = MagicMock()
    batch = MagicMock()
    db.batch.return_value = batch
    
    collection = MagicMock()
    db.collection.return_value = collection
    
    doc = MagicMock()
    collection.document.return_value = doc
    doc.get.return_value = MagicMock(exists=False, to_dict=lambda: {})
    
    return {'db': db, 'batch': batch, 'collection': collection, 'doc': doc}


@pytest.fixture
def mock_cache():
    """Mock Redis cache manager"""
    cache = MagicMock()
    cache.is_available.return_value = True
    cache.get.return_value = None
    cache.set.return_value = True
    cache.delete.return_value = True
    return cache


@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        'user_id': 'test_user_123',
        'email': 'test@example.com',
        'display_name': 'Test User'
    }


@pytest.fixture
def sample_group():
    """Sample group data"""
    return {
        'group_id': 'grp_test123',
        'name': 'Test Group',
        'currency': 'USD',
        'created_by': 'test_user_123',
        'members': [
            {'user_id': 'test_user_123', 'display_name': 'Test User', 'role': 'owner'},
            {'user_id': 'test_user_456', 'display_name': 'Other User', 'role': 'member'}
        ],
        'balances': {'test_user_123': 50.0, 'test_user_456': -50.0},
        'recent_expenses': [],
        'recent_settlements': []
    }


@pytest.fixture
def sample_expense():
    """Sample expense data"""
    return {
        'expense_id': 'exp_test123',
        'group_id': 'grp_test123',
        'amount': 100.0,
        'description': 'Test Expense',
        'paid_by': 'test_user_123',
        'splits': [
            {'user_id': 'test_user_123', 'amount': 50.0},
            {'user_id': 'test_user_456', 'amount': 50.0}
        ],
        'category': 'food',
        'created_by': 'test_user_123'
    }


@pytest.fixture
def sample_dashboard(sample_group):
    """Sample dashboard data from cache"""
    return {
        'user_id': 'test_user_123',
        'user_email': 'test@example.com',
        'groups': {
            'grp_test123': sample_group
        },
        'pending_invitations': [],
        'summary': {
            'total_owed_to_you': 50.0,
            'total_you_owe': 0.0,
            'net_balance': 50.0,
            'group_count': 1
        }
    }


# ============================================================================
# ExtremeDashboardService Tests
# ============================================================================

class TestExtremeDashboardService:
    """Tests for ExtremeDashboardService"""
    
    def test_get_dashboard_from_cache_hit(self, mock_cache):
        """Test cache hit returns data without Firestore read"""
        # Import after mocking
        from expense_engine.services.extreme_dashboard_service import ExtremeDashboardService
        
        # Setup cache hit
        mock_cache.get.return_value = {'user_id': 'test_123', 'groups': {}}
        
        service = ExtremeDashboardService()
        service._cache = mock_cache
        
        result = service.get_dashboard_from_cache('test_123')
        
        assert result is not None
        assert result['user_id'] == 'test_123'
        mock_cache.get.assert_called_once()
    
    def test_get_dashboard_from_cache_miss(self, mock_cache):
        """Test cache miss returns None"""
        from expense_engine.services.extreme_dashboard_service import ExtremeDashboardService
        
        mock_cache.get.return_value = None
        
        service = ExtremeDashboardService()
        service._cache = mock_cache
        
        result = service.get_dashboard_from_cache('test_123')
        
        assert result is None


# ============================================================================
# ExtremeGroupService Tests
# ============================================================================

class TestExtremeGroupService:
    """Tests for ExtremeGroupService"""
    
    def test_create_group_extreme_uses_batch(self, mock_db, mock_cache):
        """Test create_group_extreme uses single batch write"""
        from expense_engine.services.extreme_group_service import ExtremeGroupService
        
        service = ExtremeGroupService()
        service._db = mock_db['db']
        service._cache = mock_cache
        
        result = service.create_group_extreme(
            user_id='test_user_123',
            name='New Group',
            currency='USD',
            description='Test description'
        )
        
        # Verify batch was used
        mock_db['db'].batch.assert_called_once()
        mock_db['batch'].commit.assert_called_once()
        
        # Verify result structure
        assert 'group_id' in result
        assert result['name'] == 'New Group'
        assert result['currency'] == 'USD'
    
    def test_update_group_extreme_uses_batch(self, mock_db, mock_cache, sample_group):
        """Test update_group_extreme uses single batch write"""
        from expense_engine.services.extreme_group_service import ExtremeGroupService
        
        service = ExtremeGroupService()
        service._db = mock_db['db']
        service._cache = mock_cache
        
        result = service.update_group_extreme(
            group_id='grp_test123',
            updates={'name': 'Updated Group'},
            group_data_from_cache=sample_group,
            requester_id='test_user_123'
        )
        
        # Verify batch was used
        mock_db['db'].batch.assert_called_once()
        mock_db['batch'].commit.assert_called_once()
        
        # Verify result
        assert result['name'] == 'Updated Group'
    
    def test_add_member_extreme_uses_batch(self, mock_db, mock_cache, sample_group):
        """Test add_member_extreme uses single batch write"""
        from expense_engine.services.extreme_group_service import ExtremeGroupService
        
        service = ExtremeGroupService()
        service._db = mock_db['db']
        service._cache = mock_cache
        
        result = service.add_member_extreme(
            group_id='grp_test123',
            email='newuser@example.com',
            group_data_from_cache=sample_group,
            inviter_id='test_user_123'
        )
        
        # Verify batch was used
        mock_db['db'].batch.assert_called_once()
        mock_db['batch'].commit.assert_called_once()
    
    def test_remove_member_extreme_uses_batch(self, mock_db, mock_cache, sample_group):
        """Test remove_member_extreme uses single batch write"""
        from expense_engine.services.extreme_group_service import ExtremeGroupService
        
        service = ExtremeGroupService()
        service._db = mock_db['db']
        service._cache = mock_cache
        
        result = service.remove_member_extreme(
            group_id='grp_test123',
            user_id='test_user_456',
            group_data_from_cache=sample_group,
            requester_id='test_user_123'
        )
        
        # Verify batch was used
        mock_db['db'].batch.assert_called_once()
        mock_db['batch'].commit.assert_called_once()


# ============================================================================
# ExtremeExpenseService Tests
# ============================================================================

class TestExtremeExpenseService:
    """Tests for ExtremeExpenseService"""
    
    def test_create_expense_extreme_uses_batch(self, mock_db, mock_cache, sample_group):
        """Test create_expense_extreme uses single batch write"""
        from expense_engine.services.extreme_expense_service import ExtremeExpenseService
        
        service = ExtremeExpenseService()
        service._db = mock_db['db']
        service._cache = mock_cache
        
        expense_data = {
            'amount': 100.0,
            'description': 'Test Expense',
            'paid_by': 'test_user_123',
            'splits': [
                {'user_id': 'test_user_123', 'amount': 50.0},
                {'user_id': 'test_user_456', 'amount': 50.0}
            ],
            'category': 'food',
            'created_by': 'test_user_123'
        }
        
        result = service.create_expense_extreme(
            group_id='grp_test123',
            expense_data=expense_data,
            group_from_cache=sample_group
        )
        
        # Verify batch was used
        mock_db['db'].batch.assert_called_once()
        mock_db['batch'].commit.assert_called_once()
        
        # Verify result structure
        assert 'expense_id' in result
        assert result['amount'] == 100.0
    
    def test_update_expense_extreme_uses_batch(self, mock_db, mock_cache, sample_group, sample_expense):
        """Test update_expense_extreme uses single batch write"""
        from expense_engine.services.extreme_expense_service import ExtremeExpenseService
        
        service = ExtremeExpenseService()
        service._db = mock_db['db']
        service._cache = mock_cache
        
        result = service.update_expense_extreme(
            expense_id='exp_test123',
            updates={'amount': 150.0, 'description': 'Updated'},
            expense_from_cache=sample_expense,
            group_from_cache=sample_group
        )
        
        # Verify batch was used
        mock_db['db'].batch.assert_called_once()
        mock_db['batch'].commit.assert_called_once()
    
    def test_delete_expense_extreme_uses_batch(self, mock_db, mock_cache, sample_group, sample_expense):
        """Test delete_expense_extreme uses single batch write"""
        from expense_engine.services.extreme_expense_service import ExtremeExpenseService
        
        service = ExtremeExpenseService()
        service._db = mock_db['db']
        service._cache = mock_cache
        
        result = service.delete_expense_extreme(
            expense_id='exp_test123',
            expense_from_cache=sample_expense,
            group_from_cache=sample_group
        )
        
        # Verify batch was used
        mock_db['db'].batch.assert_called_once()
        mock_db['batch'].commit.assert_called_once()


# ============================================================================
# ExtremeSettlementService Tests
# ============================================================================

class TestExtremeSettlementService:
    """Tests for ExtremeSettlementService"""
    
    def test_create_settlement_extreme_uses_batch(self, mock_db, mock_cache, sample_group):
        """Test create_settlement_extreme uses single batch write"""
        from expense_engine.services.extreme_settlement_service import ExtremeSettlementService
        
        service = ExtremeSettlementService()
        service._db = mock_db['db']
        service._cache = mock_cache
        
        settlement_data = {
            'amount': 50.0,
            'payer_id': 'test_user_456',
            'payee_id': 'test_user_123',
            'created_by': 'test_user_456',
            'notes': 'Settling up'
        }
        
        result = service.create_settlement_extreme(
            group_id='grp_test123',
            settlement_data=settlement_data,
            group_from_cache=sample_group
        )
        
        # Verify batch was used
        mock_db['db'].batch.assert_called_once()
        mock_db['batch'].commit.assert_called_once()
        
        # Verify result structure
        assert 'settlement_id' in result
        assert result['amount'] == 50.0


# ============================================================================
# Integration Tests - Operation Count Verification
# ============================================================================

class TestOperationCounts:
    """Tests to verify operation counts match 10-op target"""
    
    def test_full_session_flow(self, mock_db, mock_cache, sample_dashboard):
        """Test a complete session achieves ~10 operations"""
        from expense_engine.services.extreme_dashboard_service import ExtremeDashboardService
        from expense_engine.services.extreme_group_service import ExtremeGroupService
        from expense_engine.services.extreme_expense_service import ExtremeExpenseService
        from expense_engine.services.extreme_settlement_service import ExtremeSettlementService
        
        # Track operation counts
        write_count = 0
        
        def track_commit():
            nonlocal write_count
            write_count += 1
        
        mock_db['batch'].commit.side_effect = track_commit
        
        # Setup cache hit for dashboard
        mock_cache.get.return_value = sample_dashboard
        
        # Initialize services
        dashboard_service = ExtremeDashboardService()
        dashboard_service._cache = mock_cache
        
        group_service = ExtremeGroupService()
        group_service._db = mock_db['db']
        group_service._cache = mock_cache
        
        expense_service = ExtremeExpenseService()
        expense_service._db = mock_db['db']
        expense_service._cache = mock_cache
        
        settlement_service = ExtremeSettlementService()
        settlement_service._db = mock_db['db']
        settlement_service._cache = mock_cache
        
        # Simulate session:
        # 1. Login - Get dashboard from cache (0 reads if cached)
        dashboard = dashboard_service.get_dashboard_from_cache('test_user_123')
        assert dashboard is not None
        
        # 2. Create group (0 reads, 1 write)
        group_service.create_group_extreme(
            user_id='test_user_123',
            name='Session Group',
            currency='USD'
        )
        
        # 3. Create expense (0 reads, 1 write)
        sample_group = sample_dashboard['groups']['grp_test123']
        expense_service.create_expense_extreme(
            group_id='grp_test123',
            expense_data={
                'amount': 100.0,
                'description': 'Test',
                'paid_by': 'test_user_123',
                'splits': [{'user_id': 'test_user_123', 'amount': 100.0}],
                'created_by': 'test_user_123'
            },
            group_from_cache=sample_group
        )
        
        # 4. Create settlement (0 reads, 1 write)
        settlement_service.create_settlement_extreme(
            group_id='grp_test123',
            settlement_data={
                'amount': 50.0,
                'payer_id': 'test_user_456',
                'payee_id': 'test_user_123',
                'created_by': 'test_user_456'
            },
            group_from_cache=sample_group
        )
        
        # Verify operation counts
        print(f"\nSession Summary:")
        print(f"  Writes: {write_count}")
        
        # Target: 0 reads from cache hit + N writes
        assert write_count == 3, f"Expected 3 writes, got {write_count}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
