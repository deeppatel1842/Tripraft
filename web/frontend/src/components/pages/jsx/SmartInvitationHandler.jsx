import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import InvitationAccept from './InvitationAccept';
import InvitationAcceptPage from '../../groupPlanner/jsx/InvitationAcceptPage';

/**
 * SmartInvitationHandler
 * Intelligently routes to either:
 * - InvitationAccept (for expense invitations - handled by expenseApi)
 * - InvitationAcceptPage (for group planner invitations - handled by groupPlannerApi)
 * 
 * Supports both URL formats:
 * 1. Path parameter: /invitation/:invitationId or /invitations/:invitationId
 * 2. Query parameter: /accept-invitation?id=xxx&type=expense|group
 */
export default function SmartInvitationHandler() {
  const { invitationId: pathInvitationId } = useParams();
  const [searchParams] = useSearchParams();
  
  // Support both path and query parameter formats
  const invitationId = pathInvitationId || searchParams.get('id');
  const typeParam = searchParams.get('type'); // 'expense' or 'group'
  
  const [invitationType, setInvitationType] = useState(null);
  const [isDetecting, setIsDetecting] = useState(true);

  useEffect(() => {
    const detectInvitationType = async () => {
      try {
        // If type is explicitly provided in query params, use it
        if (typeParam === 'expense') {
          setInvitationType('expense');
        } else if (typeParam === 'group') {
          setInvitationType('group');
        } else {
          // Default to group planner invitations for backward compatibility
          setInvitationType('group');
        }
      } catch (error) {
        // If detection fails, default to group planner
        setInvitationType('group');
      } finally {
        setIsDetecting(false);
      }
    };

    detectInvitationType();
  }, [invitationId, typeParam]);

  if (isDetecting) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        fontSize: '18px',
        color: 'white'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            borderRadius: '50%',
            border: '4px solid rgba(255,255,255,0.3)',
            borderTop: '4px solid white',
            width: '48px',
            height: '48px',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 20px'
          }}></div>
          <p>Processing your invitation...</p>
        </div>
      </div>
    );
  }

  // Route to appropriate handler based on invitation type
  if (invitationType === 'expense') {
    return <InvitationAccept invitationId={invitationId} />;
  }

  // Group planner or default
  return <InvitationAcceptPage invitationId={invitationId} />;
}
