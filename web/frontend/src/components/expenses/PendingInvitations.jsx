import React, { useState } from 'react';
import { Mail, Check, X, Clock } from 'lucide-react';
import { useInvitationsQuery, useAcceptInvitationMutation, useDeclineInvitationMutation } from '../../hooks/useExpenseQuery';

const PendingInvitations = ({ onInvitationAccepted, currentUser }) => {
  const [processing, setProcessing] = useState({});
  
  // Use React Query for invitations
  const { data: invitationsData, isLoading: loading, refetch: refetchInvitations } = useInvitationsQuery();
  const acceptMutation = useAcceptInvitationMutation();
  const declineMutation = useDeclineInvitationMutation();
  
  // Extract invitations from response
  const invitations = invitationsData?.invitations || [];

  const handleAccept = async (invitationId) => {
    setProcessing(prev => ({ ...prev, [invitationId]: 'accepting' }));
    try {
      // CRITICAL: Manually trigger refetch after mutation
      const response = await acceptMutation.mutateAsync(invitationId);
      
      // Force immediate refetch of this component's query
      await refetchInvitations();
      
      // ✅ React Query will automatically invalidate and refetch invitations/groups
      console.log('✅ Invitation accepted, React Query refreshing data...');
      
      // Notify parent to refresh groups immediately
      if (onInvitationAccepted) {
        onInvitationAccepted();
      }
      
      // 🔔 If backend says refresh required, force immediate refetch
      if (response?.refresh_required) {
        console.log('🔄 Backend requested refresh, forcing immediate refetch...');
        window.dispatchEvent(new Event('invitationAccepted')); // Trigger global refresh event
      }
    } catch (error) {
      console.error('Error accepting invitation:', error);
      alert(`Failed to accept invitation: ${error.message}`);
    } finally {
      setProcessing(prev => {
        const updated = { ...prev };
        delete updated[invitationId];
        return updated;
      });
    }
  };

  const handleDecline = async (invitationId) => {
    setProcessing(prev => ({ ...prev, [invitationId]: 'declining' }));
    try {
      await declineMutation.mutateAsync(invitationId);
    } catch (error) {
      console.error('Error declining invitation:', error);
      alert(`Failed to decline invitation: ${error.message}`);
    } finally {
      setProcessing(prev => {
        const updated = { ...prev };
        delete updated[invitationId];
        return updated;
      });
    }
  };

  if (loading) {
    return (
      <div className="pending-invitations-card">
        <h3>
          <Mail size={18} />
          Pending Invitations
        </h3>
        <p style={{ textAlign: 'center', color: '#666', padding: '1rem' }}>
          Loading...
        </p>
      </div>
    );
  }

  if (invitations.length === 0) {
    return null; // Don't show card if no pending invitations
  }

  return (
    <div className="pending-invitations-card">
      <h3>
        <Mail size={18} />
        Pending Invitations ({invitations.length})
      </h3>
      
      <div className="invitations-list">
        {invitations.map(invitation => (
          <div key={invitation.invitation_id} className="invitation-item">
            <div className="invitation-info">
              <div className="invitation-header">
                <strong>{invitation.group_name}</strong>
                <span className="currency-badge">{invitation.group_currency}</span>
              </div>
              <div className="invitation-meta">
                <Clock size={12} />
                <span>Invited by {invitation.invited_by_name}</span>
              </div>
            </div>
            
            <div className="invitation-actions">
              <button
                className="btn-accept"
                onClick={() => handleAccept(invitation.invitation_id)}
                disabled={processing[invitation.invitation_id]}
                title="Accept invitation"
              >
                {processing[invitation.invitation_id] === 'accepting' ? (
                  'Accepting...'
                ) : (
                  <>
                    <Check size={16} />
                    Accept
                  </>
                )}
              </button>
              <button
                className="btn-decline"
                onClick={() => handleDecline(invitation.invitation_id)}
                disabled={processing[invitation.invitation_id]}
                title="Decline invitation"
              >
                {processing[invitation.invitation_id] === 'declining' ? (
                  '...'
                ) : (
                  <X size={16} />
                )}
              </button>
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .pending-invitations-card {
          background: white;
          border-radius: 12px;
          padding: 1.5rem;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          margin-bottom: 1.5rem;
        }

        .pending-invitations-card h3 {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin: 0 0 1rem 0;
          font-size: 1.1rem;
          color: #333;
        }

        .invitations-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .invitation-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          transition: all 0.2s;
        }

        .invitation-item:hover {
          background: #f3f4f6;
          border-color: #d1d5db;
        }

        .invitation-info {
          flex: 1;
        }

        .invitation-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.25rem;
        }

        .invitation-header strong {
          color: #1f2937;
          font-size: 0.95rem;
        }

        .currency-badge {
          font-size: 0.7rem;
          background: #e0e7ff;
          color: #4338ca;
          padding: 0.15rem 0.4rem;
          border-radius: 8px;
          font-weight: 600;
        }

        .invitation-meta {
          display: flex;
          align-items: center;
          gap: 0.3rem;
          font-size: 0.85rem;
          color: #6b7280;
        }

        .invitation-actions {
          display: flex;
          gap: 0.5rem;
        }

        .btn-accept,
        .btn-decline {
          display: flex;
          align-items: center;
          gap: 0.3rem;
          padding: 0.5rem 0.75rem;
          border: none;
          border-radius: 6px;
          font-size: 0.85rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-accept {
          background: #10b981;
          color: white;
        }

        .btn-accept:hover:not(:disabled) {
          background: #059669;
          transform: translateY(-1px);
        }

        .btn-accept:disabled {
          background: #9ca3af;
          cursor: not-allowed;
        }

        .btn-decline {
          background: transparent;
          color: #ef4444;
          padding: 0.5rem;
        }

        .btn-decline:hover:not(:disabled) {
          background: #fee2e2;
        }

        .btn-decline:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        @media (max-width: 640px) {
          .invitation-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.75rem;
          }

          .invitation-actions {
            width: 100%;
            justify-content: stretch;
          }

          .btn-accept {
            flex: 1;
          }
        }
      `}</style>
    </div>
  );
};

export default PendingInvitations;
