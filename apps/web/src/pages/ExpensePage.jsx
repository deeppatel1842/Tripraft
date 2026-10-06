// Purpose: Renders the Expense Page interface within apps\web\src\pages.
import React from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/layout/jsx/Header';
import Footer from '../components/layout/jsx/Footer';
import ExpenseManager from '../features/expenses/jsx/ExpenseManager';
import { useAuth } from '../context/AuthContext';
import './styles/ExpensePage.css';

const ExpensePage = () => {
  const navigate = useNavigate();
  const { currentUser, signOut } = useAuth();
  
  return (
    <div className="expense-page">
      <Header 
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={async () => { await signOut(); navigate('/'); }}
      />
      <main className="main-content">
        <div className="expense-container">
          <ExpenseManager />
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default ExpensePage;
