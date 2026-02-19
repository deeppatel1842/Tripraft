import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import groupPlannerApi from '../../../services/groupPlannerApi';
import Header from '../../layout/jsx/Header';
import Footer from '../../layout/jsx/Footer';
import '../css/InvitationAcceptPage.css';

/**
 * InvitationAcceptPage for Group Planner
 * Handles accepting group planner trip invitations
 * Full standalone page with Header/Footer
 */
export default function InvitationAcceptPage() {
  const { invitationId: pathInvitationId } = useParams();
  const [searchParams] = useSearchParams();
  const invitationId = pathInvitationId || searchParams.get('id');
  
  const { user, currentUser, signOut } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');
  const [tripDetails, setTripDetails] = useState(null);
  const [showWrongUserWarning, setShowWrongUserWarning] = useState(false);
  const [invitedEmail, setInvitedEmail] = useState(null);
  
  // Prevent duplicate API calls
  const acceptInProgress = useRef(false);
  const initialized = useRef(false);

  useEffect(() => {
    if (!invitationId) {
      navigate('/login', { replace: true });
      return;
    }

    // Prevent duplicate execution
    if (initialized.current || acceptInProgress.current) {
      return;
    }
    
    initialized.current = true;

    if (user) {
      handleAcceptInvitation();
    } else {
      // Redirect to login with invitation context
      localStorage.setItem('pendingGroupInvitation', invitationId);
      navigate(`/login?redirect=group-invitation&invitationId=${invitationId}`, { replace: true });
    }
  }, [invitationId, user]);

  const handleLogoutAndRetry = async () => {
    await signOut();
    localStorage.setItem('pendingGroupInvitation', invitationId);
    navigate('/login?redirect=group-invitation');
  };

  const handleAcceptInvitation = async () => {
    if (acceptInProgress.current) return;
    acceptInProgress.current = true;
    
    try {
      setStatus('loading');
      setMessage('Processing your trip invitation...');
      setShowWrongUserWarning(false);

      const response = await groupPlannerApi.acceptInvitation(invitationId);

      if (response.success) {
        setStatus('success');
        setMessage(`You've successfully joined the trip "${response.group_name || response.trip_name || 'Trip'}"!`);
        setTripDetails(response);
        
        // Clear pending invitation
        localStorage.removeItem('pendingGroupInvitation');

        setTimeout(() => {
          // Navigate to the group planner page
          if (response.group_id) {
            navigate(`/group-planner/${response.group_id}`);
          } else {
            navigate('/group-planner');
          }
        }, 2000);
      } else {
        setStatus('error');
        setMessage(response.message || 'Failed to accept invitation');
      }
    } catch (error) {
      setStatus('error');

      if (error.message.includes('404')) {
        setMessage('This invitation link is invalid or has expired.');
        localStorage.removeItem('pendingGroupInvitation');
      } else if (error.message.includes('already accepted') || error.message.includes('already a member')) {
        setMessage('You have already joined this trip.');
        localStorage.removeItem('pendingGroupInvitation');
        setTimeout(() => {
          navigate('/group-planner');
        }, 2000);
      } else if (error.message.includes('403')) {
        setMessage('This invitation is not for your account. Please log in with the correct email address.');
        setShowWrongUserWarning(true);
      } else {
        setMessage(`Failed to accept invitation: ${error.message}`);
      }
    } finally {
      acceptInProgress.current = false;
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'loading':
        return (
          <div className="iap-spinner">
            <div className="iap-spinner-circle"></div>
          </div>
        );
      case 'success':
        return (
          <svg className="iap-status-icon iap-success" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10" strokeWidth="2"/>
            <path d="M9 12l2 2 4-4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        );
      case 'error':
        return (
          <svg className="iap-status-icon iap-error" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10" strokeWidth="2"/>
            <path d="M15 9l-6 6M9 9l6 6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <>
      <Header
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={signOut}
      />
      <div className="iap-container">
        <div className="iap-card">
          <div className="iap-header">
            <h1>Trip Invitation</h1>
            <p>You've been invited to join a trip!</p>
          </div>

          <div className="iap-content">
            {getStatusIcon()}
            <h2>{status === 'success' ? 'Welcome Aboard!' : status === 'error' ? 'Oops!' : 'Processing'}</h2>
            <p className="iap-message">{message}</p>

            {status === 'success' && tripDetails && (
              <div className="iap-details">
                <p>Redirecting you to the trip planner...</p>
              </div>
            )}

            {showWrongUserWarning && (
              <div className="iap-action-buttons">
                <button 
                  className="iap-btn-primary"
                  onClick={handleLogoutAndRetry}
                >
                  Log out and sign in with correct account
                </button>
                <button 
                  className="iap-btn-secondary"
                  onClick={() => navigate('/group-planner')}
                >
                  Go to My Trips
                </button>
              </div>
            )}

            {status === 'error' && !showWrongUserWarning && (
              <div className="iap-action-buttons">
                <button 
                  className="iap-btn-primary"
                  onClick={() => navigate('/group-planner')}
                >
                  Go to My Trips
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}
