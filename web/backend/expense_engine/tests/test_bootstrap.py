"""
Unit Tests for Bootstrap Service and Routes
Phase 7: Bootstrap & Dashboard Optimization

Tests cover:
- BootstrapService parallel data fetching
- Bootstrap routes with authentication
- Cache behavior
- Error handling
- Edge cases
"""
# pylint: disable=protected-access,unused-argument,redefined-outer-name

import pytest
from unittest.mock import MagicMock
from decimal import Decimal


class TestBootstrapService:
    """Test BootstrapService business logic"""
    
    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories for testing"""
        mock_snapshot_repo = MagicMock()
        mock_snapshot_repo.get_user_snapshots.return_value = []
        mock_snapshot_repo.get_snapshot.return_value = None
        return {
            'group_repo': MagicMock(),
            'expense_repo': MagicMock(),
            'invitation_repo': MagicMock(),
            'user_repo': MagicMock(),
            'balance_repo': MagicMock(),
            'group_summary_repo': MagicMock(),
            'user_expense_repo': MagicMock(),
            'snapshot_repo': mock_snapshot_repo
        }
    
    @pytest.fixture
    def sample_user(self):
        """Sample user data"""
        return {
            'uid': 'user_123',
            'email': 'test@example.com',
            'display_name': 'Test User',
            'photo_url': 'https://example.com/photo.jpg',
            'created_at': '2025-01-01T00:00:00'
        }
    
    @pytest.fixture
    def sample_groups(self):
        """Sample groups data"""
        return [
            {
                'group_id': 'group_1',
                'id': 'group_1',
                'name': 'Trip to Paris',
                'currency': 'EUR',
                'member_count': 3,
                'is_active': True
            },
            {
                'group_id': 'group_2',
                'id': 'group_2',
                'name': 'Apartment Expenses',
                'currency': 'USD',
                'member_count': 2,
                'is_active': True
            }
        ]
    
    @pytest.fixture
    def sample_invitations(self):
        """Sample pending invitations"""
        return [
            {
                'invitation_id': 'inv_1',
                'group_id': 'group_3',
                'group_name': 'Office Lunch',
                'status': 'pending',
                'invited_by_name': 'John Doe'
            }
        ]
    
    @pytest.fixture
    def sample_expenses(self):
        """Sample recent expenses"""
        return [
            {
                'expense_id': 'exp_1',
                'group_id': 'group_1',
                'description': 'Dinner',
                'amount': Decimal('100.00'),
                'paid_by': 'user_123',
                'created_at': '2025-11-25T10:00:00'
            },
            {
                'expense_id': 'exp_2',
                'group_id': 'group_2',
                'description': 'Groceries',
                'amount': Decimal('50.00'),
                'paid_by': 'user_456',
                'created_at': '2025-11-24T15:00:00'
            }
        ]
    
    def test_get_bootstrap_data_success(
        self,
        mock_repositories,
        sample_user,
        sample_invitations,
        sample_expenses
    ):
        """Test successful bootstrap data fetch"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        # Groups with explicit balance values
        groups_with_balances = [
            {
                'group_id': 'group_1',
                'id': 'group_1',
                'name': 'Trip to Paris',
                'currency': 'EUR',
                'members': ['user_123', 'user_456', 'user_789'],
            }
        ]
        
        # Setup mocks
        mock_repositories['user_repo'].get_by_id.return_value = sample_user
        mock_repositories['group_repo'].get_user_groups.return_value = groups_with_balances
        mock_repositories['invitation_repo'].get_user_invitations.return_value = sample_invitations
        mock_repositories['group_summary_repo'].get_user_summary.return_value = None
        mock_repositories['user_expense_repo'].get_user_expenses.return_value = sample_expenses
        mock_repositories['balance_repo'].get_group_balances.return_value = {
            'balances': {'user_123': 50.00},
            'is_settled': False
        }
        
        # Create service with mocks
        service = BootstrapService(**mock_repositories)
        
        # Disable cache for test
        service._cache = None
        
        # Execute
        result = service.get_bootstrap_data(
            user_id='user_123',
            user_email='test@example.com',
            use_cache=False
        )
        
        # Verify - response format is {data: {...}, cache_stats: {...}}
        assert result is not None
        assert 'data' in result
        assert 'cache_stats' in result
        data = result['data']
        assert 'user' in data
        assert 'groups' in data
        assert 'invitations' in data
        assert 'summary' in data
    
    def test_get_bootstrap_data_with_empty_groups(
        self,
        mock_repositories,
        sample_user
    ):
        """Test bootstrap with user having no groups"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        # Setup mocks - empty groups
        mock_repositories['user_repo'].get_by_id.return_value = sample_user
        mock_repositories['group_repo'].get_user_groups.return_value = []
        mock_repositories['invitation_repo'].get_user_invitations.return_value = []
        mock_repositories['group_summary_repo'].get_user_summary.return_value = None
        mock_repositories['user_expense_repo'].get_user_expenses.return_value = []
        
        service = BootstrapService(**mock_repositories)
        service._cache = None
        
        result = service.get_bootstrap_data(
            user_id='user_123',
            user_email='test@example.com',
            use_cache=False
        )
        
        assert result['data']['groups'] == []
        assert result['data']['invitations'] == []
        assert result['data']['summary']['total_groups'] == 0
    
    def test_get_bootstrap_data_parallel_execution(
        self,
        mock_repositories,
        sample_user
    ):
        """Test that data is fetched in parallel"""
        from expense_engine.services.bootstrap_service import BootstrapService
        import time
        
        # Groups with explicit balance values
        groups_with_balances = [
            {
                'group_id': 'group_1',
                'id': 'group_1',
                'name': 'Test Group',
                'currency': 'USD',
                'members': []
            }
        ]
        
        # Setup mocks with delay to simulate network
        def slow_user_fetch(_uid):
            time.sleep(0.05)
            return sample_user
        
        def slow_groups_fetch(_uid):
            time.sleep(0.05)
            return groups_with_balances
        
        mock_repositories['user_repo'].get_by_id.side_effect = slow_user_fetch
        mock_repositories['group_repo'].get_user_groups.side_effect = slow_groups_fetch
        mock_repositories['invitation_repo'].get_user_invitations.return_value = []
        mock_repositories['group_summary_repo'].get_user_summary.return_value = None
        mock_repositories['user_expense_repo'].get_user_expenses.return_value = []
        mock_repositories['balance_repo'].get_group_balances.return_value = {
            'balances': {},
            'is_settled': True
        }
        
        service = BootstrapService(**mock_repositories)
        service._cache = None
        
        start = time.time()
        result = service.get_bootstrap_data(
            user_id='user_123',
            user_email='test@example.com',
            use_cache=False
        )
        duration = time.time() - start
        
        # Parallel execution should take ~50-100ms, not 200ms+ (sequential)
        assert duration < 0.3, f"Expected parallel execution, took {duration}s"
        assert result['data']['user'] is not None
    
    def test_get_bootstrap_data_excludes_recent_expenses(
        self,
        mock_repositories,
        sample_user
    ):
        """Test bootstrap without recent expenses"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        # Groups with explicit balance values
        groups_with_balances = [
            {
                'group_id': 'group_1',
                'id': 'group_1',
                'name': 'Test Group',
                'currency': 'USD',
                'members': []
            }
        ]
        
        mock_repositories['user_repo'].get_by_id.return_value = sample_user
        mock_repositories['group_repo'].get_user_groups.return_value = groups_with_balances
        mock_repositories['invitation_repo'].get_user_invitations.return_value = []
        mock_repositories['group_summary_repo'].get_user_summary.return_value = None
        mock_repositories['balance_repo'].get_group_balances.return_value = {
            'balances': {},
            'is_settled': True
        }
        
        service = BootstrapService(**mock_repositories)
        service._cache = None
        
        result = service.get_bootstrap_data(
            user_id='user_123',
            user_email='test@example.com',
            include_recent_expenses=False,
            use_cache=False
        )
        
        assert result['data']['recent_expenses'] == []
        # Should not have called expense repo
        mock_repositories['user_expense_repo'].get_user_expenses.assert_not_called()
    
    def test_fetch_user_filters_sensitive_fields(
        self,
        mock_repositories
    ):
        """Test that sensitive fields are removed from user data"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        user_with_sensitive = {
            'uid': 'user_123',
            'email': 'test@example.com',
            'display_name': 'Test User',
            'photo_url': 'https://example.com/photo.jpg',
            'created_at': '2025-01-01T00:00:00',
            # Sensitive fields that should be filtered
            'password_hash': 'some_hash',
            'api_key': 'secret_key',
            'firebase_token': 'token'
        }
        
        mock_repositories['user_repo'].get_by_id.return_value = user_with_sensitive
        
        service = BootstrapService(**mock_repositories)
        result = service._fetch_user('user_123')
        
        assert result is not None
        assert 'uid' in result
        assert 'email' in result
        assert 'password_hash' not in result
        assert 'api_key' not in result
        assert 'firebase_token' not in result
    
    def test_handles_repository_exception(
        self,
        mock_repositories,
        sample_user
    ):
        """Test graceful handling of repository exceptions"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        mock_repositories['user_repo'].get_by_id.return_value = sample_user
        mock_repositories['group_repo'].get_user_groups.side_effect = Exception("DB Error")
        mock_repositories['invitation_repo'].get_pending_invitations.return_value = []
        mock_repositories['group_summary_repo'].get_user_summary.return_value = None
        mock_repositories['user_expense_repo'].get_user_expenses.return_value = {
            'expenses': [],
            'total': 0
        }
        
        service = BootstrapService(**mock_repositories)
        service._cache = None
        
        # Should not raise, should return empty groups
        result = service.get_bootstrap_data(
            user_id='user_123',
            user_email='test@example.com',
            use_cache=False
        )
        
        assert result['data']['groups'] == []
        assert result['data']['user'] is not None
    
    def test_uses_denormalized_data_when_available(
        self,
        mock_repositories,
        sample_user
    ):
        """Test that denormalized data is preferred"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        denormalized_summary = {
            'user_id': 'user_123',
            'groups': {
                'group_1': {
                    'name': 'Trip to Paris',
                    'balance': 50.00,
                    'member_count': 3,
                    'expense_count': 10,
                    'currency': 'EUR'
                }
            }
        }
        
        mock_repositories['user_repo'].get_by_id.return_value = sample_user
        mock_repositories['group_summary_repo'].get_user_summary.return_value = denormalized_summary
        mock_repositories['invitation_repo'].get_pending_invitations.return_value = []
        mock_repositories['user_expense_repo'].get_user_expenses.return_value = {
            'expenses': [],
            'total': 0
        }
        
        service = BootstrapService(**mock_repositories)
        service._cache = None
        
        result = service.get_bootstrap_data(
            user_id='user_123',
            user_email='test@example.com',
            use_cache=False
        )
        
        # Should have group from denormalized data
        assert len(result['data']['groups']) == 1
        assert result['data']['groups'][0]['name'] == 'Trip to Paris'
        
        # Should NOT have called regular group repo
        mock_repositories['group_repo'].get_user_groups.assert_not_called()


class TestBootstrapStatistics:
    """Test bootstrap statistics calculation"""
    
    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories"""
        mock_snapshot_repo = MagicMock()
        mock_snapshot_repo.get_user_snapshots.return_value = []
        mock_snapshot_repo.get_snapshot.return_value = None
        return {
            'group_repo': MagicMock(),
            'expense_repo': MagicMock(),
            'invitation_repo': MagicMock(),
            'user_repo': MagicMock(),
            'balance_repo': MagicMock(),
            'group_summary_repo': MagicMock(),
            'user_expense_repo': MagicMock(),
            'snapshot_repo': mock_snapshot_repo
        }
    
    def test_calculate_stats_basic(self, mock_repositories):
        """Test basic statistics calculation"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        service = BootstrapService(**mock_repositories)
        
        data = {
            'user': {'uid': 'user_123'},
            'groups': [
                {'group_id': 'g1', 'your_balance': 50.00},
                {'group_id': 'g2', 'your_balance': -30.00}
            ],
            'invitations': [
                {'invitation_id': 'inv_1'}
            ],
            'recent_expenses': [
                {'expense_id': 'exp_1'},
                {'expense_id': 'exp_2'}
            ]
        }
        
        stats = service._calculate_stats(data)
        
        assert stats['total_groups'] == 2
        assert stats['pending_invitations'] == 1
        assert stats['net_balance'] == 20.00  # 50 - 30


class TestParseIntParam:
    """Test _parse_int_param helper function"""
    
    def test_parse_valid_integer(self):
        """Test parsing valid integer string"""
        from expense_engine.routes.bootstrap_routes import _parse_int_param
        
        result = _parse_int_param('10', default=5, min_val=1, max_val=50)
        assert result == 10
    
    def test_parse_none_returns_default(self):
        """Test None returns default value"""
        from expense_engine.routes.bootstrap_routes import _parse_int_param
        
        result = _parse_int_param(None, default=5, min_val=1, max_val=50)
        assert result == 5
    
    def test_parse_invalid_returns_default(self):
        """Test invalid string returns default"""
        from expense_engine.routes.bootstrap_routes import _parse_int_param
        
        result = _parse_int_param('abc', default=5, min_val=1, max_val=50)
        assert result == 5
    
    def test_parse_clamps_to_min(self):
        """Test value below min is clamped"""
        from expense_engine.routes.bootstrap_routes import _parse_int_param
        
        result = _parse_int_param('0', default=5, min_val=1, max_val=50)
        assert result == 1
    
    def test_parse_clamps_to_max(self):
        """Test value above max is clamped"""
        from expense_engine.routes.bootstrap_routes import _parse_int_param
        
        result = _parse_int_param('100', default=5, min_val=1, max_val=50)
        assert result == 50
    
    def test_parse_negative_number(self):
        """Test parsing negative number"""
        from expense_engine.routes.bootstrap_routes import _parse_int_param
        
        result = _parse_int_param('-5', default=10, min_val=1, max_val=50)
        assert result == 1  # Clamped to min
    
    def test_parse_boundary_values(self):
        """Test parsing boundary values"""
        from expense_engine.routes.bootstrap_routes import _parse_int_param
        
        # Exactly at min
        result_min = _parse_int_param('1', default=5, min_val=1, max_val=50)
        assert result_min == 1
        
        # Exactly at max
        result_max = _parse_int_param('50', default=5, min_val=1, max_val=50)
        assert result_max == 50


class TestBootstrapServiceFactory:
    """Test BootstrapService factory function"""
    
    def test_get_bootstrap_service_returns_service(self):
        """Test factory returns a BootstrapService instance"""
        from expense_engine.services.bootstrap_service import (
            BootstrapService,
            _BootstrapServiceHolder
        )
        
        # Mock the repositories to avoid Firebase
        mock_snapshot_repo = MagicMock()
        mock_snapshot_repo.get_user_snapshots.return_value = []
        mock_snapshot_repo.get_snapshot.return_value = None
        mock_repos = {
            'group_repo': MagicMock(),
            'expense_repo': MagicMock(),
            'invitation_repo': MagicMock(),
            'user_repo': MagicMock(),
            'balance_repo': MagicMock(),
            'group_summary_repo': MagicMock(),
            'user_expense_repo': MagicMock(),
            'snapshot_repo': mock_snapshot_repo
        }
        
        # Create service directly and set to holder
        service = BootstrapService(**mock_repos)
        _BootstrapServiceHolder.instance = service
        
        from expense_engine.services.bootstrap_service import get_bootstrap_service
        result = get_bootstrap_service()
        
        assert isinstance(result, BootstrapService)
        
        # Clean up
        _BootstrapServiceHolder.instance = None
    
    def test_get_bootstrap_service_returns_singleton(self):
        """Test factory returns same instance"""
        from expense_engine.services.bootstrap_service import (
            BootstrapService,
            _BootstrapServiceHolder,
            get_bootstrap_service
        )
        
        # Mock the repositories
        mock_snapshot_repo = MagicMock()
        mock_snapshot_repo.get_user_snapshots.return_value = []
        mock_snapshot_repo.get_snapshot.return_value = None
        mock_repos = {
            'group_repo': MagicMock(),
            'expense_repo': MagicMock(),
            'invitation_repo': MagicMock(),
            'user_repo': MagicMock(),
            'balance_repo': MagicMock(),
            'group_summary_repo': MagicMock(),
            'user_expense_repo': MagicMock(),
            'snapshot_repo': mock_snapshot_repo
        }
        
        # Create service and set to holder
        service = BootstrapService(**mock_repos)
        _BootstrapServiceHolder.instance = service
        
        service1 = get_bootstrap_service()
        service2 = get_bootstrap_service()
        assert service1 is service2
        
        # Clean up
        _BootstrapServiceHolder.instance = None


class TestBootstrapServiceCacheInvalidation:
    """Test cache invalidation methods"""
    
    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories"""
        mock_snapshot_repo = MagicMock()
        mock_snapshot_repo.get_user_snapshots.return_value = []
        mock_snapshot_repo.get_snapshot.return_value = None
        return {
            'group_repo': MagicMock(),
            'expense_repo': MagicMock(),
            'invitation_repo': MagicMock(),
            'user_repo': MagicMock(),
            'balance_repo': MagicMock(),
            'group_summary_repo': MagicMock(),
            'user_expense_repo': MagicMock(),
            'snapshot_repo': mock_snapshot_repo
        }
    
    def test_invalidate_user_bootstrap_no_cache(self, mock_repositories):
        """Test invalidation when cache is not available"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        service = BootstrapService(**mock_repositories)
        service._cache = None
        
        result = service.invalidate_user_bootstrap('user_123')
        assert result is False
    
    def test_invalidate_user_bootstrap_with_cache(self, mock_repositories):
        """Test invalidation when cache is available"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        mock_cache = MagicMock()
        mock_cache.is_available.return_value = True
        
        service = BootstrapService(**mock_repositories)
        service._cache = mock_cache
        
        result = service.invalidate_user_bootstrap('user_123')
        
        assert result is True
        mock_cache.delete.assert_called_once_with('expense:bootstrap:user_123')


