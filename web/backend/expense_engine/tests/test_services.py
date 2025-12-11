"""
Unit Tests for Expense Engine Services
Tests for business logic layer with mocked repositories
"""

# pylint: disable=unused-argument,unused-variable,protected-access

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import datetime


# =============================================================================
# BALANCE SERVICE TESTS (Pure logic, no Firebase)
# =============================================================================

class TestBalanceService:
    """Test BalanceService calculations - pure logic tests"""
    
    def test_calculate_expense_deltas_equal_split(self):
        """Test delta calculation for equal split"""
        from expense_engine.services.balance_service import BalanceService
        from expense_engine.models.expense import Expense, ExpenseSplit
        
        service = BalanceService(
            balance_repo=MagicMock(),
            expense_repo=MagicMock()
        )
        
        # User1 pays 100, split equally between user1 and user2
        expense = Expense(
            group_id='group_1',
            description='Dinner',
            amount=Decimal('100.00'),
            paid_by='user_1',
            split_type='equal',
            splits=[
                ExpenseSplit(user_id='user_1', amount=Decimal('50.00')),
                ExpenseSplit(user_id='user_2', amount=Decimal('50.00'))
            ],
            created_by='user_1'
        )
        
        deltas = service.calculate_expense_deltas(expense)
        
        # user_1: paid 100, owes 50 = net +50
        # user_2: paid 0, owes 50 = net -50
        assert deltas['user_1'] == Decimal('50.00')
        assert deltas['user_2'] == Decimal('-50.00')
    
    def test_calculate_expense_deltas_unequal_split(self):
        """Test delta with unequal amounts"""
        from expense_engine.services.balance_service import BalanceService
        from expense_engine.models.expense import Expense, ExpenseSplit
        
        service = BalanceService(
            balance_repo=MagicMock(),
            expense_repo=MagicMock()
        )
        
        # User1 pays 100, split: user1=10, user2=40, user3=50
        expense = Expense(
            group_id='group_1',
            description='Dinner',
            amount=Decimal('100.00'),
            paid_by='user_1',
            split_type='exact',
            splits=[
                ExpenseSplit(user_id='user_1', amount=Decimal('10.00')),
                ExpenseSplit(user_id='user_2', amount=Decimal('40.00')),
                ExpenseSplit(user_id='user_3', amount=Decimal('50.00'))
            ],
            created_by='user_1'
        )
        
        deltas = service.calculate_expense_deltas(expense)
        
        # user_1: paid 100, owes 10 = net +90
        # user_2: paid 0, owes 40 = net -40
        # user_3: paid 0, owes 50 = net -50
        assert deltas['user_1'] == Decimal('90.00')
        assert deltas['user_2'] == Decimal('-40.00')
        assert deltas['user_3'] == Decimal('-50.00')
    
    def test_calculate_expense_deltas_single_user(self):
        """Test delta when single user pays for themselves"""
        from expense_engine.services.balance_service import BalanceService
        from expense_engine.models.expense import Expense, ExpenseSplit
        
        service = BalanceService(
            balance_repo=MagicMock(),
            expense_repo=MagicMock()
        )
        
        # User1 pays 100 for themselves
        expense = Expense(
            group_id='group_1',
            description='Personal',
            amount=Decimal('100.00'),
            paid_by='user_1',
            split_type='exact',
            splits=[
                ExpenseSplit(user_id='user_1', amount=Decimal('100.00'))
            ],
            created_by='user_1'
        )
        
        deltas = service.calculate_expense_deltas(expense)
        
        # user_1: paid 100, owes 100 = net 0
        assert deltas['user_1'] == Decimal('0.00')
    
    def test_calculate_expense_deltas_three_way_split(self):
        """Test delta for three-way split"""
        from expense_engine.services.balance_service import BalanceService
        from expense_engine.models.expense import Expense, ExpenseSplit
        
        service = BalanceService(
            balance_repo=MagicMock(),
            expense_repo=MagicMock()
        )
        
        # User1 pays 90, split three ways
        expense = Expense(
            group_id='group_1',
            description='Lunch',
            amount=Decimal('90.00'),
            paid_by='user_1',
            split_type='equal',
            splits=[
                ExpenseSplit(user_id='user_1', amount=Decimal('30.00')),
                ExpenseSplit(user_id='user_2', amount=Decimal('30.00')),
                ExpenseSplit(user_id='user_3', amount=Decimal('30.00'))
            ],
            created_by='user_1'
        )
        
        deltas = service.calculate_expense_deltas(expense)
        
        assert deltas['user_1'] == Decimal('60.00')  # paid 90, owes 30
        assert deltas['user_2'] == Decimal('-30.00')
        assert deltas['user_3'] == Decimal('-30.00')
    
    def test_is_group_settled_delegates_to_repo(self):
        """Test is_group_settled calls repository"""
        from expense_engine.services.balance_service import BalanceService
        
        mock_repo = MagicMock()
        mock_repo.is_group_settled.return_value = True
        
        service = BalanceService(balance_repo=mock_repo, expense_repo=MagicMock())
        result = service.is_group_settled('group_1')
        
        assert result is True
        mock_repo.is_group_settled.assert_called_once_with('group_1')


