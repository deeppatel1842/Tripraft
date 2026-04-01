/**
 * ExpenseManager Component - Simplified Version
 * 
 * Clean, simple expense management using direct SQL API calls.
 * Features:
 * - Smart polling (auto-refresh every 30s when tab is focused)
 * - Refetch on window focus
 * - Direct state management (no complex caching layers)
 * - Single source of truth
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ExpenseSummary from './ExpenseSummary';
import TransactionList from './TransactionList';
import TransactionModal from './TransactionModal';
import GroupManager from './GroupManager';
import GroupBalances from './GroupBalances';
import GroupSummaryCards from './GroupSummaryCards';
import SettlementHistoryModal from './SettlementHistoryModal';
import TabbedGroupView from './TabbedGroupView';
import PersonalTabbedView from './PersonalTabbedView';
import ModeToggle from './ModeToggle';
import PendingInvitations from './PendingInvitations';
import ExpenseAnalytics from './ExpenseAnalytics';
import MemberSpending from './MemberSpending';
import Toast from '../../common/jsx/Toast';
import ErrorBoundary from '../../common/jsx/ErrorBoundary';
import { PlusCircle, RefreshCw } from 'lucide-react';
import expenseApi from '../../../services/expenseApi';
import { generateExpensePDF } from '../../../services/pdfExportService';
import {
  useAuth,
  useGroups,
  useGroupDetail,
  useInvitations,
  usePersonalExpenses
} from '../../../hooks/useExpenseQuery';
import '../css/ExpenseManager.css';

/** Unwrap backend response envelope { success, data, meta } -> inner data */
const unwrapEnvelope = (r) => (r && typeof r === 'object' && 'success' in r && 'data' in r) ? r.data : r;

