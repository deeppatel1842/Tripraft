import React from 'react';
import { TrendingUp, Users, ArrowRight, Receipt } from 'lucide-react';

const GroupSummaryCards = ({ 
  totalExpenses = 0, 
  totalAmount = 0, 
  remainingBalance = 0,
  totalSettlements = 0,
  settlementCount = 0,
  myShare = 0,
  memberCount = 1,
  transactionCount = 0,
  onSettlementCardClick,
  currency = 'USD' 
}) => {
  const formatCurrency = (amount) => {
    // Handle NaN, null, undefined
    const safeAmount = (amount && !isNaN(amount)) ? amount : 0;
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: currency 
    }).format(Math.abs(safeAmount));
  };

  // Calculate average share per member (avoid NaN)
  const safeMemberCount = memberCount > 0 ? memberCount : 1;
  const safeTotalAmount = (totalAmount && !isNaN(totalAmount)) ? totalAmount : 0;
  const averageShare = safeTotalAmount / safeMemberCount;
  const sharePercentage = safeMemberCount > 0 ? Math.round(100 / safeMemberCount) : 0;

  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
      gap: '1rem', 
      marginBottom: '1.5rem' 
    }}>
      {/* Total Group Spend Card */}
      <div style={{
        background: 'white',
        padding: '1.25rem',
        borderRadius: '12px',
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <span style={{ fontSize: '0.875rem', fontWeight: '500', color: '#6b7280' }}>Total Group Spend</span>
            <div style={{ fontSize: '2rem', fontWeight: '700', color: '#111827', marginTop: '0.25rem' }}>
              {formatCurrency(safeTotalAmount)}
            </div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '4px',
              marginTop: '0.5rem',
              fontSize: '0.8rem', 
              color: '#6b7280' 
            }}>
              <span>{transactionCount || totalExpenses} transaction{(transactionCount || totalExpenses) !== 1 ? 's' : ''}</span>
            </div>
          </div>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #fef2f2, #fee2e2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <TrendingUp size={24} style={{ color: '#ef4444' }} />
          </div>
        </div>
      </div>

      {/* My Share Card */}
      <div style={{
        background: 'white',
        padding: '1.25rem',
        borderRadius: '12px',
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div style={{ flex: 1 }}>
            <span style={{ fontSize: '0.875rem', fontWeight: '500', color: '#6b7280' }}>My Share</span>
            <div style={{ fontSize: '2rem', fontWeight: '700', color: '#111827', marginTop: '0.25rem' }}>
              {formatCurrency(averageShare)}
            </div>
            {/* Progress bar */}
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ 
                height: '6px', 
                background: '#e5e7eb', 
                borderRadius: '3px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${Math.min(sharePercentage, 100)}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #3b82f6, #2563eb)',
                  borderRadius: '3px'
                }} />
              </div>
              <div style={{ 
                fontSize: '0.75rem', 
                color: '#6b7280', 
                marginTop: '0.5rem' 
              }}>
                Average share: ~{sharePercentage}% ({safeMemberCount} member{safeMemberCount !== 1 ? 's' : ''})
              </div>
            </div>
          </div>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #eff6ff, #dbeafe)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginLeft: '1rem'
          }}>
            <Users size={24} style={{ color: '#3b82f6' }} />
          </div>
        </div>
      </div>

      {/* To be Settled Card */}
      <div 
        onClick={onSettlementCardClick}
        style={{
          background: 'white',
          padding: '1.25rem',
          borderRadius: '12px',
          border: '1px solid #e5e7eb',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          cursor: 'pointer',
          transition: 'all 0.2s'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)';
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <span style={{ fontSize: '0.875rem', fontWeight: '500', color: '#6b7280' }}>To be settled</span>
            <div style={{ 
              fontSize: '2rem', 
              fontWeight: '700', 
              color: remainingBalance > 0 ? '#16a34a' : '#111827', 
              marginTop: '0.25rem' 
            }}>
              {remainingBalance > 0 ? '+' : ''}{formatCurrency(remainingBalance)}
            </div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '4px',
              marginTop: '0.5rem',
              fontSize: '0.8rem', 
              color: '#3b82f6',
              cursor: 'pointer'
            }}>
              <span>Settlement History </span>
              <ArrowRight size={14} />
            </div>
          </div>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #ecfdf5, #d1fae5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Receipt size={24} style={{ color: '#10b981' }} />
          </div>
        </div>
      </div>
    </div>
  );
};

// Memoize to prevent unnecessary re-renders
export default React.memo(GroupSummaryCards);
