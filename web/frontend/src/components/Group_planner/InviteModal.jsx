import React, { useState } from 'react';

export default function InviteModal({ isOpen, onClose, onSubmit, error, successMessage }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!email.trim()) {
      console.error('Email address is required');
      return;
    }
    setLoading(true);
    try {
      await onSubmit(email);
      setEmail('');
    } catch (error) {
      console.error('Error sending invitation:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={`demo-modal ${isOpen ? 'show' : ''}`} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="demo-dialog">
        <header>
          <strong>Invite Member</strong>
          <button className="demo-close" onClick={onClose}>×</button>
        </header>
        <div className="demo-body">
          {error && (
            <div style={{ color: '#b91c1c', fontSize: '14px', marginBottom: '8px', padding: '8px', backgroundColor: '#fee2e2', borderRadius: '4px' }}>
              {error}
            </div>
          )}
          {successMessage && (
            <div style={{ color: '#16a34a', fontSize: '14px', marginBottom: '8px', padding: '8px', backgroundColor: '#dcfce7', borderRadius: '4px' }}>
              {successMessage}
            </div>
          )}
          <div className="demo-field">
            <input
              type="email"
              className="demo-input"
              placeholder="friend@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            />
          </div>
        </div>
        <div className="demo-foot">
          <button className="demo-ghost" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button className="demo-primary" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Sending...' : 'Send Invitation'}
          </button>
        </div>
      </div>
    </div>
  );
}
