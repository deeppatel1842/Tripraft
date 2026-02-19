import React, { useState, useEffect } from 'react';
import { X, Crown, Trash2, AlertTriangle, CheckCircle, UserPlus } from 'lucide-react';
import '../css/MembersModal.css';

const MembersModal = ({
  isOpen,
  onClose,
  groupId,
  groupName,
  currentUserId,
  onRemoveMember
}) => {
  const [members, setMembers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [removingMemberId, setRemovingMemberId] = useState(null);
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(null);
  const [removeSuccess, setRemoveSuccess] = useState(null);

  useEffect(() => {
    if (isOpen && groupId) {
      fetchMembers();
    }
  }, [isOpen, groupId]);

  const fetchMembers = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/v2/group-planner/groups/${groupId}/members`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMembers(data.data.members || []);
      } else {
        setError(data.error || 'Failed to load members');
      }
    } catch (err) {
      setError('Failed to load members');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (removingMemberId) return; // Prevent double-click
    
    setRemovingMemberId(memberId);
    setError(null);
    
    try {
      const response = await fetch(
        `/api/v2/group-planner/groups/${groupId}/members/${memberId}`,
        {
          method: 'DELETE',
          credentials: 'include',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          }
        }
      );
      
      const data = await response.json();
      
      if (data.success) {
        // Show success message
        setRemoveSuccess(data.data);
        
        // Remove member from local state
        setMembers(prev => prev.filter(m => m.id !== memberId));
        
        // Hide confirmation dialog
        setShowRemoveConfirm(null);
        
        // Notify parent component
        if (onRemoveMember) {
          onRemoveMember(memberId, data.data);
        }
        
        // Hide success message after 3 seconds
        setTimeout(() => {
          setRemoveSuccess(null);
        }, 3000);
        
      } else {
        setError(data.error || 'Failed to remove member');
      }
    } catch (err) {
      setError('Failed to remove member');
    } finally {
      setRemovingMemberId(null);
    }
  };

  const getMemberDisplayName = (member) => {
    return member.name || member.email?.split('@')[0] || 'Unknown';
  };

  const isCurrentUserOwner = () => {
    return members.some(m => m.id === currentUserId && m.is_owner);
  };

  if (!isOpen) return null;

  return (
    <div className="members-modal-overlay">
      <div className="members-modal">
        <div className="members-modal-header">
          <h2>
            Group Members
            {groupName && <span className="group-name-subtitle">in {groupName}</span>}
          </h2>
          <button 
            className="close-button" 
            onClick={onClose}
            aria-label="Close members modal"
          >
            <X size={24} />
          </button>
        </div>

        <div className="members-modal-content">
          {/* Success Message */}
          {removeSuccess && (
            <div className="success-message">
              <CheckCircle size={20} />
              <div>
                <div className="success-title">{removeSuccess.message}</div>
                <div className="success-subtitle">{removeSuccess.reinvite_message}</div>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="error-message">
              <AlertTriangle size={20} />
              {error}
            </div>
          )}

          {/* Loading State */}
          {isLoading ? (
            <div className="loading-members">
              <div className="loading-spinner"></div>
              <p>Loading members...</p>
            </div>
          ) : (
            <>
              {/* Members List */}
              <div className="members-list">
                <div className="members-count">
                  {members.length} {members.length === 1 ? 'member' : 'members'}
                </div>

                {members.map((member) => (
                  <div key={member.id} className="member-item">
                    <div className="member-info">
                      <div className="member-avatar">
                        {getMemberDisplayName(member).charAt(0).toUpperCase()}
                      </div>
                      <div className="member-details">
                        <div className="member-name">
                          {getMemberDisplayName(member)}
                          {member.is_owner && (
                            <span className="owner-badge">
                              <Crown size={16} />
                              Owner
                            </span>
                          )}
                        </div>
                        <div className="member-email">{member.email}</div>
                        {member.joined_at && (
                          <div className="member-joined">
                            Joined {new Date(member.joined_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Remove Button (only for owner, not for themselves) */}
                    {isCurrentUserOwner() && member.can_remove && (
                      <button
                        className="remove-member-btn"
                        onClick={() => setShowRemoveConfirm(member)}
                        disabled={removingMemberId === member.id}
                        title={`Remove ${getMemberDisplayName(member)} from group`}
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                ))}

                {members.length === 0 && !isLoading && (
                  <div className="no-members">
                    <UserPlus size={48} />
                    <p>No members found</p>
                  </div>
                )}
              </div>

              {/* Owner Info for Non-Owners */}
              {!isCurrentUserOwner() && (
                <div className="owner-info">
                  <Crown size={16} />
                  Only the group owner can remove members from the group.
                </div>
              )}
            </>
          )}
        </div>

        {/* Remove Confirmation Dialog */}
        {showRemoveConfirm && (
          <div className="confirm-overlay">
            <div className="confirm-dialog">
              <div className="confirm-header">
                <AlertTriangle size={24} className="warning-icon" />
                <h3>Remove Member</h3>
              </div>
              
              <div className="confirm-content">
                <p>
                  Are you sure you want to remove <strong>{getMemberDisplayName(showRemoveConfirm)}</strong> from the group?
                </p>
                <p className="confirm-warning">
                  This will also remove them from any linked expenses. They will need a new invitation to rejoin.
                </p>
              </div>
              
              <div className="confirm-actions">
                <button 
                  className="cancel-btn"
                  onClick={() => setShowRemoveConfirm(null)}
                >
                  Cancel
                </button>
                <button 
                  className="remove-btn"
                  onClick={() => handleRemoveMember(showRemoveConfirm.id)}
                  disabled={removingMemberId === showRemoveConfirm.id}
                >
                  {removingMemberId === showRemoveConfirm.id ? 'Removing...' : 'Remove Member'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MembersModal;