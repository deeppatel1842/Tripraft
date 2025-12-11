import React, { useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import expenseApi from '../../services/expenseApi';
import './SettlementHistory.css';

const SettlementHistory = forwardRef(({ groupId, totalExpenses }, ref) => {
  const [settlements, setSettlements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isExpanded, setIsExpanded] = useState(totalExpenses > 0); // Auto-expand if there are expenses

  // Expose refresh method to parent
  useImperativeHandle(ref, () => ({
    refresh: loadSettlements
  }));

  useEffect(() => {
    // Load settlements when component mounts or groupId changes
    if (groupId) {
      loadSettlements();
    }
  }, [groupId]);

  // Auto-expand when expenses exist
  useEffect(() => {
    if (totalExpenses > 0 && !isExpanded) {
      setIsExpanded(true);
    }
  }, [totalExpenses]);

  const loadSettlements = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await expenseApi.getGroupSettlements(groupId);
      setSettlements(data.settlements || []);
    } catch (err) {
      console.error('Error loading settlements:', err);
      setError('Failed to load settlement history');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  if (!groupId) return null;

  return (
    <div className="settlement-history">
      <div 
        className="settlement-history-header"
        onClick={() => setIsExpanded(!isExpanded)}
        style={{ cursor: 'pointer' }}
      >
        <h3>
          <span className="header-icon">📝</span>
          Settlement History
          {settlements.length > 0 && (
            <span className="settlement-count">{settlements.length}</span>
          )}
        </h3>
        <span style={{ 
          fontSize: '0.875rem', 
          color: '#9ca3af',
          transition: 'transform 0.2s',
          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
          display: 'inline-block'
        }}>
          ▼
        </span>
      </div>

      {isExpanded && (
        <div className="settlement-content">
          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <span>Loading settlements...</span>
            </div>
          ) : error ? (
            <div className="error-state">
              <p>{error}</p>
              <button onClick={loadSettlements} className="retry-button">
                Try Again
              </button>
            </div>
          ) : settlements.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">💸</span>
              <p>No settlements recorded yet</p>
              <small>Settlements will appear here once recorded</small>
            </div>
          ) : (
            <div className="settlements-list">
              <div className="settlements-table-header">
                <div>Description</div>
                <div>Category</div>
                <div>Date</div>
                <div style={{ textAlign: 'right' }}>Amount</div>
              </div>
              
              {settlements.map((settlement, index) => (
                <div key={settlement.id || settlement.settlement_id || `settlement-${index}`} className="settlement-item">
                  <div className="settlement-description">
                    {settlement.notes || `${settlement.from_user_name} paid ${settlement.to_user_name}`}
                  </div>
                  
                  <div className="settlement-category">
                    settlement
                  </div>
                  
                  <div className="settlement-date">
                    {formatDate(settlement.created_at)}
                  </div>
                  
                  <div className="settlement-amount">
                    {formatAmount(settlement.amount)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default SettlementHistory;
