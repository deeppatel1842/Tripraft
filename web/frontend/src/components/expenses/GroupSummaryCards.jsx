import React from 'react';
import { DollarSign, TrendingDown, Receipt } from 'lucide-react';

const GroupSummaryCards = ({ 
  totalExpenses = 0, 
  totalAmount = 0, 
  remainingBalance = 0,
  totalSettlements = 0,
  settlementCount = 0,
  onSettlementCardClick,
  currency = 'USD' 
}) => {
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: currency 
    }).format(Math.abs(amount));
  };

  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
      gap: '1rem', 
      marginBottom: '1.5rem' 
    }}>
      {/* Total Expenses Card */}
      <div style={{
        background: 'white',
        padding: '1rem',
        borderRadius: '8px',
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: '500', color: '#6b7280' }}>Total Expenses</span>
          <DollarSign size={18} style={{ color: '#ef4444' }} />
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#dc2626', marginBottom: '0.25rem' }}>
          {formatCurrency(totalAmount)}
        </div>
        <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
          {totalExpenses} transaction{totalExpenses !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Remaining Balance Card */}
      <div style={{
        background: 'white',
        padding: '1rem',
        borderRadius: '8px',
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: '500', color: '#6b7280' }}>Remaining Balance</span>
          <TrendingDown size={18} style={{ color: '#3b82f6' }} />
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#111827', marginBottom: '0.25rem' }}>
          {formatCurrency(remainingBalance)}
        </div>
        <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
          To be settled
        </div>
      </div>

      {/* Total Settlements Card (Clickable) */}
      <div 
        onClick={onSettlementCardClick}
        style={{
          background: 'white',
          padding: '1rem',
          borderRadius: '8px',
          border: '1px solid #e5e7eb',
          boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
          cursor: 'pointer',
          transition: 'all 0.2s'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = '0 1px 2px rgba(0,0,0,0.05)';
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: '500', color: '#6b7280' }}>Total Settlements</span>
          <Receipt size={18} style={{ color: '#10b981' }} />
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#16a34a', marginBottom: '0.25rem' }}>
          {formatCurrency(totalSettlements)}
        </div>
        <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
          {settlementCount} payment{settlementCount !== 1 ? 's' : ''} • Click for details
        </div>
      </div>
    </div>
  );
};

// Memoize to prevent unnecessary re-renders
export default React.memo(GroupSummaryCards);
