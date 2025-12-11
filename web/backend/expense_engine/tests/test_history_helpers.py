"""
Unit Tests for Phase 17 History Helpers

Tests batch history operations for efficient frontend updates.
"""

# pylint: disable=unused-argument,unused-variable,protected-access

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestHistoryEnricher:
    """Test HistoryEnricher batch operations"""
    
    @pytest.fixture
    def mock_history_repo(self):
        """Create mocked history repository"""
        return MagicMock()
    
    @pytest.fixture
    def enricher(self, mock_history_repo):
        """Create HistoryEnricher with mocked repo"""
        from expense_engine.utils.history_helpers import HistoryEnricher
        return HistoryEnricher(history_repo=mock_history_repo)
    
    def test_get_edit_counts_batch_returns_zero_for_unedited(
        self, mock_history_repo, enricher
    ):
        """Test unedited expenses return edit_count of 0"""
        # No history entries
        mock_history_repo.query.return_value = []
        
        result = enricher.get_edit_counts_batch(['exp_1', 'exp_2', 'exp_3'])
        
        assert result == {'exp_1': 0, 'exp_2': 0, 'exp_3': 0}
    
    def test_get_edit_counts_batch_counts_edits_correctly(
        self, mock_history_repo, enricher
    ):
        """Test edit counts are calculated correctly"""
        mock_history_repo.query.return_value = [
            {'expense_id': 'exp_1', 'action': 'updated'},
            {'expense_id': 'exp_1', 'action': 'updated'},
            {'expense_id': 'exp_2', 'action': 'updated'},
        ]
        
        result = enricher.get_edit_counts_batch(['exp_1', 'exp_2', 'exp_3'])
        
        assert result['exp_1'] == 2
        assert result['exp_2'] == 1
        assert result['exp_3'] == 0
    
    def test_get_edit_counts_batch_handles_empty_list(
        self, mock_history_repo, enricher
    ):
        """Test empty expense list returns empty dict"""
        result = enricher.get_edit_counts_batch([])
        
        assert result == {}
        mock_history_repo.query.assert_not_called()
    
    def test_get_edit_counts_batch_deduplicates_ids(
        self, mock_history_repo, enricher
    ):
        """Test duplicate IDs are handled"""
        mock_history_repo.query.return_value = []
        
        result = enricher.get_edit_counts_batch(['exp_1', 'exp_1', 'exp_2'])
        
        # Should deduplicate
        assert len(result) == 2
        assert 'exp_1' in result
        assert 'exp_2' in result
    
    def test_get_edit_counts_batch_batches_large_lists(
        self, mock_history_repo, enricher
    ):
        """Test large lists are batched correctly"""
        # Create 50 expense IDs (should be batched into 2 queries with batch_size=30)
        expense_ids = [f'exp_{i}' for i in range(50)]
        mock_history_repo.query.return_value = []
        
        result = enricher.get_edit_counts_batch(expense_ids, batch_size=30)
        
        # Should have called query twice (30 + 20)
        assert mock_history_repo.query.call_count == 2
        assert len(result) == 50
    
    def test_get_edit_counts_batch_handles_error(
        self, mock_history_repo, enricher
    ):
        """Test graceful error handling"""
        mock_history_repo.query.side_effect = Exception("DB error")
        
        result = enricher.get_edit_counts_batch(['exp_1', 'exp_2'])
        
        # Should return zeros on error
        assert result == {'exp_1': 0, 'exp_2': 0}
    
    def test_get_last_edit_batch_returns_most_recent(
        self, mock_history_repo, enricher
    ):
        """Test returns most recent edit for each expense"""
        mock_history_repo.query.return_value = [
            {
                'expense_id': 'exp_1',
                'action': 'updated',
                'changed_at': '2025-01-02T00:00:00Z',
                'changed_by': 'user_2',
                'changed_by_name': 'User Two'
            },
            {
                'expense_id': 'exp_1',
                'action': 'updated',
                'changed_at': '2025-01-01T00:00:00Z',  # Older
                'changed_by': 'user_1',
                'changed_by_name': 'User One'
            },
        ]
        
        result = enricher.get_last_edit_batch(['exp_1'])
        
        assert result['exp_1']['changed_by'] == 'user_2'
        assert result['exp_1']['changed_by_name'] == 'User Two'
    
    def test_get_last_edit_batch_returns_none_for_unedited(
        self, mock_history_repo, enricher
    ):
        """Test unedited expenses return None"""
        mock_history_repo.query.return_value = []
        
        result = enricher.get_last_edit_batch(['exp_1', 'exp_2'])
        
        assert result == {'exp_1': None, 'exp_2': None}
    
    def test_enrich_expenses_with_history_adds_fields(
        self, mock_history_repo, enricher
    ):
        """Test enrichment adds edit_count and last_edited fields"""
        # Setup mocks
        mock_history_repo.query.side_effect = [
            # First call: edit counts
            [
                {'expense_id': 'exp_1', 'action': 'updated'},
                {'expense_id': 'exp_1', 'action': 'updated'},
            ],
            # Second call: last edits
            [
                {
                    'expense_id': 'exp_1',
                    'action': 'updated',
                    'changed_at': '2025-01-01T00:00:00Z',
                    'changed_by': 'user_1',
                    'changed_by_name': 'User One'
                }
            ]
        ]
        
        expenses = [
            {'expense_id': 'exp_1', 'description': 'Test 1'},
            {'expense_id': 'exp_2', 'description': 'Test 2'},
        ]
        
        result = enricher.enrich_expenses_with_history(expenses)
        
        # exp_1 was edited
        assert result[0]['edit_count'] == 2
        assert result[0]['last_edited_by'] == 'user_1'
        
        # exp_2 was not edited
        assert result[1]['edit_count'] == 0
        assert 'last_edited_by' not in result[1]
    
    def test_enrich_expenses_handles_id_vs_expense_id(
        self, mock_history_repo, enricher
    ):
        """Test handles both 'id' and 'expense_id' field names"""
        mock_history_repo.query.return_value = []
        
        expenses = [
            {'id': 'exp_1', 'description': 'Test 1'},
            {'expense_id': 'exp_2', 'description': 'Test 2'},
        ]
        
        result = enricher.enrich_expenses_with_history(expenses)
        
        assert result[0]['edit_count'] == 0
        assert result[1]['edit_count'] == 0
    
    def test_enrich_expenses_handles_empty_list(
        self, mock_history_repo, enricher
    ):
        """Test empty expense list returns empty list"""
        result = enricher.enrich_expenses_with_history([])
        
        assert result == []
        mock_history_repo.query.assert_not_called()


