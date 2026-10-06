// Purpose: Renders the Expense Summary interface within apps\web\src\features\expenses\jsx.
import React from 'react';
import { Wallet, ArrowUpCircle, ArrowDownCircle } from 'lucide-react';

const ExpenseSummary = ({ transactions, mode = 'personal' }) => {
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  };

  // Income category - only Salary is income
  const isIncome = (category) => {
    return category && category.toLowerCase() === 'salary';
  };
  
  // Filter out deleted transactions for calculations
  const activeTransactions = transactions.filter(t => !t.is_deleted);
  
  // For group mode: only show total expenses
  if (mode === 'group') {
    const totalExpenses = activeTransactions.reduce((sum, t) => sum + parseFloat(t.amount || 0), 0);
    
    return (
      <div className="summary-cards">
        <div className="summary-card expense-card-modern">
          <div className="expense-icon-wrapper">
            <ArrowDownCircle size={32} />
          </div>
          <div className="expense-details">
            <span className="expense-label">Total Expenses</span>
            <span className="expense-amount">{formatCurrency(totalExpenses)}</span>
            <span className="expense-count">{activeTransactions.length} transaction{activeTransactions.length !== 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>
    );
  }
  
  // For personal mode: show all three cards
  const income = activeTransactions
    .filter(t => isIncome(t.category))
    .reduce((sum, t) => sum + parseFloat(t.amount || 0), 0);
  
  const expense = activeTransactions
    .filter(t => !isIncome(t.category))
    .reduce((sum, t) => sum + parseFloat(t.amount || 0), 0);
  
  const balance = income - expense;

  return (
    <div className="summary-cards">
      <div className="summary-card">
        <div className="card-header">
          <h2>Total Balance</h2>
          <Wallet className="icon-green" size={24} />
        </div>
        <p className="amount">{formatCurrency(balance)}</p>
      </div>
      <div className="summary-card">
        <div className="card-header">
          <h2>Total Income</h2>
          <ArrowUpCircle className="icon-blue" size={24} />
        </div>
        <p className="amount income-green">{formatCurrency(income)}</p>
      </div>
      <div className="summary-card">
        <div className="card-header">
          <h2>Total Expenses</h2>
          <ArrowDownCircle className="icon-red" size={24} />
        </div>
        <p className="amount expense-red">{formatCurrency(expense)}</p>
      </div>
    </div>
  );
};

export default ExpenseSummary;
