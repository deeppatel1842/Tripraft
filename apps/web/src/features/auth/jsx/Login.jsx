// Purpose: Renders the Login interface within apps\web\src\features\auth\jsx.
import React, { useState, useEffect, useRef } from 'react';
import { Plane, Shield, AlertCircle, Home } from 'lucide-react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
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
      
      // Phase 17.5 Fix: Check localStorage first to avoid duplicate API calls
      const cachedEmail = localStorage.getItem('invitationEmail');
      if (cachedEmail) {
        setInvitationEmail(cachedEmail);
        setEmail(cachedEmail);
        return; // Skip API call - email already cached from InvitationAccept
      }
      
      // Only fetch if not cached (fallback for direct navigation)
      const fetchInvitationEmail = async () => {
        try {
          const expenseApi = (await import('../../../services/expenseApi')).default;
          const response = await expenseApi.getInvitationDetails(invitationId);
          if (response.success && (response.data ?? response).invitation?.invited_email) {
            const invitedEmail = (response.data ?? response).invitation.invited_email;
            localStorage.setItem('invitationEmail', invitedEmail);
            setInvitationEmail(invitedEmail);
            setEmail(invitedEmail);
          }
        } catch (error) {
          setError('Invitation details could not be loaded. Sign in to open the invitation.');
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
      setEmail(groupInvitationEmail);
      setInvitationEmail(groupInvitationEmail);
    }
  }, [location.search]);

  // Route once after authentication; the accept page owns the mutation.
  useEffect(() => {
    if (!currentUser || loading) return;
    const groupInvite = localStorage.getItem('pendingGroupInvitation');
    const expenseInvite = localStorage.getItem('pendingInvitation');
    navigate(groupInvite ? '/invitations/' + groupInvite : expenseInvite ? '/invitation/' + expenseInvite : from, { replace: true });
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
      
      const result = await signIn(email.trim().toLowerCase(), password);
      
      if (result.success) {
        // The authentication effect owns the redirect.
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
      {/* Home button */}
      <Link to="/" style={{
        position: 'absolute', top: '1.25rem', left: '1.25rem', zIndex: 10,
        display: 'flex', alignItems: 'center', gap: '0.4rem',
        padding: '0.5rem 1rem', background: 'rgba(255,255,255,0.15)',
        borderRadius: '10px', color: '#fff', textDecoration: 'none',
        fontSize: '0.9rem', fontWeight: '600', backdropFilter: 'blur(8px)',
        border: '1px solid rgba(255,255,255,0.2)', transition: 'background 0.2s'
      }}>
        <Home size={16} /> Home
      </Link>
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
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && isFormValid && !loading) {
                      e.preventDefault();
                      handleLogin();
                    }
                  }}
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
