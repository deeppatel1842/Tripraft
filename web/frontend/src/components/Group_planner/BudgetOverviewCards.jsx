import React, { useState, useMemo } from 'react';
import { Edit2 } from 'lucide-react';
import './BudgetOverviewCards.css';

/**
 * BudgetOverviewCards Component
 * Shows 3-column budget summary cards (Estimated, Spent, Remaining)
 * White theme with editable estimated cost
 */
export default function BudgetOverviewCards({ 
  budget = { transactions: [], estimated_budget: 0 },
  estimatedBudget = 0,
  onUpdateBudget
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedAmount, setEditedAmount] = useState('');

  // Use estimated_budget from props or budget object
  const totalEstimatedCost = estimatedBudget || budget.estimated_budget || 0;

  const totalSpentCost = useMemo(() =>
    budget.transactions
      .filter(t => t.type === 'spent')
      .reduce((sum, t) => sum + (parseFloat(t.amount) || 0), 0),
    [budget.transactions]
  );

  const remainingBudget = 0;
  const isOverBudget = totalSpentCost > totalEstimatedCost;

  const handleEditClick = () => {
    setEditedAmount(totalEstimatedCost.toString());
    setIsEditing(true);
  };

  const handleSave = async () => {
    const newAmount = parseFloat(editedAmount) || 0;
    if (onUpdateBudget) {
      await onUpdateBudget(newAmount);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
  };

  return (
    <div className="budget-overview-cards">
      {/* Estimated Cost Card */}
      <div className="budget-card budget-card-estimated">
        <div className="budget-card-header">
          <p className="budget-card-label">Total Estimated Cost</p>
          {!isEditing && onUpdateBudget && (
            <button className="budget-edit-btn" onClick={handleEditClick} title="Edit estimated cost">
              <Edit2 size={14} />
            </button>
          )}
        </div>
        {isEditing ? (
          <div className="budget-edit-input-wrapper">
            <input
              type="number"
              className="budget-edit-input"
              value={editedAmount}
              onChange={(e) => setEditedAmount(e.target.value)}
              autoFocus
            />
            <div className="budget-edit-actions">
              <button className="budget-save-btn" onClick={handleSave}>Save</button>
              <button className="budget-cancel-btn" onClick={handleCancel}>Cancel</button>
            </div>
          </div>
        ) : (
          <p className="budget-card-amount">${totalEstimatedCost.toFixed(2)}</p>
        )}
      </div>

      {/* Spent Cost Card */}
      <div className="budget-card budget-card-spent">
        <p className="budget-card-label">Total Spent So Far</p>
        <p className="budget-card-amount">${totalSpentCost.toFixed(2)}</p>
      </div>

      {/* Remaining Budget Card */}
      <div className={`budget-card ${isOverBudget ? 'budget-card-over' : 'budget-card-remaining'}`}>
        <p className="budget-card-label">Per Person</p>
        <p className="budget-card-amount">${remainingBudget.toFixed(2)}</p>
      </div>
    </div>
  );
}