# =============================================================================
# EXPENSE SERVICE TESTS
# =============================================================================

class TestExpenseService:
    """Test ExpenseService business logic"""
    
    def test_create_expense_validates_group_exists(self):
        """Test that expense creation requires valid group"""
        from expense_engine.services.expense_service import ExpenseService
        from expense_engine.exceptions import ResourceNotFoundError
        
        mock_expense_repo = MagicMock()
        mock_group_repo = MagicMock()
        mock_balance_repo = MagicMock()
        mock_group_summary_repo = MagicMock()
        mock_user_expense_repo = MagicMock()
        mock_history_repo = MagicMock()
        
        # Mock group not found
        mock_group_repo.get_by_id.return_value = None
        
        service = ExpenseService(
            expense_repo=mock_expense_repo,
            group_repo=mock_group_repo,
            balance_repo=mock_balance_repo,
            group_summary_repo=mock_group_summary_repo,
            user_expense_repo=mock_user_expense_repo,
            history_repo=mock_history_repo
        )
        
        with pytest.raises(ResourceNotFoundError):
            service.create_expense(
                group_id='nonexistent_group',
                description='Test',
                amount=Decimal('100.00'),
                paid_by='user_123',
                split_type='equal',
                splits=[],
                created_by='user_123'
            )
    
    def test_create_expense_validates_payer_membership(self):
        """Test that payer must be group member"""
        from expense_engine.services.expense_service import ExpenseService
        from expense_engine.exceptions import ValidationError
        
        mock_expense_repo = MagicMock()
        mock_group_repo = MagicMock()
        mock_balance_repo = MagicMock()
        mock_group_summary_repo = MagicMock()
        mock_user_expense_repo = MagicMock()
        mock_history_repo = MagicMock()
        
        # Mock group exists but payer not a member
        mock_group_repo.get_by_id.return_value = {
            'group_id': 'group_123',
            'members': ['user_456']  # user_123 not in members
        }
        
        service = ExpenseService(
            expense_repo=mock_expense_repo,
            group_repo=mock_group_repo,
            balance_repo=mock_balance_repo,
            group_summary_repo=mock_group_summary_repo,
            user_expense_repo=mock_user_expense_repo,
            history_repo=mock_history_repo
        )
        
        with pytest.raises(ValidationError):
            service.create_expense(
                group_id='group_123',
                description='Test',
                amount=Decimal('100.00'),
                paid_by='user_123',  # Not a member
                split_type='equal',
                splits=[{'user_id': 'user_456', 'amount': '100.00'}],
                created_by='user_123'
            )
    
    def test_create_expense_validates_split_users_are_members(self):
        """Test that all split users must be members"""
        from expense_engine.services.expense_service import ExpenseService
        from expense_engine.exceptions import ValidationError
        
        mock_expense_repo = MagicMock()
        mock_group_repo = MagicMock()
        mock_balance_repo = MagicMock()
        mock_group_summary_repo = MagicMock()
        mock_user_expense_repo = MagicMock()
        mock_history_repo = MagicMock()
        
        # Mock group with only user_1 as member
        mock_group_repo.get_by_id.return_value = {
            'group_id': 'group_123',
            'members': ['user_1']
        }
        
        service = ExpenseService(
            expense_repo=mock_expense_repo,
            group_repo=mock_group_repo,
            balance_repo=mock_balance_repo,
            group_summary_repo=mock_group_summary_repo,
            user_expense_repo=mock_user_expense_repo,
            history_repo=mock_history_repo
        )
        
        with pytest.raises(ValidationError):
            service.create_expense(
                group_id='group_123',
                description='Test',
                amount=Decimal('100.00'),
                paid_by='user_1',
                split_type='equal',
                splits=[
                    {'user_id': 'user_1', 'amount': '50.00'},
                    {'user_id': 'user_999', 'amount': '50.00'}  # Not a member
                ],
                created_by='user_1'
            )
    
    def test_get_expense_returns_expense(self):
        """Test get_expense returns expense data (cache may be used)"""
        from expense_engine.services.expense_service import ExpenseService
        
        mock_expense_repo = MagicMock()
        mock_group_repo = MagicMock()
        mock_balance_repo = MagicMock()
        mock_group_summary_repo = MagicMock()
        mock_user_expense_repo = MagicMock()
        mock_history_repo = MagicMock()
        
        expected_expense = {
            'expense_id': 'exp_123',
            'description': 'Test',
            'amount': 100.0
        }
        mock_expense_repo.get_by_id.return_value = expected_expense
        
        service = ExpenseService(
            expense_repo=mock_expense_repo,
            group_repo=mock_group_repo,
            balance_repo=mock_balance_repo,
            group_summary_repo=mock_group_summary_repo,
            user_expense_repo=mock_user_expense_repo,
            history_repo=mock_history_repo
        )
        
        result = service.get_expense('exp_123')
        
        # Result should match expected (from cache or repo)
        assert result == expected_expense
        # Note: With Phase 13 caching, get_by_id may not be called if cache hits
        # The important thing is that correct data is returned
    
    def test_get_group_expenses_with_pagination(self):
        """Test get_group_expenses passes pagination params"""
        from expense_engine.services.expense_service import ExpenseService
        
        mock_expense_repo = MagicMock()
        mock_group_repo = MagicMock()
        mock_balance_repo = MagicMock()
        mock_group_summary_repo = MagicMock()
        mock_user_expense_repo = MagicMock()
        mock_history_repo = MagicMock()
        
        mock_expense_repo.get_group_expenses.return_value = {
            'expenses': [],
            'total': 0,
            'has_more': False
        }
        
        service = ExpenseService(
            expense_repo=mock_expense_repo,
            group_repo=mock_group_repo,
            balance_repo=mock_balance_repo,
            group_summary_repo=mock_group_summary_repo,
            user_expense_repo=mock_user_expense_repo,
            history_repo=mock_history_repo
        )
        
        service.get_group_expenses('group_1', limit=20, offset=10)
        
        mock_expense_repo.get_group_expenses.assert_called_once_with(
            'group_1', limit=20, offset=10, include_deleted=False
        )