const ExpenseManager = () => {
  const navigate = useNavigate();
  const { userId: routeUserId, mode: routeMode } = useParams();
  
  // Auth state
  const { isAuthenticated, currentUser, loading: authLoading } = useAuth();
  
  // Data hooks - simple, direct SQL API calls with smart polling + INSTANT UPDATES
  const {
    groups,
    loading: groupsLoading,
    refetch: refetchGroups,
    updateGroupsFromResponse,  // INSTANT UPDATE helper
    setGroups
  } = useGroups();
  
  const [state, setState] = useState({
    mode: 'personal',
    activeGroupId: null,
    editingTransactionId: null,
    filter: { type: 'all', sortBy: 'date-desc' }
  });
  
  // Group detail (only when group is selected) - with INSTANT UPDATE helpers
  const {
    group: activeGroupData,
    members: activeGroupMembers,
    expenses: activeGroupExpenses,
    balances: activeGroupBalances,
    settlements: activeGroupSettlements,
    invitations: groupInvitations,
    loading: groupDetailLoading,
    refetch: refetchGroupDetail,
    updateFromResponse: updateGroupDetailFromResponse,  // INSTANT UPDATE helper
    updateExpensesAndBalances,  // INSTANT UPDATE helper
    updateSettlementsAndBalances,  // INSTANT UPDATE helper for settlements
    updateMembers  // INSTANT UPDATE helper
  } = useGroupDetail(state.activeGroupId);
  
  // Invitations for current user - with INSTANT UPDATE helpers
  const {
    invitations,
    loading: invitationsLoading,
    refetch: refetchInvitations,
    updateInvitationsFromResponse,  // INSTANT UPDATE helper
    removeInvitation  // INSTANT UPDATE helper
  } = useInvitations();
  
  // Personal expenses
  const {
    expenses: personalExpenses,
    loading: personalLoading,
    refetch: refetchPersonalExpenses,
    markAsDeleted: markPersonalAsDeleted,
    rollbackDelete: rollbackPersonalDelete
  } = usePersonalExpenses();

  // UI State
  const [showTransactionModal, setShowTransactionModal] = useState(false);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [confirmMessage, setConfirmMessage] = useState('');
  const [confirmCallback, setConfirmCallback] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [mutationLoading, setMutationLoading] = useState(false);

  // Initialize mode from URL path on mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (routeMode === 'group') {
      setState(prev => ({ ...prev, mode: 'group' }));
    } else if (routeMode === 'personal') {
      setState(prev => ({ ...prev, mode: 'personal' }));
    }
  }, []); // run once on mount

  // Keep URL path in sync: /expenses/<userId>/<mode>
  useEffect(() => {
    if (authLoading || !currentUser) return;
    const userId = currentUser?.uid || currentUser?.user_id || '';
    if (!userId) return;
    navigate(`/expenses/${userId}/${state.mode}`, { replace: true });
  }, [state.mode, currentUser, authLoading, navigate]);

  // Auto-select first group if in group mode and no group selected
  useEffect(() => {
    if (state.mode === 'group' && !state.activeGroupId && groups && groups.length > 0) {
      setState(prev => ({ ...prev, activeGroupId: groups[0].id || groups[0].group_id }));
    }
  }, [state.mode, state.activeGroupId, groups]);

  // Helper functions
  const showAlert = (message) => {
    setAlertMessage(message);
    setShowAlertModal(true);
  };
  
  const showToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  };
  
  const hideToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  const showConfirm = (message, callback) => {
    setConfirmMessage(message);
    setConfirmCallback(() => callback);
    setShowConfirmModal(true);
  };

  // Get current transactions based on mode
  const getCurrentTransactions = () => {
    if (state.mode === 'personal') {
      return personalExpenses || [];
    }
    if (!state.activeGroupId) return [];
    return activeGroupExpenses || [];
  };
  
  // Get current balances
  const getCurrentBalances = () => {
    if (state.mode === 'personal') return null;
    if (!state.activeGroupId) return null;
    
    let balances = activeGroupBalances || [];
    
    // Handle various balance formats
    if (!Array.isArray(balances) && typeof balances === 'object') {
      if (Object.keys(balances).length === 0) return [];
      
      if (balances.member_balances && Array.isArray(balances.member_balances)) {
        return balances.member_balances;
      }
      
      if (balances.member_balances && typeof balances.member_balances === 'object') {
        return Object.entries(balances.member_balances).map(([userId, balance]) => ({
          user_id: userId,
          balance: parseFloat(balance) || 0,
          net_balance: parseFloat(balance) || 0
        }));
      }
      
      const firstValue = Object.values(balances)[0];
      if (typeof firstValue === 'number' || typeof firstValue === 'string') {
        return Object.entries(balances).map(([userId, balance]) => ({
          user_id: userId,
          balance: parseFloat(balance) || 0,
          net_balance: parseFloat(balance) || 0
        }));
      }
      
      return [];
    }
    
    return Array.isArray(balances) ? balances : [];
  };

  // Build members map
  const getAllMembersMap = () => {
    const map = {};
    (activeGroupMembers || []).forEach(m => {
      const userId = m.user_id || m.id;
      if (userId) {
        map[userId] = {
          user_id: userId,
          display_name: m.display_name || m.username || 'Unknown',
          email: m.email
        };
      }
    });
    return map;
  };

  // Event Handlers
  const handleModeToggle = () => {
    setState(prev => ({ ...prev, mode: prev.mode === 'personal' ? 'group' : 'personal' }));
  };

  const handleGroupChange = (groupId) => {
    setState(prev => ({ ...prev, activeGroupId: groupId }));
  };

  const handleOpenModal = () => {
    if (state.mode === 'group') {
      if (!state.activeGroupId) {
        showAlert('Please select a group first.');
        return;
      }
      if (!activeGroupMembers || activeGroupMembers.length === 0) {
        showAlert('Please add members to the group before adding an expense.');
        return;
      }
      if (activeGroupMembers.length < 2) {
        showAlert('At least 2 members required to create group expense. Invite more members first.');
        return;
      }
    }
    setState(prev => ({ ...prev, editingTransactionId: null }));
    setShowTransactionModal(true);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      if (state.mode === 'personal') {
        await refetchPersonalExpenses();
      } else if (state.activeGroupId) {
        await refetchGroupDetail();
      }
      await refetchGroups();
      await refetchInvitations();
    } catch (error) {
      showAlert(`Failed to refresh: ${error.message}`);
    } finally {
      setRefreshing(false);
    }
  };

  // Group CRUD - with INSTANT UPDATES
  const handleCreateGroup = async (groupData) => {
    try {
      setMutationLoading(true);
      
      const result = unwrapEnvelope(await expenseApi.createGroup(groupData));
      
      showToast('Group created successfully!', 'success');
      
      // INSTANT UPDATE: Use returned groups directly instead of refetching
      if (result?.groups && Array.isArray(result.groups)) {
        updateGroupsFromResponse(result.groups);
      } else {
        // Fallback: Refetch groups if not returned
        await refetchGroups();
      }
      
      // Switch to the newly created group
      const newGroupId = result?.group?.group_id || result?.group?.id || result?.group_id;
      if (newGroupId) {
        setState(prev => ({ ...prev, activeGroupId: newGroupId, mode: 'group' }));
        setSearchParams({ view: 'group', groupId: newGroupId });
      }
      
      return result;
    } catch (error) {
      showToast(`Failed to create group: ${error.message}`, 'error');
      throw error;
    } finally {
      setMutationLoading(false);
    }
  };

  const handleDeleteGroup = async (groupId) => {
    try {
      setMutationLoading(true);
      
      const result = await expenseApi.deleteGroup(groupId);
      
      // Check for explicit failure in response
      if (result?.success === false || result?.error) {
        throw new Error(result.error || result.message || 'Cannot delete group');
      }
      
      // Only show success and switch mode if deletion actually succeeded
      showToast('Group deleted successfully!', 'success');
      
      // Clear active group AFTER successful deletion
      if (state.activeGroupId === groupId) {
        setState(prev => ({ ...prev, activeGroupId: null, mode: 'personal' }));
      }
      
      // Refetch groups
      await refetchGroups();
    } catch (error) {
      // Only show error toast, don't redirect
      showToast(error.message || 'Cannot delete group', 'error');
      // Re-throw so GroupManager knows it failed
      throw error;
    } finally {
      setMutationLoading(false);
    }
  };

  // Transaction CRUD
  // Transaction CRUD - with INSTANT UPDATES
  const handleSaveTransaction = async (transactionData) => {
    try {
      setMutationLoading(true);
      
      if (state.mode === 'personal') {
        let result;
        if (state.editingTransactionId) {
          result = await expenseApi.updateExpense(state.editingTransactionId, transactionData);
          showToast('Transaction updated!', 'success');
        } else {
          result = await expenseApi.createExpense({
            group_id: null,
            description: transactionData.description,
            amount: transactionData.amount,
            currency: transactionData.currency || 'USD',
            category: transactionData.category,
            expense_date: transactionData.expense_date,
            paid_by: currentUser.uid || currentUser.user_id,
            split_type: 'equal',
            splits: [{ user_id: currentUser.uid || currentUser.user_id, amount: transactionData.amount }]
          });
          showToast('Transaction created!', 'success');
        }
        await refetchPersonalExpenses();
      } else {
        // Group expense
        const splitAmount = transactionData.amount / transactionData.splitWith.length;
        const splits = transactionData.splitWith.map(userId => ({
          user_id: userId,
          amount: splitAmount
        }));

        const expensePayload = {
          group_id: state.activeGroupId,
          description: transactionData.description,
          amount: transactionData.amount,
          currency: transactionData.currency || activeGroupData?.currency || 'USD',
          category: transactionData.category,
          expense_date: transactionData.expense_date,
          paid_by: transactionData.paidBy,
          split_type: 'equal',
          splits: splits
        };

        let result;
        if (state.editingTransactionId) {
          result = unwrapEnvelope(await expenseApi.updateExpense(state.editingTransactionId, expensePayload));
          showToast('Transaction updated!', 'success');
        } else {
          result = unwrapEnvelope(await expenseApi.createExpense(expensePayload));
          showToast('Transaction created!', 'success');
        }
        
        // INSTANT UPDATE: Add new expense to list immediately
        if (result?.expense) {
          const newExpense = result.expense;
          const updatedExpenses = state.editingTransactionId
            ? activeGroupExpenses.map(e => (e.id === state.editingTransactionId || e.expense_id === state.editingTransactionId) ? newExpense : e)
            : [newExpense, ...(activeGroupExpenses || [])];
          
          // Use new balances if returned, otherwise refetch to get accurate balances
          if (result.group_balances && result.group_balances.length > 0) {
            updateExpensesAndBalances(updatedExpenses, result.group_balances);
          } else {
            // Balances not returned - refetch to ensure accurate calculation
            await refetchGroupDetail();
          }
        } else {
          // Fallback: Refetch group data
          await refetchGroupDetail();
        }
      }
      
      setShowTransactionModal(false);
      setState(prev => ({ ...prev, editingTransactionId: null }));
    } catch (error) {
      showToast(`Failed to save transaction: ${error.message}`, 'error');
    } finally {
      setMutationLoading(false);
    }
  };

  const handleEditTransaction = (transaction) => {
    const expenseId = transaction.id || transaction.expense_id;
    if (expenseId && expenseId.toString().startsWith('temp-')) {
      showToast('Please wait, expense is still being created...', 'info');
      return;
    }
    setState(prev => ({ ...prev, editingTransactionId: expenseId }));
    setShowTransactionModal(true);
  };

  const handleDeleteTransaction = async (id) => {
    try {
      if (id && id.toString().startsWith('temp-')) return;
      
      setMutationLoading(true);
      showToast('Deleting transaction...', 'info');
      
      if (state.mode === 'personal') {
        markPersonalAsDeleted(id);
      }
      
      const result = unwrapEnvelope(await expenseApi.deleteExpense(id));
      
      // INSTANT UPDATE: Use returned data if available
      if (state.mode === 'group' && (result?.expenses || result?.group_balances)) {
        updateExpensesAndBalances(result.expenses, result.group_balances);
      } else if (state.mode === 'personal') {
        await refetchPersonalExpenses();
      } else {
        await refetchGroupDetail();
      }
      
      showToast('Transaction deleted!', 'success');
    } catch (error) {
      if (state.mode === 'personal') {
        rollbackPersonalDelete(id);
      }
      showToast(`Failed to delete: ${error.message}`, 'error');
    } finally {
      setMutationLoading(false);
    }
  };

  // Settlement handler - with INSTANT UPDATES
  const handleSettlementSuccess = async (settlementData) => {
    try {
      setMutationLoading(true);
      showToast('Creating settlement...', 'info');
      
      const result = unwrapEnvelope(await expenseApi.createSettlement(settlementData));
      
      // INSTANT UPDATE: Use returned settlements and balances from API response
      if (result?.settlements || result?.balances) {
        updateSettlementsAndBalances(result.settlements, result.balances);
        showToast('Settlement recorded successfully', 'success');
      } else {
        // Fallback: Refetch group data
        await refetchGroupDetail();
        showToast('Settlement recorded successfully', 'success');
      }
    } catch (error) {
      showToast(error.message || 'Failed to record settlement', 'error');
    } finally {
      setMutationLoading(false);
    }
  };

  // Get editing transaction
  const editingTransaction = state.editingTransactionId
    ? getCurrentTransactions().find(t => t.id === state.editingTransactionId || t.expense_id === state.editingTransactionId)
    : null;

  // PDF Export handler
  const handleExportPDF = () => {
    try {
      showToast('Generating PDF report...', 'info');
      
      generateExpensePDF({
        mode: state.mode,
        groupName: state.mode === 'group' ? (activeGroupData?.name || 'Group') : 'Personal',
        expenses: getCurrentTransactions().filter(t => !t.is_deleted),
        settlements: activeGroupSettlements || [],
        members: activeGroupMembers || [],
        balances: getCurrentBalances() || [],
        currency: state.mode === 'group' ? (activeGroupData?.currency || 'USD') : 'USD',
        userName: currentUser?.display_name || currentUser?.email || 'User'
      });
      
      showToast('PDF downloaded successfully!', 'success');
    } catch (error) {
      showToast('Failed to generate PDF', 'error');
    }
  };

  // Loading state
  if (authLoading) {
    return (
      <div className="expense-manager">
        <div style={{ textAlign: 'center', padding: '4rem' }}>
          <RefreshCw className="spinning" size={48} />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  // Auth required
  if (!isAuthenticated) {
    return (
      <div className="expense-manager">
        <div style={{ textAlign: 'center', padding: '4rem' }}>
          <h2>Welcome Back!</h2>
          <p>Sign in to manage your expenses and keep your budget on track.</p>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary 
      onRetry={handleRefresh}
      onGoHome={() => navigate('/')}
    >
    <div className="expense-manager">
      <header className="expense-header">
        <div>
          <h1>Expense Dashboard</h1>
          <p>Manage your personal and group trip expenses.</p>
        </div>
        <div className="header-actions">
          <button 
            className="btn-refresh" 
            onClick={handleRefresh}
            disabled={refreshing || mutationLoading}
            title="Refresh data"
          >
            <RefreshCw size={20} className={refreshing ? 'spinning' : ''} />
          </button>
          <ModeToggle mode={state.mode} onToggle={handleModeToggle} />
          <button className="btn-add-transaction" onClick={handleOpenModal} disabled={mutationLoading}>
            <PlusCircle size={20} />
            <span>Add Transaction</span>
          </button>
        </div>
      </header>

      {/* Pending Invitations - with INSTANT UPDATES */}
      <PendingInvitations 
        invitationsFromParent={invitations}
        onRefreshInvitations={refetchInvitations}
        onGroupsUpdate={updateGroupsFromResponse}
        onInvitationAccepted={async (result) => {
          // INSTANT UPDATE: Use groups from response if available
          if (result?.groups && Array.isArray(result.groups)) {
            updateGroupsFromResponse(result.groups);
            
            // Select the newly joined group
            const newGroup = result.groups.find(g => g.id === result?.group?.id || g.group_id === result?.group?.group_id) || result.groups[0];
            const groupId = newGroup?.group_id || newGroup?.id;
            
            if (groupId) {
              setState(prev => ({ ...prev, mode: 'group', activeGroupId: groupId }));
              setSearchParams({ view: 'group', groupId: groupId });
              showToast('Welcome to the group!', 'success');
            } else {
              setState(prev => ({ ...prev, mode: 'group' }));
              showToast('Invitation accepted!', 'success');
            }
          } else {
            // Fallback: Refetch if no data returned
            await refetchGroups();
            await refetchInvitations();
            
            if (groups && groups.length > 0) {
              const newGroup = groups[0];
              const groupId = newGroup.group_id || newGroup.id;
              setState(prev => ({ ...prev, mode: 'group', activeGroupId: groupId }));
              setSearchParams({ view: 'group', groupId: groupId });
              showToast('Welcome to the group!', 'success');
            } else {
              setState(prev => ({ ...prev, mode: 'group' }));
              showToast('Invitation accepted!', 'success');
            }
          }
        }}
        currentUser={currentUser}
      />

      {/* Group Management Section */}
      {state.mode === 'group' && (
        <GroupManager
          groups={(groups || []).filter(g => g && (g.id || g.group_id))}
          activeGroupId={state.activeGroupId}
          activeGroup={state.activeGroupId ? activeGroupData : null}
          members={activeGroupMembers || []}
          loading={groupsLoading || groupDetailLoading}
          onGroupChange={handleGroupChange}
          onGroupCreate={handleCreateGroup}
          onGroupDelete={handleDeleteGroup}
          onMemberAdd={async () => await refetchGroupDetail()}
          onMemberRemove={async () => await refetchGroupDetail()}
          showAlert={showAlert}
          currentUser={currentUser}
          pendingInvitationsFromParent={groupInvitations}
          onRefreshInvitations={refetchGroupDetail}
          usingMegaBootstrap={false}
        />
      )}

      {/* Personal Expense Summary */}
      {state.mode === 'personal' && (
        <ExpenseSummary 
          transactions={getCurrentTransactions()}
          mode={state.mode}
          currency='USD'
        />
      )}

      {/* Group Summary Cards */}
      {state.mode === 'group' && state.activeGroupId && (() => {
        const transactions = getCurrentTransactions() || [];
        const activeExpenses = transactions.filter(t => !t.is_deleted);
        const totalAmount = activeExpenses.reduce((sum, t) => sum + (t.amount || 0), 0);
        const expenseCount = activeExpenses.length;
        
        const balances = getCurrentBalances() || [];
        const totalSettled = (activeGroupSettlements || []).reduce((sum, s) => sum + (s.amount || 0), 0);
        
        let currentOwed = 0;
        if (Array.isArray(balances)) {
          currentOwed = balances
            .filter(b => Math.abs(b.net_balance || 0) > 0.01)
            .reduce((sum, b) => sum + Math.abs(b.net_balance || 0), 0) / 2;
        }
        
        // Calculate "My Share" - user's balance from the expense group
        const members = activeGroupMembers || [];
        const memberCount = members.length || 1;
        const userId = currentUser?.id || currentUser?.uid || currentUser?.user_id;
        
        // Get user's balance from balances array (this is the authoritative source)
        let myShare = 0;
        if (Array.isArray(balances)) {
          const userBalance = balances.find(b => {
            return b.user_id === userId || 
                   String(b.user_id) === String(userId);
          });
          if (userBalance) {
            myShare = Math.abs(userBalance.net_balance || userBalance.balance || 0);
          }
        }
        
        return (
          <>
            <GroupSummaryCards
              totalExpenses={expenseCount}
              totalAmount={totalAmount}
              remainingBalance={currentOwed}
              totalSettlements={totalSettled}
              settlementCount={(activeGroupSettlements || []).length}
              myShare={myShare}
              memberCount={memberCount}
              currency={activeGroupData?.currency || 'USD'}
              onSettlementCardClick={() => setIsHistoryModalOpen(true)}
            />
            
            <SettlementHistoryModal
              isOpen={isHistoryModalOpen}
              onClose={() => setIsHistoryModalOpen(false)}
              settlements={activeGroupSettlements || []}
              currency={activeGroupData?.currency || 'USD'}
            />
          </>
        );
      })()}

      {/* Group View with Tabs (Balances, Settle Up, Spending, Transactions, Analytics) */}
      {state.mode === 'group' && state.activeGroupId && activeGroupData && (
        <TabbedGroupView
          key={`tabbed-${state.activeGroupId}-${(getCurrentBalances() || []).length}`}
          group={activeGroupData}
          balances={getCurrentBalances() || []}
          members={activeGroupMembers || []}
          allMembersMap={getAllMembersMap()}
          onBalanceUpdate={refetchGroupDetail}
          settlementHistory={activeGroupSettlements || []}
          onSettlementSuccess={handleSettlementSuccess}
          transactions={getCurrentTransactions()}
          filter={state.filter}
          onFilterChange={(filterType, value) => setState(prev => ({
            ...prev,
            filter: { ...prev.filter, [filterType]: value }
          }))}
          activeGroupMembers={activeGroupMembers || []}
          currentUserId={currentUser?.uid || currentUser?.user_id}
          onEdit={handleEditTransaction}
          onDelete={(id) => showConfirm('Are you sure you want to delete this transaction?', () => handleDeleteTransaction(id))}
          onExportPDF={handleExportPDF}
        />
      )}

      {/* Personal Mode - Tabbed View (Transaction History + Analytics) */}
      {state.mode === 'personal' && (
        <PersonalTabbedView
          key={`personal-${(getCurrentTransactions() || []).length}`}
          transactions={getCurrentTransactions()}
          filter={state.filter}
          onFilterChange={(filterType, value) => setState(prev => ({
            ...prev,
            filter: { ...prev.filter, [filterType]: value }
          }))}
          onEdit={handleEditTransaction}
          onDelete={(id) => showConfirm('Are you sure you want to delete this transaction?', () => handleDeleteTransaction(id))}
          currentUserId={currentUser?.uid || currentUser?.user_id}
          currency="USD"
          onExportPDF={handleExportPDF}
        />
      )}

      {/* Transaction Modal */}
      {showTransactionModal && (
        <TransactionModal
          mode={state.mode}
          activeGroup={activeGroupData}
          members={activeGroupMembers || []}
          editingTransaction={editingTransaction}
          currency={state.mode === 'group' ? activeGroupData?.currency : 'USD'}
          currentUser={currentUser}
          onSave={handleSaveTransaction}
          onClose={() => setShowTransactionModal(false)}
          onAlert={showAlert}
        />
      )}

      {/* Alert Modal */}
      {showAlertModal && (
        <div className="modal-backdrop" onClick={() => setShowAlertModal(false)}>
          <div className="modal modal-small" onClick={(e) => e.stopPropagation()}>
            <h2>Heads up!</h2>
            <p>{alertMessage}</p>
            <div className="modal-actions">
              <button className="btn-save" onClick={() => setShowAlertModal(false)}>OK</button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Modal */}
      {showConfirmModal && (
        <div className="modal-backdrop" onClick={() => setShowConfirmModal(false)}>
          <div className="modal modal-small" onClick={(e) => e.stopPropagation()}>
            <h2>Are you sure?</h2>
            <p>{confirmMessage}</p>
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setShowConfirmModal(false)}>Cancel</button>
              <button 
                className="btn-delete"
                onClick={() => {
                  if (confirmCallback) confirmCallback();
                  setShowConfirmModal(false);
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Toast notifications */}
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => hideToast(toast.id)}
        />
      ))}
    </div>
    </ErrorBoundary>
  );
};

export default ExpenseManager;
