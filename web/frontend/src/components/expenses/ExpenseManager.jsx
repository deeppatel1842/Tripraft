import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import ExpenseSummary from './ExpenseSummary';
import TransactionList from './TransactionList';
import TransactionModal from './TransactionModal';
import GroupManager from './GroupManager';
import GroupBalances from './GroupBalances';
import GroupSummaryCards from './GroupSummaryCards';
import SettlementHistoryModal from './SettlementHistoryModal';
import ModeToggle from './ModeToggle';
import PendingInvitations from './PendingInvitations';
import Toast from '../common/Toast';
import { PlusCircle, RefreshCw } from 'lucide-react';
import { useExpenseApi, useUserExpenses } from '../../hooks/useExpense';
import { 
  useGroupsQuery, 
  useGroupQuery,
  useCreateGroupMutation,
  useDeleteGroupMutation,
  useCreateExpenseMutation,
  useUpdateExpenseMutation,
  useDeleteExpenseMutation,
  useCreateSettlementMutation,
  queryKeys
} from '../../hooks/useExpenseQuery';
import expenseApi from '../../services/expenseApi';
import { groupMembershipMonitor } from '../../utils/groupMembershipMonitor';
import '../css/ExpenseManager.css';

// Helper function to calculate optimistic balances after expense edit/create
const calculateOptimisticBalances = (currentBalances, members, oldExpense, newExpense) => {
  console.log('🧮 Starting optimistic balance calculation:', {
    currentBalances: currentBalances.map(b => ({ user_id: b.user_id, balance: b.balance })),
    oldExpense: oldExpense ? {
      amount: oldExpense.amount,
      paid_by: oldExpense.paid_by || oldExpense.paidBy,
      splits: oldExpense.splits || oldExpense.splitWith
    } : null,
    newExpense: {
      amount: newExpense.amount,
      paid_by: newExpense.paid_by,
      splits: newExpense.splits
    }
  });
  
  // Create a copy of current balances
  const newBalances = currentBalances.map(b => ({ ...b }));
  
  // Reverse the old expense impact (if editing existing expense)
  if (oldExpense) {
    const oldPaidBy = oldExpense.paid_by || oldExpense.paidBy;
    const oldSplits = oldExpense.splits || oldExpense.splitWith?.map(userId => ({
      user_id: userId,
      amount: oldExpense.amount / oldExpense.splitWith.length
    })) || [];
    
    // Reverse old balances
    newBalances.forEach(balance => {
      // Reverse old payer credit
      if (balance.user_id === oldPaidBy) {
        balance.balance -= oldExpense.amount;
        balance.net_balance = balance.balance; // ✅ Update net_balance
        console.log(`  ↩️  ${balance.user_id}: Reverse old payer credit -${oldExpense.amount}`);
      }
      
      // Reverse old split debits
      const oldSplit = oldSplits.find(s => s.user_id === balance.user_id);
      if (oldSplit) {
        balance.balance += oldSplit.amount;
        balance.net_balance = balance.balance; // ✅ Update net_balance
        console.log(`  ↩️  ${balance.user_id}: Reverse old split debit +${oldSplit.amount}`);
      }
    });
  }
  
  // Apply new expense impact
  const newPaidBy = newExpense.paid_by;
  const newSplits = newExpense.splits;
  
  console.log('📊 Applying new expense:', {
    newPaidBy,
    newAmount: newExpense.amount,
    newSplits: newSplits.map(s => ({ user_id: s.user_id, amount: s.amount }))
  });
  
  // Update balances with new expense
  newBalances.forEach(balance => {
    // Apply new payer credit
    if (balance.user_id === newPaidBy) {
      balance.balance += newExpense.amount;
      balance.net_balance = balance.balance; // ✅ CRITICAL: Update net_balance (UI reads this!)
      console.log(`  ✅ ${balance.user_id}: Apply new payer credit +${newExpense.amount} (→ ${balance.balance})`);
    }
    
    // Apply new split debits
    const newSplit = newSplits.find(s => s.user_id === balance.user_id);
    if (newSplit) {
      balance.balance -= newSplit.amount;
      balance.net_balance = balance.balance; // ✅ CRITICAL: Update net_balance (UI reads this!)
      console.log(`  ✅ ${balance.user_id}: Apply new split debit -${newSplit.amount} (→ ${balance.balance})`);
    }
  });
  
  console.log('⚡ Final optimistic balances:', newBalances.map(b => ({ user_id: b.user_id, balance: b.balance })));
  
  return newBalances;
};

