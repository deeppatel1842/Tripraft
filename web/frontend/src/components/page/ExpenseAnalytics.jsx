import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import '../css/ExpenseAnalytics.css';

const ExpenseAnalytics = () => {
  const { currentUser } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboardUrl, setDashboardUrl] = useState('');

  // Admin check - you can modify this
  const ADMIN_EMAIL = 'rdcoding1842@gmail.com'; // Your admin email
  const isAdmin = currentUser && (
    currentUser.email === ADMIN_EMAIL || 
    currentUser.email === 'tripraft@gmail.com'
  );

  useEffect(() => {
    // Redirect non-admins
    if (!loading && !isAdmin) {
      navigate('/expenses');
      return;
    }

    if (isAdmin) {
      // Backend analytics dashboard URL
      // Uses auto_auth parameter to bypass manual token entry
      // Backend will automatically use TOKEN_ADMIN from .env
      const url = `http://localhost:5000/api/expense/analytics/dashboard?auto_auth=true`;
      setDashboardUrl(url);
      setLoading(false);
    }
  }, [isAdmin, loading, navigate]);

  if (loading) {
    return (
      <div className="expense-analytics-loading">
        <div className="spinner"></div>
        <p>Loading Analytics Dashboard...</p>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="expense-analytics-denied">
        <i className="fas fa-lock"></i>
        <h2>Access Denied</h2>
        <p>This analytics dashboard is only accessible to administrators.</p>
        <button onClick={() => navigate('/expenses')}>
          Return to Expenses
        </button>
      </div>
    );
  }

  if (error) {
    return (
      <div className="expense-analytics-error">
        <i className="fas fa-exclamation-triangle"></i>
        <h2>Error Loading Dashboard</h2>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="expense-analytics-page">
      <div className="analytics-header">
        <button 
          className="back-button"
          onClick={() => navigate('/expenses')}
        >
          <i className="fas fa-arrow-left"></i> Back to Expenses
        </button>
        <h1>
          <i className="fas fa-chart-line"></i> Expense Engine Analytics
        </h1>
        <button 
          className="refresh-button"
          onClick={() => window.location.reload()}
        >
          <i className="fas fa-sync-alt"></i> Refresh
        </button>
      </div>
      
      <div className="analytics-info">
        <p>
          <i className="fas fa-info-circle"></i> 
          Real-time performance monitoring for Expense Management System
        </p>
      </div>

      <div className="analytics-frame-container">
        <iframe
          src={dashboardUrl}
          title="Expense Analytics Dashboard"
          className="analytics-iframe"
          frameBorder="0"
          allow="clipboard-read; clipboard-write"
          loading="eager"
          onError={() => setError('Failed to load dashboard')}
        />
      </div>
    </div>
  );
};

export default ExpenseAnalytics;
