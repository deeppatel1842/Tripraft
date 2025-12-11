"""
Unit Tests for Expense Engine Repositories
Tests for data access layer with mocked Firestore

Phase 1 Implementation - November 25, 2025
"""

# pylint: disable=unused-argument,redefined-outer-name,unused-variable

from unittest.mock import MagicMock, patch
from decimal import Decimal


# =============================================================================
# BASE REPOSITORY TESTS
# =============================================================================

class TestBaseRepository:
    """Test BaseRepository functionality"""
    
    def test_get_collection_returns_firestore_collection(self, mock_firestore_patch):
        """Test that get_collection returns Firestore collection reference"""
        from expense_engine.repositories.user_repository import UserRepository
        
        repo = UserRepository(db=mock_firestore_patch)
        _ = repo.get_collection()
        
        mock_firestore_patch.collection.assert_called_with('users')
    
    def test_get_by_id_returns_document_with_id(self, mock_firestore_patch):
        """Test get_by_id returns document data with id field"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'test_123'
        mock_doc.to_dict.return_value = {'uid': 'test_123', 'email': 'test@example.com'}
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = UserRepository(db=mock_firestore_patch)
        result = repo.get_by_id('test_123')
        
        assert result is not None
        assert result['id'] == 'test_123'
        assert result['uid'] == 'test_123'
    
    def test_get_by_id_returns_none_for_missing(self, mock_firestore_patch):
        """Test get_by_id returns None for non-existent document"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = UserRepository(db=mock_firestore_patch)
        result = repo.get_by_id('non_existent_id')
        
        assert result is None
    
    def test_create_calls_set_on_document(self, mock_firestore_patch):
        """Test create calls set on document reference"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        
        repo = UserRepository(db=mock_firestore_patch)
        repo.create('doc_123', {'name': 'Test'})
        
        mock_doc_ref.set.assert_called_once_with({'name': 'Test'})
    
    def test_update_calls_update_on_document(self, mock_firestore_patch):
        """Test update calls update on document reference"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        
        repo = UserRepository(db=mock_firestore_patch)
        repo.update('doc_123', {'name': 'Updated'})
        
        mock_doc_ref.update.assert_called_once_with({'name': 'Updated'})
    
    def test_delete_calls_delete_on_document(self, mock_firestore_patch):
        """Test delete calls delete on document reference"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        
        repo = UserRepository(db=mock_firestore_patch)
        repo.delete('doc_123')
        
        mock_doc_ref.delete.assert_called_once()
    
    def test_exists_returns_true_for_existing_doc(self, mock_firestore_patch):
        """Test exists returns True for existing document"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = UserRepository(db=mock_firestore_patch)
        result = repo.exists('doc_123')
        
        assert result is True
    
    def test_exists_returns_false_for_missing_doc(self, mock_firestore_patch):
        """Test exists returns False for non-existent document"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = UserRepository(db=mock_firestore_patch)
        result = repo.exists('non_existent')
        
        assert result is False
    
    def test_batch_create_commits_batch(self, mock_firestore_patch):
        """Test batch_create commits multiple documents"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_batch = MagicMock()
        mock_firestore_patch.batch.return_value = mock_batch
        
        repo = UserRepository(db=mock_firestore_patch)
        documents = {
            'doc_1': {'name': 'Doc 1'},
            'doc_2': {'name': 'Doc 2'}
        }
        repo.batch_create(documents)
        
        assert mock_batch.set.call_count == 2
        mock_batch.commit.assert_called_once()
    
    def test_batch_update_commits_updates(self, mock_firestore_patch):
        """Test batch_update commits multiple updates"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_batch = MagicMock()
        mock_firestore_patch.batch.return_value = mock_batch
        
        repo = UserRepository(db=mock_firestore_patch)
        updates = {
            'doc_1': {'name': 'Updated 1'},
            'doc_2': {'name': 'Updated 2'}
        }
        repo.batch_update(updates)
        
        assert mock_batch.update.call_count == 2
        mock_batch.commit.assert_called_once()
    
    def test_batch_delete_commits_deletes(self, mock_firestore_patch):
        """Test batch_delete commits multiple deletes"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_batch = MagicMock()
        mock_firestore_patch.batch.return_value = mock_batch
        
        repo = UserRepository(db=mock_firestore_patch)
        repo.batch_delete(['doc_1', 'doc_2', 'doc_3'])
        
        assert mock_batch.delete.call_count == 3
        mock_batch.commit.assert_called_once()
    
    def test_query_applies_filters(self, mock_firestore_patch):
        """Test query applies filters correctly"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.stream.return_value = []
        mock_firestore_patch.collection.return_value = mock_query
        
        repo = UserRepository(db=mock_firestore_patch)
        repo.query(filters=[('status', '==', 'active')])
        
        mock_query.where.assert_called()
    
    def test_query_with_cursor_returns_pagination_info(self, mock_firestore_patch):
        """Test query_with_cursor returns documents with pagination metadata"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc = MagicMock()
        mock_doc.id = 'doc_1'
        mock_doc.to_dict.return_value = {'name': 'Test'}
        
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]
        mock_firestore_patch.collection.return_value = mock_query
        
        repo = UserRepository(db=mock_firestore_patch)
        result = repo.query_with_cursor(limit=10)
        
        assert 'documents' in result
        assert 'has_more' in result
        assert 'next_cursor' in result


