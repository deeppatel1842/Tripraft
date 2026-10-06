// Purpose: Renders the Invitation Accept Page interface within apps\web\src\features\trips\jsx.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import groupPlannerApi from '../../../services/groupPlannerApi';

/**
 * Accepts a group-planner (travel group) invitation.
 *
 * SmartInvitationHandler has imported this module since the first commit, but
 * the file was never added, so `vite build` failed to resolve it and the
 * frontend could not be built at all. The API it needs already existed on both
 * sides (`GET /invitations/:id`, `POST /invitations/:id/accept`); only the page
 * was missing.
 *
 * Expense invitations are handled by pages/jsx/InvitationAccept instead.
 */
export default function InvitationAcceptPage({ invitationId: invitationIdProp }) {
  const { invitationId: pathInvitationId } = useParams();
  const [searchParams] = useSearchParams();
  const invitationId =
    invitationIdProp || pathInvitationId || searchParams.get('id');

  const { currentUser, signOut } = useAuth();
  const navigate = useNavigate();

  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('Preparing your invitation…');
  const [invitation, setInvitation] = useState(null);
  const [wrongAccount, setWrongAccount] = useState(false);

  // Both effects below can fire twice under StrictMode; accepting twice would
  // surface a spurious "already accepted" error.
  const ranRef = useRef(false);

  const unwrap = (response) => response?.data ?? response ?? {};

  const goToGroup = useCallback(
    (groupId) => {
      navigate(groupId ? `/group-planner?group=${groupId}` : '/group-planner', {
        replace: true,
      });
    },
    [navigate]
  );

  const accept = useCallback(async () => {
    try {
      setStatus('loading');
      setMessage('Joining the group…');
      setWrongAccount(false);

      const response = await groupPlannerApi.acceptInvitation(invitationId);
      const result = unwrap(response);

      setStatus('success');
      setMessage(
        result.group_name
          ? `You've joined "${result.group_name}".`
          : "You've joined the group."
      );
      setTimeout(() => goToGroup(result.group_id), 1800);
    } catch (error) {
      const text = String(error?.message || '');
      setStatus('error');

      if (text.includes('different email')) {
        setWrongAccount(true);
        setMessage(
          invitation?.invited_email
            ? `This invitation is for ${invitation.invited_email}, but you are signed in as ${currentUser?.email}.`
            : 'This invitation was sent to a different email address.'
        );
      } else if (text.includes('expired')) {
        setMessage('This invitation has expired. Ask the group to send a new one.');
      } else if (text.includes('404') || text.includes('not found')) {
        setMessage('This invitation link is invalid or has already been used.');
      } else {
        setMessage(text || 'Could not accept this invitation.');
      }
    }
  }, [invitationId, invitation, currentUser, goToGroup]);

  useEffect(() => {
    if (!invitationId) {
      navigate('/login', { replace: true });
      return;
    }
    if (ranRef.current) return;
    ranRef.current = true;

    if (!currentUser) {
      // Both endpoints require auth, so send the visitor to sign in first and
      // come straight back.
      navigate(
        `/login?redirect=invitation&invitationId=${encodeURIComponent(invitationId)}`,
        { replace: true }
      );
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const details = unwrap(
          await groupPlannerApi.getInvitationDetails(invitationId)
        );
        if (!cancelled) setInvitation(details);
      } catch {
        // Details are only used to write a clearer message; accepting is
        // still worth attempting.
      }
      if (!cancelled) accept();
    })();

    return () => {
      cancelled = true;
    };
  }, [invitationId, currentUser, navigate, accept]);

  const handleSwitchAccount = async () => {
    await signOut();
    navigate(
      `/login?redirect=invitation&invitationId=${encodeURIComponent(invitationId)}`,
      { replace: true }
    );
  };

  return (
    <div className="gp-invite-accept">
      <div className="gp-invite-card">
        <h1 className="gp-invite-title">
          {status === 'success' ? 'You are in' : 'Group invitation'}
        </h1>

        {status === 'loading' && <div className="gp-invite-spinner" aria-hidden="true" />}

        <p className="gp-invite-message" role="status">
          {message}
        </p>

        {invitation?.group_name && status !== 'success' && (
          <p className="gp-invite-meta">
            {invitation.invited_by_name
              ? `${invitation.invited_by_name} invited you to `
              : 'You were invited to '}
            <strong>{invitation.group_name}</strong>
          </p>
        )}

        {status === 'error' && (
          <div className="gp-invite-actions">
            {wrongAccount && (
              <button type="button" className="gp-invite-btn primary" onClick={handleSwitchAccount}>
                Sign in with a different account
              </button>
            )}
            <button type="button" className="gp-invite-btn" onClick={() => goToGroup(null)}>
              Go to my groups
            </button>
          </div>
        )}
      </div>

      <style>{`
        .gp-invite-accept {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .gp-invite-card {
          width: 100%;
          max-width: 480px;
          background: #fff;
          border-radius: 12px;
          padding: 40px 32px;
          text-align: center;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        }
        .gp-invite-title {
          margin: 0 0 18px;
          font-size: 24px;
          color: #1f2937;
        }
        .gp-invite-spinner {
          width: 48px;
          height: 48px;
          margin: 0 auto 18px;
          border: 4px solid #f3f4f6;
          border-top-color: #667eea;
          border-radius: 50%;
          animation: gp-invite-spin 1s linear infinite;
        }
        @keyframes gp-invite-spin { to { transform: rotate(360deg); } }
        .gp-invite-message { margin: 0; color: #6b7280; line-height: 1.6; }
        .gp-invite-meta { margin: 14px 0 0; color: #374151; font-size: 14px; }
        .gp-invite-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          justify-content: center;
          margin-top: 26px;
        }
        .gp-invite-btn {
          padding: 11px 22px;
          border: none;
          border-radius: 6px;
          font-size: 15px;
          font-weight: 500;
          cursor: pointer;
          background: #e5e7eb;
          color: #374151;
        }
        .gp-invite-btn.primary { background: #667eea; color: #fff; }
        @media (max-width: 640px) {
          .gp-invite-actions { flex-direction: column; }
          .gp-invite-btn { width: 100%; }
        }
      `}</style>
    </div>
  );
}