# =============================================================================
# GROUP SERVICE TESTS
# =============================================================================

class TestGroupService:
    """Test GroupService business logic"""
    
    def test_generate_group_code_format(self):
        """Test that group code has correct format"""
        from expense_engine.services.group_service import GroupService
        
        service = GroupService(
            group_repo=MagicMock(),
            balance_repo=MagicMock()
        )
        
        code = service._generate_group_code()
        
        # Should be 8 uppercase alphanumeric characters
        assert len(code) == 8
        assert code.isupper()
        assert code.isalnum()
    
    def test_get_group_raises_not_found(self):
        """Test get_group raises error for missing group"""
        from expense_engine.services.group_service import GroupService
        from expense_engine.exceptions import ResourceNotFoundError
        
        mock_group_repo = MagicMock()
        mock_group_repo.get_by_id.return_value = None
        
        service = GroupService(
            group_repo=mock_group_repo,
            balance_repo=MagicMock()
        )
        
        with pytest.raises(ResourceNotFoundError):
            service.get_group('nonexistent')
    
    def test_get_group_returns_data(self):
        """Test get_group returns group data"""
        from expense_engine.services.group_service import GroupService
        
        mock_group_repo = MagicMock()
        expected_group = {
            'group_id': 'group_1',
            'name': 'Test Group'
        }
        mock_group_repo.get_by_id.return_value = expected_group
        
        service = GroupService(
            group_repo=mock_group_repo,
            balance_repo=MagicMock()
        )
        
        result = service.get_group('group_1')
        
        assert result == expected_group
    
    @patch('expense_engine.services.group_service.get_cache_manager')
    @patch('expense_engine.services.group_service.CACHE_ENABLED', False)
    def test_get_user_groups_returns_list(self, mock_cache):
        """Test get_user_groups returns groups list"""
        from expense_engine.services.group_service import GroupService
        
        mock_group_repo = MagicMock()
        expected_groups = [
            {'group_id': 'group_1', 'name': 'Group 1'},
            {'group_id': 'group_2', 'name': 'Group 2'}
        ]
        mock_group_repo.get_user_groups.return_value = expected_groups
        
        service = GroupService(
            group_repo=mock_group_repo,
            balance_repo=MagicMock()
        )
        
        result = service.get_user_groups('user_1')
        
        assert result == expected_groups
        mock_group_repo.get_user_groups.assert_called_once_with('user_1')


