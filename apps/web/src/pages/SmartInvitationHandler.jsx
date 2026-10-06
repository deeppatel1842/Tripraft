// Purpose: Renders the Smart Invitation Handler interface within apps\web\src\pages.
import React, { useEffect, useState } from 'react';
import { useLocation, useParams, useSearchParams } from 'react-router-dom';
import InvitationAccept from './InvitationAccept';
import InvitationAcceptPage from '../features/trips/jsx/InvitationAcceptPage';
import expenseApi from '../services/expenseApi';
import groupPlannerApi from '../services/groupPlannerApi';

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
  const location = useLocation();

  // Support both path and query parameter formats
  const invitationId = pathInvitationId || searchParams.get('id');
  const typeParam = searchParams.get('type'); // 'expense' or 'group'

  const [invitationType, setInvitationType] = useState(null);
  const [isDetecting, setIsDetecting] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsDetecting(true);
    if (location.pathname.startsWith('/invitation/') || location.pathname.startsWith('/invitations/')) {
      setInvitationType(location.pathname.startsWith('/invitations/') ? 'group' : 'expense');
      setIsDetecting(false);
      return;
    }

    // Singular /invitation/:id is the expense link, plural /invitations/:id
    // the group-planner one. Used when the probes cannot decide -- both
    // detail endpoints require auth, so a signed-out visitor 401s on each.
    const typeFromPath = () =>
      location.pathname.startsWith('/invitations/') ? 'group' : 'expense';

    const probe = async (request) => {
      try {
        const response = await request();
        // apiClient returns the raw {success, data} envelope.
        return response?.success !== false;
      } catch {
        return false;
      }
    };

    const detectInvitationType = async () => {
      if (typeParam === 'expense' || typeParam === 'group') {
        if (!cancelled) {
          setInvitationType(typeParam);
          setIsDetecting(false);
        }
        return;
      }

      if (!invitationId) {
        if (!cancelled) {
          setInvitationType(typeFromPath());
          setIsDetecting(false);
        }
        return;
      }

      // Ask each API whether it knows this invitation, rather than assuming.
      // Previously every link -- including every expense invitation -- was
      // sent to the group-planner handler.
      let detected = null;
      if (await probe(() => expenseApi.getInvitationDetails(invitationId))) {
        detected = 'expense';
      } else if (
        await probe(() => groupPlannerApi.getInvitationDetails(invitationId))
      ) {
        detected = 'group';
      }

      if (!cancelled) {
        setInvitationType(detected || typeFromPath());
        setIsDetecting(false);
      }
    };

    detectInvitationType();
    return () => {
      cancelled = true;
    };
  }, [invitationId, typeParam, location.pathname]);

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
    return <InvitationAccept />;
  }

  // Group planner or default
  return <InvitationAcceptPage invitationId={invitationId} />;
}