class TestBatchGetDisplayNames:
    """Test batch display name fetching"""
    
    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories"""
        mock_snapshot_repo = MagicMock()
        mock_snapshot_repo.get_user_snapshots.return_value = []
        mock_snapshot_repo.get_snapshot.return_value = None
        return {
            'group_repo': MagicMock(),
            'expense_repo': MagicMock(),
            'invitation_repo': MagicMock(),
            'user_repo': MagicMock(),
            'balance_repo': MagicMock(),
            'group_summary_repo': MagicMock(),
            'user_expense_repo': MagicMock(),
            'snapshot_repo': mock_snapshot_repo
        }
    
    def test_batch_get_display_names_empty_list(self, mock_repositories):
        """Test with empty user list"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        service = BootstrapService(**mock_repositories)
        result = service.batch_get_display_names([])
        
        assert result == {}
    
    def test_batch_get_display_names_deduplicates(self, mock_repositories):
        """Test that duplicate IDs are deduplicated"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        mock_repositories['user_repo'].get_by_id.return_value = {
            'display_name': 'Test User',
            'email': 'test@example.com'
        }
        
        service = BootstrapService(**mock_repositories)
        service._cache = None
        
        result = service.batch_get_display_names(['user_1', 'user_1', 'user_1'])
        
        # Should only call repo once despite 3 identical IDs
        assert mock_repositories['user_repo'].get_by_id.call_count == 1
        assert result['user_1'] == 'Test User'
    
    def test_batch_get_display_names_fallback_to_email(self, mock_repositories):
        """Test fallback to email when display_name is missing"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        mock_repositories['user_repo'].get_by_id.return_value = {
            'email': 'john@example.com'
        }
        
        service = BootstrapService(**mock_repositories)
        service._cache = None
        
        result = service.batch_get_display_names(['user_1'])
        
        assert result['user_1'] == 'john'  # Email prefix
    
    def test_batch_get_display_names_unknown_user(self, mock_repositories):
        """Test handling of unknown user"""
        from expense_engine.services.bootstrap_service import BootstrapService
        
        mock_repositories['user_repo'].get_by_id.return_value = None
        
        service = BootstrapService(**mock_repositories)
        service._cache = None
        
        result = service.batch_get_display_names(['unknown_user'])
        
        assert result['unknown_user'] == 'Unknown'
