// Purpose: Warns about inactivity and resets the logout timer when activity resumes.
/**
 * Inactivity Tracker Component
 * Monitors user activity and logs out after 15 minutes of inactivity
 * Shows a warning popup before logout (like banks do)
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '../../../context/AuthContext';

// Inactivity timeout in milliseconds (15 minutes)
const INACTIVITY_TIMEOUT = 15 * 60 * 1000;
// Warning popup time before logout (1 minute before timeout)
const WARNING_BEFORE_LOGOUT = 60 * 1000;

const InactivityTracker = () => {
  const { currentUser, signOut } = useAuth();
  const [showWarning, setShowWarning] = useState(false);
  const [countdown, setCountdown] = useState(60);
  const inactivityTimer = useRef(null);
  const warningTimer = useRef(null);
  const countdownInterval = useRef(null);

  const handleLogout = useCallback(async () => {
    setShowWarning(false);
    clearAllTimers();
    await signOut();
    // Redirect to login page
    window.location.href = '/login';
  }, [signOut]);

  const clearAllTimers = () => {
    if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
    if (warningTimer.current) clearTimeout(warningTimer.current);
    if (countdownInterval.current) clearInterval(countdownInterval.current);
  };

  const resetTimer = useCallback(() => {
    // Clear existing timers
    clearAllTimers();
    setShowWarning(false);
    setCountdown(60);

    // Don't set timers if user is not logged in
    if (!currentUser) return;

    // Set warning timer (shows popup 1 minute before logout)
    warningTimer.current = setTimeout(() => {
      setShowWarning(true);
      setCountdown(60);
      
      // Start countdown
      countdownInterval.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(countdownInterval.current);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }, INACTIVITY_TIMEOUT - WARNING_BEFORE_LOGOUT);

    // Set logout timer
    inactivityTimer.current = setTimeout(() => {
      handleLogout();
    }, INACTIVITY_TIMEOUT);
  }, [currentUser, handleLogout]);

  const handleStayLoggedIn = () => {
    setShowWarning(false);
    resetTimer();
  };

  useEffect(() => {
    if (!currentUser) {
      clearAllTimers();
      return;
    }

    // Events that indicate user activity
    const activityEvents = [
      'mousedown',
      'mousemove',
      'keydown',
      'scroll',
      'touchstart',
      'click',
      'keypress'
    ];

    // Reset timer on any activity
    const handleActivity = () => {
      resetTimer();
    };

    // Add event listeners
    activityEvents.forEach(event => {
      document.addEventListener(event, handleActivity, { passive: true });
    });

    // Initialize timer
    resetTimer();

    // Cleanup
    return () => {
      activityEvents.forEach(event => {
        document.removeEventListener(event, handleActivity);
      });
      clearAllTimers();
    };
  }, [currentUser, resetTimer]);

  // Don't render anything if user is not logged in
  if (!currentUser || !showWarning) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '2rem',
        maxWidth: '400px',
        width: '90%',
        textAlign: 'center',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
      }}>
        <div style={{
          width: '60px',
          height: '60px',
          backgroundColor: '#fff3e0',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1.5rem',
          fontSize: '1.5rem'
        }}>
          ⏱️
        </div>
        
        <h2 style={{
          margin: '0 0 0.5rem',
          color: '#333',
          fontSize: '1.25rem',
          fontWeight: '600'
        }}>
          Session Timeout Warning
        </h2>
        
        <p style={{
          color: '#666',
          margin: '0 0 1.5rem',
          lineHeight: '1.5'
        }}>
          You have been inactive for 14 minutes. For your security, you will be logged out in:
        </p>
        
        <div style={{
          fontSize: '2.5rem',
          fontWeight: '700',
          color: countdown <= 30 ? '#e74c3c' : '#f39c12',
          marginBottom: '1.5rem'
        }}>
          {countdown}s
        </div>
        
        <div style={{
          display: 'flex',
          gap: '1rem',
          justifyContent: 'center'
        }}>
          <button
            onClick={handleStayLoggedIn}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#667eea',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#5a6fd6'}
            onMouseOut={(e) => e.target.style.backgroundColor = '#667eea'}
          >
            Stay Logged In
          </button>
          
          <button
            onClick={handleLogout}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#f5f5f5',
              color: '#666',
              border: '1px solid #ddd',
              borderRadius: '8px',
              fontSize: '1rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#eee'}
            onMouseOut={(e) => e.target.style.backgroundColor = '#f5f5f5'}
          >
            Logout Now
          </button>
        </div>
        
        <p style={{
          color: '#999',
          fontSize: '0.75rem',
          marginTop: '1rem'
        }}>
          Move your mouse or press any key to stay active
        </p>
      </div>
    </div>
  );
};

export default InactivityTracker;
