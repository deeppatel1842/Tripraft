/**
 * Protected Route Component
 * Secures routes that require authentication
 * Shows a login-required page if user is not authenticated
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { RefreshCw, LogIn, Home, Lock } from 'lucide-react';

const ProtectedRoute = ({ children }) => {
  const { currentUser, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  // Show loading spinner while checking auth
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
      }}>
        <RefreshCw 
          size={48} 
          color="#fff" 
          style={{ animation: 'spin 1s linear infinite' }}
        />
        <p style={{ 
          marginTop: '1rem', 
          color: '#fff', 
          fontSize: '1.1rem',
          fontWeight: '500'
        }}>
          Securing your journey...
        </p>
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Show login-required page if not authenticated
  if (!currentUser) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '2rem',
        textAlign: 'center'
      }}>
        <div style={{
          background: 'rgba(255,255,255,0.12)',
          borderRadius: '50%',
          width: '100px',
          height: '100px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '1.5rem'
        }}>
          <Lock size={48} color="#fff" />
        </div>
        <h2 style={{ color: '#fff', fontSize: '1.8rem', marginBottom: '0.5rem', fontWeight: '700' }}>
          Login Required
        </h2>
        <p style={{ color: 'rgba(255,255,255,0.85)', fontSize: '1.05rem', maxWidth: '400px', lineHeight: '1.5', marginBottom: '2rem' }}>
          Sign in to access this feature. One login gives you full access to all TripRaft services.
        </p>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
          <button
            onClick={() => navigate('/login', { state: { from: location } })}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.75rem 2rem', fontSize: '1rem', fontWeight: '600',
              background: '#fff', color: '#667eea', border: 'none',
              borderRadius: '12px', cursor: 'pointer',
              transition: 'transform 0.15s, box-shadow 0.15s',
              boxShadow: '0 4px 15px rgba(0,0,0,0.15)'
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.2)'; }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 15px rgba(0,0,0,0.15)'; }}
          >
            <LogIn size={18} /> Sign In
          </button>
          <button
            onClick={() => navigate('/')}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.75rem 2rem', fontSize: '1rem', fontWeight: '600',
              background: 'transparent', color: '#fff',
              border: '2px solid rgba(255,255,255,0.5)',
              borderRadius: '12px', cursor: 'pointer',
              transition: 'transform 0.15s, border-color 0.15s'
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.borderColor = '#fff'; }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.5)'; }}
          >
            <Home size={18} /> Go Home
          </button>
        </div>
      </div>
    );
  }

  // Render protected content
  return children;
};

export default ProtectedRoute;
