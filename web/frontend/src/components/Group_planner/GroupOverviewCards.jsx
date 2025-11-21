import React, { useState, useMemo } from 'react';
import { ListChecks, DollarSign, Plus, Check, X } from 'lucide-react';
import './GroupOverviewCards.css';

/**
 * GroupOverviewCards Component
 * Displays Checklist and Expense summary cards for the group
 */
export default function GroupOverviewCards({
  checklist = [],
  budget = { transactions: [] },
  currentUserId,
  onAddChecklistItem,
  onToggleChecklistItem,
  onAddTransaction,
}) {
  const [newChecklistItem, setNewChecklistItem] = useState('');
  const [newTransactionDesc, setNewTransactionDesc] = useState('');
  const [newTransactionAmount, setNewTransactionAmount] = useState('');
  const [transactionType, setTransactionType] = useState('estimated');

  // Calculate budget totals
  const totalEstimated = useMemo(() => {
    return budget.transactions
      ?.filter(t => t.type === 'estimated')
      .reduce((sum, t) => sum + (parseFloat(t.amount) || 0), 0) || 0;
  }, [budget.transactions]);

  const totalSpent = useMemo(() => {
    return budget.transactions
      ?.filter(t => t.type === 'spent')
      .reduce((sum, t) => sum + (parseFloat(t.amount) || 0), 0) || 0;
  }, [budget.transactions]);

  const remaining = totalEstimated - totalSpent;

  // Checklist stats
  const completedCount = checklist.filter(item => item.completed).length;
  const totalCount = checklist.length;

  const handleAddChecklistItem = (e) => {
    e.preventDefault();
    if (newChecklistItem.trim() && onAddChecklistItem) {
      onAddChecklistItem(newChecklistItem.trim());
      setNewChecklistItem('');
    }
  };

  const handleAddTransaction = (e) => {
    e.preventDefault();
    if (newTransactionDesc.trim() && newTransactionAmount && onAddTransaction) {
      onAddTransaction({
        description: newTransactionDesc.trim(),
        amount: parseFloat(newTransactionAmount),
        type: transactionType,
      });
      setNewTransactionDesc('');
      setNewTransactionAmount('');
      setTransactionType('estimated');
    }
  };

  return (
    <div className="group-overview-cards">
      {/* Checklist Card */}
      <div className="overview-card checklist-card">
        <div className="card-header">
          <div className="header-left">
            <ListChecks className="header-icon" size={24} />
            <div>
              <h3>Trip Checklist</h3>
              <p className="card-subtitle">
                {completedCount} of {totalCount} completed
              </p>
            </div>
          </div>
          {totalCount > 0 && (
            <div className="progress-badge">
              {Math.round((completedCount / totalCount) * 100)}%
            </div>
          )}
        </div>

        {/* Add New Item Form */}
        <form onSubmit={handleAddChecklistItem} className="add-item-form">
          <input
            type="text"
            placeholder="Add a packing item or task..."
            value={newChecklistItem}
            onChange={(e) => setNewChecklistItem(e.target.value)}
            className="add-input"
          />
          <button type="submit" className="add-btn" title="Add Item">
            <Plus size={18} />
          </button>
        </form>

        {/* Checklist Items */}
        <div className="checklist-items">
          {checklist.length === 0 ? (
            <p className="empty-message">No items yet. Add your first task!</p>
          ) : (
            checklist.slice(0, 5).map((item) => (
              <label key={item.id} className="checklist-item">
                <input
                  type="checkbox"
                  checked={item.completed}
                  onChange={() => onToggleChecklistItem && onToggleChecklistItem(item.id)}
                  className="checkbox-input"
                />
                <span className={item.completed ? 'item-text completed' : 'item-text'}>
                  {item.item}
                </span>
                {item.completed && <Check className="check-icon" size={14} />}
              </label>
            ))
          )}
          {checklist.length > 5 && (
            <p className="more-items">+{checklist.length - 5} more items...</p>
          )}
        </div>
      </div>

      {/* Expense Card */}
      <div className="overview-card expense-card">
        <div className="card-header">
          <div className="header-left">
            <DollarSign className="header-icon" size={24} />
            <div>
              <h3>Trip Budget</h3>
              <p className="card-subtitle">Track estimated & spent costs</p>
            </div>
          </div>
        </div>

        {/* Budget Summary */}
        <div className="budget-summary">
          <div className="budget-row estimated">
            <span className="budget-label">Estimated</span>
            <span className="budget-amount">${totalEstimated.toFixed(2)}</span>
          </div>
          <div className="budget-row spent">
            <span className="budget-label">Spent</span>
            <span className="budget-amount">${totalSpent.toFixed(2)}</span>
          </div>
          <div className={`budget-row remaining ${remaining < 0 ? 'negative' : ''}`}>
            <span className="budget-label">Remaining</span>
            <span className="budget-amount">${remaining.toFixed(2)}</span>
          </div>
        </div>

        {/* Add Transaction Form */}
        <form onSubmit={handleAddTransaction} className="add-transaction-form">
          <input
            type="text"
            placeholder="Description (e.g., Flight, Hotel)"
            value={newTransactionDesc}
            onChange={(e) => setNewTransactionDesc(e.target.value)}
            className="add-input transaction-desc"
          />
          <div className="transaction-row">
            <input
              type="number"
              placeholder="Amount"
              value={newTransactionAmount}
              onChange={(e) => setNewTransactionAmount(e.target.value)}
              min="0"
              step="0.01"
              className="add-input transaction-amount"
            />
            <select
              value={transactionType}
              onChange={(e) => setTransactionType(e.target.value)}
              className="transaction-type"
            >
              <option value="estimated">Estimated</option>
              <option value="spent">Spent</option>
            </select>
            <button type="submit" className="add-btn" title="Add Transaction">
              <Plus size={18} />
            </button>
          </div>
        </form>

        {/* Recent Transactions */}
        <div className="recent-transactions">
          {budget.transactions?.length === 0 ? (
            <p className="empty-message">No transactions yet</p>
          ) : (
            budget.transactions?.slice(0, 3).map((transaction) => (
              <div key={transaction.id} className="transaction-item">
                <div className="transaction-info">
                  <span className="transaction-desc">{transaction.description}</span>
                  <span className={`transaction-badge ${transaction.type}`}>
                    {transaction.type === 'estimated' ? 'EST' : 'SPENT'}
                  </span>
                </div>
                <span className={`transaction-amount ${transaction.type}`}>
                  ${transaction.amount.toFixed(2)}
                </span>
              </div>
            ))
          )}
          {budget.transactions?.length > 3 && (
            <p className="more-items">+{budget.transactions.length - 3} more transactions...</p>
          )}
        </div>
      </div>
    </div>
  );
}