# =============================================================================
# SETTLEMENT SERVICE TESTS
# =============================================================================

class TestSettlementService:
    """Test SettlementService business logic"""
    
    @patch('expense_engine.services.settlement_service.BalanceService')
    def test_create_settlement_validates_group_exists(self, mock_balance_service_class):
        """Test settlement creation requires valid group"""
        from expense_engine.services.settlement_service import SettlementService
        from expense_engine.exceptions import ResourceNotFoundError
        
        mock_settlement_repo = MagicMock()
        mock_group_repo = MagicMock()
        mock_balance_repo = MagicMock()
        
        mock_group_repo.get_by_id.return_value = None
        
        service = SettlementService(
            settlement_repo=mock_settlement_repo,
            group_repo=mock_group_repo,
            balance_repo=mock_balance_repo
        )
        
        with pytest.raises(ResourceNotFoundError):
            service.create_settlement(
                group_id='nonexistent',
                payer_id='user_1',
                receiver_id='user_2',
                amount=Decimal('50.00'),
                created_by='user_1'
            )
    
    @patch('expense_engine.services.settlement_service.BalanceService')
    def test_create_settlement_validates_payer_membership(self, mock_balance_service_class):
        """Test payer must be group member"""
        from expense_engine.services.settlement_service import SettlementService
        from expense_engine.exceptions import ValidationError
        
        mock_settlement_repo = MagicMock()
        mock_group_repo = MagicMock()
        mock_balance_repo = MagicMock()
        
        # Group exists
        mock_group_repo.get_by_id.return_value = {
            'group_id': 'group_1',
            'members': ['user_2']  # user_1 not a member
        }
        # get_member returns None for non-member
        mock_group_repo.get_member.return_value = None
        
        service = SettlementService(
            settlement_repo=mock_settlement_repo,
            group_repo=mock_group_repo,
            balance_repo=mock_balance_repo
        )
        
        with pytest.raises(ValidationError):
            service.create_settlement(
                group_id='group_1',
                payer_id='user_1',
                receiver_id='user_2',
                amount=Decimal('50.00'),
                created_by='user_1'
            )
    
    @patch('expense_engine.services.settlement_service.BalanceService')
    def test_create_settlement_validates_positive_amount(self, mock_balance_service_class):
        """Test settlement amount must be positive"""
        from expense_engine.services.settlement_service import SettlementService
        from expense_engine.exceptions import ValidationError
        
        mock_settlement_repo = MagicMock()
        mock_group_repo = MagicMock()
        mock_balance_repo = MagicMock()
        
        mock_group_repo.get_by_id.return_value = {
            'group_id': 'group_1',
            'members': ['user_1', 'user_2']
        }
        
        service = SettlementService(
            settlement_repo=mock_settlement_repo,
            group_repo=mock_group_repo,
            balance_repo=mock_balance_repo
        )
        
        with pytest.raises(ValidationError):
            service.create_settlement(
                group_id='group_1',
                payer_id='user_1',
                receiver_id='user_2',
                amount=Decimal('-50.00'),
                created_by='user_1'
            )
    
    @patch('expense_engine.services.settlement_service.BalanceService')
    def test_get_settlement_returns_data(self, mock_balance_service_class):
        """Test get_settlement returns settlement"""
        from expense_engine.services.settlement_service import SettlementService
        
        mock_settlement_repo = MagicMock()
        expected = {'settlement_id': 'set_1', 'amount': 50.0}
        mock_settlement_repo.get_by_id.return_value = expected
        
        service = SettlementService(
            settlement_repo=mock_settlement_repo,
            group_repo=MagicMock(),
            balance_repo=MagicMock()
        )
        
        result = service.get_settlement('set_1')
        assert result == expected