const ExpenseManager = () => {
  // PHASE 2.9: React Query migration
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { isAuthenticated, currentUser, loading: authLoading } = useExpenseApi();
  
  // Replace useUserGroups with React Query
  // API returns { success: true, groups: [...] }, so extract groups array
  const { data: groupsData, isLoading: groupsLoading, refetch: reloadGroups } = useGroupsQuery();
  const groups = groupsData?.groups || [];
  const createGroupMutation = useCreateGroupMutation();
  
  // Expense mutations (Phase 2.9)
  const createExpenseMutation = useCreateExpenseMutation();
  const updateExpenseMutation = useUpdateExpenseMutation();
  const deleteExpenseMutation = useDeleteExpenseMutation();
  const createSettlementMutation = useCreateSettlementMutation();
  const deleteGroupMutation = useDeleteGroupMutation();
  
  const { expenses: personalExpenses, loading: personalLoading, reload: reloadPersonalExpenses } = useUserExpenses();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [state, setState] = useState({
    mode: 'personal',
    activeGroupId: null,
    editingTransactionId: null,
    filter: { type: 'all', sortBy: 'date-desc' }
  });

  const [showTransactionModal, setShowTransactionModal] = useState(false);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [confirmMessage, setConfirmMessage] = useState('');
  const [confirmCallback, setConfirmCallback] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  
  // PHASE 2: Removed groupBalancesRef - settlement loading now centralized
  
  // Optimistic state for instant updates (overrides API data)
  const [optimisticExpenses, setOptimisticExpenses] = useState([]);
  const [optimisticBalances, setOptimisticBalances] = useState(null);
  
  // Toast notifications
  const [toasts, setToasts] = useState([]);
  
  // Settlement history for summary cards
  const [settlementHistory, setSettlementHistory] = useState([]);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  // PHASE 2.9: Replace useGroup with React Query
  const { data: groupData, isLoading: groupLoading, isPlaceholderData, refetch: refetchGroup } = useGroupQuery(state.activeGroupId);
  
  // Extract data from React Query response
  // keepPreviousData ensures these never become undefined during refetch
  const activeGroupData = groupData?.group || null;
  const activeGroupMembers = groupData?.members || [];
  const activeGroupExpenses = groupData?.expenses || [];
  const activeGroupBalances = groupData?.balances || [];
  
  // Helper function to reload active group (with cache bypass option)
  const reloadActiveGroup = async (bypassCache = false) => {
    if (bypassCache) {
      // Invalidate cache to force fresh data from server
      queryClient.invalidateQueries({ queryKey: queryKeys.group(state.activeGroupId) });
    }
    await refetchGroup();
  };

  // Check URL params for group view (from invitation acceptance)
  useEffect(() => {
    const viewParam = searchParams.get('view');
    if (viewParam === 'group' && state.mode !== 'group') {
      console.log('Switching to group mode from URL parameter');
      setState(prev => ({ ...prev, mode: 'group' }));
      // Clear the URL parameter
      setSearchParams({});
    }
  }, [searchParams, state.mode, setSearchParams]);

  // Auto-select first group if in group mode and no group selected
  useEffect(() => {
    if (state.mode === 'group' && !state.activeGroupId && groups && groups.length > 0) {
      console.log('Auto-selecting first group:', groups[0].id);
      setState(prev => ({ ...prev, activeGroupId: groups[0].id }));
    }
  }, [state.mode, state.activeGroupId, groups]);

  // Clear optimistic state when switching groups or modes to load fresh data
  useEffect(() => {
    console.log('🧹 Clearing optimistic state (mode/group changed)');
    setOptimisticExpenses([]);
    setOptimisticBalances(null);
    
    // PHASE 2: Load settlements when group changes (centralized)
    if (state.mode === 'group' && state.activeGroupId) {
      loadSettlements(state.activeGroupId);
    }
  }, [state.mode, state.activeGroupId]);

  // 🐛 BUG FIX #3 & #4: Monitor group membership changes
  useEffect(() => {
    if (!isAuthenticated || !currentUser) return;

    // Start monitoring for removed groups/members
    groupMembershipMonitor.startMonitoring(
      // Fetch groups function
      () => expenseApi.getUserGroups(),
      // On group removed callback
      (groupId, groupInfo) => {
        console.warn(`🚨 Group ${groupInfo.name} was deleted or you were removed!`);
        
        // Show toast notification
        showToast(`Group "${groupInfo.name}" is no longer accessible`, 'warning');
        
        // If currently viewing this group, switch to personal mode
        if (state.activeGroupId === groupId) {
          setState(prev => ({ 
            ...prev, 
            mode: 'personal', 
            activeGroupId: null 
          }));
        }
        
        // Force refresh groups list
        reloadGroups();
      },
      // On member removed callback (same behavior)
      (groupId, groupInfo) => {
        console.warn(`🚨 You were removed from group ${groupInfo.name}!`);
        showToast(`You were removed from "${groupInfo.name}"`, 'warning');
        
        if (state.activeGroupId === groupId) {
          setState(prev => ({ 
            ...prev, 
            mode: 'personal', 
            activeGroupId: null 
          }));
        }
        
        reloadGroups();
      },
      15000 // Check every 15 seconds
    );

    // Cleanup on unmount
    return () => {
      groupMembershipMonitor.stopMonitoring();
    };
  }, [isAuthenticated, currentUser, state.activeGroupId]);

  // PHASE 2: Removed redundant settlement reload on expense changes
  // Settlements are now reloaded only when:
  // 1. Group changes (above useEffect)
  // 2. Settlement is created (handleSettlementSuccess)
  // 3. Balance update is requested (handleBalanceUpdate)

  // Load settlement history
  const loadSettlements = async (groupId) => {
    if (!groupId) return;
    
    try {
      const data = await expenseApi.getGroupSettlements(groupId);
      setSettlementHistory(data.settlements || []);
    } catch (err) {
      console.error('Error loading settlements:', err);
    }
  };

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
  
  // Wrapper for reloadActiveGroup that clears optimistic state first
  const handleBalanceUpdate = async () => {
    console.log('🔄 Balance update requested - clearing optimistic state and reloading');
    setOptimisticExpenses([]);
    setOptimisticBalances(null);
    await reloadActiveGroup();
    
    // PHASE 2 FIX: Do NOT reload settlements here
    // Settlements are reloaded by handleSettlementSuccess when needed
    // This prevents duplicate API calls (was causing 2x settlements loading)
  };

  // PHASE 2.7 FIX: Settlement success with cache bypass
  const handleSettlementSuccess = async (settlementData) => {
    console.log('💰 ExpenseManager: Settlement submitted, processing...');
    
    // Show toast notification for settlement processing
    showToast('Creating transaction...', 'info');
    
    try {
      // CRITICAL FIX: Clear optimistic state BEFORE API call
      // This ensures UI shows fresh data from server, not stale optimistic data
      console.log('🧹 Clearing optimistic state before settlement save');
      setOptimisticBalances(null);
      setOptimisticExpenses([]);
      
      // Save settlement to backend using React Query mutation
      await createSettlementMutation.mutateAsync(settlementData);
      console.log('✅ Settlement saved successfully');
      
      // React Query automatically invalidates cache
      // Force fresh data reload with cache bypass
      if (state.activeGroupId) {
        console.log('🔄 Forcing fresh data reload with cache bypass...');
        await Promise.all([
          loadSettlements(state.activeGroupId),
          reloadActiveGroup(true) // ✅ PASS TRUE to bypass cache
        ]);
        console.log('✅ Fresh data loaded - balances updated!');
      }
      
      // Show success toast
      showToast('Transaction recorded successfully', 'success');
    } catch (error) {
      console.error('❌ Settlement save failed:', error);
      showToast(error.message || 'Failed to record settlement', 'error');
    }
  };

  const showConfirm = (message, callback) => {
    setConfirmMessage(message);
    setConfirmCallback(() => callback);
    setShowConfirmModal(true);
  };

  const getCurrentTransactions = () => {
    let transactions = [];
    if (state.mode === 'personal') {
      transactions = personalExpenses || [];
    } else {
      // Use optimistic expenses if available, otherwise use API data
      transactions = optimisticExpenses.length > 0 ? optimisticExpenses : (activeGroupExpenses || []);
    }
    
    // Reduced logging - only log when in development mode
    if (process.env.NODE_ENV === 'development' && Math.random() < 0.1) {
      console.log('🔍 getCurrentTransactions:', {
        mode: state.mode,
        count: transactions.length
      });
    }
    
    return transactions;
  };
  
  // Get current balances (optimistic or API)
  const getCurrentBalances = () => {
    if (state.mode === 'personal') return null;
    
    // Use optimistic balances if available
    if (optimisticBalances) {
      console.log('💡 Using optimistic balances');
      return optimisticBalances;
    }
    
    // Return activeGroupBalances - keepPreviousData keeps old data during refetch
    // Only return null if we truly have no group selected
    if (!state.activeGroupId) return null;
    
    return activeGroupBalances || []; // Return empty array instead of undefined
  };
  
  // Calculate balances from expenses (for optimistic updates)
  const calculateBalancesFromExpenses = (expenses) => {
    // ⚠️ CRITICAL: This function CANNOT accurately calculate balances
    // because it only looks at expenses, NOT settlements!
    // 
    // Example problem:
    // - Total expenses: $460 (5 transactions)
    // - Settlements: $50 paid
    // - This function calculates: ±$230 (WRONG!)
    // - Backend calculates: ±$200 (CORRECT - includes settlements)
    //
    // SOLUTION: Don't use optimistic balance calculations.
    // Always fetch from backend which has the correct incremental updates.
    
    if (!expenses || expenses.length === 0) {
      return { balances: [], debts: [], is_settled: true, total_spent: 0 };
    }
    
    // Calculate member balances (INCOMPLETE - missing settlements!)
    const memberBalances = {};
    let totalSpent = 0;
    
    expenses.forEach(expense => {
      const amount = parseFloat(expense.amount || 0);
      const paidBy = expense.paid_by;
      const splits = expense.splits || [];
      
      totalSpent += amount;
      
      // Person who paid gets positive balance
      if (paidBy) {
        memberBalances[paidBy] = (memberBalances[paidBy] || 0) + amount;
      }
      
      // People in split get negative balance
      splits.forEach(split => {
        const userId = split.user_id;
        const splitAmount = parseFloat(split.amount || 0);
        memberBalances[userId] = (memberBalances[userId] || 0) - splitAmount;
      });
    });
    
    // Convert to array format
    const balances = Object.entries(memberBalances).map(([userId, balance]) => ({
      user_id: userId,
      balance: balance,
      net_balance: balance
    }));
    
    // Calculate simplified debts - use COPIES to avoid mutation
    const creditors = balances.filter(b => b.balance > 0.01).map(b => ({ ...b }));
    const debtors = balances.filter(b => b.balance < -0.01).map(b => ({ ...b }));
    const debts = [];
    
    // Simple greedy algorithm
    creditors.forEach(creditor => {
      debtors.forEach(debtor => {
        if (Math.abs(debtor.balance) > 0.01 && creditor.balance > 0.01) {
          const amount = Math.min(creditor.balance, Math.abs(debtor.balance));
          debts.push({
            from: debtor.user_id,
            to: creditor.user_id,
            amount: amount
          });
          creditor.balance -= amount;
          debtor.balance += amount;
        }
      });
    });
    
    return {
      balances,
      debts,
      is_settled: debts.length === 0,
      total_spent: totalSpent
    };
  };

  const handleModeToggle = () => {
    setState(prev => ({ ...prev, mode: prev.mode === 'personal' ? 'group' : 'personal' }));
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
      // Check if group has at least 2 members
      if (activeGroupMembers.length < 2) {
        showAlert('At least 2 members required to create group expense. Invite more members first.');
        return;
      }
    }
    setState(prev => ({ ...prev, editingTransactionId: null }));
    setShowTransactionModal(true);
  };

  const handleSaveTransaction = async (transactionData) => {
    try {
      if (state.mode === 'personal') {
        // Create or update personal expense
        if (state.editingTransactionId) {
          await expenseApi.updateExpense(state.editingTransactionId, transactionData);
          showToast('Transaction updated!', 'success');
        } else {
          await expenseApi.createExpense({
            group_id: null,
            description: transactionData.description,
            amount: transactionData.amount,
            currency: transactionData.currency || 'USD',
            category: transactionData.category,
            date: transactionData.date,
            paid_by: currentUser.uid,
            split_type: 'EQUAL',
            splits: [{ user_id: currentUser.uid, amount: transactionData.amount }]
          });
          showToast('Transaction created!', 'success');
        }
        await reloadPersonalExpenses();
      } else {
        // Create or update group expense
        if (state.editingTransactionId) {
          // EDIT - Reload real data immediately
          console.log('✏️ Editing expense:', state.editingTransactionId);
          
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
            date: transactionData.date,
            paid_by: transactionData.paidBy,
            split_type: 'EQUAL',
            splits: splits
          };
          
          // Close modal immediately
          setShowTransactionModal(false);
          setState(prev => ({ ...prev, editingTransactionId: null }));
          showToast('Updating transaction...', 'info');
          
          // Update with optimistic balance updates
          try {
            const startTime = performance.now();
            
            // Calculate optimistic balances BEFORE backend call
            if (activeGroupBalances && activeGroupMembers) {
              console.log('🔍 Looking for old expense:', {
                editingId: state.editingTransactionId,
                availableExpenses: activeGroupExpenses?.map(e => ({ id: e.id, expense_id: e.expense_id, description: e.description }))
              });
              
              const oldExpense = activeGroupExpenses?.find(e => 
                e.id === state.editingTransactionId || e.expense_id === state.editingTransactionId
              );
              
              if (oldExpense) {
                console.log('✅ Found old expense:', {
                  description: oldExpense.description,
                  amount: oldExpense.amount,
                  paid_by: oldExpense.paid_by || oldExpense.paidBy
                });
                
                const optimisticBalances = calculateOptimisticBalances(
                  activeGroupBalances,
                  activeGroupMembers,
                  oldExpense,
                  expensePayload
                );
                setOptimisticBalances(optimisticBalances);
                console.log('⚡ Optimistic balances set! Balance display should update instantly');
              } else {
                console.warn('⚠️ Old expense not found - skipping optimistic update');
              }
            } else {
              console.warn('⚠️ Missing balances or members - skipping optimistic update');
            }
            
            // Backend update happens in background using React Query mutation
            await updateExpenseMutation.mutateAsync({
              expenseId: state.editingTransactionId,
              data: transactionData
            });
            console.log(`✅ Update confirmed in ${(performance.now() - startTime).toFixed(0)}ms`);
            
            // React Query automatically invalidates and refetches the group data
            // DON'T manually reload - it causes flicker!
            // await reloadActiveGroup(true);
            
            // Clear optimistic state after mutation completes (React Query handles refetch)
            setTimeout(() => {
              setOptimisticExpenses([]);
              setOptimisticBalances(null);
              console.log('✅ Optimistic state cleared after React Query refetch');
            }, 300); // 300ms ensures refetch completes
            
            console.log(`✅ All data reloaded in ${(performance.now() - startTime).toFixed(0)}ms total`);
            showToast('Transaction updated!', 'success');
          } catch (error) {
            console.error('❌ Update failed:', error);
            showToast(`Failed: ${error.message}`, 'error');
            await reloadActiveGroup();
          }
          
          return;
        } else {
          // CREATE - Use faster reload
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
            date: transactionData.date,
            paid_by: transactionData.paidBy,
            split_type: 'EQUAL',
            splits: splits
          };

          console.log('📤 Creating expense with optimistic balance updates...');
          
          // Close modal immediately for snappy UX
          setShowTransactionModal(false);
          setState(prev => ({ ...prev, editingTransactionId: null }));
          
          // Create expense and show optimistic balances immediately
          try {
            const startTime = performance.now();
            
            // Calculate optimistic balances BEFORE backend call (for new expense, oldExpense = null)
            if (activeGroupBalances && activeGroupMembers) {
              const optimisticBalances = calculateOptimisticBalances(
                activeGroupBalances,
                activeGroupMembers,
                null, // No old expense (this is a new one)
                expensePayload
              );
              setOptimisticBalances(optimisticBalances);
              console.log('⚡ Optimistic balances set for CREATE! Balance display should update instantly');
            }
            
            // Show loading toast
            showToast('Creating transaction...', 'info');
            
            // Backend create happens in background using React Query mutation
            const createResponse = await createExpenseMutation.mutateAsync(expensePayload);
            console.log(`✅ Expense created in ${(performance.now() - startTime).toFixed(0)}ms`);
            
            // React Query automatically invalidates and refetches the group data
            // DON'T manually reload - it causes flicker!
            // await reloadActiveGroup(true);
            
            // Clear optimistic state after mutation completes (React Query handles refetch)
            // Use delay to let React Query's refetch complete first
            setTimeout(() => {
              setOptimisticExpenses([]);
              setOptimisticBalances(null);
              console.log('✅ Optimistic state cleared after React Query refetch');
            }, 300); // 300ms ensures refetch completes
            
            console.log(`✅ All data reloaded in ${(performance.now() - startTime).toFixed(0)}ms total`);
            showToast('Transaction created!', 'success');
          } catch (error) {
            console.error('❌ Create failed:', error);
            showToast(`Failed: ${error.message}`, 'error');
            // Clear optimistic state on error
            setOptimisticBalances(null);
            await reloadActiveGroup();
          }
          
          return;
        }
      }
      
      setShowTransactionModal(false);
      setState(prev => ({ ...prev, editingTransactionId: null }));
    } catch (error) {
      console.error('Error saving transaction:', error);
      showToast(`Failed to save transaction: ${error.message}`, 'error');
    }
  };

  const handleEditTransaction = (transaction) => {
    // Block editing temp expenses (still being created in backend)
    const expenseId = transaction.id || transaction.expense_id;
    if (expenseId && expenseId.toString().startsWith('temp-')) {
      showToast('Please wait, expense is still being created...', 'info');
      console.log('⚠️ Cannot edit temporary expense (still being created)');
      return;
    }
    
    setState(prev => ({ ...prev, editingTransactionId: expenseId }));
    setShowTransactionModal(true);
  };

  const handleDeleteTransaction = async (id) => {
    try {
      // Skip deletion if this is a temporary ID
      if (id && id.toString().startsWith('temp-')) {
        console.log('⚠️ Skipping delete of temporary expense');
        return;
      }
      
      console.log('🗑️ DELETING EXPENSE - ID:', id);
      
      showToast('Deleting transaction...', 'info');
      
      // Delete and reload
      const startTime = performance.now();
      
      // Use React Query mutation for deletion
      await deleteExpenseMutation.mutateAsync(id, {
        context: { groupId: state.activeGroupId }
      });
      console.log(`✅ Backend delete confirmed in ${(performance.now() - startTime).toFixed(0)}ms`);
      
      // Clear stale state
      setOptimisticExpenses([]);
      setOptimisticBalances(null);
      
      // PHASE 2: React Query automatically invalidates cache
      // Bypass cache to get fresh data after deletion
      if (state.mode === 'group') {
        await reloadActiveGroup(true);
      } else {
        await reloadPersonalExpenses();
      }
      
      console.log(`✅ All data reloaded in ${(performance.now() - startTime).toFixed(0)}ms total`);
      showToast('Transaction deleted!', 'success');
      
    } catch (error) {
      console.error('❌ Error deleting:', error);
      showToast(`Failed to delete: ${error.message}`, 'error');
    }
  };

  const handleFilterChange = (filterType, value) => {
    setState(prev => ({
      ...prev,
      filter: { ...prev.filter, [filterType]: value }
    }));
  };

  const handleGroupChange = (groupId) => {
    setState(prev => ({ ...prev, activeGroupId: groupId }));
  };

  // PHASE 2.9: Wrapper for group creation using React Query mutation
  const createGroup = async (groupData) => {
    try {
      console.log('📤 Creating group:', groupData);
      const result = await createGroupMutation.mutateAsync(groupData);
      console.log('✅ Group created, result:', result);
      
      // React Query automatically invalidates groups cache
      showToast('Group created successfully!', 'success');
      
      // Reload groups list to ensure new group appears
      await reloadGroups();
      
      // Automatically switch to the newly created group
      // Backend returns: { success: true, group: { group_id, name, ... } }
      const newGroupId = result?.group?.group_id || result?.group_id;
      if (newGroupId) {
        console.log('🎯 Switching to newly created group:', newGroupId);
        setState(prev => ({ ...prev, activeGroupId: newGroupId, mode: 'group' }));
        // Update URL to reflect new group
        setSearchParams({ view: 'group', groupId: newGroupId });
      } else {
        console.warn('⚠️ No group_id in response:', result);
      }
      
      return result;
    } catch (error) {
      console.error('❌ Group creation failed:', error);
      showToast(`Failed to create group: ${error.message}`, 'error');
      throw error;
    }
  };

  const handleDeleteGroup = async (groupId) => {
    try {
      // Clear active group BEFORE deletion
      const wasActive = state.activeGroupId === groupId;
      if (wasActive) {
        setState(prev => ({ ...prev, activeGroupId: null, mode: 'personal' }));
        setOptimisticExpenses([]);
        setOptimisticBalances(null);
      }
      
      // Use mutation - automatically invalidates cache
      await deleteGroupMutation.mutateAsync(groupId);
      
      // CRITICAL FIX: Force immediate refetch to update UI
      console.log('🔄 Forcing groups refetch after deletion...');
      await reloadGroups();
      
      showToast('Group deleted successfully!', 'success');
      
    } catch (error) {
      console.error('❌ Delete failed:', error);
      showToast(`Failed to delete: ${error.message}`, 'error');
      // Reload to restore correct state on error
      await reloadGroups();
      throw error;
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      if (state.mode === 'personal') {
        await reloadPersonalExpenses();
      } else {
        await reloadActiveGroup();
      }
      await reloadGroups();
    } catch (error) {
      console.error('Error refreshing:', error);
      showAlert(`Failed to refresh: ${error.message}`);
    } finally {
      setRefreshing(false);
    }
  };

  const editingTransaction = state.editingTransactionId
    ? getCurrentTransactions().find(t => t.id === state.editingTransactionId)
    : null;

  // Show loading state
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

  // Show auth required message
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
            disabled={refreshing}
            title="Refresh data"
          >
            <RefreshCw size={20} className={refreshing ? 'spinning' : ''} />
          </button>
          <ModeToggle mode={state.mode} onToggle={handleModeToggle} />
          <button className="btn-add-transaction" onClick={handleOpenModal}>
            <PlusCircle size={20} />
            <span>Add Transaction</span>
          </button>
        </div>
      </header>

      {/* PHASE 2.7 FIX: Show pending invitations in BOTH modes (personal and group) */}
      {/* User should see invitations even when they have no groups */}
      <PendingInvitations 
        onInvitationAccepted={async () => {
          console.log('🎉 Invitation accepted! Reloading groups...');
          
          // Invalidate and refetch groups to get fresh data
          queryClient.invalidateQueries({ queryKey: queryKeys.groups });
          const { data: freshGroups } = await reloadGroups();
          
          console.log('✅ Groups reloaded:', freshGroups);
          
          // Get groups array from response (handle different response formats)
          const groupsList = freshGroups?.groups || freshGroups || [];
          
          // Switch to group mode and select the first group (the one just joined)
          if (groupsList && groupsList.length > 0) {
            const newGroup = groupsList[0]; // Most recent group
            const groupId = newGroup.group_id || newGroup.id;
            console.log('🎯 Switching to new group:', groupId, newGroup);
            
            setState(prev => ({ 
              ...prev, 
              mode: 'group',
              activeGroupId: groupId
            }));
            setSearchParams({ view: 'group', groupId: groupId });
            showToast('Welcome to the group!', 'success');
          } else {
            setState(prev => ({ ...prev, mode: 'group' }));
            showToast('Invitation accepted!', 'success');
          }
        }}
        currentUser={currentUser}
      />

      {state.mode === 'group' && (
        <>
          <GroupManager
            groups={(groups || []).filter(g => g && g.id)}
            activeGroupId={state.activeGroupId}
            activeGroup={state.activeGroupId ? activeGroupData : null}
            members={activeGroupMembers || []}
            loading={groupsLoading}
            onGroupChange={handleGroupChange}
            onGroupCreate={createGroup}
            onGroupDelete={handleDeleteGroup}
            onMemberAdd={async () => await reloadActiveGroup()}
            onMemberRemove={async () => await reloadActiveGroup()}
            showAlert={showAlert}
            currentUser={currentUser}
          />
        </>
      )}

      {/* Show ExpenseSummary only for personal mode */}
      {state.mode === 'personal' && (
        <ExpenseSummary 
          transactions={getCurrentTransactions()}
          mode={state.mode}
          currency='USD'
        />
      )}

      {/* Show Summary Cards for group mode */}
      {state.mode === 'group' && state.activeGroupId && (() => {
        const transactions = getCurrentTransactions() || [];
        const expenses = transactions.filter(t => t.type === 'expense');
        const totalAmount = expenses.reduce((sum, t) => sum + (t.amount || 0), 0);
        const expenseCount = expenses.length;
        
        // Calculate remaining balance
        const balances = getCurrentBalances() || [];
        const totalSettled = settlementHistory.reduce((sum, s) => sum + (s.amount || 0), 0);
        
        // Sum of all absolute balances / 2 (because each debt has a payer and receiver)
        const currentOwed = balances
          .filter(b => Math.abs(b.net_balance || 0) > 0.01)
          .reduce((sum, b) => sum + Math.abs(b.net_balance || 0), 0) / 2;
        
        return (
          <>
            <GroupSummaryCards
              totalExpenses={expenseCount}
              totalAmount={totalAmount}
              remainingBalance={currentOwed}
              totalSettlements={totalSettled}
              settlementCount={settlementHistory.length}
              currency={activeGroupData?.currency || 'USD'}
              onSettlementCardClick={() => setIsHistoryModalOpen(true)}
            />
            
            <SettlementHistoryModal
              isOpen={isHistoryModalOpen}
              onClose={() => setIsHistoryModalOpen(false)}
              settlements={settlementHistory}
              currency={activeGroupData?.currency || 'USD'}
            />
          </>
        );
      })()}

      {state.mode === 'group' && state.activeGroupId && activeGroupData && (
        <GroupBalances 
          key={`${state.activeGroupId}-${getCurrentBalances()?.length || 0}-${getCurrentTransactions()?.length || 0}-${optimisticBalances ? 'optimistic' : 'real'}`}
          group={activeGroupData} 
          balances={getCurrentBalances() || []}
          members={activeGroupMembers || []}
          onBalanceUpdate={handleBalanceUpdate}
          settlementHistory={settlementHistory}
          loadingSettlements={false}
          onSettlementSuccess={handleSettlementSuccess}
          totalExpenses={
            getCurrentTransactions()?.filter(t => t.type === 'expense').length || 0
          }
          totalExpensesAmount={
            getCurrentTransactions()
              ?.filter(t => t.type === 'expense')
              .reduce((sum, t) => sum + (t.amount || 0), 0) || 0
          }
        />
      )}

      <TransactionList
        key={`${state.mode}-${state.activeGroupId || 'personal'}-${getCurrentTransactions()?.length || 0}`}
        transactions={getCurrentTransactions()}
        filter={state.filter}
        mode={state.mode}
        activeGroup={activeGroupData}
        members={activeGroupMembers || []}
        loading={state.mode === 'personal' ? personalLoading : !activeGroupData}
        onEdit={handleEditTransaction}
        onDelete={(id) => showConfirm('Are you sure you want to delete this transaction?', () => handleDeleteTransaction(id))}
        onFilterChange={handleFilterChange}
        currency={state.mode === 'group' ? activeGroupData?.currency : 'USD'}
        currentUserId={currentUser?.uid}
      />

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
  );
};

export default ExpenseManager;
