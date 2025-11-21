import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useGroupPlannerAuth } from '../../hooks/useGroupPlannerAuth';
import { useGroupPlanner } from '../../context/GroupPlannerContext';
import groupPlannerService from '../../services/groupPlannerService';
import './InvitationAcceptPage.css';

export default function InvitationAcceptPage() {
  const { invitationId } = useParams();
  const navigate = useNavigate();
  const { user } = useGroupPlannerAuth();
  const { acceptInvitation } = useGroupPlanner();
  
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');
  const [invitationInfo, setInvitationInfo] = useState(null);
  const [showWrongUserWarning, setShowWrongUserWarning] = useState(false);

  useEffect(() => {
    // Use sessionStorage to track processing across page reloads (prevents redirect loop)
    const processingKey = `invitation_processing_${invitationId}`;
    const hasProcessed = sessionStorage.getItem(processingKey);
    
    console.log('🔵 [INVITATION] InvitationAcceptPage mounted', {
      invitationId,
      userLoggedIn: !!user,
      userEmail: user?.email,
      hasProcessed: !!hasProcessed
    });

    if (!invitationId) {
      setStatus('error');
      setMessage('Invalid invitation link');
      return;
    }

    // Check if already processed AND accepted
    if (hasProcessed === 'accepted') {
      console.log('✅ [INVITATION] Already accepted, redirecting to group page...');
      navigate('/group-trip', { replace: true });
      return;
    }

    // If user is logged in, accept the invitation
    if (user) {
      console.log('✅ [INVITATION] User logged in, attempting to accept invitation');
      
      // Mark as processing (not accepted yet)
      if (!hasProcessed) {
        sessionStorage.setItem(processingKey, 'processing');
      }
      
      handleAcceptInvitation();
    } else {
      // If not logged in, load details and redirect to login
      console.log('⚠️ [INVITATION] User not logged in, loading invitation details...');
      
      // Mark that we've seen this invitation
      sessionStorage.setItem(processingKey, 'seen');
      
      loadInvitationDetails();
    }
  }, [invitationId, user]);

  const loadInvitationDetails = async () => {
    try {
      setStatus('loading');
      setMessage('Loading invitation details...');

      const response = await groupPlannerService.getInvitationDetails(invitationId);
      
      if (response) {
        setInvitationInfo(response);
        console.log('✅ [INVITATION] Invitation details loaded:', response);
        
        // Store invitation info in localStorage for after login
        localStorage.setItem('pendingGroupInvitation', invitationId);
        localStorage.setItem('groupInvitationEmail', response.invited_email);
        localStorage.setItem('groupInvitationCreatedBy', response.created_by_name || 'Someone');
        
        // Redirect to login
        navigate('/auth?redirect=group-invitation', { replace: true });
      } else {
        setStatus('error');
        setMessage('Invitation not found or has expired.');
      }
    } catch (error) {
      console.error('❌ [INVITATION] Error loading invitation details:', error);
      setStatus('error');
      setMessage(error.message || 'Failed to load invitation details');
    }
  };

  const handleAcceptInvitation = async () => {
    try {
      setStatus('loading');
      setMessage('Processing invitation...');
      setShowWrongUserWarning(false);

      console.log('🟡 [INVITATION] Accepting invitation:', invitationId);
      console.log('🟡 [INVITATION] User email:', user?.email);
      
      // 🔑 CRITICAL: Ensure API is initialized with current user and fresh token
      const groupPlannerApi = (await import('../../services/groupPlannerApi')).default;
      groupPlannerApi.setCurrentUser(user);
      const freshToken = await user.getIdToken(true);
      groupPlannerApi.setAuthToken(freshToken);
      console.log('✅ [INVITATION] API initialized with fresh token for:', user?.email);
      
      // First, check if we need to load invitation details for validation
      if (!invitationInfo) {
        console.log('Loading invitation details for validation...');
        try {
          const detailsResponse = await groupPlannerService.getInvitationDetails(invitationId);
          if (detailsResponse) {
            setInvitationInfo(detailsResponse);
            
            // Check email match
            const invitedEmail = detailsResponse.invited_email?.toLowerCase();
            const currentEmail = user?.email?.toLowerCase();
            
            console.log('Email validation:', { invitedEmail, currentEmail });
            
            if (invitedEmail && currentEmail && invitedEmail !== currentEmail) {
              // Wrong user is logged in
              setShowWrongUserWarning(true);
              setStatus('error');
              setMessage(`This invitation is for ${detailsResponse.invited_email}, but you're logged in as ${user?.email}.`);
              return;
            }
          }
        } catch (err) {
          console.error('Failed to load invitation details:', err);
        }
      }

      // Now accept the invitation
      const result = await acceptInvitation(invitationId);

      console.log('✅ [INVITATION] Invitation accepted:', result);

      setStatus('success');
      setMessage('✓ Invitation accepted! Redirecting...');

      // Clear pending invitation data
      localStorage.removeItem('pendingGroupInvitation');
      localStorage.removeItem('groupInvitationEmail');
      localStorage.removeItem('groupInvitationCreatedBy');
      
      // Mark as accepted in sessionStorage (prevents re-processing)
      const processingKey = `invitation_processing_${invitationId}`;
      sessionStorage.setItem(processingKey, 'accepted');
      console.log('✅ [INVITATION] Marked as accepted in sessionStorage');
      
      // ⚡ CRITICAL: Clear cache to force fresh group data load
      const groupPlannerService = (await import('../../services/groupPlannerService')).default;
      groupPlannerService.clearAllCache();
      console.log('🗑️ [INVITATION] Cache cleared for fresh data');

      // Redirect immediately to group-trip page
      console.log('🔄 [INVITATION] Redirecting to /group-trip');
      navigate('/group-trip', { replace: true });
    } catch (error) {
      console.error('❌ [INVITATION] Error accepting invitation:', error);
      
      // Check if already accepted
      if (error.message?.includes('already accepted') || error.message?.includes('already a member')) {
        setStatus('success');
        setMessage('✓ You\'re already part of this group!');
        setTimeout(() => {
          navigate('/group-trip', { replace: true });
        }, 1500);
      } else {
        setStatus('error');
        setMessage(error.message || 'Failed to accept invitation');
      }
    }
  };

  const handleLogoutAndRetry = async () => {
    // Store invitation details for after login
    localStorage.setItem('pendingGroupInvitation', invitationId);
    if (invitationInfo) {
      localStorage.setItem('groupInvitationEmail', invitationInfo.invited_email);
      localStorage.setItem('groupInvitationCreatedBy', invitationInfo.created_by_name || 'Someone');
    }
    navigate('/auth?redirect=group-invitation', { replace: true });
  };

  return (
    <div className="invitation-accept-page">
      <div className="invitation-container">
        {status === 'loading' && (
          <div className="invitation-content">
            <div className="invitation-spinner">
              <div className="spinner-ring"></div>
            </div>
            <h2 className="invitation-title">Processing Invitation...</h2>
            <p className="invitation-message">{message}</p>
          </div>
        )}

        {status === 'success' && (
          <div className="invitation-content success">
            <div className="invitation-icon">✨</div>
            <h2 className="invitation-title">Welcome to the Group!</h2>
            <p className="invitation-message">{message}</p>
            <p className="invitation-redirect">Redirecting to your group...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="invitation-content error">
            <div className="invitation-icon">⚠️</div>
            <h2 className="invitation-title">Unable to Accept Invitation</h2>
            <p className="invitation-message">{message}</p>
            {showWrongUserWarning && (
              <button 
                className="invitation-btn primary"
                onClick={handleLogoutAndRetry}
              >
                Logout & Sign In With Correct Email
              </button>
            )}
            <button 
              className="invitation-btn secondary"
              onClick={() => navigate('/')}
            >
              Back to Home
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