# =============================================================================
# USER REPOSITORY TESTS
# =============================================================================

class TestUserRepository:
    """Test UserRepository functionality"""
    
    def test_collection_name_is_users(self, mock_firestore_patch):
        """Test that collection name is 'users'"""
        from expense_engine.repositories.user_repository import UserRepository
        
        repo = UserRepository(db=mock_firestore_patch)
        assert repo.get_collection_name() == 'users'
    
    def test_get_user_by_email_returns_user(self, mock_firestore_patch, sample_user_data):
        """Test getting user by email"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = sample_user_data
        mock_doc.id = 'user_123'
        
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc]
        mock_firestore_patch.collection.return_value.where.return_value = mock_query
        
        repo = UserRepository(db=mock_firestore_patch)
        result = repo.get_user_by_email('test@example.com')
        
        assert result is not None
        assert isinstance(result, dict)
        assert result.get('email') == 'test@example.com'
    
    def test_get_user_by_email_returns_none_when_not_found(self, mock_firestore_patch):
        """Test getting user by email returns None when not found"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_firestore_patch.collection.return_value.where.return_value = mock_query
        
        repo = UserRepository(db=mock_firestore_patch)
        result = repo.get_user_by_email('nonexistent@example.com')
        
        assert result is None
    
    def test_create_or_update_user_creates_new_user(self, mock_firestore_patch):
        """Test creating a new user"""
        from expense_engine.repositories.user_repository import UserRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = UserRepository(db=mock_firestore_patch)
        result = repo.create_or_update_user(
            uid='user_123',
            email='test@example.com',
            display_name='Test User'
        )
        
        assert result is not None
        assert result['uid'] == 'user_123'
        assert result['email'] == 'test@example.com'


# =============================================================================
# GROUP REPOSITORY TESTS
# =============================================================================