# =============================================================================
# INVITATION SERVICE TESTS
# =============================================================================

class TestInvitationService:
    """Test InvitationService business logic"""
    
    def test_create_invitation_validates_group_exists(self):
        """Test invitation creation requires valid group"""
        from expense_engine.services.invitation_service import InvitationService
        from expense_engine.exceptions import ResourceNotFoundError
        
        mock_invitation_repo = MagicMock()
        mock_group_repo = MagicMock()
        
        mock_group_repo.get_by_id.return_value = None
        
        service = InvitationService(
            invitation_repo=mock_invitation_repo,
            group_repo=mock_group_repo
        )
        
        with pytest.raises(ResourceNotFoundError):
            service.create_invitation(
                group_id='nonexistent',
                invitee_email='test@example.com',
                invited_by='user_1'
            )
    
    def test_create_invitation_validates_role(self):
        """Test invitation role must be valid"""
        from expense_engine.services.invitation_service import InvitationService
        from expense_engine.exceptions import ValidationError
        
        mock_invitation_repo = MagicMock()
        mock_group_repo = MagicMock()
        
        mock_group_repo.get_by_id.return_value = {
            'group_id': 'group_1',
            'members': ['user_1']
        }
        mock_invitation_repo.get_pending_invitations.return_value = []
        
        service = InvitationService(
            invitation_repo=mock_invitation_repo,
            group_repo=mock_group_repo
        )
        
        with pytest.raises(ValidationError):
            service.create_invitation(
                group_id='group_1',
                invitee_email='test@example.com',
                invited_by='user_1',
                role='invalid_role'
            )
    
    def test_create_invitation_prevents_duplicate(self):
        """Test cannot create duplicate invitation"""
        from expense_engine.services.invitation_service import InvitationService
        from expense_engine.exceptions import ValidationError
        
        mock_invitation_repo = MagicMock()
        mock_group_repo = MagicMock()
        
        mock_group_repo.get_by_id.return_value = {
            'group_id': 'group_1',
            'members': ['user_1']
        }
        # Existing invitation found
        mock_invitation_repo.get_pending_invitations.return_value = [
            {'invitation_id': 'inv_1', 'email': 'test@example.com'}
        ]
        
        service = InvitationService(
            invitation_repo=mock_invitation_repo,
            group_repo=mock_group_repo
        )
        
        with pytest.raises(ValidationError):
            service.create_invitation(
                group_id='group_1',
                invitee_email='test@example.com',
                invited_by='user_1'
            )
    
    def test_get_invitation_returns_data(self):
        """Test get_invitation returns invitation"""
        from expense_engine.services.invitation_service import InvitationService
        
        mock_invitation_repo = MagicMock()
        expected = {'invitation_id': 'inv_1', 'email': 'test@example.com'}
        mock_invitation_repo.get_by_id.return_value = expected
        
        service = InvitationService(
            invitation_repo=mock_invitation_repo,
            group_repo=MagicMock()
        )
        
        result = service.get_invitation('inv_1')
        assert result == expected


