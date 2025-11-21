import React, { useState, useEffect, useRef } from 'react';
import { Plane, Shield, AlertCircle } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import QRCode from 'qrcode';
import '../css/Login.css';

const Login = ({ onSwitchToSignup }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn, currentUser } = useAuth();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isFormValid, setIsFormValid] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState(2);
  const [isSuccess, setIsSuccess] = useState(false);
  const [agreePolicy, setAgreePolicy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [invitationEmail, setInvitationEmail] = useState('');
  
  const sliderRef = useRef(null);
  const handleRef = useRef(null);
  const qrCanvasRef = useRef(null);
  const startXRef = useRef(0);
  const currentXRef = useRef(0);

  const currentYear = new Date().getFullYear();
  const from = location.state?.from?.pathname || '/';

  // Check for pending invitation - ONLY if redirected from invitation page
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const isInvitationRedirect = searchParams.get('redirect') === 'invitation';
    const invitationId = searchParams.get('invitationId');
    
    if (isInvitationRedirect && invitationId) {
      // Store invitation ID for after login
      localStorage.setItem('pendingInvitation', invitationId);
      
      // Fetch invitation details to pre-fill email
      const fetchInvitationEmail = async () => {
        try {
          const expenseApi = (await import('../../services/expenseApi')).default;
          const response = await expenseApi.getInvitationDetails(invitationId);
          if (response.success && response.invitation?.invited_email) {
            const invitedEmail = response.invitation.invited_email;
            localStorage.setItem('invitationEmail', invitedEmail);
            setInvitationEmail(invitedEmail);
            setEmail(invitedEmail); // Pre-fill the email
          }
        } catch (error) {
          console.error('Error fetching invitation details:', error);
        }
      };
      
      fetchInvitationEmail();
    } else if (!isInvitationRedirect) {
      // Not from invitation, clear any old invitation data
      setInvitationEmail('');
    }
    
    // Check for group planner invitation email
    const groupInvitationEmail = localStorage.getItem('groupInvitationEmail');
    if (groupInvitationEmail) {
      console.log('📧 Pre-filling email from group invitation:', groupInvitationEmail);
      setEmail(groupInvitationEmail);
      setInvitationEmail(groupInvitationEmail);
    }
  }, [location.search]);

  // Handle pending invitation after user is authenticated
  useEffect(() => {
    const processPendingInvitation = async () => {
      if (currentUser && !loading) {
        // Check for group invitation first
        const pendingGroupInvitation = localStorage.getItem('pendingGroupInvitation');
        const pendingInvitation = localStorage.getItem('pendingInvitation');
        
        try {
          // Wait a bit for the token to be fully set
          await new Promise(resolve => setTimeout(resolve, 500));
          
          if (pendingGroupInvitation) {
            console.log('🔵 Processing pending GROUP invitation for authenticated user:', pendingGroupInvitation);
            
            // 🔑 CRITICAL: Set currentUser in groupPlannerApi for auth
            const groupPlannerApi = (await import('../../services/groupPlannerApi')).default;
            groupPlannerApi.setCurrentUser(currentUser);
            
            // Get and store token
            const token = await currentUser.getIdToken(true);
            groupPlannerApi.setAuthToken(token);
            console.log('✅ Token set for group planner API');
            
            // Wait a bit more for everything to be ready
            await new Promise(resolve => setTimeout(resolve, 300));
            
            // DON'T remove localStorage items here - let InvitationAcceptPage do it after successful acceptance
            // This ensures the invitation ID is available when the page loads
            console.log('🔄 Redirecting to invitation acceptance page');
            
            navigate(`/invitations/${pendingGroupInvitation}`, { replace: true });
          } else if (pendingInvitation) {
            console.log('Processing pending EXPENSE invitation for authenticated user:', pendingInvitation);
            
            // Import expenseApi
            const expenseApi = (await import('../../services/expenseApi')).default;
            
            // Accept the invitation
            const acceptResponse = await expenseApi.acceptInvitation(pendingInvitation);
            console.log('Invitation accepted:', acceptResponse);
            
            // Clear the pending invitation
            localStorage.removeItem('pendingInvitation');
            localStorage.removeItem('invitationEmail');
            
            // Redirect to expenses page with group view
            navigate('/expenses?view=group', { replace: true });
          } else {
            // No pending invitation, redirect normally
            navigate(from, { replace: true });
          }
        } catch (inviteError) {
          console.error('Error processing invitation:', inviteError);
          // Clear any pending invitations
          localStorage.removeItem('pendingGroupInvitation');
          localStorage.removeItem('groupInvitationEmail');
          localStorage.removeItem('groupInvitationCreatedBy');
          localStorage.removeItem('pendingInvitation');
          localStorage.removeItem('invitationEmail');
          
          // Redirect to appropriate page
          navigate(from, { replace: true });
        }
      }
    };
    
    processPendingInvitation();
  }, [currentUser, loading, navigate, from]);

  // Generate QR Code
  useEffect(() => {
    if (qrCanvasRef.current) {
      QRCode.toCanvas(qrCanvasRef.current, 'https://tripraft.com', {
        width: 150,
        margin: 1,
        color: {
          dark: '#000000',
          light: '#FFFFFF'
        }
      });
    }
  }, []);

  // Email validation
  const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Validate form
  useEffect(() => {
    const valid = isValidEmail(email) && password.trim().length > 0;
    setIsFormValid(valid);
    if (!valid) {
      setDragPosition(2);
      setIsSuccess(false);
    }
  }, [email, password]);

  // Drag handlers
  const handleDragStart = (e) => {
    if (!isFormValid) return;
    
    setIsDragging(true);
    const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
    startXRef.current = clientX - dragPosition;
  };

  const handleDragMove = (e) => {
    if (!isDragging || !isFormValid) return;

    const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
    currentXRef.current = clientX;

    const sliderRect = sliderRef.current.getBoundingClientRect();
    const handleWidth = 46;
    const maxDrag = sliderRect.width - handleWidth - 4;
    
    let newPosition = clientX - startXRef.current;
    newPosition = Math.max(2, Math.min(newPosition, maxDrag));
    
    setDragPosition(newPosition);
  };

  const handleDragEnd = () => {
    if (!isDragging) return;
    
    setIsDragging(false);

    const sliderRect = sliderRef.current.getBoundingClientRect();
    const handleWidth = 46;
    const maxDrag = sliderRect.width - handleWidth - 4;

    if (dragPosition >= maxDrag - 10) {
      setIsSuccess(true);
      setDragPosition(maxDrag);
      
      // Submit login
      setTimeout(async () => {
        await handleLogin();
      }, 500);
    } else {
      setDragPosition(2);
    }
  };

  // Handle email/password login
  const handleLogin = async () => {
    if (!isFormValid || loading) return;
    
    try {
      setError('');
      setLoading(true);
      
      const result = await signIn(email, password);
      
      if (result.success) {
        // Check if there's a pending invitation
        const pendingInvitation = localStorage.getItem('pendingInvitation');
        
        if (pendingInvitation) {
          console.log('Pending invitation found, will process after auth state updates:', pendingInvitation);
          // Don't process here - let the useEffect handle it after currentUser is set
          // Just navigate or wait - the useEffect will handle the invitation
        } else {
          // Navigate to intended page or home
          navigate(from, { replace: true });
        }
      } else {
        setError(result.error || 'Failed to sign in. Please check your credentials.');
        setDragPosition(2);
        setIsSuccess(false);
      }
    } catch (err) {
      setError(err.message || 'An error occurred during sign in.');
      setDragPosition(2);
      setIsSuccess(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleDragMove);
      document.addEventListener('mouseup', handleDragEnd);
      document.addEventListener('touchmove', handleDragMove);
      document.addEventListener('touchend', handleDragEnd);
    }

    return () => {
      document.removeEventListener('mousemove', handleDragMove);
      document.removeEventListener('mouseup', handleDragEnd);
      document.removeEventListener('touchmove', handleDragMove);
      document.removeEventListener('touchend', handleDragEnd);
    };
  }, [isDragging, dragPosition]);

  return (
    <div className="login-container">
      <div className="login-boarding-pass">
        
        {/* Left Side - Boarding Pass Info */}
        <div className="login-left-panel">
          {/* Background pattern */}
          <div className="login-bg-pattern">
            <div className="login-bg-circle-1"></div>
            <div className="login-bg-circle-2"></div>
          </div>

          <div className="login-left-content">
            <div className="login-header">
              <h1 className="login-brand">Tripraft</h1>
              <Shield className="login-shield-icon" strokeWidth={2} />
            </div>
            
            <div className="login-flight-info">
              <p className="login-flight-label">Flight Number</p>
              <p className="login-flight-number">TR{currentYear}</p>
            </div>

            <div className="login-journey-info">
              <div className="login-route-display">
                <div className="login-route-item">
                  <span className="login-route-label">From</span>
                  <span className="login-route-value">Dreams</span>
                </div>
                <div className="login-route-divider"></div>
                <div className="login-plane-icon-wrapper">
                  <Plane className="login-plane-icon" />
                </div>
                <div className="login-route-divider"></div>
                <div className="login-route-item">
                  <span className="login-route-label">To</span>
                  <span className="login-route-value">Reality</span>
                </div>
              </div>
              
              <div className="login-tagline-box">
                <p className="login-tagline">
                  Your Journey Begins<br />With A Click
                </p>
              </div>
            </div>
          </div>

          <div className="login-qr-section">
            <div className="login-qr-wrapper">
              <canvas ref={qrCanvasRef} className="login-qr-canvas"></canvas>
            </div>
            <div className="login-policy-check">
              <input 
                type="checkbox" 
                id="policy-agree" 
                checked={agreePolicy}
                onChange={(e) => setAgreePolicy(e.target.checked)}
                className="login-policy-checkbox"
              />
              <label htmlFor="policy-agree" className="login-policy-label">
                I agree to Terms & Policy
              </label>
            </div>
          </div>
        </div>

        {/* Perforated divider */}
        <div className="login-divider-vertical"></div>
        <div className="login-divider-horizontal"></div>

        {/* Right Side - Login Form */}
        <div className="login-right-panel">
          <div className="login-form-container">
            <div className="login-form-header">
              <h2 className="login-form-title">Welcome Aboard</h2>
              <p className="login-form-subtitle">Present your boarding credentials</p>
            </div>

            <form onSubmit={(e) => e.preventDefault()} className="login-form">
              {invitationEmail && (
                <div style={{
                  padding: '0.75rem',
                  background: '#eff6ff',
                  border: '1px solid #dbeafe',
                  borderRadius: '8px',
                  marginBottom: '1rem',
                  color: '#1e40af',
                  fontSize: '0.9rem',
                  textAlign: 'center'
                }}>
                  <strong>Group Invitation:</strong> Please log in with {invitationEmail}
                </div>
              )}

              {error && (
                <div style={{
                  padding: '0.75rem',
                  background: '#fee',
                  border: '1px solid #fcc',
                  borderRadius: '8px',
                  marginBottom: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: '#c33'
                }}>
                  <AlertCircle size={18} />
                  <span style={{ fontSize: '0.9rem' }}>{error}</span>
                </div>
              )}

              <div className="login-form-group">
                <label htmlFor="login-email" className="login-label">
                  Email Address
                </label>
                <input
                  type="email"
                  id="login-email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="passenger@email.com"
                  className={`login-input ${email && !isValidEmail(email) ? 'error' : ''}`}
                />
              </div>

              <div className="login-form-group">
                <label htmlFor="login-password" className="login-label">
                  Password
                </label>
                <input
                  type="password"
                  id="login-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="login-input"
                />
              </div>

              {/* Beautiful Drag to Login */}
              <div className="login-slider-wrapper">
                <div
                  ref={sliderRef}
                  className={`login-slider-container ${
                    isSuccess
                      ? 'login-slider-success'
                      : isFormValid
                      ? 'login-slider-enabled'
                      : 'login-slider-disabled'
                  }`}
                >
                  {/* Progress bar */}
                  <div
                    className="login-slider-progress"
                    style={{
                      width: isFormValid && sliderRef.current ? `${(dragPosition / (sliderRef.current.offsetWidth - 50)) * 100}%` : '0%'
                    }}
                  ></div>

                  {/* Slide text */}
                  <div className="login-slider-text">
                    <span>
                      {isSuccess ? '✓ Ready for Takeoff!' : isFormValid ? 'Slide to Board ✈' : 'Enter Valid Credentials'}
                    </span>
                  </div>

                  {/* Plane handle */}
                  {isFormValid && (
                    <div
                      ref={handleRef}
                      onMouseDown={handleDragStart}
                      onTouchStart={handleDragStart}
                      className={`login-slider-handle ${isDragging ? 'dragging' : ''}`}
                      style={{ left: `${dragPosition}px` }}
                    >
                      <Plane 
                        className="login-plane-handle-icon"
                        style={{ transform: isDragging ? 'rotate(12deg)' : 'rotate(0deg)' }}
                      />
                    </div>
                  )}
                </div>
                <p className="login-slider-hint">
                  {isFormValid ? '✈ Drag the plane to the right to board your flight' : '⚠ Please enter a valid email and password'}
                </p>
              </div>
            </form>

            <div className="login-footer">
              <p className="login-footer-text">
                Don't have a ticket?{' '}
                <button
                  onClick={() => onSwitchToSignup ? onSwitchToSignup() : navigate('/signup')}
                  className="login-footer-link"
                >
                  Book Your Raft
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
