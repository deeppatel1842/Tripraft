import React, { useState, useEffect } from 'react';
import { Users, Plus, Mail, Trash2, Clock, X } from 'lucide-react';
import { formatDateLocal } from '../../../utils/timezoneUtils';
import expenseApi from '../../../services/expenseApi';

const currencies = {
  USD: { code: 'USD', symbol: '$', name: 'US Dollar' },
  EUR: { code: 'EUR', symbol: '\u20ac', name: 'Euro' },
  INR: { code: 'INR', symbol: '\u20b9', name: 'Indian Rupee' },
  GBP: { code: 'GBP', symbol: '\u00a3', name: 'British Pound' },
  JPY: { code: 'JPY', symbol: '\u00a5', name: 'Japanese Yen' },
  CAD: { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar' },
  AUD: { code: 'AUD', symbol: 'A$', name: 'Australian Dollar' },
  CHF: { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc' },
  CNY: { code: 'CNY', symbol: '\u00a5', name: 'Chinese Yuan' },
  KRW: { code: 'KRW', symbol: '\u20a9', name: 'South Korean Won' },
  BRL: { code: 'BRL', symbol: 'R$', name: 'Brazilian Real' },
  MXN: { code: 'MXN', symbol: 'Mex$', name: 'Mexican Peso' },
  SGD: { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar' },
  HKD: { code: 'HKD', symbol: 'HK$', name: 'Hong Kong Dollar' },
  NZD: { code: 'NZD', symbol: 'NZ$', name: 'New Zealand Dollar' }
};

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
  currentUser,
  pendingInvitationsFromParent,
  onRefreshInvitations,
  usingMegaBootstrap = false
}) => {
  // Simplified: No complex prefetch or mutation hooks
  
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupCurrency, setNewGroupCurrency] = useState('USD');
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [inviting, setInviting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [pendingInvitations, setPendingInvitations] = useState([]);
  const [loadingInvitations, setLoadingInvitations] = useState(false);
  const [activeTab, setActiveTab] = useState('members'); // 'members' or 'pending'

  //  PHASE 16: Use invitations from parent (mega-bootstrap) if available
  useEffect(() => {
    if (pendingInvitationsFromParent !== undefined) {
      // PHASE 17 FIX: Show pending AND declined invitations to owner
      // Owner can see declined invitations and resend them
      const relevantInvitations = (pendingInvitationsFromParent || []).filter(
        inv => inv.status === 'pending' || inv.status === 'PENDING' || 
               inv.status === 'declined' || inv.status === 'DECLINED'
      );
      // PHASE 19 FIX: Deduplicate by invitation_id to prevent React key warnings
      const uniqueInvitations = relevantInvitations.filter((inv, index, self) => 
        index === self.findIndex(i => i.invitation_id === inv.invitation_id)
      );
      setPendingInvitations(uniqueInvitations);
    }
  }, [pendingInvitationsFromParent]);

  // Load pending invitations when active group changes (fallback ONLY if not using mega-bootstrap)
  useEffect(() => {
    // 🚀 PHASE 16: Skip fallback API call if mega-bootstrap is active/loading
    if (usingMegaBootstrap) {
      return;
    }
    
    // 🚀 ULTRA FIX: Skip fallback if parent already provided invitations
    // This prevents double-fetch when mega-bootstrap cache is pre-populated
    if (pendingInvitationsFromParent !== undefined) {
      return;
    }
    
    if (activeGroupId) {
      loadPendingInvitations();
    } else {
      setPendingInvitations([]);
    }
  }, [activeGroupId, usingMegaBootstrap, pendingInvitationsFromParent]);

  // 🔄 Auto-refresh pending invitations every 10 seconds when viewing "Pending" tab
  // 🔥 PHASE 16: Uses mega-bootstrap refresh, no direct API calls
  useEffect(() => {
    let intervalId = null;
    
    if (activeGroupId && activeTab === 'pending') {
      // 🚀 ULTRA FIX: Only enable polling when NOT using mega-bootstrap
      // Mega-bootstrap handles data updates
      if (!usingMegaBootstrap && pendingInvitationsFromParent === undefined) {
        // Set up polling every 10 seconds - only when truly in fallback mode
        intervalId = setInterval(() => {
          loadPendingInvitations();
        }, 10000); // 10 seconds
      }
    }
    
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [activeGroupId, activeTab, usingMegaBootstrap, pendingInvitationsFromParent]);

  // 🔥 Listen for global invitation acceptance events
  useEffect(() => {
    const handleInvitationAccepted = () => {
      if (activeGroupId) {
        // 🚀 ULTRA FIX: Only fetch if in true fallback mode
        if (!usingMegaBootstrap && pendingInvitationsFromParent === undefined) {
          loadPendingInvitations();
        } else if (onRefreshInvitations) {
          onRefreshInvitations();
        }
        // Otherwise: REST API polling will update automatically (SQL backend)
      }
    };
    
    window.addEventListener('invitationAccepted', handleInvitationAccepted);
    
    return () => {
      window.removeEventListener('invitationAccepted', handleInvitationAccepted);
    };
  }, [activeGroupId, onRefreshInvitations, usingMegaBootstrap, pendingInvitationsFromParent]);

  const loadPendingInvitations = async () => {
    if (!activeGroupId) return;
    
    setLoadingInvitations(true);
    try {
      // CRITICAL FIX: Add cache-busting timestamp to force fresh API call
      // includeAll=true to show declined invitations to owner
      const timestamp = Date.now();
      const response = await expenseApi.getGroupInvitations(activeGroupId, true, timestamp);
      // PHASE 17 FIX: Filter for pending AND declined invitations (to show owner who declined)
      const relevantStatuses = ['pending', 'PENDING', 'declined', 'DECLINED'];
      const relevantInvitations = (response.invitations || []).filter(
        inv => relevantStatuses.includes(inv.status)
      );
      // PHASE 19 FIX: Deduplicate by invitation_id
      const uniqueInvitations = relevantInvitations.filter((inv, index, self) => 
        index === self.findIndex(i => i.invitation_id === inv.invitation_id)
      );
      setPendingInvitations(uniqueInvitations);
    } catch (error) {
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
        currency: newGroupCurrency,
        // Phase 21: Pass user info for extreme API
        user_email: currentUser.email,
        user_display_name: currentUser.displayName || currentUser.email?.split('@')[0] || 'Unknown'
      });
      setNewGroupName('');
      setNewGroupCurrency('USD');
      showAlert('Group created successfully!');
    } catch (error) {
      showAlert(`Failed to create group: ${error.message}`);
    } finally {
      setCreating(false);
    }
  };

  const handleInviteMember = async (e, isResend = false, emailToResend = null) => {
    e.preventDefault();
    
    // Prevent double submission
    if (inviting) {
      return;
    }
    
    // Get email - either from resend parameter or from input field
    const invitedEmail = emailToResend || newMemberEmail.trim();
    
    if (!invitedEmail) {
      showAlert('Please enter an email address');
      return;
    }
    
    if (!activeGroupId) {
      showAlert('Please select a group first');
      return;
    }

    // Immediately clear the email to prevent duplicate submissions
    if (!isResend) {
      setNewMemberEmail('');
    }

    setInviting(true);
    try {
      // Direct API call - simple and clean
      const response = await expenseApi.sendInvitation({
        group_id: activeGroupId,
        invitee_email: invitedEmail
      });
      
      // Reload invitations to get updated list
      loadPendingInvitations();
      
      // Check email status: 'sending', 'sent', 'disabled', or 'not_sent'
      if (response.email_status === 'sending' || response.email_status === 'sent') {
        const action = isResend ? 'resent' : 'sent';
        showAlert(`Invitation email ${action} to ${invitedEmail}!\n\nThey'll receive an email with a link to join the group.`);
      } else if (response.email_status === 'disabled') {
        // Email service disabled - show link to copy
        if (navigator.clipboard) {
          try {
            await navigator.clipboard.writeText(response.invitation_link);
            showAlert(`Invitation link copied to clipboard!\n\nEmail service is currently disabled.\nPlease share this link with ${invitedEmail} manually.`);
          } catch (err) {
            showAlert(`Invitation created but email service disabled.\n\nPlease share this link:\n${response.invitation_link}`);
          }
        } else {
          showAlert(`Invitation created but email service disabled.\n\nPlease share this link:\n${response.invitation_link}`);
        }
      } else {
        // Fallback for 'not_sent' or other cases
        showAlert(`Invitation created for ${invitedEmail}!`);
      }
      
      if (onMemberAdd) await onMemberAdd();
      
      // Notify parent to refresh if needed
      if (onRefreshInvitations) {
        onRefreshInvitations();
      }
    } catch (error) {
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
      showAlert(error.message || 'Cannot remove member');
    }
  };

  const handleDeleteGroup = async () => {
    if (!activeGroupId) return;

    try {
      await onGroupDelete(activeGroupId);
      // Success message is shown by parent (ExpenseManager)
    } catch (error) {
      // Error is already shown by parent, but show here too for clarity
      showAlert(error.message || 'Cannot delete group');
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
              <option key={group.id || group.group_id} value={group.id || group.group_id}>
                {group.name} ({group.currency || 'USD'})
              </option>
            ))}
          </select>

          {activeGroup && (
            <div className="group-info-card">
              <div className="group-info-header">
                <h3>
                  {activeGroup.name}
                  {(activeGroup.created_by === currentUser.id || String(activeGroup.created_by) === currentUser.uid) && (
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
                {(activeGroup.created_by === currentUser.id || String(activeGroup.created_by) === currentUser.uid) && (
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
                      
                      // Convert ALL IDs to numbers to handle type mismatches
                      const memberId = Number(member.user_id);
                      const groupOwnerId = Number(activeGroup?.created_by);
                      const currentUserId = Number(currentUser.uid);
                      
                      const isCreator = memberId === groupOwnerId;
                      const isCurrentUser = memberId === currentUserId;
                      const canRemove = groupOwnerId === currentUserId && !isCurrentUser;
                      
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
                    {pendingInvitations.map(invitation => {
                      const isDeclined = invitation.status?.toLowerCase() === 'declined';
                      const isExpired = invitation.expires_at && new Date(invitation.expires_at) < new Date();
                      const bgColor = isDeclined ? '#ffebee' : isExpired ? '#f5f5f5' : '#fff9e6';
                      const statusColor = isDeclined ? '#e74c3c' : isExpired ? '#999' : '#f39c12';
                      const statusText = isDeclined ? 'Declined' : isExpired ? 'Expired' : 'Pending';
                      const canResend = isDeclined || isExpired;
                      
                      return (
                        <li key={invitation.invitation_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: bgColor, padding: '0.75rem', borderRadius: '6px', marginBottom: '0.5rem' }}>
                          <div>
                            <div style={{ fontWeight: '500' }}>
                              {invitation.invited_email || invitation.invited_username || 'Unknown'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.25rem' }}>
                              <Clock size={12} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '0.25rem' }} />
                              Invited {formatDateLocal(new Date(invitation.created_at), { year: 'numeric', month: 'short', day: 'numeric' })}
                              {invitation.expires_at && (
                                <span style={{ marginLeft: '0.5rem', color: isExpired ? '#e74c3c' : '#999' }}>
                                  {isExpired ? '(Expired)' : `• Expires ${formatDateLocal(new Date(invitation.expires_at), { year: 'numeric', month: 'short', day: 'numeric' })}`}
                                </span>
                              )}
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            {canResend && (
                              <button
                                onClick={(e) => handleInviteMember(e, true, invitation.invited_email)}
                                style={{ 
                                  padding: '0.25rem 0.75rem', 
                                  fontSize: '0.7rem', 
                                  background: '#667eea', 
                                  color: 'white', 
                                  border: 'none', 
                                  borderRadius: '4px', 
                                  cursor: 'pointer',
                                  fontWeight: '600'
                                }}
                                title="Resend invitation"
                              >
                                Resend
                              </button>
                            )}
                            <span style={{ fontSize: '0.75rem', color: statusColor, fontWeight: '600', textTransform: 'uppercase' }}>
                              {statusText}
                            </span>
                          </div>
                        </li>
                      );
                    })}
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