class TestGroupRepository:
    """Test GroupRepository functionality"""
    
    def test_collection_name_is_expense_groups(self, mock_firestore_patch):
        """Test that collection name is 'expense_groups'"""
        from expense_engine.repositories.group_repository import GroupRepository
        
        repo = GroupRepository(db=mock_firestore_patch)
        assert repo.get_collection_name() == 'expense_groups'
    
    def test_get_by_id_normalizes_group_id(self, mock_firestore_patch, sample_group_data):
        """Test that get_by_id normalizes group_id field"""
        from expense_engine.repositories.group_repository import GroupRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'group_123'
        mock_doc.to_dict.return_value = {'id': 'group_123', 'name': 'Test Group'}
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = GroupRepository(db=mock_firestore_patch)
        result = repo.get_by_id('group_123')
        
        assert result is not None
        assert result.get('group_id') == 'group_123'
    
    def test_get_user_groups_queries_by_member(self, mock_firestore_patch, sample_group_data):
        """Test getting groups for a user queries by members array"""
        from expense_engine.repositories.group_repository import GroupRepository
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = sample_group_data
        mock_doc.id = 'group_123'
        
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]
        mock_firestore_patch.collection.return_value.where.return_value = mock_query
        
        repo = GroupRepository(db=mock_firestore_patch)
        result = repo.get_user_groups('user_123')
        
        assert len(result) == 1
        mock_firestore_patch.collection.return_value.where.assert_called()
    
    def test_soft_delete_group_marks_inactive(self, mock_firestore_patch, sample_group_data):
        """Test soft_delete_group marks group as inactive"""
        from expense_engine.repositories.group_repository import GroupRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'group_123'
        mock_doc.to_dict.return_value = sample_group_data
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        mock_doc_ref.get.return_value = mock_doc
        
        repo = GroupRepository(db=mock_firestore_patch)
        repo.soft_delete_group('group_123')
        
        mock_doc_ref.update.assert_called()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args['is_active'] is False
        assert 'deleted_at' in call_args
    
    def test_restore_group_marks_active(self, mock_firestore_patch, sample_group_data):
        """Test restore_group marks group as active"""
        from expense_engine.repositories.group_repository import GroupRepository
        
        deleted_group = {**sample_group_data, 'is_active': False}
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'group_123'
        mock_doc.to_dict.return_value = deleted_group
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        mock_doc_ref.get.return_value = mock_doc
        
        repo = GroupRepository(db=mock_firestore_patch)
        repo.restore_group('group_123')
        
        mock_doc_ref.update.assert_called()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args['is_active'] is True
    
    def test_get_active_groups_for_user_filters_inactive(self, mock_firestore_patch, sample_group_data):
        """Test get_active_groups_for_user only returns active groups"""
        from expense_engine.repositories.group_repository import GroupRepository
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = sample_group_data
        mock_doc.id = 'group_123'
        
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]
        mock_firestore_patch.collection.return_value.where.return_value = mock_query
        
        repo = GroupRepository(db=mock_firestore_patch)
        result = repo.get_active_groups_for_user('user_123')
        
        assert len(result) == 1


# =============================================================================
# EXPENSE REPOSITORY TESTS
# =============================================================================

class TestExpenseRepository:
    """Test ExpenseRepository functionality"""
    
    def test_collection_name_is_expense_expenses(self, mock_firestore_patch):
        """Test that collection name is 'expense_expenses'"""
        from expense_engine.repositories.expense_repository import ExpenseRepository
        
        repo = ExpenseRepository(db=mock_firestore_patch)
        assert repo.get_collection_name() == 'expense_expenses'
    
    def test_get_group_expenses_returns_paginated_results(self, mock_firestore_patch, sample_expense_data):
        """Test get_group_expenses returns paginated results"""
        from expense_engine.repositories.expense_repository import ExpenseRepository
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = sample_expense_data
        mock_doc.id = 'expense_123'
        
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]
        mock_firestore_patch.collection.return_value = mock_query
        
        repo = ExpenseRepository(db=mock_firestore_patch)
        result = repo.get_group_expenses('group_123', limit=10, offset=0)
        
        assert 'expenses' in result
        assert 'total' in result
        assert 'has_more' in result
    
    def test_soft_delete_expense_marks_deleted(self, mock_firestore_patch, sample_expense_data):
        """Test soft_delete_expense marks expense as deleted"""
        from expense_engine.repositories.expense_repository import ExpenseRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'expense_123'
        mock_doc.to_dict.return_value = sample_expense_data
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        mock_doc_ref.get.return_value = mock_doc
        
        repo = ExpenseRepository(db=mock_firestore_patch)
        repo.soft_delete_expense('expense_123')
        
        mock_doc_ref.update.assert_called()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args['is_deleted'] is True
        assert 'deleted_at' in call_args
    
    def test_restore_expense_removes_deleted_flag(self, mock_firestore_patch, sample_expense_data):
        """Test restore_expense removes deleted flag"""
        from expense_engine.repositories.expense_repository import ExpenseRepository
        
        deleted_expense = {**sample_expense_data, 'is_deleted': True}
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'expense_123'
        mock_doc.to_dict.return_value = deleted_expense
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        mock_doc_ref.get.return_value = mock_doc
        
        repo = ExpenseRepository(db=mock_firestore_patch)
        repo.restore_expense('expense_123')
        
        mock_doc_ref.update.assert_called()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args['is_deleted'] is False


