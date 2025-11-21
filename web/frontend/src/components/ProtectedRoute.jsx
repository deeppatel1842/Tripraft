/**
 * Protected Route Component
 * Secures routes that require authentication
 * Redirects to login if user is not authenticated
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { RefreshCw } from 'lucide-react';

const ProtectedRoute = ({ children }) => {
  const { currentUser, loading } = useAuth();
  const location = useLocation();

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

  // Redirect to login if not authenticated
  if (!currentUser) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Render protected content
  return children;
};

export default ProtectedRoute;
