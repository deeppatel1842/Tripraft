import React, { useState, useEffect, useCallback, useRef } from 'react';
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
import ErrorBoundary from '../common/ErrorBoundary';
import { OfflineIndicator } from '../common/MutationStatus';
import { PlusCircle, RefreshCw } from 'lucide-react';
import { useExpenseApi, useUserExpenses } from '../../hooks/useExpense';
import { 
  useGroupQuery,
  useMegaBootstrap,
  useCreateGroupMutation,
  useCreateExpenseMutation,
  useUpdateExpenseMutation,
  useDeleteExpenseMutation,
  useCreateSettlementMutation,
  queryKeys
} from '../../hooks/useExpenseQuery';
import GroupPlannerContext from '../../context/GroupPlannerContext';
import expenseApi from '../../services/expenseApi';
// Phase 18.7: groupMembershipMonitor disabled - Firestore real-time listeners handle membership detection
// import { groupMembershipMonitor } from '../../utils/groupMembershipMonitor';
import expenseFirestoreListener from '../../services/expenseFirestoreListener';
import firestoreListenerService from '../../services/firestoreListenerService';
import '../css/ExpenseManager.css';

// Helper function to calculate optimistic balances after expense edit/create
const calculateOptimisticBalances = (currentBalances, members, oldExpense, newExpense) => {
  // Ensure currentBalances is an array
  if (!Array.isArray(currentBalances)) {
    console.warn('⚠️ calculateOptimisticBalances: currentBalances is not an array, converting...');
    if (typeof currentBalances === 'object' && currentBalances !== null) {
      // Convert dict format {user_id: balance} to array format
      currentBalances = Object.entries(currentBalances).map(([userId, balance]) => ({
        user_id: userId,
        balance: parseFloat(balance) || 0,
        net_balance: parseFloat(balance) || 0
      }));
    } else {
      console.error('❌ Cannot convert currentBalances to array, initializing from members');
      // Initialize balances from members list
      currentBalances = (members || []).map(m => ({
        user_id: m.user_id || m.id,
        balance: 0,
        net_balance: 0
      }));
    }
  }
  
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
  
  // Get groups from Firestore real-time listener (GroupPlannerContext)
  const { groups: groupsObject } = React.useContext(GroupPlannerContext);
  // Convert object {groupId: groupData} to array [groupData]
  const groups = Object.values(groupsObject || {});
  const groupsLoading = false; // Firestore listener handles loading
  
  // Keep refetch function for compatibility (manual refresh)
  const reloadGroups = useCallback(() => {
    console.log('📡 Manual group refresh requested');
    // Groups auto-update via Firestore listener
  }, []);
  const createGroupMutation = useCreateGroupMutation();
  
  // Expense mutations (Phase 2.9)
  const createExpenseMutation = useCreateExpenseMutation();
  const updateExpenseMutation = useUpdateExpenseMutation();
  const deleteExpenseMutation = useDeleteExpenseMutation();
  const createSettlementMutation = useCreateSettlementMutation();
  
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

  // 🔥 PHASE 17 FIX: Debounce Firestore invalidations to prevent 5-6 re-renders per action
  // All Firestore listeners fire within milliseconds - batch them into ONE invalidation
  // 🔥 PHASE 17 FIX: Mutation cooldown - prevent Firestore from overwriting fresh mutation data
  // When a mutation is in progress, we set this to true
  // During cooldown, Firestore cache updates are skipped (mutation already updated cache)
  const mutationCooldownRef = useRef(false);
  const mutationCooldownTimer = useRef(null);
  
  const startMutationCooldown = useCallback(() => {
    mutationCooldownRef.current = true;
    // Clear any existing timer
    if (mutationCooldownTimer.current) {
      clearTimeout(mutationCooldownTimer.current);
    }
    // End cooldown after 5 seconds (enough time for backend writes + Firestore sync)
    mutationCooldownTimer.current = setTimeout(() => {
      mutationCooldownRef.current = false;
      console.log('🔥 Mutation cooldown ended - Firestore listeners active again');
    }, 5000);
    console.log('🔥 Mutation cooldown started - Firestore listeners paused for 5s');
  }, []);

  // PHASE 2.9: Replace useGroup with React Query
  // 🚀 PHASE 16: Use mega-bootstrap for ONE unified API call
  const { 
    data: megaData, 
    isLoading: megaLoading, 
    refetch: refetchMega 
  } = useMegaBootstrap(state.activeGroupId, {
    enabled: state.mode === 'group' && !!state.activeGroupId
  });
  
  // 🚀 PHASE 16: Only use fallback when mega-bootstrap has COMPLETED with no data
  // Previously: !megaData would trigger fallback while mega-bootstrap was still loading
  const megaBootstrapComplete = !megaLoading;
  const useFallbackQuery = state.mode === 'group' && !!state.activeGroupId && megaBootstrapComplete && !megaData;
  
  // Track online status for UI indicators
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  
  // Fallback to useGroupQuery when mega-bootstrap is not active (personal mode)
  const { data: groupData, isLoading: groupLoading, isPlaceholderData, refetch: refetchGroup } = useGroupQuery(
    state.activeGroupId,
    { enabled: useFallbackQuery }
  );
  
  // Extract data from mega-bootstrap or fallback to group query
  // keepPreviousData ensures these never become undefined during refetch
  const activeGroupFromMega = megaData?.data?.active_group;
  const activeGroupData = activeGroupFromMega?.group || groupData?.group || null;
  const activeGroupMembers = activeGroupFromMega?.members || groupData?.members || [];
  const activeGroupExpenses = activeGroupFromMega?.expenses || groupData?.expenses || [];
  const activeGroupBalances = activeGroupFromMega?.balances || groupData?.balances || [];
  const activeGroupSettlements = activeGroupFromMega?.settlements || [];
  const allMembersMap = activeGroupFromMega?.all_members_map || groupData?.all_members_map || {};
  
  // Get groups and invitations from mega-bootstrap
  // Phase 17 Bug Fix: Only set megaInvitations when mega-bootstrap is actually used
  // Pass undefined (not empty array) when mega-bootstrap is disabled so PendingInvitations uses its own API
  const megaGroups = megaData?.data?.groups || [];
  const megaInvitations = megaData?.data ? megaData.data.invitations : undefined;
  
  // DEBUG: Log group data to diagnose member visibility issue
  useEffect(() => {
    if (groupData && state.activeGroupId) {
      console.log('📊 Group Data Updated:', {
        groupId: state.activeGroupId,
        groupName: activeGroupData?.name,
        memberCount: activeGroupMembers?.length,
        members: activeGroupMembers?.map(m => ({ id: m.user_id, name: m.display_name || m.username })),
        balanceCount: activeGroupBalances?.length,
        balancesType: Array.isArray(activeGroupBalances) ? 'array' : typeof activeGroupBalances,
        expenseCount: activeGroupExpenses?.length
      });
    }
  }, [groupData, state.activeGroupId]);
  
  // Helper function to reload active group (with cache bypass option)
  const reloadActiveGroup = async (bypassCache = false) => {
    if (bypassCache) {
      // 🚀 PHASE 16: Invalidate mega-bootstrap cache
      queryClient.invalidateQueries({ queryKey: queryKeys.megaBootstrap(state.activeGroupId) });
      // Also invalidate group cache for fallback
      queryClient.invalidateQueries({ queryKey: queryKeys.group(state.activeGroupId) });
    }
    // Refetch mega-bootstrap if available, otherwise refetch group
    if (megaData) {
      await refetchMega();
    } else {
      await refetchGroup();
    }
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
  // PHASE 17 FIX: Only clear when mode or activeGroupId ACTUALLY changes
  // NOT when megaData refreshes (that would wipe optimistic updates)
  const prevModeRef = useRef(state.mode);
  const prevGroupIdRef = useRef(state.activeGroupId);
  
  useEffect(() => {
    const modeChanged = prevModeRef.current !== state.mode;
    const groupChanged = prevGroupIdRef.current !== state.activeGroupId;
    
    // Only clear if mode or group actually changed
    if (modeChanged || groupChanged) {
      console.log('🧹 Clearing optimistic state (mode/group changed)');
      setOptimisticExpenses([]);
      setOptimisticBalances(null);
      
      // Update refs
      prevModeRef.current = state.mode;
      prevGroupIdRef.current = state.activeGroupId;
    }
    
    // 🚀 PHASE 16: Settlements come from mega-bootstrap
    // Only use fallback if mega-bootstrap has finished loading with no data
    if (state.mode === 'group' && state.activeGroupId && !megaLoading && !megaData) {
      loadSettlements(state.activeGroupId);
    }
  }, [state.mode, state.activeGroupId, megaData, megaLoading]);

  // 🔥 FIRESTORE REAL-TIME LISTENERS: Listen to user's groups
  useEffect(() => {
    if (!isAuthenticated || !currentUser?.user_id) return;

    console.log('🔥 Setting up Firestore listener for user groups:', currentUser.user_id);

    // Listen to all user's groups in real-time
    const unsubscribe = expenseFirestoreListener.listenToUserExpenseGroups(
      currentUser.user_id,
      (updatedGroups) => {
        console.log('🔥 Firestore: Groups updated:', updatedGroups.length);
        
        // Phase 18.6: Update cache DIRECTLY instead of invalidating (prevents API refetch)
        queryClient.setQueryData(queryKeys.groups, {
          success: true,
          groups: updatedGroups
        });
        
        // If active group was deleted or user removed, switch to personal mode
        if (state.activeGroupId) {
          const stillMember = updatedGroups.some(g => g.id === state.activeGroupId);
          if (!stillMember) {
            console.warn('🚨 Active group no longer accessible');
            showToast('Group is no longer accessible', 'warning');
            setState(prev => ({ 
              ...prev, 
              mode: 'personal', 
              activeGroupId: null 
            }));
          }
        }
      },
      (error) => {
        console.error('❌ Firestore listener error:', error);
      }
    );

    return () => {
      console.log('🔥 Cleaning up Firestore listeners');
      unsubscribe();
    };
  }, [isAuthenticated, currentUser?.user_id, queryClient]);

  // 🔥 FIRESTORE REAL-TIME LISTENERS: Listen to active group members
  useEffect(() => {
    if (!state.activeGroupId || !isAuthenticated) return;

    console.log('🔥 Setting up Firestore listener for group members:', state.activeGroupId);

    const unsubscribe = expenseFirestoreListener.listenToGroupMembers(
      state.activeGroupId,
      (updatedMembers) => {
        console.log('🔥 Firestore: Group members updated:', updatedMembers.length);
        
        // Phase 18.6: Update cache DIRECTLY instead of invalidating (prevents API refetch)
        // IMPORTANT: Firestore only returns raw member docs (user_id, is_active, etc.)
        // We need to MERGE with existing user details (display_name, email, etc.)
        queryClient.setQueryData(queryKeys.megaBootstrap(state.activeGroupId), (old) => {
          if (!old?.data?.active_group) return old;
          
          // Create a map of existing members with their user details
          const existingMembersMap = {};
          (old.data.active_group.members || []).forEach(m => {
            existingMembersMap[m.user_id] = m;
          });
          
          // Get existing all_members_map for preserving removed members' names
          const existingAllMembersMap = { ...(old.data.active_group.all_members_map || {}) };
          
          // Merge: Keep existing user details, update is_active/role from Firestore
          const mergedMembers = updatedMembers.map(firestoreMember => {
            const existing = existingMembersMap[firestoreMember.user_id];
            if (existing) {
              // Member exists - preserve user details, update membership status
              return {
                ...existing,
                is_active: firestoreMember.is_active,
                role: firestoreMember.role || existing.role,
                joined_at: firestoreMember.joined_at || existing.joined_at
              };
            }
            // New member - use Firestore data (will get full details on next API call)
            // Create a reasonable display name from available data
            return {
              ...firestoreMember,
              display_name: firestoreMember.display_name || firestoreMember.email?.split('@')[0] || `User ${firestoreMember.user_id?.slice(0, 6)}`,
              user: {
                display_name: firestoreMember.display_name || firestoreMember.email?.split('@')[0] || `User ${firestoreMember.user_id?.slice(0, 6)}`,
                email: firestoreMember.email || ''
              }
            };
          });
          
          // PHASE 18 FIX: Preserve removed members in all_members_map
          // Members who were in the old list but not in the updated list were removed
          const currentMemberIds = new Set(updatedMembers.map(m => m.user_id));
          Object.keys(existingMembersMap).forEach(userId => {
            if (!currentMemberIds.has(userId)) {
              // This member was removed - preserve their info in all_members_map
              const removedMember = existingMembersMap[userId];
              existingAllMembersMap[userId] = {
                display_name: removedMember.display_name || removedMember.user?.display_name || `Former Member (${userId.slice(0, 8)})`,
                is_active: false
              };
              console.log('🔥 Preserved removed member in all_members_map:', userId, existingAllMembersMap[userId].display_name);
            }
          });
          
          // If new members were added, trigger a background refresh to get full details
          const newMemberIds = updatedMembers
            .filter(m => !existingMembersMap[m.user_id])
            .map(m => m.user_id);
          
          if (newMemberIds.length > 0) {
            console.log('🔥 New members detected, will fetch full details:', newMemberIds);
            // Invalidate cache after a short delay to fetch full member details
            setTimeout(() => {
              queryClient.invalidateQueries({ queryKey: queryKeys.megaBootstrap(state.activeGroupId) });
            }, 1000);
          }
          
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                members: mergedMembers,
                all_members_map: existingAllMembersMap
              }
            }
          };
        });
        
        // Also update group cache with merged members
        queryClient.setQueryData(queryKeys.group(state.activeGroupId), (old) => {
          if (!old) return old;
          
          const existingMembersMap = {};
          (old.members || []).forEach(m => {
            existingMembersMap[m.user_id] = m;
          });
          
          const mergedMembers = updatedMembers.map(firestoreMember => {
            const existing = existingMembersMap[firestoreMember.user_id];
            if (existing) {
              return { ...existing, is_active: firestoreMember.is_active, role: firestoreMember.role || existing.role };
            }
            return firestoreMember;
          });
          
          return { ...old, members: mergedMembers };
        });
        
        // Check if current user was removed
        if (currentUser?.user_id) {
          const stillMember = updatedMembers.some(m => m.user_id === currentUser.user_id && m.is_active);
          if (!stillMember) {
            console.warn('🚨 You were removed from this group');
            showToast('You were removed from this group', 'warning');
            setState(prev => ({ 
              ...prev, 
              mode: 'personal', 
              activeGroupId: null 
            }));
          }
        }
      },
      (error) => {
        console.error('❌ Firestore members listener error:', error);
      }
    );

    return () => {
      console.log('🔥 Cleaning up Firestore member listener');
      unsubscribe();
    };
  }, [state.activeGroupId, isAuthenticated, currentUser?.user_id, queryClient]);

  // 🔥 PHASE 17 OPTIMIZATION: FIRESTORE REAL-TIME LISTENERS for group invitations
  // Update cache directly instead of invalidating
  useEffect(() => {
    if (!state.activeGroupId || !isAuthenticated) return;

    console.log('🔥 Setting up Firestore listener for group invitations:', state.activeGroupId);

    const unsubscribe = expenseFirestoreListener.listenToGroupInvitations(
      state.activeGroupId,
      (updatedInvitations) => {
        // Skip if in mutation cooldown (mutation already updated cache correctly)
        if (mutationCooldownRef.current) {
          console.log('🔥 Firestore invitations update skipped - mutation cooldown active');
          return;
        }
        
        console.log('🔥 Firestore: Updating group invitations cache directly:', updatedInvitations.length);
        
        // Update cache directly - no API call needed
        // Note: The field is "invitations" not "pending_invitations" to match GroupManager props
        queryClient.setQueryData(queryKeys.megaBootstrap(state.activeGroupId), (old) => {
          if (!old?.data?.active_group) return old;
          
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                invitations: updatedInvitations  // This feeds into pendingInvitationsFromParent
              }
            }
          };
        });
      },
      (error) => {
        console.error('❌ Firestore invitations listener error:', error);
      }
    );

    return () => {
      console.log('🔥 Cleaning up Firestore invitations listener');
      unsubscribe();
    };
  }, [state.activeGroupId, isAuthenticated, queryClient]);

  // 🔥 PHASE 17.5: FIRESTORE REAL-TIME LISTENER for user's pending invitations (invitee)
  // This allows User B to see invitations instantly when User A sends them
  useEffect(() => {
    if (!isAuthenticated || !currentUser?.email) return;

    // Phase 17.9: Normalize email to lowercase for consistent matching with backend
    const normalizedEmail = currentUser.email.toLowerCase().trim();
    console.log('🔥 Setting up Firestore listener for user invitations:', normalizedEmail);

    const unsubscribe = expenseFirestoreListener.listenToUserInvitations(
      normalizedEmail,
      (updatedInvitations) => {
        console.log('🔥 Firestore: User invitations updated:', updatedInvitations.length);
        
        // IMPORTANT: Update BOTH caches so invitations show in all modes
        
        // 1. Update mega-bootstrap cache (for group mode)
        queryClient.setQueryData(queryKeys.megaBootstrap(state.activeGroupId), (old) => {
          if (!old?.data) return old;
          
          return {
            ...old,
            data: {
              ...old.data,
              invitations: updatedInvitations
            }
          };
        });
        
        // 2. Update invitations cache directly (for personal/dashboard mode)
        // This ensures PendingInvitations component sees updates even when mega-bootstrap is disabled
        queryClient.setQueryData(queryKeys.invitations, {
          success: true,
          invitations: updatedInvitations
        });
        
        // Phase 18.6: DON'T invalidate groups - invitations update is already handled above
        // Removing this prevents unnecessary API refetch cascade
        // queryClient.invalidateQueries({ queryKey: queryKeys.groups });
      },
      (error) => {
        console.error('❌ Firestore user invitations listener error:', error);
      }
    );

    return () => {
      console.log('🔥 Cleaning up Firestore user invitations listener');
      unsubscribe();
    };
  }, [isAuthenticated, currentUser?.email, state.activeGroupId, queryClient]);

  // 🔥 PHASE 17 OPTIMIZATION: FIRESTORE REAL-TIME LISTENERS for expenses
  // Instead of invalidating (causing refetch), update cache directly for instant UI
  useEffect(() => {
    if (!state.activeGroupId || !isAuthenticated) return;

    console.log('🔥 Setting up Firestore listener for group expenses:', state.activeGroupId);

    const unsubscribe = expenseFirestoreListener.listenToGroupExpenses(
      state.activeGroupId,
      (updatedExpenses) => {
        // Skip if in mutation cooldown (mutation already updated cache correctly)
        if (mutationCooldownRef.current) {
          console.log('🔥 Firestore expenses update skipped - mutation cooldown active');
          return;
        }
        
        console.log('🔥 Firestore: Updating expenses cache directly:', updatedExpenses.length);
        
        // Phase 17.9: MERGE expenses instead of replacing
        // Firestore listener only returns non-deleted expenses (is_deleted: false filter)
        // We need to preserve deleted expenses in cache for history display
        queryClient.setQueryData(queryKeys.megaBootstrap(state.activeGroupId), (old) => {
          if (!old?.data?.active_group) return old;
          
          // Get existing deleted expenses (to preserve them)
          const existingExpenses = old.data.active_group.expenses || [];
          const deletedExpenses = existingExpenses.filter(e => e.is_deleted);
          
          // Merge: live expenses from Firestore + preserved deleted expenses
          const mergedExpenses = [
            ...updatedExpenses,
            ...deletedExpenses
          ];
          
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                expenses: mergedExpenses
              }
            }
          };
        });
      },
      (error) => {
        console.error('❌ Firestore expenses listener error:', error);
      }
    );

    return () => {
      console.log('🔥 Cleaning up Firestore expenses listener');
      unsubscribe();
    };
  }, [state.activeGroupId, isAuthenticated, queryClient]);

  // 🔥 PHASE 17 OPTIMIZATION: FIRESTORE REAL-TIME LISTENERS for balances
  // Update cache directly instead of invalidating for instant UI updates
  useEffect(() => {
    if (!state.activeGroupId || !isAuthenticated) return;

    console.log('🔥 Setting up Firestore listener for group balances:', state.activeGroupId);

    const unsubscribe = expenseFirestoreListener.listenToGroupBalances(
      state.activeGroupId,
      (updatedBalanceData) => {
        // Skip if in mutation cooldown (mutation already updated cache correctly)
        if (mutationCooldownRef.current) {
          console.log('🔥 Firestore balance update skipped - mutation cooldown active');
          return;
        }
        
        if (!updatedBalanceData?.balances) {
          console.log('🔥 Firestore: No balance data received');
          return;
        }
        
        console.log('🔥 Firestore: Updating balances cache directly with', Object.keys(updatedBalanceData.balances).length, 'entries');
        
        // Update cache directly - no API call needed
        queryClient.setQueryData(queryKeys.megaBootstrap(state.activeGroupId), (old) => {
          if (!old?.data?.active_group) {
            console.log('🔥 Firestore: No active group cache, skipping balance update');
            return old;
          }
          
          // Create a map of existing balances with their display names
          const existingBalancesMap = {};
          (old.data.active_group.balances || []).forEach(b => {
            existingBalancesMap[b.user_id] = b;
          });
          
          // Create a map of members for display names
          const membersMap = {};
          (old.data.active_group.members || []).forEach(m => {
            membersMap[m.user_id] = m;
          });
          
          // Merge Firestore balance values with existing display names
          // Include ALL users from Firestore balances (not just existing cache members)
          const updatedBalances = Object.entries(updatedBalanceData.balances).map(([userId, balance]) => {
            const existing = existingBalancesMap[userId];
            const member = membersMap[userId];
            const displayName = existing?.display_name || 
                              member?.display_name || 
                              member?.user?.display_name ||
                              member?.email?.split('@')[0] ||
                              `User ${userId.slice(0, 6)}`;
            
            return {
              user_id: userId,
              display_name: displayName,
              balance: parseFloat(balance) || 0,
              net_balance: parseFloat(balance) || 0,
              is_active: existing?.is_active ?? member?.is_active ?? true
            };
          });
          
          console.log('🔥 Firestore: Updated balances array:', updatedBalances.length, 'entries');
          
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                balances: updatedBalances
              }
            }
          };
        });
      },
      (error) => {
        console.error('❌ Firestore balances listener error:', error);
      }
    );

    return () => {
      console.log('🔥 Cleaning up Firestore balances listener');
      unsubscribe();
    };
  }, [state.activeGroupId, isAuthenticated, queryClient]);

  // 🔥 PHASE 17 OPTIMIZATION: FIRESTORE REAL-TIME LISTENERS for settlements
  // Update cache directly instead of invalidating
  useEffect(() => {
    if (!state.activeGroupId || !isAuthenticated) return;

    console.log('🔥 Setting up Firestore listener for group settlements:', state.activeGroupId);

    const unsubscribe = expenseFirestoreListener.listenToGroupSettlements(
      state.activeGroupId,
      (updatedSettlements) => {
        // Skip if in mutation cooldown (mutation already updated cache correctly)
        if (mutationCooldownRef.current) {
          console.log('🔥 Firestore settlements update skipped - mutation cooldown active');
          return;
        }
        
        console.log('🔥 Firestore: Updating settlements cache directly:', updatedSettlements.length);
        
        // Update cache directly - no API call needed
        queryClient.setQueryData(queryKeys.megaBootstrap(state.activeGroupId), (old) => {
          if (!old?.data?.active_group) return old;
          
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                settlements: updatedSettlements
              }
            }
          };
        });
      },
      (error) => {
        console.error('❌ Firestore settlements listener error:', error);
      }
    );

    return () => {
      console.log('🔥 Cleaning up Firestore settlements listener');
      unsubscribe();
    };
  }, [state.activeGroupId, isAuthenticated, queryClient]);

  // 🐛 BUG FIX #3 & #4: Monitor group membership changes
  // PHASE 18.7: DISABLED API POLLING - Firestore real-time listeners handle membership detection
  // The listenToUserGroups listener in GroupPlannerContext automatically detects:
  // - Group deletions (group disappears from user's groups)
  // - Member removals (membership doc is deleted, triggering listener update)
  // No need for redundant API polling every 15s that was causing 24+ GET /user/groups calls
  //
  // If you need to re-enable polling for some reason, use:
  // groupMembershipMonitor.startMonitoring(..., 300000) // 5 min interval minimum
  useEffect(() => {
    // Membership changes are now detected by Firestore listeners:
    // 1. GroupPlannerContext.listenToUserGroups - detects when user's group list changes
    // 2. ExpenseManager.listenToGroupMembers - detects member changes within active group
    console.log('📡 Group membership monitoring handled by Firestore real-time listeners (no API polling)');
  }, [isAuthenticated, currentUser]);

  // PHASE 2: Removed redundant settlement reload on expense changes
  // 🚀 PHASE 16: Settlements now come from mega-bootstrap
  // Settlements are reloaded only when:
  // 1. Group changes (mega-bootstrap handles it)
  // 2. Settlement is created (handleSettlementSuccess triggers refetch)
  // 3. Balance update is requested (handleBalanceUpdate)

  // 🚀 PHASE 16: Update settlementHistory from mega-bootstrap data
  useEffect(() => {
    if (activeGroupSettlements && activeGroupSettlements.length > 0) {
      console.log('📊 Using settlements from mega-bootstrap:', activeGroupSettlements.length);
      setSettlementHistory(activeGroupSettlements);
    }
  }, [activeGroupSettlements]);

  // Load settlement history (fallback - only used when mega-bootstrap not available)
  const loadSettlements = async (groupId) => {
    if (!groupId) return;
    
    // 🚀 PHASE 16: Skip if already have settlements from mega-bootstrap
    if (activeGroupSettlements && activeGroupSettlements.length > 0) {
      console.log('📊 Skipping loadSettlements - data already from mega-bootstrap');
      return;
    }
    
    try {
      console.log('📊 Fallback: Loading settlements via separate API call');
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
    
    // 🔥 PHASE 17 CRITICAL: Start cooldown BEFORE mutation
    // Firestore listeners fire when server writes, BEFORE mutateAsync resolves
    startMutationCooldown();
    
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
      // BUG FIX: Don't show transactions if no group is selected
      // This prevents stale data from showing via keepPreviousData
      if (!state.activeGroupId) {
        return [];
      }
      // Use API data directly (no more optimistic updates)
      transactions = activeGroupExpenses || [];
    }
    
    return transactions;
  };
  
  // Get current balances from API
  const getCurrentBalances = () => {
    if (state.mode === 'personal') return null;
    
    // Return activeGroupBalances - keepPreviousData keeps old data during refetch
    // Only return null if we truly have no group selected
    if (!state.activeGroupId) return null;
    
    // Handle balance data from API
    let balances = activeGroupBalances || [];
    
    // If balances is an object (not array), try to extract array
    if (!Array.isArray(balances) && typeof balances === 'object') {
      // Check for empty object
      if (Object.keys(balances).length === 0) {
        console.log('📊 Empty balances object, returning empty array');
        return [];
      }
      
      console.log('🔧 Converting balance object to array:', balances);
      
      // Check if it has member_balances property
      if (balances.member_balances && Array.isArray(balances.member_balances)) {
        return balances.member_balances;
      }
      
      // If member_balances is an object (dict), convert to array
      if (balances.member_balances && typeof balances.member_balances === 'object') {
        const memberBalancesDict = balances.member_balances;
        const converted = Object.entries(memberBalancesDict).map(([userId, balance]) => ({
          user_id: userId,
          balance: parseFloat(balance) || 0,
          net_balance: parseFloat(balance) || 0,
          username: userId // Will be enriched by backend
        }));
        console.log('✅ Converted member_balances dict to array:', converted.length, 'members');
        return converted;
      }
      
      // Handle direct dict format {user_id: balance_value} (e.g., from cache or optimistic update response)
      const firstValue = Object.values(balances)[0];
      if (typeof firstValue === 'number' || typeof firstValue === 'string') {
        const converted = Object.entries(balances).map(([userId, balance]) => ({
          user_id: userId,
          balance: parseFloat(balance) || 0,
          net_balance: parseFloat(balance) || 0
        }));
        console.log('✅ Converted direct dict to array:', converted.length, 'members');
        return converted;
      }
      
      console.warn('⚠️ Unknown balance structure, returning empty array:', balances);
      return [];
    }
    
    // If it's already an array, return it
    if (Array.isArray(balances)) {
      return balances;
    }
    
    console.error('❌ balances is neither array nor object:', typeof balances, balances);
    return [];
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
      console.log('💾 handleSaveTransaction called:', { 
        mode: state.mode, 
        editing: !!state.editingTransactionId,
        data: transactionData 
      });

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
          
          // 🔥 PHASE 17 CRITICAL: Start cooldown BEFORE mutation
          // Firestore listeners fire when server writes, BEFORE mutateAsync resolves
          startMutationCooldown();
          
          // Update expense - mutation handles cache refresh
          try {
            const startTime = performance.now();
            
            // Backend update - mutation's onSuccess will update cache with server data
            await updateExpenseMutation.mutateAsync({
              expenseId: state.editingTransactionId,
              data: expensePayload
            });
            
            console.log(`✅ Update completed in ${(performance.now() - startTime).toFixed(0)}ms`);
            
            showToast('Transaction updated!', 'success');
          } catch (error) {
            console.error('❌ Update failed:', error);
            showToast(`Failed: ${error.message}`, 'error');
          }
          
          return;
        } else {
          // CREATE - Simple flow: create expense, mutation handles cache refresh
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

          console.log('📤 Creating expense...');
          
          // Close modal immediately for snappy UX
          setShowTransactionModal(false);
          setState(prev => ({ ...prev, editingTransactionId: null }));
          
          // Show loading toast
          showToast('Creating transaction...', 'info');
          
          // 🔥 PHASE 17 CRITICAL: Start cooldown BEFORE mutation
          // Firestore listeners fire when server writes, BEFORE mutateAsync resolves
          // Cooldown must be active by then to prevent cache invalidation
          startMutationCooldown();
          
          try {
            const startTime = performance.now();
            
            // Create expense - mutation's onSuccess will update cache with server data
            await createExpenseMutation.mutateAsync(expensePayload);
            
            console.log(`✅ Expense created and data refreshed in ${(performance.now() - startTime).toFixed(0)}ms`);
            
            showToast('Transaction created!', 'success');
          } catch (error) {
            console.error('❌ Expense creation FAILED:', error);
            
            // Show detailed error to user
            const errorMessage = error.response?.data?.error 
              || error.message 
              || 'Unknown error occurred';
            
            showToast(`Failed to create expense: ${errorMessage}`, 'error');
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
      
      console.log('🗑️ DELETING EXPENSE - ID:', id, 'Group:', state.activeGroupId);
      
      showToast('Deleting transaction...', 'info');
      
      // 🔥 PHASE 17.9 CRITICAL: Start cooldown BEFORE mutation
      // Prevents Firestore listeners from overwriting optimistic updates and balance_deltas
      startMutationCooldown();
      
      // Delete and reload
      const startTime = performance.now();
      
      // Use React Query mutation for deletion with groupId for optimistic update
      await deleteExpenseMutation.mutateAsync({
        expenseId: id,
        groupId: state.activeGroupId
      });
      console.log(`✅ Backend delete confirmed in ${(performance.now() - startTime).toFixed(0)}ms`);
      
      // Clear stale optimistic state
      setOptimisticExpenses([]);
      setOptimisticBalances(null);
      
      console.log(`✅ Expense deleted in ${(performance.now() - startTime).toFixed(0)}ms total`);
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
      // CRITICAL FIX Phase 17.9: Unsubscribe from ALL Firestore listeners for this group FIRST
      // This prevents "permission denied" errors after deletion
      console.log('🧹 Cleaning up ALL Firestore listeners before group deletion...');
      
      // 1. Cleanup expense-related listeners (expenses, settlements, balances, members, invitations)
      // Pass true as second arg to mark group as "being deleted" - suppresses permission errors
      const expenseListenerCount = expenseFirestoreListener.unsubscribeFromGroup(groupId, true);
      console.log(`   Cleaned up ${expenseListenerCount} expense listeners`);
      
      // 2. Cleanup group planner listeners
      firestoreListenerService.stopListeningToGroup(groupId, true);
      console.log('   Cleaned up group planner listeners');
      
      // Phase 17.9: Small delay to ensure all listeners are properly unsubscribed
      // before we modify Firestore (prevents race conditions)
      await new Promise(resolve => setTimeout(resolve, 100));
      
      console.log('✅ All listeners cleaned up for group:', groupId);
      
      // Clear active group BEFORE deletion
      const wasActive = state.activeGroupId === groupId;
      if (wasActive) {
        setState(prev => ({ ...prev, activeGroupId: null, mode: 'personal' }));
        setOptimisticExpenses([]);
        setOptimisticBalances(null);
      }
      
      // PHASE 18.8 FIX: Use Expense Engine API for deletion (not Group Planner!)
      // Groups are stored in expense_groups collection, so use expenseApi.deleteGroup
      console.log('⚡ Deleting group via Expense Engine API...');
      
      // PHASE 18.9 FIX: Optimistic update BEFORE API call to prevent "two-click" issue
      // Remove the group from cache immediately so it doesn't reappear
      // Note: queryKeys.groups stores { success: true, groups: [...] }, not direct array
      queryClient.setQueryData(queryKeys.groups, (oldData) => {
        if (!oldData?.groups) return oldData;
        return {
          ...oldData,
          groups: oldData.groups.filter(g => (g.id || g.group_id) !== groupId)
        };
      });
      
      // Also update mega-bootstrap cache to remove the group
      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), null);
      
      // Remove from dashboard mega-bootstrap (groups list)
      queryClient.setQueryData(queryKeys.megaBootstrap(null), (old) => {
        if (!old?.data?.groups) return old;
        return {
          ...old,
          data: {
            ...old.data,
            groups: old.data.groups.filter(g => (g.id || g.group_id) !== groupId)
          }
        };
      });
      
      try {
        // Call the Expense Engine delete endpoint
        await expenseApi.deleteGroup(groupId);
        
        // Clean up any remaining cached queries for this group
        queryClient.removeQueries({ queryKey: queryKeys.group(groupId) });
        
        showToast('Group deleted successfully!', 'success');
      } catch (deleteError) {
        // If API fails, restore the group to cache (rollback optimistic update)
        console.error('❌ Delete API failed, rolling back optimistic update');
        queryClient.invalidateQueries({ queryKey: queryKeys.groups });
        throw deleteError;
      }
      
    } catch (error) {
      console.error('❌ Delete failed:', error);
      showToast(`Failed to delete: ${error.message}`, 'error');
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
    <ErrorBoundary 
      onRetry={handleRefresh}
      onGoHome={() => navigate('/')}
      onError={(error, errorInfo) => {
        console.error('🚨 ExpenseManager Error:', error);
        // Could send to error tracking service here
      }}
    >
    {/* 🚀 PHASE 17 Week 5: Offline indicator */}
    <OfflineIndicator isOnline={isOnline} />
    
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
      {/* Phase 17: Pass invitations from mega-bootstrap to avoid duplicate API calls */}
      <PendingInvitations 
        invitationsFromParent={megaInvitations}
        onRefreshInvitations={() => {
          console.log('🔄 Phase 17: Refreshing mega-bootstrap for invitations');
          queryClient.invalidateQueries({ queryKey: queryKeys.megaBootstrap(state.activeGroupId) });
        }}
        onInvitationAccepted={async () => {
          console.log('🎉 Invitation accepted! Reloading groups...');
          
          // Invalidate queries - groups will auto-update via Firestore listener
          queryClient.invalidateQueries({ queryKey: queryKeys.groups });
          queryClient.invalidateQueries({ queryKey: queryKeys.megaBootstrap(state.activeGroupId) });
          
          // Wait briefly for Firestore listener to update groups
          await new Promise(resolve => setTimeout(resolve, 500));
          
          // Groups are already available from context (Firestore real-time listener)
          console.log('✅ Groups available from context:', groups);
          
          // Switch to group mode and select the first group (the one just joined)
          if (groups && groups.length > 0) {
            const newGroup = groups[0]; // Most recent group
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
            loading={groupsLoading || megaLoading}
            onGroupChange={handleGroupChange}
            onGroupCreate={createGroup}
            onGroupDelete={handleDeleteGroup}
            onMemberAdd={async () => await reloadActiveGroup()}
            onMemberRemove={async () => await reloadActiveGroup()}
            showAlert={showAlert}
            currentUser={currentUser}
            pendingInvitationsFromParent={megaData?.data?.active_group?.invitations}
            onRefreshInvitations={() => refetchMega()}
            usingMegaBootstrap={!!megaData || megaLoading}  // 🚀 PHASE 16: Tell GroupManager we're using mega-bootstrap
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
        // Filter out deleted expenses from calculations (all transactions are expenses in group mode)
        const activeExpenses = transactions.filter(t => !t.is_deleted);
        const totalAmount = activeExpenses.reduce((sum, t) => sum + (t.amount || 0), 0);
        const expenseCount = activeExpenses.length;
        
        // Calculate remaining balance
        const balances = getCurrentBalances() || [];
        const totalSettled = settlementHistory.reduce((sum, s) => sum + (s.amount || 0), 0);
        
        // CRITICAL FIX: Ensure balances is an array before calling filter()
        let currentOwed = 0;
        if (Array.isArray(balances)) {
          // Sum of all absolute balances / 2 (because each debt has a payer and receiver)
          currentOwed = balances
            .filter(b => Math.abs(b.net_balance || 0) > 0.01)
            .reduce((sum, b) => sum + Math.abs(b.net_balance || 0), 0) / 2;
        } else {
          console.error('❌ balances is not an array in GroupSummaryCards:', typeof balances, balances);
        }
        
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
          key={`${state.activeGroupId}-${getCurrentBalances()?.length || 0}-${getCurrentTransactions()?.length || 0}`}
          group={activeGroupData} 
          balances={getCurrentBalances() || []}
          members={activeGroupMembers || []}
          allMembersMap={allMembersMap}
          onBalanceUpdate={handleBalanceUpdate}
          settlementHistory={settlementHistory}
          loadingSettlements={false}
          onSettlementSuccess={handleSettlementSuccess}
          totalExpenses={
            getCurrentTransactions()?.filter(t => !t.is_deleted).length || 0
          }
          totalExpensesAmount={
            getCurrentTransactions()
              ?.filter(t => !t.is_deleted)
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
        allMembersMap={allMembersMap}
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
    </ErrorBoundary>
  );
};

export default ExpenseManager;
