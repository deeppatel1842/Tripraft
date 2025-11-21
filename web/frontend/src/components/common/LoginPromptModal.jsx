import React from 'react';
import { useNavigate } from 'react-router-dom';
import './LoginPromptModal.css';

/**
 * LoginPromptModal - Reusable modal to prompt users to login
 * Isolated component with its own styling
 */
const LoginPromptModal = ({ isOpen, onClose, message }) => {
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleLogin = () => {
    onClose();
    navigate('/login');
  };

  return (
    <div className="login-prompt-overlay" onClick={onClose}>
      <div className="login-prompt-modal" onClick={(e) => e.stopPropagation()}>
        <div className="login-prompt-header">
          <h2>Authentication Required</h2>
          <button className="login-prompt-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        
        <div className="login-prompt-body">
          <div className="login-prompt-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
              <polyline points="10 17 15 12 10 7"></polyline>
              <line x1="15" y1="12" x2="3" y2="12"></line>
            </svg>
          </div>
          <p className="login-prompt-message">
            {message || 'Please login to continue using this feature.'}
          </p>
        </div>
        
        <div className="login-prompt-footer">
          <button className="login-prompt-btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button className="login-prompt-btn-login" onClick={handleLogin}>
            Go to Login
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginPromptModal;
