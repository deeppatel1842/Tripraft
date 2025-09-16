/**
 * Login Page Component with dark theme and Firebase authentication
 */
import React, { useState, useEffect } from 'react';
import authService from '../firebase/authService';
import './LoginPage.css';

const LoginPage = ({ onLoginSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Handle email/password authentication
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validation
    if (!email || !password) {
      setError('Email and password are required');
      setLoading(false);
      return;
    }

    if (!isLogin && password !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      let result;
      
      if (isLogin) {
        result = await authService.signInWithEmail(email, password);
      } else {
        result = await authService.signUpWithEmail(email, password, displayName);
      }

      if (result.success) {
        // Verify with backend
        const backendResult = await authService.verifyWithBackend(result.token);
        
        if (backendResult.success) {
          onLoginSuccess(backendResult.user);
        } else {
          console.error('Backend verification failed', backendResult);
          const msg = backendResult.error || backendResult.message || `Server error${backendResult.status ? ' ' + backendResult.status : ''}`;
          setError(`Failed to verify with server: ${msg}`);
        }
      } else {
        setError(getErrorMessage(result.error));
      }
    } catch (err) {
      setError('An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Handle Google authentication
  const handleGoogleAuth = async () => {
    setLoading(true);
    setError('');

    try {
      const result = await authService.signInWithGoogle();
      
      if (result.success) {
        const backendResult = await authService.verifyWithBackend(result.token);
        
        if (backendResult.success) {
          onLoginSuccess(backendResult.user);
        } else {
          console.error('Backend verification failed', backendResult);
          const msg = backendResult.error || backendResult.message || `Server error${backendResult.status ? ' ' + backendResult.status : ''}`;
          setError(`Failed to verify with server: ${msg}`);
        }
      } else {
        setError(getErrorMessage(result.error));
      }
    } catch (err) {
      setError('Google authentication failed');
    } finally {
      setLoading(false);
    }
  };

  // Handle Apple authentication
  const handleAppleAuth = async () => {
    setLoading(true);
    setError('');

    try {
      const result = await authService.signInWithApple();
      
      if (result.success) {
        const backendResult = await authService.verifyWithBackend(result.token);
        
        if (backendResult.success) {
          onLoginSuccess(backendResult.user);
        } else {
          console.error('Backend verification failed', backendResult);
          const msg = backendResult.error || backendResult.message || `Server error${backendResult.status ? ' ' + backendResult.status : ''}`;
          setError(`Failed to verify with server: ${msg}`);
        }
      } else {
        setError(getErrorMessage(result.error));
      }
    } catch (err) {
      setError('Apple authentication failed');
    } finally {
      setLoading(false);
    }
  };

  // Convert Firebase error codes to user-friendly messages
  const getErrorMessage = (errorCode) => {
    switch (errorCode) {
      case 'auth/user-not-found':
        return 'No account found with this email';
      case 'auth/wrong-password':
        return 'Incorrect password';
      case 'auth/email-already-in-use':
        return 'Email is already registered';
      case 'auth/weak-password':
        return 'Password should be at least 6 characters';
      case 'auth/invalid-email':
        return 'Invalid email address';
      default:
        return 'Authentication failed. Please try again.';
    }
  };

  return (
    <div className="login-container">
      <div className="login-content">
        <div className="login-header">
          <h1 className="app-title">Wayfinder</h1>
        </div>

        <div className="login-form-container">
          <div className="login-form-header">
            <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
            <p>{isLogin ? 'Log in to your account.' : 'Join Wayfinder today.'}</p>
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="login-form">
            {!isLogin && (
              <div className="input-group">
                <input
                  type="text"
                  placeholder="Full Name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="form-input"
                />
              </div>
            )}

            <div className="input-group">
              <input
                type="email"
                placeholder="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="form-input"
                required
              />
            </div>

            <div className="input-group">
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="form-input"
                required
              />
            </div>

            {!isLogin && (
              <div className="input-group">
                <input
                  type="password"
                  placeholder="Confirm Password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="form-input"
                  required
                />
              </div>
            )}

            {isLogin && (
              <div className="forgot-password">
                <a href="#" onClick={(e) => e.preventDefault()}>
                  Forgot Password?
                </a>
              </div>
            )}

            <button
              type="submit"
              className="login-button"
              disabled={loading}
            >
              {loading ? 'Loading...' : (isLogin ? 'Log In' : 'Sign Up')}
            </button>
          </form>

          <div className="divider">
            <span>OR</span>
          </div>

          <div className="social-auth">
            <button
              type="button"
              className="social-button google-button"
              onClick={handleGoogleAuth}
              disabled={loading}
            >
              <span className="social-icon">G</span>
              Continue with Google
            </button>

          </div>

          <div className="switch-auth">
            <p>
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <button
                type="button"
                className="switch-button"
                onClick={() => setIsLogin(!isLogin)}
              >
                {isLogin ? 'Sign Up' : 'Log In'}
              </button>
            </p>
          </div>
        </div>

        <div className="login-footer">
          <p>Wayfinder</p>
          <div className="footer-links">
            <a href="#">Privacy Policy</a>
            <span>•</span>
            <a href="#">Terms of Service</a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;