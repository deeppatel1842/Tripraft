"""
Pytest Configuration and Fixtures
Shared fixtures for expense engine tests
"""

# pylint: disable=redefined-outer-name,unused-argument

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal


# =============================================================================
# MOCK FIRESTORE FIXTURES
# =============================================================================

@pytest.fixture
def mock_firestore_client():
    """Create a mock Firestore client"""
    client = MagicMock()
    
    # Mock collection method
    collection = MagicMock()
    client.collection.return_value = collection
    
    # Mock document method
    doc = MagicMock()
    collection.document.return_value = doc
    
    # Mock get method
    snapshot = MagicMock()
    snapshot.exists = True
    snapshot.to_dict.return_value = {}
    snapshot.id = 'test_doc_id'
    doc.get.return_value = snapshot
    
    return client


@pytest.fixture
def mock_firestore_patch(mock_firestore_client):
    """Patch firebase_admin.firestore.client"""
    with patch('firebase_admin.firestore.client', return_value=mock_firestore_client):
        yield mock_firestore_client


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_user_data():
    """Sample user document data"""
    return {
        'uid': 'user_123',
        'email': 'test@example.com',
        'display_name': 'Test User',
        'first_name': 'Test',
        'last_name': 'User',
        'photo_url': 'https://example.com/photo.jpg',
        'email_verified': True,
        'created_at': '2025-01-01T00:00:00',
        'last_login': '2025-11-25T00:00:00'
    }


@pytest.fixture
def sample_group_data():
    """Sample group document data"""
    return {
        'id': 'group_123',
        'group_id': 'group_123',
        'name': 'Test Group',
        'description': 'A test expense group',
        'created_by': 'user_123',
        'currency': 'USD',
        'members': ['user_123', 'user_456'],
        'is_active': True,
        'created_at': '2025-01-01T00:00:00',
        'updated_at': '2025-11-25T00:00:00'
    }


@pytest.fixture
def sample_expense_data():
    """Sample expense document data"""
    return {
        'id': 'expense_123',
        'expense_id': 'expense_123',
        'group_id': 'group_123',
        'description': 'Test Expense',
        'amount': Decimal('100.00'),
        'currency': 'USD',
        'paid_by': 'user_123',
        'paid_by_name': 'Test User',
        'split_type': 'equal',
        'splits': [
            {'user_id': 'user_123', 'amount': Decimal('50.00')},
            {'user_id': 'user_456', 'amount': Decimal('50.00')}
        ],
        'category': 'food',
        'expense_date': '2025-11-25T00:00:00',
        'created_by': 'user_123',
        'is_deleted': False,
        'created_at': '2025-11-25T00:00:00',
        'updated_at': '2025-11-25T00:00:00'
    }


@pytest.fixture
def sample_settlement_data():
    """Sample settlement document data"""
    return {
        'id': 'settlement_123',
        'settlement_id': 'settlement_123',
        'group_id': 'group_123',
        'payer_id': 'user_456',
        'payee_id': 'user_123',
        'amount': Decimal('50.00'),
        'currency': 'USD',
        'status': 'pending',
        'method': 'cash',
        'notes': 'Test settlement',
        'created_by': 'user_456',
        'created_at': '2025-11-25T00:00:00'
    }


@pytest.fixture
def sample_invitation_data():
    """Sample invitation document data"""
    return {
        'id': 'invitation_123',
        'invitation_id': 'invitation_123',
        'group_id': 'group_123',
        'group_name': 'Test Group',
        'email': 'invitee@example.com',
        'invited_by': 'user_123',
        'invited_by_name': 'Test User',
        'status': 'pending',
        'role': 'member',
        'expires_at': '2025-12-25T00:00:00',
        'created_at': '2025-11-25T00:00:00'
    }


@pytest.fixture
def sample_balance_data():
    """Sample group balance data"""
    return {
        'group_id': 'group_123',
        'balances': {
            'user_123': Decimal('50.00'),
            'user_456': Decimal('-50.00')
        },
        'total_spent': Decimal('100.00'),
        'last_updated': '2025-11-25T00:00:00'
    }


# =============================================================================
# MOCK REPOSITORY FIXTURES
# =============================================================================

@pytest.fixture
def mock_user_repo(sample_user_data):
    """Mock UserRepository"""
    repo = MagicMock()
    repo.get_by_id.return_value = sample_user_data
    repo.get_user_by_email.return_value = sample_user_data
    repo.create_or_update_user.return_value = sample_user_data
    return repo


@pytest.fixture
def mock_group_repo(sample_group_data):
    """Mock GroupRepository"""
    repo = MagicMock()
    repo.get_by_id.return_value = sample_group_data
    repo.get_user_groups.return_value = [sample_group_data]
    repo.get_member.return_value = {'user_id': 'user_123', 'role': 'admin'}
    return repo


@pytest.fixture
def mock_expense_repo(sample_expense_data):
    """Mock ExpenseRepository"""
    repo = MagicMock()
    repo.get_by_id.return_value = sample_expense_data
    repo.get_group_expenses.return_value = {
        'expenses': [sample_expense_data],
        'total': 1,
        'has_more': False
    }
    return repo


@pytest.fixture
def mock_settlement_repo(sample_settlement_data):
    """Mock SettlementRepository"""
    repo = MagicMock()
    repo.get_by_id.return_value = sample_settlement_data
    repo.get_group_settlements.return_value = [sample_settlement_data]
    return repo


@pytest.fixture
def mock_invitation_repo(sample_invitation_data):
    """Mock InvitationRepository"""
    repo = MagicMock()
    repo.get_by_id.return_value = sample_invitation_data
    repo.get_pending_invitations.return_value = []
    repo.get_collection.return_value.document.return_value.id = 'new_invitation_id'
    return repo


@pytest.fixture
def mock_balance_repo(sample_balance_data):
    """Mock BalanceRepository"""
    repo = MagicMock()
    repo.get_group_balances.return_value = sample_balance_data
    return repo
