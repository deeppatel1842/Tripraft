import React from 'react';
import Header from '../../layout/jsx/Header';
import Footer from '../../layout/jsx/Footer';
import ExpenseManager from '../../expenses/jsx/ExpenseManager';
import { useAuth } from '../../../context/AuthContext';
import '../css/ExpensePage.css';

const ExpensePage = () => {
  const { currentUser, signOut } = useAuth();
  
  return (
    <div className="expense-page">
      <Header 
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={signOut}
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
