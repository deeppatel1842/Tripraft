/**
 * PersonalTabbedView Component
 * Displays Transaction History and Analytics as tabs for personal expenses
 */

import React, { useState } from 'react';
import { Receipt, BarChart3 } from 'lucide-react';
import TransactionList from './TransactionList';
import ExpenseAnalytics from './ExpenseAnalytics';

const PersonalTabbedView = ({
  transactions,
  filter,
  onFilterChange,
  onEdit,
  onDelete,
  currentUserId,
  currency = 'USD',
  onExportPDF
}) => {
  const [activeTab, setActiveTab] = useState('transactions');

  const tabs = [
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
      <div style={{ padding: activeTab === 'analytics' ? '1.5rem' : '0' }}>
        {/* Transaction History Tab */}
        {activeTab === 'transactions' && (
          <div style={{ animation: 'fadeIn 0.3s ease' }}>
            <div style={{ padding: '1.5rem 1.5rem 0 1.5rem' }}>
              <div style={{ 
                display: 'flex', 
                gap: '1rem',
                marginBottom: '1rem',
                flexWrap: 'wrap'
              }}>
                <select 
                  value={filter.type}
                  onChange={(e) => onFilterChange('type', e.target.value)}
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
                  <option value="all">All Types</option>
                  <option value="income">Income</option>
                  <option value="expense">Expense</option>
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
              mode="personal"
              activeGroup={null}
              members={[]}
              allMembersMap={{}}
              currentUserId={currentUserId}
              onEdit={onEdit}
              onDelete={onDelete}
              onFilterChange={onFilterChange}
              currency={currency}
              isInTab={true}
            />
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div style={{ animation: 'fadeIn 0.3s ease' }}>
            <ExpenseAnalytics
              expenses={transactions || []}
              members={[]}
              currency={currency}
              mode="personal"
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

export default PersonalTabbedView;
