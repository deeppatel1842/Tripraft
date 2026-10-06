// Purpose: Renders the Group Balances interface within apps\web\src\features\expenses\jsx.
import React, { useState } from 'react';
import SettlementModal from './SettlementModal';
import SettlementHistoryModal from './SettlementHistoryModal';

const GroupBalances = ({ 
  group, 
  balances, 
  members, 
  allMembersMap = {},  // Phase 17 Bug Fix: Include removed members for display
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
    // The modal closes only after the save succeeds.
    
    // PHASE 2.7 FIX: Call parent callback FIRST
    // This allows parent to handle API call and actual balance reload
    // onBalanceUpdate is for optimistic updates only (not needed now)
    if (onSettlementSuccess) {
      await onSettlementSuccess(settlementData);
    }
  };
  const formatCurrency = (amount, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: currency 
    }).format(Math.abs(amount));
  };

  // Helper function to get member display name
  // Phase 17 Bug Fix: Also check allMembersMap for removed members
  // Accepts optional balance object which may already have display_name from backend
  const getMemberName = (userId, balanceObj = null) => {
    // First: Use display_name from balance object if available (backend already provides this)
    if (balanceObj?.display_name && balanceObj.display_name !== 'Unknown') {
      return balanceObj.display_name;
    }
    
    // Second: Check active members array
    if (members && userId) {
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
    }
    
    // Third: Check allMembersMap (includes removed members)
    if (allMembersMap && userId && allMembersMap[userId]) {
      return allMembersMap[userId].display_name || `Former Member (${String(userId).slice(0, 8)})`;
    }
    
    return 'Unknown User';
  };

  const currency = group?.currency || 'USD';

  // Filter out settled balances (very close to zero)
  const significantBalances = (balances || []).filter(balance => 
    balance && Math.abs(balance.net_balance || 0) > 0.01
  );

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
   // Divide by 2 because each debt is counted twice (once positive, once negative)

  // Show all members even when balanced
  const hasNoBalances = !balances || balances.length === 0;
  const allSettled = balances && balances.length > 0 && significantBalances.length === 0;
  
  if (hasNoBalances) {
    return (
      <>
        <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
          <p style={{ fontSize: '2rem', margin: '0 0 1rem 0', color: '#9CA3AF' }}>--</p>
          <p style={{ color: '#666', fontSize: '1rem', marginBottom: '0.5rem' }}>
            No balance information available
          </p>
          <p style={{ color: '#999', fontSize: '0.85rem' }}>
            Add expenses to see balances
          </p>
        </div>

        <SettlementHistoryModal
          isOpen={isHistoryModalOpen}
          onClose={() => setIsHistoryModalOpen(false)}
          settlements={settlementHistory}
          currency={currency}
        />

        <SettlementModal balances={balances} currency={currency}
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
      </>
    );
  }

  return (
    <>
      {/* Individual Balances */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.75rem' }}>
          Member Balances ({balances.length})
        </h3>
        <div className="balances-list">
          {balances.map((balance, idx) => {
            const netBalance = balance.net_balance || 0;
            const userName = getMemberName(balance.user_id, balance);
            const isOwed = netBalance >= 0;
            const isSettled = Math.abs(netBalance) < 0.01;
            
           return (
              <div key={balance.user_id} className="balance-item" style={{
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                padding: '0.75rem',
                borderBottom: '1px solid #f0f0f0',
                opacity: isSettled ? 0.6 : 1
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontWeight: '500' }}>{userName}</span>
                  {isSettled && (
                    <span style={{ 
                      fontSize: '0.75rem', 
                      color: '#27ae60',
                      background: '#e8f5e9',
                      padding: '2px 6px',
                      borderRadius: '4px'
                    }}>
                       Settled
                    </span>
                  )}
                </div>
                <span style={{ 
                  color: isSettled ? '#666' : (netBalance >= 0 ? '#27ae60' : '#e74c3c'),
                  fontWeight: isSettled ? '400' : '600'
                }}>
                  {isSettled ? formatCurrency(0, currency) : (
                    `${netBalance >= 0 ? '+' : '-'}${formatCurrency(netBalance, currency)}`
                  )}
                </span>
              </div>
            );
          })}
        </div>
        
        {allSettled && (
          <div style={{ 
            textAlign: 'center', 
            padding: '1rem', 
            background: '#e8f5e9',
            borderRadius: '6px',
            marginTop: '0.75rem'
          }}>
            <p style={{ color: '#27ae60', fontSize: '0.9rem', fontWeight: '500', margin: 0 }}>
               All members are settled up!
            </p>
          </div>
        )}
      </div>

      {/* Note: Suggested Settlements moved to Settle Up tab */}
      
      <p style={{ 
        marginTop: '1rem', 
        fontSize: '0.85rem', 
        color: '#666',
        textAlign: 'center'
      }}>
         Green (+) indicates money owed to them, Red (-) indicates money they owe
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
        balances={balances || []}
        currency={group?.currency || 'USD'}
        onSuccess={handleSettlementSuccess}
      />
    </>
  );
};

export default GroupBalances;
