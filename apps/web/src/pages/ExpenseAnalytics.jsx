// Purpose: Renders the Expense Analytics interface within apps\web\src\pages.
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Footer from '../components/layout/jsx/Footer';
import './styles/ExpenseAnalytics.css';

export default function ExpenseAnalytics() {
  const { currentUser, loading } = useAuth();
  const navigate = useNavigate();
  if (loading) return <div role="status">Loading account...</div>;
  return <div className="expense-analytics-page"><div className="analytics-container"><div className="analytics-error">
    <h1>{currentUser?.is_admin ? 'Analytics' : 'Access denied'}</h1>
    <p>{currentUser?.is_admin ? 'The analytics dashboard is not available in this build.' : 'This page is for administrators only.'}</p>
    <button onClick={() => navigate('/expenses')}>Return to Expenses</button>
  </div></div><Footer /></div>;
}
