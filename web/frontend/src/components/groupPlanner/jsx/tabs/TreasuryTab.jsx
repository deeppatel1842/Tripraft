import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useExpenseSummary } from '../../../../hooks/useGroupPlannerQuery';
import { toObject } from '../../utils/groupPlannerUtils';
import { formatCurrency } from '../../utils/formatters';

/**
 * Treasury tab - expense summary and breakdown.
 *
 * Props: groupId, budgetCurrency
 */
export default function TreasuryTab({ groupId, budgetCurrency }) {
  const navigate = useNavigate();
  const { data: expenseSummaryRaw } = useExpenseSummary(groupId);
  const expenseSummary = useMemo(() => toObject(expenseSummaryRaw), [expenseSummaryRaw]);

  const totalSpent = expenseSummary?.total_spent || 0;
  const currency = budgetCurrency || 'USD';

  return (
    <div className="gp-view">
      <div className="gp-treasury-header">
        <h2 className="gp-section-title">Treasury.</h2>
        <div style={{ textAlign: 'right' }}>
          <span className="gp-treasury-total-label">Total Spent</span>
          <p className="gp-treasury-total">{formatCurrency(totalSpent, currency)}</p>
        </div>
      </div>

      {expenseSummary?.expenses && expenseSummary.expenses.length > 0 ? (
        <table className="gp-treasury-table">
          <thead><tr><th>Item</th><th style={{ textAlign: 'right' }}>Spent</th></tr></thead>
          <tbody>
            {expenseSummary.expenses.map((e, i) => (
              <tr key={i}>
                <td>{e.description || e.item || 'Expense'}</td>
                <td>{formatCurrency(e.amount || e.actual || 0, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="gp-empty-agenda">No expenses tracked yet.</div>
      )}

      <button className="gp-treasury-link-btn" onClick={() => navigate('/expenses')} style={{ marginTop: 24 }}>
        Open Expense Management
      </button>
    </div>
  );
}