class TestCreateHistoryEntryWithReturn:
    """Test create_history_entry_with_return function"""
    
    @pytest.fixture
    def mock_history_repo(self):
        """Create mocked history repository"""
        repo = MagicMock()
        repo.create_history_entry.return_value = 'hist_new_123'
        return repo
    
    def test_creates_entry_and_returns_it(self, mock_history_repo):
        """Test entry is created and returned"""
        from expense_engine.utils.history_helpers import create_history_entry_with_return
        
        result = create_history_entry_with_return(
            history_repo=mock_history_repo,
            expense_id='exp_1',
            group_id='group_1',
            action='created',
            changed_by='user_1',
            after_snapshot={'id': 'exp_1', 'amount': 100}
        )
        
        mock_history_repo.create_history_entry.assert_called_once()
        assert result['id'] == 'hist_new_123'
        assert result['expense_id'] == 'exp_1'
        assert result['action'] == 'created'
        assert result['changed_by'] == 'user_1'
    
    def test_includes_changes_for_updates(self, mock_history_repo):
        """Test update entries compute and include changes"""
        from expense_engine.utils.history_helpers import create_history_entry_with_return
        
        with patch('expense_engine.models.expense_history.compute_changes') as mock_compute:
            mock_compute.return_value = [
                {'field': 'amount', 'old': '100', 'new': '150'}
            ]
            
            result = create_history_entry_with_return(
                history_repo=mock_history_repo,
                expense_id='exp_1',
                group_id='group_1',
                action='updated',
                changed_by='user_1',
                before_snapshot={'id': 'exp_1', 'amount': 100},
                after_snapshot={'id': 'exp_1', 'amount': 150}
            )
        
        assert len(result['changes']) == 1
        assert result['changes'][0]['field'] == 'amount'
    
    def test_handles_create_failure_gracefully(self, mock_history_repo):
        """Test returns temp entry on failure"""
        from expense_engine.utils.history_helpers import create_history_entry_with_return
        
        mock_history_repo.create_history_entry.side_effect = Exception("DB error")
        
        result = create_history_entry_with_return(
            history_repo=mock_history_repo,
            expense_id='exp_1',
            group_id='group_1',
            action='created',
            changed_by='user_1',
            after_snapshot={'id': 'exp_1'}
        )
        
        # Should return entry with temp ID and failure flag
        assert result['id'].startswith('temp_')
        assert result['_failed'] is True
        assert result['expense_id'] == 'exp_1'


