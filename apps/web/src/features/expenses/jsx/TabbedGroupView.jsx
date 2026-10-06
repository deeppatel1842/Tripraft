// Purpose: Renders the Tabbed Group View interface within apps\web\src\features\expenses\jsx.
/**
 * TabbedGroupView Component
 * Displays Group Balances, Settle Up, Member Spending, Transaction History, and Analytics as tabs
 */

import React, { useState } from 'react';
import { Scale, TrendingUp, Receipt, Handshake, BarChart3 } from 'lucide-react';
import GroupBalances from './GroupBalances';
import MemberSpending from './MemberSpending';
import TransactionList from './TransactionList';
import ExpenseAnalytics from './ExpenseAnalytics';
import SettlementModal from './SettlementModal';
import SettlementHistoryModal from './SettlementHistoryModal';

// Settle Up Tab Component - Shows suggested settlements with action buttons
const SettleUpTab = ({ 
  group, 
  balances, 
  members,
  allMembersMap,
  settlementHistory,
  onSettlementSuccess, 
  currency = 'USD' 
}) => {
  const [selectedSettlement, setSelectedSettlement] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: currency 
    }).format(Math.abs(amount));
  };

  // Helper to get member name
  const getMemberName = (userId, balanceObj = null) => {
    if (balanceObj?.display_name && balanceObj.display_name !== 'Unknown') {
      return balanceObj.display_name;
    }
    if (members && userId) {
      const member = members.find(m => (m.user_id || m.id) === userId);
      if (member) {
        return member.user?.display_name || member.display_name || member.username || member.email || 'Unknown';
      }
    }
    if (allMembersMap && userId && allMembersMap[userId]) {
      return allMembersMap[userId].display_name || 'Former Member';
    }
    return 'Unknown User';
  };

  // Filter significant balances
  const significantBalances = (balances || []).filter(balance => 
    balance && Math.abs(balance.net_balance || 0) > 0.01
  );

  // Calculate suggested settlements
  const calculateSettlements = () => {
    const settlements = [];
    const creditors = significantBalances
      .filter(b => b.net_balance > 0)
      .map(b => ({ ...b, net_balance: b.net_balance }));
    const debtors = significantBalances
      .filter(b => b.net_balance < 0)
      .map(b => ({ ...b, net_balance: b.net_balance }));
    
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
          creditor.net_balance -= amount;
          debtor.net_balance += amount;
        }
      });
    });
    return settlements;
  };

  const settlements = calculateSettlements();
  const totalSettled = settlementHistory.reduce((sum, s) => sum + (s.amount || 0), 0);
  const allSettled = significantBalances.length === 0;

  const handleSettleUp = (settlement) => {
    setSelectedSettlement(settlement);
    setIsModalOpen(true);
  };

  const handleSettlementSuccess = async (settlementData) => {
    // The modal closes only after the save succeeds.
    if (onSettlementSuccess) {
      await onSettlementSuccess(settlementData);
    }
  };

  return (
    <div>
      {/* Settlement Summary Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem'
      }}>
        <div style={{
          background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
          padding: '1.25rem',
          borderRadius: '12px',
          color: 'white'
        }}>
          <div style={{ fontSize: '0.875rem', opacity: 0.9, marginBottom: '0.25rem' }}>Total Settled</div>
          <div style={{ fontSize: '1.75rem', fontWeight: '700' }}>{formatCurrency(totalSettled)}</div>
          <div style={{ fontSize: '0.8rem', opacity: 0.85, marginTop: '0.5rem' }}>
            {settlementHistory.length} payment{settlementHistory.length !== 1 ? 's' : ''} recorded
          </div>
        </div>
        
        <div style={{
          background: allSettled ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' : 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
          padding: '1.25rem',
          borderRadius: '12px',
          color: 'white'
        }}>
          <div style={{ fontSize: '0.875rem', opacity: 0.9, marginBottom: '0.25rem' }}>
            {allSettled ? 'Status' : 'Pending Settlements'}
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: '700' }}>
            {allSettled ? 'All Settled!' : settlements.length}
          </div>
          <div style={{ fontSize: '0.8rem', opacity: 0.85, marginTop: '0.5rem' }}>
            {allSettled ? 'No pending payments' : 'Suggested transactions'}
          </div>
        </div>
      </div>

      {/* View Settlement History Button */}
      <div style={{ marginBottom: '1.5rem', textAlign: 'right' }}>
        <button
          onClick={() => setIsHistoryModalOpen(true)}
          style={{
            background: '#f3f4f6',
            color: '#374151',
            border: '1px solid #e5e7eb',
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            fontSize: '0.875rem',
            fontWeight: '500',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          View Settlement History
        </button>
      </div>

      {/* Suggested Settlements */}
      {allSettled ? (
        <div style={{ 
          textAlign: 'center', 
          padding: '3rem 1rem', 
          background: '#f0fdf4',
          borderRadius: '12px',
          border: '1px solid #bbf7d0'
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>&#127881;</div>
          <h3 style={{ color: '#166534', margin: '0 0 0.5rem 0' }}>All Settled Up!</h3>
          <p style={{ color: '#15803d', margin: 0, fontSize: '0.9rem' }}>
            Everyone in the group is square. No payments needed.
          </p>
        </div>
      ) : (
        <div>
          <h3 style={{ fontSize: '1rem', color: '#374151', marginBottom: '1rem' }}>
            Suggested Settlements ({settlements.length})
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {settlements.map((settlement, idx) => (
              <div key={settlement.from + '-' + settlement.to} style={{
                padding: '1rem 1.25rem',
                background: 'white',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                border: '1px solid #e5e7eb',
                gap: '1rem'
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ 
                      fontWeight: '600', 
                      color: '#dc2626',
                      background: '#fef2f2',
                      padding: '0.25rem 0.75rem',
                      borderRadius: '20px',
                      fontSize: '0.875rem'
                    }}>
                      {settlement.fromName}
                    </span>
                    <span style={{ color: '#6b7280', fontSize: '0.875rem' }}>pays</span>
                    <span style={{ 
                      fontWeight: '600', 
                      color: '#16a34a',
                      background: '#f0fdf4',
                      padding: '0.25rem 0.75rem',
                      borderRadius: '20px',
                      fontSize: '0.875rem'
                    }}>
                      {settlement.toName}
                    </span>
                  </div>
                </div>
                <div style={{ 
                  fontWeight: '700',
                  color: '#111827',
                  fontSize: '1.125rem',
                  marginRight: '0.5rem'
                }}>
                  {formatCurrency(settlement.amount)}
                </div>
                <button
                  onClick={() => handleSettleUp(settlement)}
                  style={{
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    color: 'white',
                    border: 'none',
                    padding: '0.625rem 1.25rem',
                    borderRadius: '8px',
                    fontSize: '0.875rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.transform = 'translateY(-2px)';
                    e.target.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.4)';
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
    </div>
  );
};

const TabbedGroupView = ({
  group,
  balances,
  members,
  allMembersMap,
  onBalanceUpdate,
  settlementHistory,
  onSettlementSuccess,
  transactions,
  filter,
  onFilterChange,
  activeGroupMembers,
  currentUserId,
  onEdit,
  onDelete,
  onExportPDF
}) => {
  const [activeTab, setActiveTab] = useState('balances');

  const tabs = [
    {
      id: 'balances',
      label: 'Group Balances',
      icon: Scale,
      color: '#667eea'
    },
    {
      id: 'settleup',
      label: 'Settle Up',
      icon: Handshake,
      color: '#10b981'
    },
    {
      id: 'spending',
      label: 'Member Spending',
      icon: TrendingUp,
      color: '#f59e0b'
    },
    {
      id: 'transactions',
      label: 'Transaction History',
      icon: Receipt,
      color: '#3b82f6'
    },
    {
      id: 'analytics',
      label: 'Analytics',
      icon: BarChart3,
      color: '#8b5cf6'
    }
  ];

  return (
    <div style={{
      background: 'white',
      borderRadius: '12px',
      border: '1px solid #e5e7eb',
      overflow: 'hidden',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      marginBottom: '1.5rem'
    }}>
      {/* Tab Headers */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid #e5e7eb',
        background: '#f9fafb'
      }}>
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1,
                padding: '1rem',
                border: 'none',
                background: isActive ? 'white' : 'transparent',
                color: isActive ? '#111827' : '#6b7280',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.75rem',
                fontSize: '0.95rem',
                fontWeight: isActive ? '600' : '500',
                transition: 'all 0.2s ease',
                borderBottom: isActive ? `3px solid ${tab.color}` : 'none',
                position: 'relative',
                top: isActive ? '1px' : '0'
              }}
            >
              <Icon size={18} style={{ color: tab.color }} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div style={{ padding: '1.5rem' }}>
        {/* Group Balances Tab */}
        {activeTab === 'balances' && (
          <div style={{ animation: 'fadeIn 0.3s ease' }}>
            <GroupBalances
              group={group}
              balances={balances}
              members={members}
              allMembersMap={allMembersMap}
              onBalanceUpdate={onBalanceUpdate}
              settlementHistory={settlementHistory}
              onSettlementSuccess={onSettlementSuccess}
              showSettleUp={false}
            />
          </div>
        )}

        {/* Settle Up Tab - Shows suggested settlements with action buttons */}
        {activeTab === 'settleup' && (
          <div style={{ animation: 'fadeIn 0.3s ease' }}>
            <SettleUpTab
              group={group}
              balances={balances}
              members={members}
              allMembersMap={allMembersMap}
              settlementHistory={settlementHistory}
              onSettlementSuccess={onSettlementSuccess}
              currency={group?.currency || 'USD'}
            />
          </div>
        )}

        {/* Member Spending Tab */}
        {activeTab === 'spending' && (
          <div style={{ animation: 'fadeIn 0.3s ease' }}>
            <MemberSpending
              expenses={transactions || []}
              members={activeGroupMembers || []}
              currency={group?.currency || 'USD'}
              currentUserId={currentUserId}
            />
          </div>
        )}

        {/* Transaction History Tab */}
        {activeTab === 'transactions' && (
          <div style={{ animation: 'fadeIn 0.3s ease', marginTop: '-1.5rem', marginLeft: '-1.5rem', marginRight: '-1.5rem', marginBottom: '-1.5rem' }}>
            <div style={{ padding: '1.5rem' }}>
              <div style={{ 
                display: 'flex', 
                gap: '1rem',
                marginBottom: '1rem',
                flexWrap: 'wrap'
              }}>
                <select 
                  value={filter.category || 'all'}
                  onChange={(e) => onFilterChange('category', e.target.value)}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: '8px',
                    border: '1px solid #e5e7eb',
                    background: 'white',
                    fontSize: '0.875rem',
                    color: '#374151',
                    cursor: 'pointer'
                  }}
                >
                  <option value="all">All Categories</option>
                  <option value="Food">Food</option>
                  <option value="Transport">Transport</option>
                  <option value="Shopping">Shopping</option>
                  <option value="Entertainment">Entertainment</option>
                  <option value="Utilities">Utilities</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Education">Education</option>
                  <option value="Accommodation">Accommodation</option>
                  <option value="Travel">Travel</option>
                  <option value="Salary">Salary</option>
                  <option value="Income">Income</option>
                  <option value="Other">Other</option>
                </select>
                <select 
                  value={filter.sortBy}
                  onChange={(e) => onFilterChange('sortBy', e.target.value)}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: '8px',
                    border: '1px solid #e5e7eb',
                    background: 'white',
                    fontSize: '0.875rem',
                    color: '#374151',
                    cursor: 'pointer'
                  }}
                >
                  <option value="date-desc">Date (Newest)</option>
                  <option value="date-asc">Date (Oldest)</option>
                  <option value="amount-desc">Amount (High-Low)</option>
                  <option value="amount-asc">Amount (Low-High)</option>
                </select>
              </div>
            </div>
            <TransactionList
              transactions={transactions}
              filter={filter}
              mode="group"
              activeGroup={group}
              members={activeGroupMembers || []}
              allMembersMap={allMembersMap}
              currentUserId={currentUserId}
              onEdit={onEdit}
              onDelete={onDelete}
              onFilterChange={onFilterChange}
              currency={group?.currency || 'USD'}
              isInTab={true}
            />
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div style={{ animation: 'fadeIn 0.3s ease' }}>
            <ExpenseAnalytics
              expenses={transactions || []}
              members={activeGroupMembers || []}
              currency={group?.currency || 'USD'}
              mode="group"
              onExportPDF={onExportPDF}
            />
          </div>
        )}
      </div>

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
};

export default TabbedGroupView;
