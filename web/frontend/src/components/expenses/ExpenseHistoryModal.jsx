import React from 'react';
import { X, History, Clock, User, ArrowRight } from 'lucide-react';
import { useExpenseEditHistory } from '../../hooks/useExpenseQuery';
import './ExpenseHistoryModal.css';

/**
 * ExpenseHistoryModal - Phase 12 (Updated Phase 19.1)
 * Shows edit history for an expense
 * 
 * Phase 19.1: Refactored to use React Query hook (useExpenseEditHistory)
 * - Prevents duplicate API calls with staleTime caching
 * - Data persists when modal is reopened (gcTime: 10 min)
 * - No re-fetch on window focus or mount
 * 
 * Features:
 * - Shows who changed what and when
 * - Color-coded field changes
 * - Chronological timeline view
 */
const ExpenseHistoryModal = ({ expense, members, onClose }) => {
  const expenseId = expense?.id || expense?.expense_id;
  
  // Phase 19.1: Use React Query hook for caching and deduplication
  const { data, isLoading, error } = useExpenseEditHistory(expenseId);
  
  const history = data?.history || [];
  const loadingState = isLoading;
  const errorMessage = error?.message || (data?.success === false ? data.error : null);

  // Get member name from user ID
  const getMemberName = (userId) => {
    if (!userId || !members) return 'Unknown User';
    const member = members.find(m => (m.user_id || m.id) === userId);
    return member?.user?.display_name || member?.display_name || member?.email || 'Unknown User';
  };

  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  // Format field value for display
  const formatValue = (field, value) => {
    if (value === null || value === undefined) return 'None';
    
    // Format amounts as currency
    if (field === 'amount') {
      return `$${parseFloat(value).toFixed(2)}`;
    }
    
    // Format user IDs as names
    if (field === 'paid_by' || field === 'changed_by') {
      return getMemberName(value);
    }
    
    // Format dates - Phase 17.5 fix for timezone issues
    // Date strings like "2025-01-15" should be displayed as-is without timezone conversion
    if (field === 'expense_date' || field === 'date') {
      // If it's a date-only string (YYYY-MM-DD), parse and display without timezone conversion
      if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
        const [year, month, day] = value.split('-');
        // Create date in local timezone by using component values
        const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        return date.toLocaleDateString();
      }
      // For full datetime strings, use normal parsing
      return new Date(value).toLocaleDateString();
    }
    
    // Format splits array
    if (field === 'splits' && Array.isArray(value)) {
      return `${value.length} ${value.length === 1 ? 'person' : 'people'}`;
    }
    
    return String(value);
  };

  // Get human-readable field name
  const getFieldLabel = (field) => {
    const labels = {
      description: 'Description',
      amount: 'Amount',
      paid_by: 'Paid By',
      category: 'Category',
      notes: 'Notes',
      expense_date: 'Date',
      splits: 'Split With',
      currency: 'Currency'
    };
    return labels[field] || field;
  };

  // Get action badge color
  const getActionColor = (action) => {
    switch (action) {
      case 'created': return 'badge-green';
      case 'updated': return 'badge-blue';
      case 'deleted': return 'badge-red';
      case 'restored': return 'badge-yellow';
      default: return 'badge-gray';
    }
  };

  return (
    <div className="expense-history-overlay" onClick={onClose}>
      <div className="expense-history-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="header-title">
            <History size={20} />
            <h2>Edit History</h2>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="expense-summary">
          <h3>{expense?.description || 'Expense'}</h3>
          <span className="amount">${parseFloat(expense?.amount || 0).toFixed(2)}</span>
        </div>

        <div className="modal-content">
          {loadingState ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Loading history...</p>
            </div>
          ) : errorMessage ? (
            <div className="error-state">
              <p>{errorMessage}</p>
            </div>
          ) : history.length === 0 ? (
            <div className="empty-state">
              <History size={48} />
              <p>No edit history available</p>
              <small>This expense hasn't been modified since creation</small>
            </div>
          ) : (
            <div className="history-timeline">
              {history.map((entry, index) => (
                <div key={entry.id || index} className="history-entry">
                  <div className="entry-marker">
                    <div className={`marker-dot ${getActionColor(entry.action)}`}></div>
                    {index < history.length - 1 && <div className="marker-line"></div>}
                  </div>
                  
                  <div className="entry-content">
                    <div className="entry-header">
                      <span className={`action-badge ${getActionColor(entry.action)}`}>
                        {entry.action}
                      </span>
                      <div className="entry-meta">
                        <User size={14} />
                        <span>{entry.changed_by_name || getMemberName(entry.changed_by)}</span>
                        <Clock size={14} />
                        <span>{formatDate(entry.changed_at)}</span>
                      </div>
                    </div>

                    {entry.action === 'updated' && entry.changes && entry.changes.length > 0 && (
                      <div className="changes-list">
                        {entry.changes
                          .filter(change => {
                            // Filter out unchanged values
                            const oldVal = change.old_value ?? change.old;
                            const newVal = change.new_value ?? change.new;
                            const fieldName = change.field_name || change.field;
                            
                            // For splits, compare lengths if arrays
                            if (fieldName === 'splits') {
                              const oldLen = Array.isArray(oldVal) ? oldVal.length : 0;
                              const newLen = Array.isArray(newVal) ? newVal.length : 0;
                              return oldLen !== newLen;
                            }
                            
                            // Skip if both are same
                            return String(oldVal) !== String(newVal);
                          })
                          .map((change, cIndex) => (
                          <div key={cIndex} className="change-item">
                            <span className="field-name">{getFieldLabel(change.field_name || change.field)}</span>
                            <div className="change-values">
                              <span className="old-value">
                                {formatValue(change.field_name || change.field, change.old_value || change.old)}
                              </span>
                              <ArrowRight size={14} className="arrow" />
                              <span className="new-value">
                                {formatValue(change.field_name || change.field, change.new_value || change.new)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {entry.action === 'created' && (
                      <p className="action-description">Expense was created</p>
                    )}

                    {entry.action === 'deleted' && (
                      <p className="action-description">Expense was deleted</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExpenseHistoryModal;
