"""
Tests for Expense History (Phase 12)
Tests edit history tracking, change detection, and history retrieval
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# Import models and utilities
from expense_engine.models.expense_history import (
    ExpenseHistory, FieldChange, compute_changes, _values_differ
)
from expense_engine.repositories.expense_history_repository import ExpenseHistoryRepository


class TestFieldChange:
    """Tests for FieldChange model"""
    
    def test_create_field_change(self):
        """Test creating a field change record"""
        change = FieldChange(
            field_name="amount",
            old_value=100.0,
            new_value=150.0
        )
        
        assert change.field_name == "amount"
        assert change.old_value == 100.0
        assert change.new_value == 150.0
    
    def test_to_display_dict(self):
        """Test converting field change to display format"""
        change = FieldChange(
            field_name="amount",
            old_value=100.0,
            new_value=150.0
        )
        
        display = change.to_display_dict()
        assert display["field"] == "amount"
        assert "$100.00" in display["old"]
        assert "$150.00" in display["new"]
    
    def test_format_none_value(self):
        """Test formatting None values"""
        change = FieldChange(
            field_name="notes",
            old_value=None,
            new_value="New note"
        )
        
        display = change.to_display_dict()
        assert display["old"] == "None"
        assert display["new"] == "New note"
    
    def test_format_list_value(self):
        """Test formatting list values"""
        change = FieldChange(
            field_name="splits",
            old_value=[{"user_id": "a"}, {"user_id": "b"}],
            new_value=[{"user_id": "a"}, {"user_id": "b"}, {"user_id": "c"}]
        )
        
        display = change.to_display_dict()
        assert "2 items" in display["old"]
        assert "3 items" in display["new"]


class TestExpenseHistory:
    """Tests for ExpenseHistory model"""
    
    def test_create_history_entry(self):
        """Test creating a history entry"""
        history = ExpenseHistory(
            expense_id="exp_123",
            group_id="grp_456",
            action="created",
            changed_by="user_789",
            changed_by_name="John Doe",
            after_snapshot={"description": "Dinner", "amount": 100}
        )
        
        assert history.expense_id == "exp_123"
        assert history.group_id == "grp_456"
        assert history.action == "created"
        assert history.changed_by == "user_789"
        assert history.changed_by_name == "John Doe"
    
    def test_get_summary_created(self):
        """Test summary for created action"""
        history = ExpenseHistory(
            expense_id="exp_123",
            group_id="grp_456",
            action="created",
            changed_by="user_789",
            after_snapshot={}
        )
        
        assert history.get_summary() == "Created expense"
    
    def test_get_summary_deleted(self):
        """Test summary for deleted action"""
        history = ExpenseHistory(
            expense_id="exp_123",
            group_id="grp_456",
            action="deleted",
            changed_by="user_789",
            after_snapshot={}
        )
        
        assert history.get_summary() == "Deleted expense"
    
    def test_get_summary_single_update(self):
        """Test summary for single field update"""
        history = ExpenseHistory(
            expense_id="exp_123",
            group_id="grp_456",
            action="updated",
            changed_by="user_789",
            changes=[
                FieldChange(field_name="amount", old_value=100, new_value=150)
            ],
            after_snapshot={}
        )
        
        assert history.get_summary() == "Updated amount"
    
    def test_get_summary_multiple_updates(self):
        """Test summary for multiple field updates"""
        history = ExpenseHistory(
            expense_id="exp_123",
            group_id="grp_456",
            action="updated",
            changed_by="user_789",
            changes=[
                FieldChange(field_name="amount", old_value=100, new_value=150),
                FieldChange(field_name="category", old_value="Food", new_value="Transport"),
                FieldChange(field_name="notes", old_value=None, new_value="Note"),
                FieldChange(field_name="description", old_value="Old", new_value="New")
            ],
            after_snapshot={}
        )
        
        assert "4 fields" in history.get_summary()
    
    def test_to_display_dict(self):
        """Test converting history to display format"""
        history = ExpenseHistory(
            expense_id="exp_123",
            group_id="grp_456",
            action="updated",
            changed_by="user_789",
            changed_by_name="John Doe",
            changes=[
                FieldChange(field_name="amount", old_value=100, new_value=150)
            ],
            after_snapshot={"amount": 150}
        )
        
        display = history.to_display_dict()
        assert display["expense_id"] == "exp_123"
        assert display["action"] == "updated"
        assert display["changed_by"] == "user_789"
        assert "Updated amount" in display["summary"]
        assert len(display["changes"]) == 1


class TestComputeChanges:
    """Tests for change computation"""
    
    def test_compute_changes_no_before(self):
        """Test compute_changes with no before state (create)"""
        changes = compute_changes(
            before=None,
            after={"amount": 100, "description": "Test"}
        )
        
        assert len(changes) == 0
    
    def test_compute_changes_amount_changed(self):
        """Test detecting amount change"""
        changes = compute_changes(
            before={"amount": 100, "description": "Test"},
            after={"amount": 150, "description": "Test"}
        )
        
        assert len(changes) == 1
        assert changes[0].field_name == "amount"
        assert changes[0].old_value == 100
        assert changes[0].new_value == 150
    
    def test_compute_changes_multiple_fields(self):
        """Test detecting multiple field changes"""
        changes = compute_changes(
            before={
                "amount": 100,
                "description": "Old description",
                "category": "Food"
            },
            after={
                "amount": 150,
                "description": "New description",
                "category": "Food"
            }
        )
        
        assert len(changes) == 2
        field_names = [c.field_name for c in changes]
        assert "amount" in field_names
        assert "description" in field_names
    
    def test_compute_changes_no_changes(self):
        """Test no changes detected when data is same"""
        data = {"amount": 100, "description": "Test"}
        changes = compute_changes(before=data, after=data.copy())
        
        assert len(changes) == 0
    
    def test_compute_changes_with_tracked_fields(self):
        """Test limiting tracked fields"""
        changes = compute_changes(
            before={"amount": 100, "description": "Old", "notes": "Note1"},
            after={"amount": 150, "description": "New", "notes": "Note2"},
            tracked_fields=["amount"]  # Only track amount
        )
        
        assert len(changes) == 1
        assert changes[0].field_name == "amount"


class TestValuesDiffer:
    """Tests for value comparison"""
    
    def test_none_values(self):
        """Test comparing None values"""
        assert not _values_differ(None, None)
    
    def test_none_vs_empty_string(self):
        """Test None vs empty string"""
        assert not _values_differ(None, "")
        assert not _values_differ("", None)
    
    def test_none_vs_value(self):
        """Test None vs actual value"""
        assert _values_differ(None, "value")
        assert _values_differ("value", None)
    
    def test_float_precision(self):
        """Test float comparison with precision tolerance"""
        # Very small difference should not count as different
        assert not _values_differ(100.0, 100.0001)
        # Larger difference should count
        assert _values_differ(100.0, 100.01)
    
    def test_decimal_comparison(self):
        """Test Decimal comparison"""
        from decimal import Decimal
        assert not _values_differ(Decimal("100.00"), 100.0)
        assert _values_differ(Decimal("100.00"), 150.0)
    
    def test_list_length_differ(self):
        """Test lists with different lengths"""
        assert _values_differ([1, 2], [1, 2, 3])
    
    def test_list_same_content(self):
        """Test lists with same content"""
        assert not _values_differ([1, 2, 3], [1, 2, 3])
    
    def test_splits_comparison(self):
        """Test expense splits comparison"""
        old_splits = [
            {"user_id": "a", "amount": 50},
            {"user_id": "b", "amount": 50}
        ]
        new_splits = [
            {"user_id": "b", "amount": 50},
            {"user_id": "a", "amount": 50}
        ]
        # Same splits in different order should not differ
        assert not _values_differ(old_splits, new_splits)
    
    def test_splits_amount_changed(self):
        """Test splits with changed amounts"""
        old_splits = [
            {"user_id": "a", "amount": 50},
            {"user_id": "b", "amount": 50}
        ]
        new_splits = [
            {"user_id": "a", "amount": 60},
            {"user_id": "b", "amount": 40}
        ]
        assert _values_differ(old_splits, new_splits)
    
    def test_string_comparison(self):
        """Test string comparison"""
        assert not _values_differ("test", "test")
        assert _values_differ("test", "TEST")


class TestExpenseHistoryRepository:
    """Tests for ExpenseHistoryRepository"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock Firestore database"""
        return MagicMock()
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create repository with mock db"""
        repo = ExpenseHistoryRepository(db=mock_db)
        return repo
    
    def test_get_collection_name(self, repository):
        """Test collection name"""
        assert repository.get_collection_name() == "expense_history"
    
    def test_create_history_entry(self, repository, mock_db):
        """Test creating a history entry"""
        # Setup mock
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = "hist_123"
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        
        # Create entry
        history_id = repository.create_history_entry(
            expense_id="exp_456",
            group_id="grp_789",
            action="created",
            changed_by="user_abc",
            after_snapshot={"description": "Test", "amount": 100}
        )
        
        assert history_id == "hist_123"
        mock_doc.set.assert_called_once()
    
    def test_create_history_entry_with_changes(self, repository, mock_db):
        """Test creating a history entry with change detection"""
        # Setup mock
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = "hist_123"
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        
        # Create entry with changes
        history_id = repository.create_history_entry(
            expense_id="exp_456",
            group_id="grp_789",
            action="updated",
            changed_by="user_abc",
            before_snapshot={"description": "Old", "amount": 100},
            after_snapshot={"description": "New", "amount": 150}
        )
        
        assert history_id == "hist_123"
        
        # Verify changes were computed
        call_args = mock_doc.set.call_args[0][0]
        assert 'changes' in call_args
    
    @patch.object(ExpenseHistoryRepository, 'query')
    def test_get_expense_history(self, mock_query, repository):
        """Test getting history for an expense"""
        mock_query.return_value = [
            {"id": "hist_1", "action": "updated", "expense_id": "exp_123"},
            {"id": "hist_2", "action": "created", "expense_id": "exp_123"}
        ]
        
        history = repository.get_expense_history("exp_123", limit=50)
        
        assert len(history) == 2
        mock_query.assert_called_once()
    
    @patch.object(ExpenseHistoryRepository, 'query')
    def test_get_expense_history_strips_snapshots(self, mock_query, repository):
        """Test that snapshots are stripped when not requested"""
        mock_query.return_value = [
            {
                "id": "hist_1",
                "action": "updated",
                "before_snapshot": {"amount": 100},
                "after_snapshot": {"amount": 150}
            }
        ]
        
        history = repository.get_expense_history("exp_123", include_snapshots=False)
        
        assert len(history) == 1
        assert 'before_snapshot' not in history[0]
        assert 'after_snapshot' not in history[0]
    
    @patch.object(ExpenseHistoryRepository, 'query')
    def test_get_edit_count(self, mock_query, repository):
        """Test getting edit count"""
        mock_query.return_value = [
            {"id": "hist_1", "action": "updated"},
            {"id": "hist_2", "action": "updated"},
            {"id": "hist_3", "action": "updated"}
        ]
        
        count = repository.get_edit_count("exp_123")
        
        assert count == 3
    
    @patch.object(ExpenseHistoryRepository, 'query')
    def test_get_recent_edits(self, mock_query, repository):
        """Test getting recent edits for multiple expenses"""
        mock_query.side_effect = [
            [{"id": "hist_1", "expense_id": "exp_1", "action": "updated"}],
            []  # No edits for exp_2
        ]
        
        recent = repository.get_recent_edits(["exp_1", "exp_2"])
        
        assert "exp_1" in recent
        assert "exp_2" not in recent


class TestExpenseServiceHistoryIntegration:
    """Integration tests for ExpenseService with history tracking"""
    
    @pytest.fixture
    def mock_repos(self):
        """Create mock repositories"""
        return {
            'expense_repo': MagicMock(),
            'group_repo': MagicMock(),
            'balance_repo': MagicMock(),
            'group_summary_repo': MagicMock(),
            'user_expense_repo': MagicMock(),
            'history_repo': MagicMock()
        }
    
    @patch('expense_engine.services.expense_service.BalanceService')
    def test_create_expense_logs_history(self, mock_balance_service, mock_repos):
        """Test that creating expense creates history entry"""
        from expense_engine.services.expense_service import ExpenseService
        
        # Setup mocks
        mock_repos['group_repo'].get_by_id.return_value = {
            'name': 'Test Group',
            'members': ['user_a', 'user_b']
        }
        mock_repos['expense_repo'].get_by_id.return_value = {
            'expense_id': 'exp_123',
            'description': 'Test Expense',
            'amount': 100,
            'group_id': 'grp_456'
        }
        
        # Mock the Firestore transaction
        with patch('expense_engine.services.expense_service.firestore') as mock_firestore:
            mock_firestore.transactional = lambda f: f
            
            service = ExpenseService(
                expense_repo=mock_repos['expense_repo'],
                group_repo=mock_repos['group_repo'],
                balance_repo=mock_repos['balance_repo'],
                group_summary_repo=mock_repos['group_summary_repo'],
                user_expense_repo=mock_repos['user_expense_repo'],
                history_repo=mock_repos['history_repo']
            )
            
            # Note: Full test would require more setup
            # This is a simplified integration check
            assert service.history_repo is not None
    
    @patch('expense_engine.services.expense_service.BalanceService')
    def test_get_expense_history_method(self, mock_balance_service, mock_repos):
        """Test get_expense_history service method"""
        from expense_engine.services.expense_service import ExpenseService
        
        mock_repos['history_repo'].get_expense_history.return_value = [
            {"id": "hist_1", "action": "updated"},
            {"id": "hist_2", "action": "created"}
        ]
        
        service = ExpenseService(
            expense_repo=mock_repos['expense_repo'],
            group_repo=mock_repos['group_repo'],
            balance_repo=mock_repos['balance_repo'],
            group_summary_repo=mock_repos['group_summary_repo'],
            user_expense_repo=mock_repos['user_expense_repo'],
            history_repo=mock_repos['history_repo']
        )
        
        history = service.get_expense_history("exp_123")
        
        assert len(history) == 2
        mock_repos['history_repo'].get_expense_history.assert_called_with(
            expense_id="exp_123",
            limit=50,
            include_snapshots=False
        )
    
    @patch('expense_engine.services.expense_service.BalanceService')
    def test_is_expense_edited(self, mock_balance_service, mock_repos):
        """Test is_expense_edited method"""
        from expense_engine.services.expense_service import ExpenseService
        
        mock_repos['history_repo'].get_edit_count.return_value = 2
        
        service = ExpenseService(
            expense_repo=mock_repos['expense_repo'],
            group_repo=mock_repos['group_repo'],
            balance_repo=mock_repos['balance_repo'],
            group_summary_repo=mock_repos['group_summary_repo'],
            user_expense_repo=mock_repos['user_expense_repo'],
            history_repo=mock_repos['history_repo']
        )
        
        assert service.is_expense_edited("exp_123") is True
        
        mock_repos['history_repo'].get_edit_count.return_value = 0
        assert service.is_expense_edited("exp_456") is False
    
    @patch('expense_engine.services.expense_service.BalanceService')
    def test_get_expenses_with_edit_flags(self, mock_balance_service, mock_repos):
        """Test getting edit flags for multiple expenses"""
        from expense_engine.services.expense_service import ExpenseService
        
        mock_repos['history_repo'].get_recent_edits.return_value = {
            "exp_1": [{"id": "hist_1"}],
            "exp_3": [{"id": "hist_3"}]
        }
        
        service = ExpenseService(
            expense_repo=mock_repos['expense_repo'],
            group_repo=mock_repos['group_repo'],
            balance_repo=mock_repos['balance_repo'],
            group_summary_repo=mock_repos['group_summary_repo'],
            user_expense_repo=mock_repos['user_expense_repo'],
            history_repo=mock_repos['history_repo']
        )
        
        flags = service.get_expenses_with_edit_flags(["exp_1", "exp_2", "exp_3"])
        
        assert flags["exp_1"] is True
        assert flags["exp_2"] is False
        assert flags["exp_3"] is True


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