# =============================================================================
# PHASE 17: ENHANCED MUTATION TESTS
# Tests for *_with_deltas methods that return balance deltas + history
# =============================================================================

class TestExpenseServicePhase17:
    """Test Phase 17 enhanced mutation methods with balance deltas"""
    
    @pytest.fixture
    def mock_repos(self):
        """Create common mocked repositories"""
        return {
            'expense_repo': MagicMock(),
            'group_repo': MagicMock(),
            'balance_repo': MagicMock(),
            'group_summary_repo': MagicMock(),
            'user_expense_repo': MagicMock(),
            'history_repo': MagicMock(),
            'snapshot_repo': MagicMock()
        }
    
    @pytest.fixture
    def expense_service(self, mock_repos):
        """Create ExpenseService with mocked repos"""
        from expense_engine.services.expense_service import ExpenseService
        return ExpenseService(**mock_repos)
    
    def test_create_expense_with_deltas_returns_balance_deltas(self, mock_repos, expense_service):
        """Test create_expense_with_deltas returns calculated balance deltas"""
        # Setup mocks
        mock_repos['group_repo'].get_by_id.return_value = {
            'group_id': 'group_1',
            'name': 'Test Group',
            'members': ['user_1', 'user_2']
        }
        
        # Mock the expense creation flow
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = 'exp_new_123'
        mock_collection.document.return_value = mock_doc_ref
        mock_repos['expense_repo'].get_collection.return_value = mock_collection
        mock_repos['expense_repo'].create.return_value = None
        mock_repos['expense_repo'].db = MagicMock()
        mock_repos['expense_repo'].db.transaction.return_value = MagicMock()
        
        # Mock history repo
        mock_repos['history_repo'].get_expense_history.return_value = [{
            'id': 'hist_1',
            'action': 'created',
            'changed_by': 'user_1'
        }]
        
        # Call the method
        with patch('expense_engine.services.expense_service.firestore'):
            result = expense_service.create_expense_with_deltas(
                group_id='group_1',
                description='Test Expense',
                amount=Decimal('100.00'),
                paid_by='user_1',
                split_type='equal',
                splits=[
                    {'user_id': 'user_1', 'amount': '50.00'},
                    {'user_id': 'user_2', 'amount': '50.00'}
                ],
                created_by='user_1'
            )
        
        # Verify structure
        assert 'expense' in result
        assert 'balance_deltas' in result
        assert 'history_entry' in result
        
        # Verify balance deltas are calculated correctly
        # user_1: paid 100, owes 50 = +50
        # user_2: paid 0, owes 50 = -50
        assert result['balance_deltas']['user_1'] == 50.0
        assert result['balance_deltas']['user_2'] == -50.0
    
    def test_create_expense_with_deltas_includes_history_entry(self, mock_repos, expense_service):
        """Test create_expense_with_deltas includes history entry"""
        mock_repos['group_repo'].get_by_id.return_value = {
            'group_id': 'group_1',
            'name': 'Test Group',
            'members': ['user_1']
        }
        
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = 'exp_123'
        mock_collection.document.return_value = mock_doc_ref
        mock_repos['expense_repo'].get_collection.return_value = mock_collection
        mock_repos['expense_repo'].db = MagicMock()
        mock_repos['expense_repo'].db.transaction.return_value = MagicMock()
        
        expected_history = {
            'id': 'hist_abc',
            'action': 'created',
            'changed_by': 'user_1',
            'changed_at': '2025-01-01T00:00:00Z'
        }
        mock_repos['history_repo'].get_expense_history.return_value = [expected_history]
        
        with patch('expense_engine.services.expense_service.firestore'):
            result = expense_service.create_expense_with_deltas(
                group_id='group_1',
                description='Test',
                amount=Decimal('50.00'),
                paid_by='user_1',
                split_type='equal',
                splits=[{'user_id': 'user_1', 'amount': '50.00'}],
                created_by='user_1'
            )
        
        assert result['history_entry'] == expected_history
    
    def test_update_expense_with_deltas_returns_combined_deltas(self, mock_repos, expense_service):
        """Test update_expense_with_deltas calculates old->new delta difference"""
        # Old expense: 100, split 50/50 between user_1 and user_2
        old_expense_data = {
            'expense_id': 'exp_123',
            'group_id': 'group_1',
            'description': 'Old Description',
            'amount': 100.0,
            'paid_by': 'user_1',
            'split_type': 'equal',
            'splits': [
                {'user_id': 'user_1', 'amount': 50.0},
                {'user_id': 'user_2', 'amount': 50.0}
            ],
            'created_by': 'user_1'
        }
        mock_repos['expense_repo'].get_by_id.return_value = old_expense_data
        mock_repos['expense_repo'].update.return_value = None
        mock_repos['expense_repo'].db = MagicMock()
        mock_repos['expense_repo'].db.transaction.return_value = MagicMock()
        
        mock_repos['history_repo'].get_expense_history.return_value = [{
            'id': 'hist_2',
            'action': 'updated'
        }]
        
        # Update amount from 100 to 200 (same split ratio)
        with patch('expense_engine.services.expense_service.firestore'):
            result = expense_service.update_expense_with_deltas(
                expense_id='exp_123',
                updated_by='user_1',
                amount=Decimal('200.00'),
                splits=[
                    {'user_id': 'user_1', 'amount': '100.00'},
                    {'user_id': 'user_2', 'amount': '100.00'}
                ]
            )
        
        # Verify structure
        assert 'expense' in result
        assert 'balance_deltas' in result
        assert 'history_entry' in result
        
        # Delta calculation:
        # Old: user_1 = +50, user_2 = -50
        # New: user_1 = +100, user_2 = -100
        # Combined: user_1 = +50, user_2 = -50
        assert result['balance_deltas']['user_1'] == 50.0
        assert result['balance_deltas']['user_2'] == -50.0
    
    def test_delete_expense_with_deltas_returns_reverse_deltas(self, mock_repos, expense_service):
        """Test delete_expense_with_deltas returns reverse balance deltas"""
        expense_data = {
            'expense_id': 'exp_123',
            'group_id': 'group_1',
            'description': 'To Delete',
            'amount': 100.0,
            'paid_by': 'user_1',
            'split_type': 'equal',
            'splits': [
                {'user_id': 'user_1', 'amount': 50.0},
                {'user_id': 'user_2', 'amount': 50.0}
            ],
            'created_by': 'user_1'
        }
        mock_repos['expense_repo'].get_by_id.return_value = expense_data
        mock_repos['expense_repo'].soft_delete_expense.return_value = None
        mock_repos['expense_repo'].db = MagicMock()
        mock_repos['expense_repo'].db.transaction.return_value = MagicMock()
        mock_repos['group_repo'].get_by_id.return_value = {'members': ['user_1', 'user_2']}
        
        mock_repos['history_repo'].get_expense_history.return_value = [{
            'id': 'hist_3',
            'action': 'deleted'
        }]
        
        with patch('expense_engine.services.expense_service.firestore'):
            result = expense_service.delete_expense_with_deltas(
                expense_id='exp_123',
                deleted_by='user_1'
            )
        
        # Verify structure
        assert 'expense_id' in result
        assert 'group_id' in result
        assert 'balance_deltas' in result
        assert 'history_entry' in result
        assert 'deleted_expense' in result
        
        # Reverse deltas (opposite of creation):
        # user_1 was +50, now -50
        # user_2 was -50, now +50
        assert result['balance_deltas']['user_1'] == -50.0
        assert result['balance_deltas']['user_2'] == 50.0
        assert result['deleted_expense']['is_deleted'] is True
    
    def test_delete_expense_with_deltas_handles_three_way_split(self, mock_repos, expense_service):
        """Test delete reverses three-way split correctly"""
        expense_data = {
            'expense_id': 'exp_456',
            'group_id': 'group_1',
            'description': 'Three Way',
            'amount': 90.0,
            'paid_by': 'user_1',
            'split_type': 'equal',
            'splits': [
                {'user_id': 'user_1', 'amount': 30.0},
                {'user_id': 'user_2', 'amount': 30.0},
                {'user_id': 'user_3', 'amount': 30.0}
            ],
            'created_by': 'user_1'
        }
        mock_repos['expense_repo'].get_by_id.return_value = expense_data
        mock_repos['expense_repo'].soft_delete_expense.return_value = None
        mock_repos['expense_repo'].db = MagicMock()
        mock_repos['expense_repo'].db.transaction.return_value = MagicMock()
        mock_repos['group_repo'].get_by_id.return_value = {'members': ['user_1', 'user_2', 'user_3']}
        mock_repos['history_repo'].get_expense_history.return_value = []
        
        with patch('expense_engine.services.expense_service.firestore'):
            result = expense_service.delete_expense_with_deltas(
                expense_id='exp_456',
                deleted_by='user_1'
            )
        
        # Original: user_1 = +60, user_2 = -30, user_3 = -30
        # Reverse: user_1 = -60, user_2 = +30, user_3 = +30
        assert result['balance_deltas']['user_1'] == -60.0
        assert result['balance_deltas']['user_2'] == 30.0
        assert result['balance_deltas']['user_3'] == 30.0
    
    def test_with_deltas_methods_handle_history_fetch_failure(self, mock_repos, expense_service):
        """Test methods gracefully handle history fetch failure"""
        mock_repos['group_repo'].get_by_id.return_value = {
            'group_id': 'group_1',
            'name': 'Test',
            'members': ['user_1']
        }
        
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = 'exp_123'
        mock_collection.document.return_value = mock_doc_ref
        mock_repos['expense_repo'].get_collection.return_value = mock_collection
        mock_repos['expense_repo'].db = MagicMock()
        mock_repos['expense_repo'].db.transaction.return_value = MagicMock()
        
        # Simulate history fetch failure
        mock_repos['history_repo'].get_expense_history.side_effect = Exception("DB error")
        
        with patch('expense_engine.services.expense_service.firestore'):
            result = expense_service.create_expense_with_deltas(
                group_id='group_1',
                description='Test',
                amount=Decimal('100.00'),
                paid_by='user_1',
                split_type='equal',
                splits=[{'user_id': 'user_1', 'amount': '100.00'}],
                created_by='user_1'
            )
        
        # Should still succeed, history_entry will be None
        assert 'expense' in result
        assert 'balance_deltas' in result
        assert result['history_entry'] is None
    
    def test_balance_deltas_are_json_serializable(self, mock_repos, expense_service):
        """Test balance_deltas are floats (not Decimal) for JSON serialization"""
        mock_repos['group_repo'].get_by_id.return_value = {
            'group_id': 'group_1',
            'name': 'Test',
            'members': ['user_1', 'user_2']
        }
        
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = 'exp_123'
        mock_collection.document.return_value = mock_doc_ref
        mock_repos['expense_repo'].get_collection.return_value = mock_collection
        mock_repos['expense_repo'].db = MagicMock()
        mock_repos['expense_repo'].db.transaction.return_value = MagicMock()
        mock_repos['history_repo'].get_expense_history.return_value = []
        
        with patch('expense_engine.services.expense_service.firestore'):
            result = expense_service.create_expense_with_deltas(
                group_id='group_1',
                description='Test',
                amount=Decimal('100.00'),
                paid_by='user_1',
                split_type='equal',
                splits=[
                    {'user_id': 'user_1', 'amount': '50.00'},
                    {'user_id': 'user_2', 'amount': '50.00'}
                ],
                created_by='user_1'
            )
        
        # Verify deltas are floats, not Decimals
        for delta in result['balance_deltas'].values():
            assert isinstance(delta, float), f"Expected float, got {type(delta)}"
