import React, { useState } from 'react';
import SettlementModal from './SettlementModal';
import SettlementHistoryModal from './SettlementHistoryModal';
import GroupSummaryCards from './GroupSummaryCards';

const GroupBalances = ({ 
  group, 
  balances, 
  members, 
  onBalanceUpdate, 
  totalExpenses = 0, 
  totalExpensesAmount = 0,
  settlementHistory = [],     // PHASE 2: Receive from parent
  loadingSettlements = false, // PHASE 2: Receive from parent
  onSettlementSuccess         // PHASE 2: Callback to parent
}) => {
  const [selectedSettlement, setSelectedSettlement] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  // PHASE 2: Removed local settlement loading - now centralized in ExpenseManager
  // This eliminates 3 redundant API calls (75% reduction)

  const handleSettleUp = (settlement) => {
    setSelectedSettlement(settlement);
    setIsModalOpen(true);
  };

  const handleSettlementSuccess = async (settlementData) => {
    setIsModalOpen(false);
    setSelectedSettlement(null);
    
    console.log('💰 [PHASE 2.7 FIX] Settlement modal closed, processing optimistic update');
    
    // PHASE 2.7 FIX: Call parent callback FIRST
    // This allows parent to handle API call and actual balance reload
    // onBalanceUpdate is for optimistic updates only (not needed now)
    if (onSettlementSuccess) {
      await onSettlementSuccess(settlementData);
    }
    
    console.log('✅ Settlement processed by parent');
  };
  const formatCurrency = (amount, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: currency 
    }).format(Math.abs(amount));
  };

  // Helper function to get member display name
  const getMemberName = (userId) => {
    if (!members || !userId) return 'Unknown User';
    
    const member = members.find(m => 
      (m.user_id || m.id) === userId
    );
    
    if (member) {
      return member.user?.display_name || 
             member.user?.username || 
             member.user?.email ||
             member.display_name ||
             member.username || 
             member.email ||
             'Unknown User';
    }
    
    return 'Unknown User';
  };

  const currency = group?.currency || 'USD';

  // DEBUG: Log balance data
  console.log('💰 [GroupBalances] Received balances:', balances);
  console.log('💰 [GroupBalances] Balance count:', balances?.length);
  if (balances && balances.length > 0) {
    console.log('💰 [GroupBalances] First balance:', balances[0]);
    console.log('💰 [GroupBalances] Balance structure:', Object.keys(balances[0]));
  }

  // Filter out settled balances (very close to zero)
  const significantBalances = (balances || []).filter(balance => 
    balance && Math.abs(balance.net_balance || 0) > 0.01
  );
  
  console.log('💰 [GroupBalances] Significant balances:', significantBalances.length);

  // Calculate who owes whom for simplified display
  const calculateSettlements = () => {
    const settlements = [];
    
    // Create COPIES of balances to avoid mutation
    const creditors = significantBalances
      .filter(b => b.net_balance > 0)
      .map(b => ({ ...b, net_balance: b.net_balance })); // Deep copy
    
    const debtors = significantBalances
      .filter(b => b.net_balance < 0)
      .map(b => ({ ...b, net_balance: b.net_balance })); // Deep copy
    
    // Simple greedy algorithm to minimize transactions
    creditors.forEach(creditor => {
      debtors.forEach(debtor => {
        if (Math.abs(debtor.net_balance) > 0.01 && Math.abs(creditor.net_balance) > 0.01) {
          const amount = Math.min(creditor.net_balance, Math.abs(debtor.net_balance));
          
          settlements.push({
            from: debtor.user_id,
            fromName: getMemberName(debtor.user_id),
            to: creditor.user_id,
            toName: getMemberName(creditor.user_id),
            amount: amount
          });
          
          // Now we can safely mutate the COPIES
          creditor.net_balance -= amount;
          debtor.net_balance += amount;
        }
      });
    });
    
    return settlements;
  };

  const settlements = calculateSettlements();

  // Calculate summary data for cards
  const totalSettlements = settlementHistory.reduce((sum, s) => sum + (s.amount || 0), 0);
  const settlementCount = settlementHistory.length;
  
  // Calculate remaining balance (sum of absolute values of all balances)
  const remainingBalance = significantBalances.reduce((sum, b) => {
    return sum + Math.abs(b.net_balance || 0);
  }, 0) / 2; // Divide by 2 because each debt is counted twice (once positive, once negative)

  if (!balances || significantBalances.length === 0) {
    return (
      <div className="card group-balances">
        <h2>Group Balances</h2>
        
        <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
          <p style={{ fontSize: '3rem', margin: '0 0 1rem 0' }}>🎉</p>
          <p style={{ color: '#27ae60', fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Everyone is settled up!
          </p>
          <p style={{ color: '#666', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
            All balances are zero. Great job keeping things square!
          </p>
          
          <p style={{ color: '#999', fontSize: '0.85rem', fontStyle: 'italic' }}>
            Use "Settle Up" buttons when you have new expenses to settle.
          </p>
        </div>

        <SettlementHistoryModal
          isOpen={isHistoryModalOpen}
          onClose={() => setIsHistoryModalOpen(false)}
          settlements={settlementHistory}
          currency={currency}
        />

        <SettlementModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setSelectedSettlement(null);
          }}
          settlement={selectedSettlement}
          groupId={group?.group_id}
          members={members}
          onSuccess={handleSettlementSuccess}
        />
      </div>
    );
  }

  return (
    <div className="card group-balances">
      <h2>Group Balances</h2>
      
      {/* Individual Balances */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.75rem' }}>Member Balances</h3>
        <div className="balances-list">
          {significantBalances.map((balance, idx) => {
            const netBalance = balance.net_balance || 0;
            const userName = getMemberName(balance.user_id);
            const isOwed = netBalance >= 0;
            const absoluteBalance = Math.abs(netBalance);
            
           return (
              <div key={idx} className="balance-item" style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                padding: '0.75rem',
                borderBottom: '1px solid #f0f0f0'
              }}>
                <div>
                  <span style={{ fontWeight: '500' }}>{userName}</span>
                </div>
                <span style={{ 
                  color: netBalance >= 0 ? '#27ae60' : '#e74c3c',
                  fontWeight: '600'
                }}>
                  {netBalance >= 0 ? '+' : '-'}{formatCurrency(netBalance, currency)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Settlement Suggestions */}
      {settlements.length > 0 && (
        <div>
          <h3 style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.75rem' }}>
            Suggested Settlements
          </h3>
          <div style={{ 
            background: '#f8f9fa', 
            borderRadius: '8px', 
            padding: '1rem'
          }}>
            {settlements.map((settlement, idx) => (
              <div key={idx} style={{ 
                padding: '0.75rem',
                background: 'white',
                borderRadius: '6px',
                marginBottom: idx < settlements.length - 1 ? '0.5rem' : '0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                gap: '1rem'
              }}>
                <div style={{ flex: 1 }}>
                  <span style={{ fontWeight: '500', color: '#e74c3c' }}>
                    {settlement.fromName}
                  </span>
                  <span style={{ margin: '0 0.5rem', color: '#666' }}>should pay</span>
                  <span style={{ fontWeight: '500', color: '#27ae60' }}>
                    {settlement.toName}
                  </span>
                </div>
                <div style={{ 
                  fontWeight: '600',
                  color: '#667eea',
                  fontSize: '1.1rem',
                  marginRight: '0.5rem'
                }}>
                  {formatCurrency(settlement.amount, currency)}
                </div>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleSettleUp(settlement);
                  }}
                  style={{
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    border: 'none',
                    padding: '0.5rem 1rem',
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.transform = 'translateY(-2px)';
                    e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = 'translateY(0)';
                    e.target.style.boxShadow = 'none';
                  }}
                >
                  Settle Up
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <p style={{ 
        marginTop: '1rem', 
        fontSize: '0.85rem', 
        color: '#666',
        textAlign: 'center'
      }}>
        💡 Green (+) indicates money owed to them, Red (-) indicates money they owe
      </p>

      {/* Settlement History Modal */}
      <SettlementHistoryModal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        settlements={settlementHistory}
        currency={currency}
      />

      {/* Settlement Modal */}
      <SettlementModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedSettlement(null);
        }}
        settlement={selectedSettlement}
        groupId={group?.group_id}
        members={members}
        onSuccess={handleSettlementSuccess}
      />
    </div>
  );
};

export default GroupBalances;
