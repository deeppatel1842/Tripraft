/**
 * MemberSpending Component
 * Shows total spending breakdown by each group member
 */

import React, { useMemo } from 'react';
import { Users, TrendingUp, DollarSign } from 'lucide-react';

const MemberSpending = ({ 
  expenses = [], 
  members = [], 
  currency = 'USD',
  currentUserId 
}) => {
  // Calculate spending per member
  const memberSpending = useMemo(() => {
    const spending = {};
    
    // Initialize all members with 0
    members.forEach(member => {
      const memberId = member.user_id || member.id;
      if (memberId) {
        spending[memberId] = {
          userId: memberId,
          name: member.display_name || member.user?.display_name || member.username || 'Unknown',
          totalPaid: 0,
          transactionCount: 0
        };
      }
    });
    
    // Sum up expenses by who paid
    expenses.forEach(exp => {
      if (exp.is_deleted) return;
      const paidBy = exp.paid_by;
      if (paidBy && spending[paidBy]) {
        spending[paidBy].totalPaid += parseFloat(exp.amount) || 0;
        spending[paidBy].transactionCount += 1;
      }
    });
    
    // Convert to array and sort by total paid (descending)
    return Object.values(spending)
      .filter(m => m.totalPaid > 0 || m.transactionCount > 0)
      .sort((a, b) => b.totalPaid - a.totalPaid);
  }, [expenses, members]);

  // Calculate totals
  const totalGroupSpend = memberSpending.reduce((sum, m) => sum + m.totalPaid, 0);
  const maxSpend = Math.max(...memberSpending.map(m => m.totalPaid), 1);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: currency 
    }).format(amount);
  };

  if (memberSpending.length === 0) {
    return null;
  }

  return (
    <>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1rem'
      }}>
        <h3 style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          margin: 0,
          fontSize: '1rem',
          fontWeight: '600',
          color: '#111827'
        }}>
          <Users size={18} style={{ color: '#667eea' }} />
          Member Spending
        </h3>
        <span style={{
          fontSize: '0.75rem',
          color: '#6b7280',
          background: '#f3f4f6',
          padding: '4px 10px',
          borderRadius: '20px'
        }}>
          {memberSpending.length} member{memberSpending.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem'
      }}>
        {memberSpending.map((member, index) => {
          const percentage = totalGroupSpend > 0 
            ? ((member.totalPaid / totalGroupSpend) * 100).toFixed(1)
            : 0;
          const barWidth = maxSpend > 0 
            ? (member.totalPaid / maxSpend) * 100
            : 0;
          const isCurrentUser = Number(member.userId) === Number(currentUserId);
          
          return (
            <div 
              key={member.userId}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                padding: '0.75rem',
                background: isCurrentUser ? '#f0f9ff' : '#f9fafb',
                borderRadius: '8px',
                border: isCurrentUser ? '1px solid #bae6fd' : '1px solid transparent'
              }}
            >
              {/* Rank */}
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                background: index === 0 ? 'linear-gradient(135deg, #fbbf24, #f59e0b)' :
                            index === 1 ? 'linear-gradient(135deg, #9ca3af, #6b7280)' :
                            index === 2 ? 'linear-gradient(135deg, #d97706, #b45309)' :
                            '#e5e7eb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.7rem',
                fontWeight: '700',
                color: index < 3 ? 'white' : '#6b7280',
                flexShrink: 0
              }}>
                {index + 1}
              </div>
              
              {/* Name and bar */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '4px'
                }}>
                  <span style={{
                    fontSize: '0.875rem',
                    fontWeight: isCurrentUser ? '600' : '500',
                    color: '#111827',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    {member.name}
                    {isCurrentUser && (
                      <span style={{
                        fontSize: '0.65rem',
                        background: '#dbeafe',
                        color: '#1d4ed8',
                        padding: '2px 6px',
                        borderRadius: '10px',
                        fontWeight: '500'
                      }}>
                        You
                      </span>
                    )}
                  </span>
                  <span style={{
                    fontSize: '0.75rem',
                    color: '#6b7280'
                  }}>
                    {member.transactionCount} expense{member.transactionCount !== 1 ? 's' : ''}
                  </span>
                </div>
                
                {/* Progress bar */}
                <div style={{
                  height: '6px',
                  background: '#e5e7eb',
                  borderRadius: '3px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${barWidth}%`,
                    height: '100%',
                    background: isCurrentUser 
                      ? 'linear-gradient(90deg, #3b82f6, #2563eb)'
                      : 'linear-gradient(90deg, #667eea, #764ba2)',
                    borderRadius: '3px',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>
              
              {/* Amount */}
              <div style={{
                textAlign: 'right',
                flexShrink: 0
              }}>
                <div style={{
                  fontSize: '0.95rem',
                  fontWeight: '700',
                  color: '#111827'
                }}>
                  {formatCurrency(member.totalPaid)}
                </div>
                <div style={{
                  fontSize: '0.7rem',
                  color: '#9ca3af'
                }}>
                  {percentage}% of total
                </div>
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Total footer */}
      <div style={{
        marginTop: '1rem',
        paddingTop: '1rem',
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span style={{
          fontSize: '0.875rem',
          color: '#6b7280',
          fontWeight: '500'
        }}>
          Total Group Spending
        </span>
        <span style={{
          fontSize: '1.125rem',
          fontWeight: '700',
          color: '#111827'
        }}>
          {formatCurrency(totalGroupSpend)}
        </span>
      </div>
    </>
  );
};

export default MemberSpending;
