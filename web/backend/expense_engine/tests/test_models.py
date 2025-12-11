"""
Unit Tests for Expense Engine Models
Tests for Pydantic validation and model behavior
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError


# =============================================================================
# EXPENSE MODEL TESTS
# =============================================================================

class TestExpenseModel:
    """Test Expense Pydantic model validation"""
    
    def test_valid_expense_creation(self):
        """Test creating a valid expense"""
        from expense_engine.models.expense import Expense, ExpenseSplit
        
        splits = [
            ExpenseSplit(user_id='user_1', amount=Decimal('50.00')),
            ExpenseSplit(user_id='user_2', amount=Decimal('50.00'))
        ]
        
        expense = Expense(
            group_id='group_123',
            description='Test Expense',
            amount=Decimal('100.00'),
            paid_by='user_1',
            created_by='user_1',
            splits=splits
        )
        
        assert expense.amount == Decimal('100.00')
        assert expense.group_id == 'group_123'
        assert len(expense.splits) == 2
        assert expense.is_deleted is False
    
    def test_expense_requires_positive_amount(self):
        """Test that expense amount must be positive"""
        from expense_engine.models.expense import Expense
        
        with pytest.raises(ValidationError):
            Expense(
                group_id='group_123',
                description='Test',
                amount=Decimal('-10.00'),
                paid_by='user_1',
                splits=[]
            )
    
    def test_expense_requires_non_empty_description(self):
        """Test that expense description cannot be empty"""
        from expense_engine.models.expense import Expense
        
        with pytest.raises(ValidationError):
            Expense(
                group_id='group_123',
                description='',
                amount=Decimal('100.00'),
                paid_by='user_1',
                splits=[]
            )
    
    def test_expense_split_validation(self):
        """Test that split amounts must be non-negative"""
        from expense_engine.models.expense import ExpenseSplit
        
        with pytest.raises(ValidationError):
            ExpenseSplit(user_id='user_1', amount=Decimal('-50.00'))
    
    def test_expense_to_dict(self):
        """Test expense serialization to dictionary"""
        from expense_engine.models.expense import Expense, ExpenseSplit
        
        expense = Expense(
            group_id='group_123',
            description='Test',
            amount=Decimal('100.00'),
            paid_by='user_1',
            created_by='user_1',
            splits=[ExpenseSplit(user_id='user_1', amount=Decimal('100.00'))]
        )
        
        data = expense.model_dump()
        
        assert 'group_id' in data
        assert 'amount' in data
        assert 'splits' in data


# =============================================================================
# GROUP MODEL TESTS
# =============================================================================

class TestGroupModel:
    """Test Group Pydantic model validation"""
    
    def test_valid_group_creation(self):
        """Test creating a valid group"""
        from expense_engine.models.group import Group
        
        group = Group(
            name='Test Group',
            description='A test group',
            created_by='user_123',
            currency='USD'
        )
        
        assert group.name == 'Test Group'
        assert group.is_active is True
        assert group.currency == 'USD'
    
    def test_group_requires_name(self):
        """Test that group name is required"""
        from expense_engine.models.group import Group
        
        with pytest.raises(ValidationError):
            Group(
                name='',
                created_by='user_123'
            )
    
    def test_group_name_max_length(self):
        """Test that group name has max length"""
        from expense_engine.models.group import Group
        
        # Name should be reasonable length
        long_name = 'A' * 256  # Very long name
        
        with pytest.raises(ValidationError):
            Group(
                name=long_name,
                created_by='user_123'
            )


# =============================================================================
# MEMBER MODEL TESTS
# =============================================================================

class TestMemberModel:
    """Test GroupMember Pydantic model validation"""
    
    def test_valid_member_creation(self):
        """Test creating a valid group member"""
        from expense_engine.models.group import GroupMember
        from expense_engine.constants import GroupRole
        
        member = GroupMember(
            user_id='user_123',
            group_id='group_456',
            role=GroupRole.MEMBER
        )
        
        assert member.user_id == 'user_123'
        assert member.role == GroupRole.MEMBER
        assert member.is_active is True
    
    def test_member_role_validation(self):
        """Test that member role must be valid"""
        from expense_engine.models.group import GroupMember
        
        with pytest.raises(ValidationError):
            GroupMember(
                user_id='user_123',
                group_id='group_456',
                role='invalid_role'
            )
    
    def test_admin_role(self):
        """Test admin role assignment"""
        from expense_engine.models.group import GroupMember
        from expense_engine.constants import GroupRole
        
        member = GroupMember(
            user_id='user_123',
            group_id='group_456',
            role=GroupRole.ADMIN
        )
        
        assert member.role == GroupRole.ADMIN


# =============================================================================
# SETTLEMENT MODEL TESTS
# =============================================================================

class TestSettlementModel:
    """Test Settlement Pydantic model validation"""
    
    def test_valid_settlement_creation(self):
        """Test creating a valid settlement"""
        from expense_engine.models.settlement import Settlement
        
        settlement = Settlement(
            group_id='group_123',
            from_user_id='user_456',
            to_user_id='user_123',
            amount=Decimal('50.00'),
            recorded_by='user_456'
        )
        
        assert settlement.amount == Decimal('50.00')
        assert settlement.is_deleted is False
    
    def test_settlement_requires_positive_amount(self):
        """Test that settlement amount must be positive"""
        from expense_engine.models.settlement import Settlement
        
        with pytest.raises(ValidationError):
            Settlement(
                group_id='group_123',
                from_user_id='user_456',
                to_user_id='user_123',
                amount=Decimal('0.00'),
                recorded_by='user_456'
            )
    
    def test_settlement_different_payer_payee(self):
        """Test that payer and payee must be different"""
        from expense_engine.models.settlement import Settlement
        
        with pytest.raises(ValidationError):
            Settlement(
                group_id='group_123',
                from_user_id='user_123',
                to_user_id='user_123',  # Same as payer
                amount=Decimal('50.00'),
                recorded_by='user_123'
            )


# =============================================================================
# INVITATION MODEL TESTS
# =============================================================================

class TestInvitationModel:
    """Test Invitation Pydantic model validation"""
    
    def test_valid_invitation_creation(self):
        """Test creating a valid invitation"""
        from expense_engine.models.invitation import Invitation
        
        invitation = Invitation(
            group_id='group_123',
            group_name='Test Group',
            email='invitee@example.com',
            invited_by='user_123'
        )
        
        assert invitation.status == 'pending'
        assert invitation.email == 'invitee@example.com'
    
    def test_invitation_email_validation(self):
        """Test that invitation email field is present and required"""
        from expense_engine.models.invitation import Invitation
        
        # Test that email field is required
        with pytest.raises(ValidationError):
            Invitation(
                group_id='group_123',
                group_name='Test Group',
                # Missing email field
                invited_by='user_123'
            )
    
    def test_invitation_status_values(self):
        """Test invitation status must be valid"""
        from expense_engine.models.invitation import Invitation
        
        invitation = Invitation(
            group_id='group_123',
            group_name='Test Group',
            email='test@example.com',
            invited_by='user_123',
            status='pending'
        )
        
        assert invitation.status == 'pending'


# =============================================================================
# BALANCE MODEL TESTS
# =============================================================================

class TestBalanceModel:
    """Test Balance model calculations"""
    
    def test_balance_calculation(self):
        """Test that balances are calculated correctly"""
        from expense_engine.models.balance import GroupBalance, Balance
        
        # GroupBalance uses Dict[str, Decimal] for balances
        group_balance = GroupBalance(
            group_id='group_123',
            balances={
                'user_1': Decimal('50.00'),
                'user_2': Decimal('-50.00')
            }
        )
        
        assert group_balance.group_id == 'group_123'
        assert len(group_balance.balances) == 2
        
        # Test individual balance
        balance = Balance(
            group_id='group_123',
            user_id='user_1',
            balance=Decimal('50.00')
        )
        assert balance.is_owed_money()
    
    def test_balance_sum_zero(self):
        """Test that all balances sum to zero"""
        from expense_engine.models.balance import Balance
        
        user_balances = [
            Balance(group_id='group_123', user_id='user_1', balance=Decimal('30.00')),
            Balance(group_id='group_123', user_id='user_2', balance=Decimal('20.00')),
            Balance(group_id='group_123', user_id='user_3', balance=Decimal('-50.00'))
        ]
        
        total = sum(b.balance for b in user_balances)
        assert total == Decimal('0.00')
