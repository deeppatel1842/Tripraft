import React, { useState } from 'react';
import './PendingTabContent.css';
import { useGroupPlanner } from '../../context/GroupPlannerContext';

export default function PendingTabContent({ pendingInvitations = [], currentUserId, onAcceptInvitation }) {
  const { acceptInvitation, resendInvitation } = useGroupPlanner();
  const [loadingInvitation, setLoadingInvitation] = useState(null);
  const [resendingInvitation, setResendingInvitation] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleAccept = async (invitationId) => {
    try {
      setLoadingInvitation(invitationId);
      setErrorMessage(null);
      await acceptInvitation(invitationId);
      setSuccessMessage('✅ Invitation accepted! You\'ve been added to the group.');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error) {
      console.error('Error accepting invitation:', error);
      setErrorMessage(`❌ Failed to accept invitation: ${error.message}`);
    } finally {
      setLoadingInvitation(null);
    }
  };

  const handleResend = async (invitationId) => {
    try {
      setResendingInvitation(invitationId);
      setErrorMessage(null);
      await resendInvitation(invitationId);
      setSuccessMessage('✅ Invitation resent successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error) {
      console.error('Error resending invitation:', error);
      setErrorMessage(`❌ Failed to resend invitation: ${error.message}`);
    } finally {
      setResendingInvitation(null);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getExpiresInDays = (expiresAt) => {
    if (!expiresAt) return null;
    const expiryDate = new Date(expiresAt);
    const today = new Date();
    const diffTime = expiryDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : null;
  };

  return (
    <div className="ptc-container">
      {successMessage && (
        <div className="ptc-alert ptc-alert-success">
          {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="ptc-alert ptc-alert-error">
          {errorMessage}
        </div>
      )}
      
      <div className="ptc-list">
        {pendingInvitations && pendingInvitations.length > 0 ? (
          pendingInvitations.map((inv) => {
            const expiresInDays = getExpiresInDays(inv.expires_at);
            const isReceived = inv.invitation_type === 'received';
            const isSent = inv.invitation_type === 'sent';
            
            return (
              <div key={inv.invitation_id || inv.id} className="ptc-invitation-card">
                <div className="ptc-invitation-left">
                  <div className="ptc-invitation-icon">{isReceived ? '📥' : '📤'}</div>
                  <div className="ptc-invitation-info">
                    <div className="ptc-invitation-email">{inv.invited_email}</div>
                    <div className="ptc-invitation-group">{inv.group_name}</div>
                    <div className="ptc-invitation-meta">
                      {isReceived && (
                        <>
                          <span className="ptc-invitation-from">From: {inv.invited_by_name || 'Unknown'}</span>
                          <span className="ptc-invitation-date">• Expires in {expiresInDays} days</span>
                        </>
                      )}
                      {isSent && (
                        <>
                          <span className="ptc-invitation-from">Invited to group</span>
                          <span className="ptc-invitation-date">• Expires in {expiresInDays} days</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="ptc-invitation-actions">
                  {/* Show ACCEPT button ONLY for received invitations */}
                  {isReceived && (
                    <button 
                      className="ptc-accept-btn"
                      onClick={() => handleAccept(inv.invitation_id || inv.id)}
                      disabled={loadingInvitation === (inv.invitation_id || inv.id)}
                    >
                      {loadingInvitation === (inv.invitation_id || inv.id) ? '⏳ Accepting...' : '✓ Accept'}
                    </button>
                  )}
                  
                  {/* Show RESEND button ONLY for sent invitations */}
                  {isSent && (
                    <button 
                      className="ptc-resend-btn"
                      onClick={() => handleResend(inv.invitation_id || inv.id)}
                      disabled={resendingInvitation === (inv.invitation_id || inv.id)}
                      title="Resend invitation email"
                    >
                      {resendingInvitation === (inv.invitation_id || inv.id) ? '⏳ Resending...' : '↻ Resend'}
                    </button>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div className="ptc-empty">
            <div className="ptc-empty-icon">📭</div>
            <div className="ptc-empty-text">No pending invitations</div>
            <div className="ptc-empty-subtext">You're all caught up!</div>
          </div>
        )}
      </div>
    </div>
  );
}