# =============================================================================
# SETTLEMENT REPOSITORY TESTS
# =============================================================================

class TestSettlementRepository:
    """Test SettlementRepository functionality"""
    
    def test_collection_name_is_expense_settlements(self, mock_firestore_patch):
        """Test that collection name is 'expense_settlements'"""
        from expense_engine.repositories.settlement_repository import SettlementRepository
        
        repo = SettlementRepository(db=mock_firestore_patch)
        assert repo.get_collection_name() == 'expense_settlements'
    
    def test_get_group_settlements_filters_by_group(self, mock_firestore_patch, sample_settlement_data):
        """Test get_group_settlements filters by group_id"""
        from expense_engine.repositories.settlement_repository import SettlementRepository
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = sample_settlement_data
        mock_doc.id = 'settlement_123'
        
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]
        mock_firestore_patch.collection.return_value = mock_query
        
        repo = SettlementRepository(db=mock_firestore_patch)
        result = repo.get_group_settlements('group_123')
        
        assert len(result) == 1
    
    def test_mark_as_completed_updates_status(self, mock_firestore_patch, sample_settlement_data):
        """Test mark_as_completed updates settlement status"""
        from expense_engine.repositories.settlement_repository import SettlementRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'settlement_123'
        mock_doc.to_dict.return_value = sample_settlement_data
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        mock_doc_ref.get.return_value = mock_doc
        
        repo = SettlementRepository(db=mock_firestore_patch)
        repo.mark_as_completed('settlement_123', 'user_456')
        
        mock_doc_ref.update.assert_called()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args['status'] == 'completed'
        assert 'completed_at' in call_args
    
    def test_soft_delete_settlement_marks_deleted(self, mock_firestore_patch, sample_settlement_data):
        """Test soft_delete_settlement marks as deleted"""
        from expense_engine.repositories.settlement_repository import SettlementRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'settlement_123'
        mock_doc.to_dict.return_value = sample_settlement_data
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        mock_doc_ref.get.return_value = mock_doc
        
        repo = SettlementRepository(db=mock_firestore_patch)
        repo.soft_delete_settlement('settlement_123')
        
        mock_doc_ref.update.assert_called()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args['is_deleted'] is True
    
    def test_restore_settlement_removes_deleted_flag(self, mock_firestore_patch, sample_settlement_data):
        """Test restore_settlement removes deleted flag"""
        from expense_engine.repositories.settlement_repository import SettlementRepository
        
        deleted_settlement = {**sample_settlement_data, 'is_deleted': True}
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'settlement_123'
        mock_doc.to_dict.return_value = deleted_settlement
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        mock_doc_ref.get.return_value = mock_doc
        
        repo = SettlementRepository(db=mock_firestore_patch)
        repo.restore_settlement('settlement_123')
        
        mock_doc_ref.update.assert_called()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args['is_deleted'] is False


# =============================================================================
# INVITATION REPOSITORY TESTS
# =============================================================================

class TestInvitationRepository:
    """Test InvitationRepository functionality"""
    
    def test_collection_name_is_expense_invitations(self, mock_firestore_patch):
        """Test that collection name is 'expense_invitations'"""
        from expense_engine.repositories.invitation_repository import InvitationRepository
        
        repo = InvitationRepository(db=mock_firestore_patch)
        assert repo.get_collection_name() == 'expense_invitations'
    
    def test_get_pending_invitations_filters_by_status(self, mock_firestore_patch, sample_invitation_data):
        """Test get_pending_invitations filters by pending status"""
        from expense_engine.repositories.invitation_repository import InvitationRepository
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = sample_invitation_data
        mock_doc.id = 'invitation_123'
        
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]
        mock_firestore_patch.collection.return_value = mock_query
        
        repo = InvitationRepository(db=mock_firestore_patch)
        _result = repo.get_pending_invitations(email='invitee@example.com')
        
        mock_firestore_patch.collection.return_value.where.assert_called()
    
    def test_accept_invitation_updates_status(self, mock_firestore_patch, sample_invitation_data):
        """Test accept_invitation updates status to accepted"""
        from expense_engine.repositories.invitation_repository import InvitationRepository
        from datetime import datetime, timedelta
        
        future_date = datetime.utcnow() + timedelta(days=7)
        invitation_data = {
            **sample_invitation_data,
            'expires_at': future_date
        }
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'invitation_123'
        mock_doc.to_dict.return_value = invitation_data
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        mock_doc_ref.get.return_value = mock_doc
        
        repo = InvitationRepository(db=mock_firestore_patch)
        _result = repo.accept_invitation('invitation_123', 'user_789')
        
        mock_doc_ref.update.assert_called()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args['status'] == 'accepted'
    
    def test_decline_invitation_updates_status(self, mock_firestore_patch, sample_invitation_data):
        """Test decline_invitation updates status to declined"""
        from expense_engine.repositories.invitation_repository import InvitationRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'invitation_123'
        mock_doc.to_dict.return_value = sample_invitation_data
        mock_doc_ref = mock_firestore_patch.collection.return_value.document.return_value
        mock_doc_ref.get.return_value = mock_doc
        
        repo = InvitationRepository(db=mock_firestore_patch)
        repo.decline_invitation('invitation_123', 'user_789')
        
        mock_doc_ref.update.assert_called()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args['status'] == 'declined'


