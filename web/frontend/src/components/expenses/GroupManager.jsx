import React, { useState, useEffect } from 'react';
import { Users, Plus, Mail, Trash2, Clock, X } from 'lucide-react';
import expenseApi from '../../services/expenseApi';
import { currencies } from '../../hooks/useExpense';

const GroupManager = ({ 
  groups, 
  activeGroupId, 
  activeGroup,
  members,
  loading,
  onGroupChange, 
  onGroupCreate,
  onGroupDelete,
  onMemberAdd,
  onMemberRemove,
  showAlert,
  currentUser
}) => {
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupCurrency, setNewGroupCurrency] = useState('USD');
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [inviting, setInviting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [pendingInvitations, setPendingInvitations] = useState([]);
  const [loadingInvitations, setLoadingInvitations] = useState(false);
  const [activeTab, setActiveTab] = useState('members'); // 'members' or 'pending'

  // Load pending invitations when active group changes
  useEffect(() => {
    if (activeGroupId) {
      loadPendingInvitations();
    } else {
      setPendingInvitations([]);
    }
  }, [activeGroupId]);

  // 🔄 Auto-refresh pending invitations every 10 seconds when viewing "Pending" tab
  // This ensures User A sees when User B accepts an invitation
  useEffect(() => {
    let intervalId = null;
    
    if (activeGroupId && activeTab === 'pending') {
      // Initial load
      loadPendingInvitations();
      
      // Set up polling every 10 seconds
      intervalId = setInterval(() => {
        console.log('🔄 Auto-refreshing pending invitations...');
        loadPendingInvitations();
      }, 10000); // 10 seconds
    }
    
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
        console.log('🛑 Stopped auto-refresh for pending invitations');
      }
    };
  }, [activeGroupId, activeTab]);

  // 🔔 Listen for global invitation acceptance events
  useEffect(() => {
    const handleInvitationAccepted = () => {
      console.log('🔔 Invitation accepted event received, refreshing pending list...');
      if (activeGroupId) {
        loadPendingInvitations();
        // Also refresh groups to show new member
        if (onGroupUpdate) {
          onGroupUpdate();
        }
      }
    };
    
    window.addEventListener('invitationAccepted', handleInvitationAccepted);
    
    return () => {
      window.removeEventListener('invitationAccepted', handleInvitationAccepted);
    };
  }, [activeGroupId]);

  const loadPendingInvitations = async () => {
    if (!activeGroupId) return;
    
    console.log('📨 Loading pending invitations for group:', activeGroupId);
    setLoadingInvitations(true);
    try {
      // CRITICAL FIX: Add cache-busting timestamp to force fresh API call
      const timestamp = Date.now();
      const response = await expenseApi.getGroupInvitations(activeGroupId, timestamp);
      console.log('📨 Invitations response:', response);
      setPendingInvitations(response.invitations || []);
      console.log('📨 Set pending invitations:', response.invitations?.length || 0);
    } catch (error) {
      console.error('❌ Error loading invitations:', error);
      setPendingInvitations([]);
    } finally {
      setLoadingInvitations(false);
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!newGroupName.trim()) {
      showAlert('Please enter a group name');
      return;
    }

    setCreating(true);
    try {
      await onGroupCreate({
        name: newGroupName.trim(),
        description: `Created by ${currentUser.displayName || currentUser.email}`,
        currency: newGroupCurrency
      });
      setNewGroupName('');
      setNewGroupCurrency('USD');
      showAlert('Group created successfully!');
    } catch (error) {
      console.error('Error creating group:', error);
      showAlert(`Failed to create group: ${error.message}`);
    } finally {
      setCreating(false);
    }
  };

  const handleInviteMember = async (e) => {
    e.preventDefault();
    if (!newMemberEmail.trim()) {
      showAlert('Please enter an email address');
      return;
    }
    
    if (!activeGroupId) {
      showAlert('Please select a group first');
      return;
    }

    console.log('Sending invitation:', {
      group_id: activeGroupId,
      email: newMemberEmail.trim(),
      group_name: activeGroup?.name
    });

    setInviting(true);
    try {
      const response = await expenseApi.sendInvitation({
        group_id: activeGroupId,
        email: newMemberEmail.trim()
      });
      
      console.log('Invitation created:', response);
      
      setNewMemberEmail('');
      
      // Check email status: 'sending', 'disabled', or 'not_sent'
      if (response.email_status === 'sending') {
        showAlert(`✅ Invitation email sent to ${newMemberEmail.trim()}!\n\nThey'll receive an email with a link to join the group.`);
      } else if (response.email_status === 'disabled') {
        // Email service disabled - show link to copy
        const invitedEmail = newMemberEmail.trim();
        
        // Try to copy to clipboard
        if (navigator.clipboard) {
          try {
            await navigator.clipboard.writeText(response.invitation_link);
            showAlert(`📋 Invitation link copied to clipboard!\n\nEmail service is currently disabled.\nPlease share this link with ${invitedEmail} manually.`);
          } catch (err) {
            showAlert(`Invitation created but email service disabled.\n\nPlease share this link:\n${response.invitation_link}`);
          }
        } else {
          showAlert(`Invitation created but email service disabled.\n\nPlease share this link:\n${response.invitation_link}`);
        }
      } else {
        // Fallback for 'not_sent' or other cases
        showAlert(`✅ Invitation created for ${newMemberEmail.trim()}!`);
      }
      
      if (onMemberAdd) await onMemberAdd();
      await loadPendingInvitations(); // Refresh pending invitations
    } catch (error) {
      console.error('Error sending invitation:', error);
      showAlert(`Failed to send invitation: ${error.message}`);
    } finally {
      setInviting(false);
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (!activeGroupId) return;

    try {
      await expenseApi.removeGroupMember(activeGroupId, memberId);
      showAlert('Member removed successfully!');
      if (onMemberRemove) await onMemberRemove(memberId);
    } catch (error) {
      console.error('Error removing member:', error);
      showAlert(`Failed to remove member: ${error.message}`);
    }
  };

  const handleDeleteGroup = async () => {
    if (!activeGroupId) return;

    try {
      await onGroupDelete(activeGroupId);
      showAlert('Group deleted successfully!');
    } catch (error) {
      console.error('Error deleting group:', error);
      showAlert(`Failed to delete group: ${error.message}`);
    }
  };

  const handleGroupSelect = (e) => {
    const groupId = e.target.value || null;
    onGroupChange(groupId);
  };

  if (loading) {
    return (
      <div className="group-section">
        <div className="group-cards">
          <div className="card">
            <p style={{ textAlign: 'center', color: '#666' }}>Loading groups...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="group-section">
      <div className="group-cards">
        <div className="card">
          <h2>
            <Users size={20} />
            Manage Groups
          </h2>
          <select 
            className="group-select"
            value={activeGroupId || ''}
            onChange={handleGroupSelect}
          >
            <option key="select-placeholder" value="">Select a group</option>
            {groups.map(group => (
              <option key={group.id} value={group.id}>
                {group.name} ({group.currency || 'USD'})
              </option>
            ))}
          </select>

          {activeGroup && (
            <div className="group-info-card">
              <div className="group-info-header">
                <h3>
                  {activeGroup.name}
                  {activeGroup.created_by === currentUser.uid && (
                    <span style={{ 
                      marginLeft: '0.5rem', 
                      fontSize: '0.75rem', 
                      background: '#667eea', 
                      color: 'white', 
                      padding: '0.15rem 0.5rem', 
                      borderRadius: '12px',
                      fontWeight: '600'
                    }}>
                      Owner
                    </span>
                  )}
                </h3>
                {activeGroup.created_by === currentUser.uid && (
                  <button 
                    className="btn-icon-delete" 
                    onClick={handleDeleteGroup}
                    title="Delete Group (Owner Only)"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
              <div className="group-info-details">
                <div className="info-item">
                  <span className="info-label">Currency</span>
                  <span className="info-value">{activeGroup.currency || 'USD'}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Members</span>
                  <span className="info-value">{members.length}</span>
                </div>
              </div>
            </div>
          )}

          <form className="create-group-form" onSubmit={handleCreateGroup}>
            <input 
              type="text" 
              placeholder="New group name..." 
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              required
              disabled={creating}
            />
            <select 
              value={newGroupCurrency}
              onChange={(e) => setNewGroupCurrency(e.target.value)}
              disabled={creating}
            >
              {Object.values(currencies).map(curr => (
                <option key={curr.code} value={curr.code}>
                  {curr.symbol} {curr.code} - {curr.name}
                </option>
              ))}
            </select>
            <button type="submit" disabled={creating}>
              <Plus size={16} />
              {creating ? 'Creating...' : 'Create Group'}
            </button>
          </form>
        </div>

        {activeGroupId && (
          <div className="card">
            <h2>
              <Users size={20} />
              Group Members & Invitations
            </h2>
            
            {/* Tab Navigation */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', borderBottom: '2px solid #f0f0f0' }}>
              <button
                onClick={() => setActiveTab('members')}
                style={{
                  padding: '0.5rem 1rem',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: activeTab === 'members' ? '2px solid #667eea' : '2px solid transparent',
                  color: activeTab === 'members' ? '#667eea' : '#666',
                  fontWeight: activeTab === 'members' ? '600' : '400',
                  cursor: 'pointer',
                  marginBottom: '-2px'
                }}
              >
                Members ({members.length})
              </button>
              <button
                onClick={() => setActiveTab('pending')}
                style={{
                  padding: '0.5rem 1rem',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: activeTab === 'pending' ? '2px solid #667eea' : '2px solid transparent',
                  color: activeTab === 'pending' ? '#667eea' : '#666',
                  fontWeight: activeTab === 'pending' ? '600' : '400',
                  cursor: 'pointer',
                  marginBottom: '-2px'
                }}
              >
                <Clock size={14} style={{ marginRight: '0.25rem', display: 'inline', verticalAlign: 'middle' }} />
                Pending ({pendingInvitations.length})
              </button>
            </div>

            {/* Members Tab */}
            {activeTab === 'members' && (
              <>
                {members.length === 0 ? (
                  <p style={{ textAlign: 'center', color: '#666', padding: '1rem' }}>
                    No members yet. Invite someone to get started!
                  </p>
                ) : (
                  <ul className="member-list">
                    {members.map(member => {
                      // Handle nested user data structure
                      const displayName = member.user?.display_name || 
                                         member.user?.username || 
                                         member.user?.email ||
                                         member.display_name ||
                                         member.username || 
                                         member.email ||
                                         'Unknown User';
                      
                      const isCreator = member.user_id === activeGroup?.created_by;
                      const isCurrentUser = member.user_id === currentUser.uid;
                      const canRemove = activeGroup?.created_by === currentUser.uid && !isCurrentUser;
                      
                      return (
                        <li key={member.user_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span>
                            {displayName}
                            {isCreator && (
                              <span style={{ 
                                marginLeft: '0.5rem', 
                                fontSize: '0.7rem', 
                                background: '#667eea', 
                                color: 'white', 
                                padding: '0.15rem 0.4rem', 
                                borderRadius: '10px',
                                fontWeight: '600'
                              }}>
                                Owner
                              </span>
                            )}
                            {isCurrentUser && <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: '#666' }}>(You)</span>}
                          </span>
                          {canRemove && (
                            <button 
                              onClick={() => handleRemoveMember(member.user_id)}
                              style={{ padding: '0.25rem', background: 'transparent', border: 'none', cursor: 'pointer', color: '#e74c3c' }}
                              title="Remove member (Owner Only)"
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
                
                {/* Invitation form - ONLY in Members tab */}
                <form className="add-member-form" onSubmit={handleInviteMember} style={{ marginTop: '1rem', borderTop: '1px solid #f0f0f0', paddingTop: '1rem' }}>
                  <input 
                    type="email" 
                    placeholder="Email address to invite..." 
                    value={newMemberEmail}
                    onChange={(e) => setNewMemberEmail(e.target.value)}
                    required
                    disabled={inviting}
                  />
                  <button type="submit" disabled={inviting}>
                    <Mail size={16} />
                    {inviting ? 'Inviting...' : 'Invite Member'}
                  </button>
                </form>
              </>
            )}

            {/* Pending Invitations Tab - VIEW ONLY (no invitation form) */}
            {activeTab === 'pending' && (
              <>
                {loadingInvitations ? (
                  <p style={{ textAlign: 'center', color: '#666', padding: '1rem' }}>
                    Loading invitations...
                  </p>
                ) : pendingInvitations.length === 0 ? (
                  <p style={{ textAlign: 'center', color: '#666', padding: '1rem' }}>
                    No pending invitations.
                  </p>
                ) : (
                  <ul className="member-list">
                    {pendingInvitations.map(invitation => (
                      <li key={invitation.invitation_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#fff9e6', padding: '0.75rem', borderRadius: '6px', marginBottom: '0.5rem' }}>
                        <div>
                          <div style={{ fontWeight: '500' }}>
                            {invitation.invited_email || invitation.invited_username || 'Unknown'}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.25rem' }}>
                            <Clock size={12} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '0.25rem' }} />
                            Invited {new Date(invitation.created_at).toLocaleDateString()}
                          </div>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: '#f39c12', fontWeight: '600', textTransform: 'uppercase' }}>
                          Pending
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GroupManager;
