import React, { useState, useEffect, useRef } from 'react';
import { Plane, UserPlus, AlertCircle } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import QRCode from 'qrcode';
import '../css/Signup.css';

const Signup = ({ onSwitchToLogin }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { signUp, currentUser } = useAuth();
  
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [isFormValid, setIsFormValid] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState(2);
  const [isSuccess, setIsSuccess] = useState(false);
  const [agreePolicy, setAgreePolicy] = useState(false);
  const [errors, setErrors] = useState({});
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
      // Store invitation ID for after signup
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
            setFormData(prev => ({ ...prev, email: invitedEmail })); // Pre-fill the email
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
  }, [location.search]);

  // Handle pending invitation after user is authenticated
  useEffect(() => {
    const processPendingInvitation = async () => {
      if (currentUser && !loading) {
        const pendingInvitation = localStorage.getItem('pendingInvitation');
        
        if (pendingInvitation) {
          console.log('Processing pending invitation for authenticated user:', pendingInvitation);
          
          try {
            // Wait a bit for the token to be fully set
            await new Promise(resolve => setTimeout(resolve, 500));
            
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
          } catch (inviteError) {
            console.error('Error accepting invitation:', inviteError);
            // Still redirect to expenses even if acceptance fails
            localStorage.removeItem('pendingInvitation');
            localStorage.removeItem('invitationEmail');
            navigate('/expenses', { replace: true });
          }
        } else {
          // No pending invitation, redirect normally
          navigate(from, { replace: true });
        }
      }
    };
    
    processPendingInvitation();
  }, [currentUser, loading, navigate, from]);

  // Redirect if already logged in (but check for pending invitation first)
  useEffect(() => {
    if (currentUser && !localStorage.getItem('pendingInvitation')) {
      navigate(from, { replace: true });
    }
  }, [currentUser, navigate, from]);

  useEffect(() => {
    if (qrCanvasRef.current) {
      QRCode.toCanvas(qrCanvasRef.current, 'https://tripraft.com/signup', {
        width: 150,
        margin: 1,
        color: { dark: '#000000', light: '#FFFFFF' }
      });
    }
  }, []);

  const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  useEffect(() => {
    const newErrors = {};
    if (formData.email && !isValidEmail(formData.email)) {
      newErrors.email = 'Invalid email format';
    }
    if (formData.password && formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }
    if (formData.confirmPassword && formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    setErrors(newErrors);

    const valid = 
      formData.firstName.trim() !== '' &&
      formData.lastName.trim() !== '' &&
      isValidEmail(formData.email) &&
      formData.password.length >= 6 &&
      formData.password === formData.confirmPassword &&
      Object.keys(newErrors).length === 0;
    
    setIsFormValid(valid);
    if (!valid) {
      setDragPosition(2);
      setIsSuccess(false);
    }
  }, [formData]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleDragStart = (e) => {
    if (!isFormValid) return;
    setIsDragging(true);
    const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
    startXRef.current = clientX - dragPosition;
  };

  const handleDragMove = (e) => {
    if (!isDragging || !isFormValid) return;
    const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
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
      setTimeout(async () => {
        await handleSignup();
      }, 500);
    } else {
      setDragPosition(2);
    }
  };

  // Handle signup
  const handleSignup = async () => {
    if (!isFormValid || loading) return;
    
    try {
      setError('');
      setLoading(true);
      
      const displayName = `${formData.firstName} ${formData.lastName}`.trim();
      const result = await signUp(formData.email, formData.password, displayName);
      
      if (result.success) {
        // Don't process invitation here - let the useEffect handle it after currentUser is set
        console.log('Signup successful, waiting for auth state to update');
      } else {
        setError(result.error || 'Failed to create account. Please try again.');
        setDragPosition(2);
        setIsSuccess(false);
      }
    } catch (err) {
      setError(err.message || 'An error occurred during sign up.');
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
    <div className="signup-container">
      <div className="signup-boarding-pass">
        <div className="signup-left-panel">
          <div className="signup-bg-pattern">
            <div className="signup-bg-circle-1"></div>
            <div className="signup-bg-circle-2"></div>
          </div>
          <div className="signup-left-content">
            <div className="signup-header">
              <h1 className="signup-brand">Tripraft</h1>
              <UserPlus className="signup-icon" strokeWidth={2} />
            </div>
            <div className="signup-booking-info">
              <p className="signup-booking-label">Booking ID</p>
              <p className="signup-booking-number">BK{currentYear}</p>
            </div>
            <div className="signup-journey-info">
              <div className="signup-route-display">
                <div className="signup-route-item">
                  <span className="signup-route-label">From</span>
                  <span className="signup-route-value">Ideas</span>
                </div>
                <div className="signup-route-divider"></div>
                <div className="signup-plane-icon-wrapper">
                  <Plane className="signup-plane-icon" />
                </div>
                <div className="signup-route-divider"></div>
                <div className="signup-route-item">
                  <span className="signup-route-label">To</span>
                  <span className="signup-route-value">Adventures</span>
                </div>
              </div>
              <div className="signup-tagline-box">
                <p className="signup-tagline">Begin Your Journey<br />With A Single Step</p>
              </div>
            </div>
          </div>
          <div className="signup-qr-section">
            <div className="signup-qr-wrapper">
              <canvas ref={qrCanvasRef} className="signup-qr-canvas"></canvas>
            </div>
            <div className="signup-policy-check">
              <input type="checkbox" id="policy-agree-signup" checked={agreePolicy}
                onChange={(e) => setAgreePolicy(e.target.checked)} className="signup-policy-checkbox" />
              <label htmlFor="policy-agree-signup" className="signup-policy-label">I agree to Terms & Policy</label>
            </div>
          </div>
        </div>
        <div className="signup-divider-vertical"></div>
        <div className="signup-divider-horizontal"></div>
        <div className="signup-right-panel">
          <div className="signup-form-container">
            <div className="signup-form-header">
              <h2 className="signup-form-title">Book Your Raft</h2>
              <p className="signup-form-subtitle">Create your account and start exploring</p>
            </div>
            <form onSubmit={(e) => e.preventDefault()} className="signup-form">
              <div className="signup-form-row">
                <div className="signup-form-group">
                  <label htmlFor="firstName" className="signup-label">First Name</label>
                  <input type="text" id="firstName" name="firstName" value={formData.firstName}
                    onChange={handleInputChange} placeholder="John" className="signup-input" />
                </div>
                <div className="signup-form-group">
                  <label htmlFor="lastName" className="signup-label">Last Name</label>
                  <input type="text" id="lastName" name="lastName" value={formData.lastName}
                    onChange={handleInputChange} placeholder="Doe" className="signup-input" />
                </div>
              </div>
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
                  <strong>Group Invitation:</strong> Please sign up with {invitationEmail}
                </div>
              )}
              {error && (
                <div style={{
                  padding: '0.75rem 1rem',
                  marginBottom: '1rem',
                  backgroundColor: 'rgba(220, 38, 38, 0.1)',
                  border: '1px solid rgba(220, 38, 38, 0.3)',
                  borderRadius: '0.5rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: '#c33'
                }}>
                  <AlertCircle size={18} />
                  <span style={{ fontSize: '0.9rem' }}>{error}</span>
                </div>
              )}
              <div className="signup-form-group">
                <label htmlFor="email" className="signup-label">Email Address</label>
                <input type="email" id="email" name="email" value={formData.email}
                  onChange={handleInputChange} placeholder="passenger@email.com"
                  className={`signup-input ${formData.email && !isValidEmail(formData.email) ? 'error' : ''}`} />
              </div>
              <div className="signup-form-group">
                <label htmlFor="password" className="signup-label">Password</label>
                <input type="password" id="password" name="password" value={formData.password}
                  onChange={handleInputChange} placeholder="Min. 6 characters"
                  className={`signup-input ${errors.password ? 'error' : ''}`} />
              </div>
              <div className="signup-form-group">
                <label htmlFor="confirmPassword" className="signup-label">Confirm Password</label>
                <input type="password" id="confirmPassword" name="confirmPassword" value={formData.confirmPassword}
                  onChange={handleInputChange} placeholder="Re-enter password"
                  className={`signup-input ${errors.confirmPassword ? 'error' : ''}`} />
              </div>
              <div className="signup-slider-wrapper">
                <div ref={sliderRef}
                  className={`signup-slider-container ${
                    isSuccess ? 'signup-slider-success' : isFormValid ? 'signup-slider-enabled' : 'signup-slider-disabled'
                  }`}>
                  <div className="signup-slider-progress"
                    style={{ width: isFormValid && sliderRef.current ? `${(dragPosition / (sliderRef.current.offsetWidth - 50)) * 100}%` : '0%' }}></div>
                  <div className="signup-slider-text">
                    <span>{isSuccess ? '✓ Account Created!' : isFormValid ? 'Slide to Create Account ✈' : 'Complete All Fields'}</span>
                  </div>
                  {isFormValid && (
                    <div ref={handleRef} onMouseDown={handleDragStart} onTouchStart={handleDragStart}
                      className={`signup-slider-handle ${isDragging ? 'dragging' : ''}`}
                      style={{ left: `${dragPosition}px` }}>
                      <Plane className="signup-plane-handle-icon" style={{ transform: isDragging ? 'rotate(12deg)' : 'rotate(0deg)' }} />
                    </div>
                  )}
                </div>
                <p className="signup-slider-hint">{isFormValid ? '✈ Drag the plane to the right to create your account' : '⚠ Please complete all fields correctly'}</p>
              </div>
            </form>
            
            <div className="signup-footer">
              <p className="signup-footer-text">
                Already have an account?{' '}
                <button onClick={() => onSwitchToLogin ? onSwitchToLogin() : navigate('/login')} className="signup-footer-link">
                  Board Your Raft
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Signup;
