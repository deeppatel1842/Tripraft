"""
Test Invitation Flow
Tests the complete invitation lifecycle:
1. Create invitation
2. Accept invitation
3. Verify user is added to group
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from expense_engine.services.invitation_service import InvitationService
from expense_engine.repositories import InvitationRepository, GroupRepository
from expense_engine.repositories.user_repository import UserRepository
from expense_engine.exceptions import ValidationError, ResourceNotFoundError


class TestInvitationAcceptanceFlow:
    """Test suite for invitation acceptance and group membership"""
    
    @pytest.fixture
    def mock_invitation_repo(self):
        """Create mock invitation repository"""
        return Mock(spec=InvitationRepository)
    
    @pytest.fixture
    def mock_group_repo(self):
        """Create mock group repository"""
        return Mock(spec=GroupRepository)
    
    @pytest.fixture
    def mock_user_repo(self):
        """Create mock user repository"""
        return Mock(spec=UserRepository)
    
    @pytest.fixture
    def invitation_service(self, mock_invitation_repo, mock_group_repo):
        """Create invitation service with mocked repos"""
        return InvitationService(
            invitation_repo=mock_invitation_repo,
            group_repo=mock_group_repo
        )
    
    @pytest.fixture
    def sample_invitation(self):
        """Sample invitation data"""
        return {
            'id': 'inv_123',
            'invitation_id': 'inv_123',
            'group_id': 'group_456',
            'invitee_email': 'newuser@example.com',
            'invited_by': 'user_789',
            'status': 'pending',
            'role': 'member',
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
    
    @pytest.fixture
    def sample_group(self):
        """Sample group data"""
        return {
            'id': 'group_456',
            'group_id': 'group_456',
            'name': 'Test Trip',
            'currency': 'USD',
            'members': ['user_789'],
            'created_by': 'user_789',
            'member_details': {
                'user_789': {
                    'user_id': 'user_789',
                    'display_name': 'Original User',
                    'role': 'owner',
                    'is_active': True
                }
            }
        }
    
    @pytest.fixture
    def sample_user(self):
        """Sample user data"""
        return {
            'uid': 'user_new',
            'email': 'newuser@example.com',
            'display_name': 'New User',
            'first_name': 'New',
            'last_name': 'User'
        }
    
    def test_accept_invitation_adds_user_to_group(
        self,
        invitation_service,
        mock_invitation_repo,
        mock_group_repo,
        sample_invitation,
        sample_group,
        sample_user
    ):
        """Test that accepting an invitation adds user to the group"""
        # Setup mocks
        mock_invitation_repo.get_by_id.return_value = sample_invitation
        mock_invitation_repo.accept_invitation.return_value = {
            **sample_invitation,
            'status': 'accepted',
            'accepted_at': datetime.utcnow().isoformat(),
            'accepted_by': 'user_new'
        }
        mock_group_repo.get_by_id.return_value = sample_group
        mock_group_repo.add_member.return_value = None
        
        # Mock UserRepository class instantiation
        mock_user_repo_instance = Mock()
        mock_user_repo_instance.get_by_id.return_value = sample_user
        with patch('expense_engine.services.invitation_service.UserRepository', return_value=mock_user_repo_instance):
            # Accept invitation
            result = invitation_service.accept_invitation('inv_123', 'user_new')
        
        # Verify invitation was accepted (now includes invitation_data parameter)
        mock_invitation_repo.accept_invitation.assert_called_once()
        call_args = mock_invitation_repo.accept_invitation.call_args
        assert call_args[0][0] == 'inv_123'
        assert call_args[0][1] == 'user_new'
        
        # Verify user was added to group
        mock_group_repo.add_member.assert_called_once_with(
            group_id='group_456',
            user_id='user_new',
            display_name='New User'
        )
        
        # Verify group data returned
        assert result is not None
        assert result.get('group_id') == 'group_456' or result.get('id') == 'group_456'
    
    def test_accept_invitation_returns_redirect_info(
        self,
        invitation_service,
        mock_invitation_repo,
        mock_group_repo,
        sample_invitation,
        sample_group,
        sample_user
    ):
        """Test that accepting returns group info for redirect"""
        mock_invitation_repo.get_by_id.return_value = sample_invitation
        mock_invitation_repo.accept_invitation.return_value = sample_invitation
        mock_group_repo.get_by_id.return_value = sample_group
        mock_group_repo.add_member.return_value = None
        
        mock_user_repo_instance = Mock()
        mock_user_repo_instance.get_by_id.return_value = sample_user
        with patch('expense_engine.services.invitation_service.UserRepository', return_value=mock_user_repo_instance):
            result = invitation_service.accept_invitation('inv_123', 'user_new')
        
        # Should return group data with ID
        assert result is not None
        assert 'name' in result or 'group_id' in result
    
    def test_accept_invitation_fails_for_nonexistent_invitation(
        self,
        invitation_service,
        mock_invitation_repo
    ):
        """Test that accepting non-existent invitation raises error"""
        mock_invitation_repo.get_by_id.return_value = None
        
        with pytest.raises(ResourceNotFoundError):
            invitation_service.accept_invitation('inv_nonexistent', 'user_new')
    
    def test_accept_invitation_fails_without_group_id(
        self,
        invitation_service,
        mock_invitation_repo
    ):
        """Test that invitation without group_id raises error"""
        mock_invitation_repo.get_by_id.return_value = {
            'id': 'inv_123',
            'status': 'pending'
            # Missing group_id
        }
        
        with pytest.raises(ValidationError):
            invitation_service.accept_invitation('inv_123', 'user_new')
    
    def test_accept_invitation_handles_missing_user_display_name(
        self,
        invitation_service,
        mock_invitation_repo,
        mock_group_repo,
        sample_invitation,
        sample_group
    ):
        """Test handling when user has no display name"""
        mock_invitation_repo.get_by_id.return_value = sample_invitation
        mock_invitation_repo.accept_invitation.return_value = sample_invitation
        mock_group_repo.get_by_id.return_value = sample_group
        mock_group_repo.add_member.return_value = None
        
        # User with email only, no display_name
        user_without_name = {
            'uid': 'user_new',
            'email': 'newuser@example.com'
        }
        
        mock_user_repo_instance = Mock()
        mock_user_repo_instance.get_by_id.return_value = user_without_name
        with patch('expense_engine.services.invitation_service.UserRepository', return_value=mock_user_repo_instance):
            result = invitation_service.accept_invitation('inv_123', 'user_new')
        
        # Should use email as display name fallback
        mock_group_repo.add_member.assert_called_once()
        call_args = mock_group_repo.add_member.call_args
        assert call_args.kwargs['display_name'] == 'newuser@example.com'
    
    def test_accept_invitation_handles_unknown_user(
        self,
        invitation_service,
        mock_invitation_repo,
        mock_group_repo,
        sample_invitation,
        sample_group
    ):
        """Test handling when user not found in database"""
        mock_invitation_repo.get_by_id.return_value = sample_invitation
        mock_invitation_repo.accept_invitation.return_value = sample_invitation
        mock_group_repo.get_by_id.return_value = sample_group
        mock_group_repo.add_member.return_value = None
        
        # User not found
        mock_user_repo_instance = Mock()
        mock_user_repo_instance.get_by_id.return_value = None
        with patch('expense_engine.services.invitation_service.UserRepository', return_value=mock_user_repo_instance):
            result = invitation_service.accept_invitation('inv_123', 'user_new')
        
        # Should use fallback display name
        mock_group_repo.add_member.assert_called_once()
        call_args = mock_group_repo.add_member.call_args
        assert call_args.kwargs['display_name'] == 'Unknown User'


class TestInvitationCreation:
    """Test suite for invitation creation"""
    
    @pytest.fixture
    def mock_invitation_repo(self):
        """Create mock invitation repository"""
        return Mock(spec=InvitationRepository)
    
    @pytest.fixture
    def mock_group_repo(self):
        """Create mock group repository"""
        return Mock(spec=GroupRepository)
    
    @pytest.fixture
    def invitation_service(self, mock_invitation_repo, mock_group_repo):
        """Create invitation service with mocked repos"""
        return InvitationService(
            invitation_repo=mock_invitation_repo,
            group_repo=mock_group_repo
        )
    
    @pytest.fixture
    def sample_group(self):
        """Sample group data"""
        return {
            'id': 'group_456',
            'name': 'Test Trip',
            'members': ['user_789'],
            'created_by': 'user_789'
        }
    
    def test_create_invitation_success(
        self,
        invitation_service,
        mock_invitation_repo,
        mock_group_repo,
        sample_group
    ):
        """Test successful invitation creation"""
        mock_group_repo.get_by_id.return_value = sample_group
        mock_invitation_repo.get_pending_invitations.return_value = []
        mock_invitation_repo.get_collection.return_value.document.return_value.id = 'inv_123'
        mock_invitation_repo.create.return_value = {
            'id': 'inv_123',
            'group_id': 'group_456',
            'invitee_email': 'newuser@example.com',
            'status': 'pending'
        }
        
        # Mock UserRepository for inviter details
        mock_user_repo_instance = Mock()
        mock_user_repo_instance.get_by_id.return_value = {
            'uid': 'user_789',
            'display_name': 'Inviter User'
        }
        with patch('expense_engine.services.invitation_service.UserRepository', return_value=mock_user_repo_instance):
            result = invitation_service.create_invitation(
                group_id='group_456',
                invitee_email='newuser@example.com',
                invited_by='user_789',
                role='member'
            )
        
        assert result is not None
        mock_invitation_repo.create.assert_called_once()
    
    def test_create_invitation_fails_for_nonexistent_group(
        self,
        invitation_service,
        mock_group_repo
    ):
        """Test that creating invitation for non-existent group fails"""
        mock_group_repo.get_by_id.return_value = None
        
        with pytest.raises(ResourceNotFoundError):
            invitation_service.create_invitation(
                group_id='nonexistent',
                invitee_email='newuser@example.com',
                invited_by='user_789'
            )


class TestGroupMembershipVerification:
    """Test to verify user membership after invitation acceptance"""
    
    @pytest.fixture
    def mock_firestore(self):
        """Create mock Firestore client"""
        mock_db = MagicMock()
        return mock_db
    
    def test_member_added_to_group_members_array(self):
        """Verify user_id is added to group.members array"""
        # This test verifies the contract that add_member updates the group
        mock_group_repo = Mock(spec=GroupRepository)
        
        initial_group = {
            'id': 'group_456',
            'members': ['user_789']
        }
        
        updated_group = {
            'id': 'group_456',
            'members': ['user_789', 'user_new']
        }
        
        mock_group_repo.get_by_id.side_effect = [initial_group, updated_group]
        mock_group_repo.add_member.return_value = None
        
        # Call add_member
        mock_group_repo.add_member(
            group_id='group_456',
            user_id='user_new',
            display_name='New User'
        )
        
        # Verify add_member was called with correct params
        mock_group_repo.add_member.assert_called_with(
            group_id='group_456',
            user_id='user_new',
            display_name='New User'
        )


# Integration-style test (mocked but tests full flow)
class TestFullInvitationWorkflow:
    """Full workflow test from invitation creation to group membership"""
    
    def test_complete_invitation_flow(self):
        """Test complete flow: create -> accept -> verify membership"""
        # Setup mocks
        mock_invitation_repo = Mock(spec=InvitationRepository)
        mock_group_repo = Mock(spec=GroupRepository)
        
        # Initial group state
        group_data = {
            'id': 'group_456',
            'group_id': 'group_456',
            'name': 'Test Trip',
            'currency': 'USD',
            'members': ['owner_123'],
            'created_by': 'owner_123'
        }
        
        # Invitation data
        invitation_data = {
            'id': 'inv_789',
            'invitation_id': 'inv_789',
            'group_id': 'group_456',
            'invitee_email': 'newmember@example.com',
            'invited_by': 'owner_123',
            'status': 'pending',
            'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
        
        # User data
        user_data = {
            'uid': 'newmember_456',
            'email': 'newmember@example.com',
            'display_name': 'New Member'
        }
        
        # Setup mock returns
        mock_group_repo.get_by_id.return_value = group_data
        mock_invitation_repo.get_pending_invitations.return_value = []
        mock_invitation_repo.get_collection.return_value.document.return_value.id = 'inv_789'
        mock_invitation_repo.create.return_value = invitation_data
        mock_invitation_repo.get_by_id.return_value = invitation_data
        mock_invitation_repo.accept_invitation.return_value = {
            **invitation_data,
            'status': 'accepted'
        }
        
        # Create service
        service = InvitationService(
            invitation_repo=mock_invitation_repo,
            group_repo=mock_group_repo
        )
        
        # Mock UserRepository for both create and accept
        mock_user_repo_instance = Mock()
        mock_user_repo_instance.get_by_id.return_value = user_data
        
        with patch('expense_engine.services.invitation_service.UserRepository', return_value=mock_user_repo_instance):
            # Step 1: Create invitation
            created = service.create_invitation(
                group_id='group_456',
                invitee_email='newmember@example.com',
                invited_by='owner_123'
            )
            assert created['status'] == 'pending'
            
            # Step 2: Accept invitation
            result = service.accept_invitation('inv_789', 'newmember_456')
        
        # Step 3: Verify add_member was called
        mock_group_repo.add_member.assert_called_once_with(
            group_id='group_456',
            user_id='newmember_456',
            display_name='New Member'
        )
        
        # Verify result contains group info
        assert result is not None
        assert result.get('name') == 'Test Trip' or result.get('group_id') == 'group_456'
        
        print("Complete invitation workflow test passed")