class TestFormatBalancesForResponse:
    """Test format_balances_for_response function"""
    
    def test_formats_balances_with_member_info(self):
        """Test balances are formatted with member details"""
        from expense_engine.utils.history_helpers import format_balances_for_response
        
        balances = {'user_1': 50.0, 'user_2': -50.0}
        members = [
            {'user_id': 'user_1', 'display_name': 'User One'},
            {'user_id': 'user_2', 'display_name': 'User Two'},
        ]
        
        result = format_balances_for_response(balances, members)
        
        assert len(result) == 2
        
        user_1_balance = next(b for b in result if b['user_id'] == 'user_1')
        assert user_1_balance['display_name'] == 'User One'
        assert user_1_balance['balance'] == 50.0
        
        user_2_balance = next(b for b in result if b['user_id'] == 'user_2')
        assert user_2_balance['display_name'] == 'User Two'
        assert user_2_balance['balance'] == -50.0
    
    def test_includes_former_members_with_balances(self):
        """Test former members with non-zero balances are included"""
        from expense_engine.utils.history_helpers import format_balances_for_response
        
        balances = {'user_1': 50.0, 'user_removed': -50.0}
        members = [{'user_id': 'user_1', 'display_name': 'User One'}]
        all_members_map = {
            'user_1': {'display_name': 'User One'},
            'user_removed': {'display_name': 'Removed User', 'is_active': False}
        }
        
        result = format_balances_for_response(balances, members, all_members_map)
        
        assert len(result) == 2
        
        removed_balance = next(b for b in result if b['user_id'] == 'user_removed')
        assert removed_balance['balance'] == -50.0
        assert removed_balance['is_active'] is False
    
    def test_excludes_former_members_with_zero_balance(self):
        """Test former members with zero balance are not included"""
        from expense_engine.utils.history_helpers import format_balances_for_response
        
        balances = {'user_1': 50.0, 'user_removed': 0.0}
        members = [{'user_id': 'user_1', 'display_name': 'User One'}]
        
        result = format_balances_for_response(balances, members)
        
        # Only active member should be included
        assert len(result) == 1
        assert result[0]['user_id'] == 'user_1'
    
    def test_handles_member_as_string(self):
        """Test handles member list as strings (just user IDs)"""
        from expense_engine.utils.history_helpers import format_balances_for_response
        
        balances = {'user_1': 100.0}
        members = ['user_1', 'user_2']
        
        result = format_balances_for_response(balances, members)
        
        assert len(result) == 2
        
        user_1 = next(b for b in result if b['user_id'] == 'user_1')
        assert user_1['balance'] == 100.0
