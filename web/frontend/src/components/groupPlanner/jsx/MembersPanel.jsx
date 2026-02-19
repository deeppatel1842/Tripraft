import React, { useState } from 'react';
import { Users, Crown, Trash2, X, LogOut } from 'lucide-react';
import '../css/MembersPanel.css';

const MembersPanel = ({
  isOpen,
  onClose,
  groupId,
  groupName,
  currentUserId,
  members = [],
  onRemoveMember,
  onLeaveGroup,
  isOwner = false
}) => {
  const [removingMemberId, setRemovingMemberId] = useState(null);
  const [showConfirm, setShowConfirm] = useState(null);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);
  const [message, setMessage] = useState(null);

  const handleRemove = async (member) => {
    if (!isOwner || member.is_owner) return;
    
    setRemovingMemberId(member.id);
    setMessage(null);
    
    try {
      const response = await fetch(
        `/api/v2/group-planner/groups/${groupId}/members/${member.id}`,
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
        setMessage({ 
          type: 'success', 
          text: `${member.name} has been removed from the group` 
        });
        
        if (onRemoveMember) {
          onRemoveMember(member.id, data.data);
        }
        
        setTimeout(() => {
          onClose();
          setMessage(null);
        }, 2000);
      } else {
        setMessage({ 
          type: 'error', 
          text: data.error || 'Failed to remove member' 
        });
      }
    } catch {
      setMessage({ 
        type: 'error', 
        text: 'Network error. Please try again.' 
      });
    } finally {
      setRemovingMemberId(null);
      setShowConfirm(null);
    }
  };

  const handleLeaveGroup = async () => {
    setIsLeaving(true);
    setMessage(null);

    try {
      const response = await fetch(
        `/api/v2/group-planner/groups/${groupId}/leave`,
        {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json',
          },
        }
      );

      const data = await response.json();

      if (data.success) {
        setMessage({ type: 'success', text: 'You have left the group.' });
        if (onLeaveGroup) {
          onLeaveGroup(groupId);
        }
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to leave group' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error. Please try again.' });
    } finally {
      setIsLeaving(false);
      setShowLeaveConfirm(false);
    }
  };

  const getMemberDisplayName = (member) => {
    return member.name || member.email?.split('@')[0] || 'Unknown';
  };

  const getJoinedDate = (joinedAt) => {
    if (!joinedAt) return '';
    try {
      const date = new Date(joinedAt);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return '';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="members-panel-overlay" onClick={onClose}>
      <div className="members-panel" onClick={(e) => e.stopPropagation()}>
        <div className="members-panel-header">
          <div className="members-panel-title">
            <Users size={18} />
            <span>Group Members</span>
            {groupName && <span className="group-name">• {groupName}</span>}
          </div>
          <button className="close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="members-panel-content">
          {message && (
            <div className={`message ${message.type}`}>
              {message.text}
            </div>
          )}

          <div className="members-list-compact">
            {members.map((member) => {
              const displayName = getMemberDisplayName(member);
              // Use the backend's can_remove field
              const canRemove = member.can_remove;
              
              return (
                <div key={member.id} className="member-item-compact">
                  {/* Delete icon shown first for non-owner members */}
                  {!member.is_owner && (
                    <div className="member-actions">
                      {canRemove ? (
                        showConfirm === member.id ? (
                          <div className="confirm-actions">
                            <button 
                              className="confirm-yes"
                              onClick={() => handleRemove(member)}
                              disabled={removingMemberId === member.id}
                            >
                              {removingMemberId === member.id ? '...' : 'Yes'}
                            </button>
                            <button 
                              className="confirm-no"
                              onClick={() => setShowConfirm(null)}
                            >
                              No
                            </button>
                          </div>
                        ) : (
                          <button 
                            className="remove-btn-small"
                            onClick={() => setShowConfirm(member.id)}
                            title={`Remove ${displayName}`}
                          >
                            <Trash2 size={14} />
                          </button>
                        )
                      ) : (
                        <Trash2 size={14} className="delete-icon-disabled" />
                      )}
                    </div>
                  )}
                  
                  <div className="member-avatar-small">
                    {displayName.charAt(0).toUpperCase()}
                  </div>
                  
                  <div className="member-info-compact">
                    <div className="member-name-small">
                      {displayName}
                      {member.is_owner && (
                        <Crown size={12} className="owner-icon" />
                      )}
                    </div>
                    <div className="member-meta-small">
                      <span className="member-email-small">{member.email}</span>
                      {getJoinedDate(member.joined_at) && (
                        <span className="member-joined-small">• Joined {getJoinedDate(member.joined_at)}</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {!isOwner && (
            <div className="members-panel-footer members-panel-footer--actions">
              <div className="members-panel-footer-info">
                <Crown size={14} />
                Only the group owner can remove members
              </div>
              {!showLeaveConfirm ? (
                <button
                  className="leave-group-btn"
                  onClick={() => setShowLeaveConfirm(true)}
                  disabled={isLeaving}
                >
                  <LogOut size={14} />
                  Leave Group
                </button>
              ) : (
                <div className="leave-confirm">
                  <p className="leave-confirm-text">Are you sure you want to leave this group?</p>
                  <div className="leave-confirm-actions">
                    <button
                      className="leave-confirm-btn leave-confirm-btn--cancel"
                      onClick={() => setShowLeaveConfirm(false)}
                      disabled={isLeaving}
                    >
                      Cancel
                    </button>
                    <button
                      className="leave-confirm-btn leave-confirm-btn--confirm"
                      onClick={handleLeaveGroup}
                      disabled={isLeaving}
                    >
                      {isLeaving ? 'Leaving...' : 'Confirm Leave'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MembersPanel;