# =============================================================================
# BALANCE REPOSITORY TESTS
# =============================================================================

class TestBalanceRepository:
    """Test BalanceRepository functionality"""
    
    def test_collection_name_is_expense_group_balances(self, mock_firestore_patch):
        """Test that collection name is 'expense_group_balances'"""
        from expense_engine.repositories.balance_repository import BalanceRepository
        
        repo = BalanceRepository(db=mock_firestore_patch)
        assert repo.get_collection_name() == 'expense_group_balances'
    
    def test_get_group_balances_returns_group_balance(self, mock_firestore_patch, sample_balance_data):
        """Test get_group_balances returns GroupBalance model"""
        from expense_engine.repositories.balance_repository import BalanceRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'group_123'
        mock_doc.to_dict.return_value = sample_balance_data
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = BalanceRepository(db=mock_firestore_patch)
        result = repo.get_group_balances('group_123')
        
        assert result is not None
        assert result.group_id == 'group_123'
    
    def test_get_group_balances_returns_empty_for_new_group(self, mock_firestore_patch):
        """Test get_group_balances returns empty balance for new group"""
        from expense_engine.repositories.balance_repository import BalanceRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = BalanceRepository(db=mock_firestore_patch)
        result = repo.get_group_balances('new_group')
        
        assert result is not None
        assert result.group_id == 'new_group'
        assert len(result.model_dump()['balances']) == 0
    
    def test_get_user_balance_returns_decimal(self, mock_firestore_patch, sample_balance_data):
        """Test get_user_balance returns Decimal value"""
        from expense_engine.repositories.balance_repository import BalanceRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'group_123'
        mock_doc.to_dict.return_value = sample_balance_data
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = BalanceRepository(db=mock_firestore_patch)
        result = repo.get_user_balance('group_123', 'user_123')
        
        assert isinstance(result, Decimal)
    
    @patch('expense_engine.repositories.balance_repository.get_cache_manager')
    def test_is_group_settled_returns_true_for_zero_balances(self, mock_cache, mock_firestore_patch):
        """Test is_group_settled returns True when all balances are zero"""
        from expense_engine.repositories.balance_repository import BalanceRepository
        
        # Disable cache for this test
        mock_cache.return_value = None
        
        settled_balance_data = {
            'group_id': 'group_123',
            'balances': {
                'user_123': Decimal('0.00'),
                'user_456': Decimal('0.00')
            }
        }
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'group_123'
        mock_doc.to_dict.return_value = settled_balance_data
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = BalanceRepository(db=mock_firestore_patch)
        result = repo.is_group_settled('group_123')
        
        assert result is True
    
    def test_is_group_settled_returns_false_for_non_zero_balances(self, mock_firestore_patch, sample_balance_data):
        """Test is_group_settled returns False when balances are not zero"""
        from expense_engine.repositories.balance_repository import BalanceRepository
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = 'group_123'
        mock_doc.to_dict.return_value = sample_balance_data
        mock_firestore_patch.collection.return_value.document.return_value.get.return_value = mock_doc
        
        repo = BalanceRepository(db=mock_firestore_patch)
        result = repo.is_group_settled('group_123')
        
        assert result is False
