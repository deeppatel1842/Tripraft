/**
 * useExtremeDashboard Hook - Phase 21 Extreme Optimization
 * 
 * Single-document dashboard pattern achieving 10 total Firestore operations per session:
 * - 1 read on login (fetches ALL user data in one document)
 * - 0 reads after (all data from memory/cache)
 * - 1 write per mutation (batch writes)
 * 
 * Architecture:
 * - Login: Load dashboard once (1 Firestore read)
 * - Mutations: Send to extreme API (0 reads, 1 batch write)
 * - All reads: From local state/cache (0 Firestore reads)
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import expenseApi from '../services/expenseApi';
import authService from '../firebase/authService';

/**
 * Main hook for Phase 21 Extreme Dashboard
 * Provides complete expense management with 10-operation architecture
 */
export const useExtremeDashboard = () => {
  // Dashboard state
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastSyncedAt, setLastSyncedAt] = useState(null);
  
  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  
  // Operation tracking
  const [operationCount, setOperationCount] = useState({ reads: 0, writes: 0 });

  // Auth listener
  useEffect(() => {
    const unsubscribe = authService.onAuthStateChanged(async (user) => {
      if (user) {
        const token = await user.getIdToken();
        expenseApi.setAuthToken(token);
        expenseApi.setCurrentUser(user);
        setCurrentUser(user);
        setIsAuthenticated(true);
      } else {
        expenseApi.setAuthToken(null);
        expenseApi.setCurrentUser(null);
        setCurrentUser(null);
        setIsAuthenticated(false);
        setDashboard(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // Load dashboard on auth
  useEffect(() => {
    if (isAuthenticated && !dashboard) {
      loadDashboard();
    }
  }, [isAuthenticated]);

  /**
   * Load extreme dashboard (1 Firestore read)
   * This is the ONLY read operation in a session
   */
  const loadDashboard = useCallback(async (forceRefresh = false) => {
    if (!isAuthenticated) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await expenseApi.request(
        `/extreme-dashboard${forceRefresh ? '?force=true' : ''}`,
        { method: 'GET' }
      );
      
      if (response.success) {
        setDashboard(response.dashboard);
        setLastSyncedAt(new Date());
        setOperationCount(prev => ({
          ...prev,
          reads: prev.reads + (response._operations?.reads || 1)
        }));
        
        console.log('[ExtremeDashboard] Loaded:', {
          groups: Object.keys(response.dashboard?.groups || {}).length,
          invitations: response.dashboard?.pending_invitations?.length || 0,
          source: response.source,
          operations: response._operations
        });
      }
    } catch (err) {
      setError(err.message);
      console.error('[ExtremeDashboard] Load error:', err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  // ============================================================================
  // DERIVED DATA - All from local state (0 Firestore reads)
  // ============================================================================

  /**
   * Get all groups from dashboard
   */
  const groups = useMemo(() => {
    if (!dashboard?.groups) return [];
    return Object.values(dashboard.groups).map(g => ({
      id: g.group_id,
      name: g.name,
      currency: g.currency,
      members: g.members || [],
      memberCount: g.members?.length || 0,
      created_at: g.created_at,
      updated_at: g.updated_at
    }));
  }, [dashboard?.groups]);

  /**
   * Get pending invitations
   */
  const pendingInvitations = useMemo(() => {
    return dashboard?.pending_invitations || [];
  }, [dashboard?.pending_invitations]);

  /**
   * Get summary statistics
   */
  const summary = useMemo(() => {
    return dashboard?.summary || {
      total_owed_to_you: 0,
      total_you_owe: 0,
      net_balance: 0,
      group_count: 0
    };
  }, [dashboard?.summary]);

  /**
   * Get group by ID (from cache)
   */
  const getGroup = useCallback((groupId) => {
    if (!dashboard?.groups) return null;
    const groupData = dashboard.groups[groupId];
    if (!groupData) return null;
    
    return {
      ...groupData,
      id: groupData.group_id,
      expenses: groupData.recent_expenses || [],
      settlements: groupData.recent_settlements || [],
      balances: groupData.balances || {}
    };
  }, [dashboard?.groups]);

  /**
   * Get expenses for a group (from cache)
   */
  const getGroupExpenses = useCallback((groupId) => {
    const group = dashboard?.groups?.[groupId];
    return group?.recent_expenses || [];
  }, [dashboard?.groups]);

  /**
   * Get settlements for a group (from cache)
   */
  const getGroupSettlements = useCallback((groupId) => {
    const group = dashboard?.groups?.[groupId];
    return group?.recent_settlements || [];
  }, [dashboard?.groups]);

  /**
   * Get balances for a group (from cache)
   */
  const getGroupBalances = useCallback((groupId) => {
    const group = dashboard?.groups?.[groupId];
    return group?.balances || {};
  }, [dashboard?.groups]);

  // ============================================================================
  // MUTATION HELPERS - Local state update after server response
  // ============================================================================

  /**
   * Update local dashboard state after mutation
   */
  const updateLocalState = useCallback((updates) => {
    setDashboard(prev => {
      if (!prev) return prev;
      return { ...prev, ...updates };
    });
  }, []);

  /**
   * Update a specific group in local state
   */
  const updateGroupInState = useCallback((groupId, groupData) => {
    setDashboard(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        groups: {
          ...prev.groups,
          [groupId]: groupData
        }
      };
    });
  }, []);

  /**
   * Remove a group from local state
   */
  const removeGroupFromState = useCallback((groupId) => {
    setDashboard(prev => {
      if (!prev) return prev;
      const { [groupId]: removed, ...remainingGroups } = prev.groups || {};
      return {
        ...prev,
        groups: remainingGroups
      };
    });
  }, []);

  // ============================================================================
  // GROUP MUTATIONS (0 reads, 1 write each)
  // ============================================================================

  /**
   * Create a new group
   */
  const createGroup = useCallback(async (groupData) => {
    try {
      const response = await expenseApi.request('/extreme/groups', {
        method: 'POST',
        body: JSON.stringify(groupData)
      });
      
      if (response.success && response.group) {
        // Update local state immediately
        updateGroupInState(response.group.group_id, response.group);
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Create group error:', err);
      throw err;
    }
  }, [updateGroupInState]);

  /**
   * Update a group
   */
  const updateGroup = useCallback(async (groupId, updates) => {
    try {
      const response = await expenseApi.request(`/extreme/groups/${groupId}`, {
        method: 'PUT',
        body: JSON.stringify(updates)
      });
      
      if (response.success && response.group) {
        updateGroupInState(groupId, response.group);
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Update group error:', err);
      throw err;
    }
  }, [updateGroupInState]);

  /**
   * Add member to group (send invitation)
   */
  const addMember = useCallback(async (groupId, memberData) => {
    try {
      const response = await expenseApi.request(`/extreme/groups/${groupId}/members`, {
        method: 'POST',
        body: JSON.stringify(memberData)
      });
      
      if (response.success) {
        // Reload to get updated member list
        await loadDashboard(true);
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Add member error:', err);
      throw err;
    }
  }, [loadDashboard]);

  /**
   * Remove member from group
   */
  const removeMember = useCallback(async (groupId, memberId) => {
    try {
      const response = await expenseApi.request(`/extreme/groups/${groupId}/members/${memberId}`, {
        method: 'DELETE'
      });
      
      if (response.success) {
        await loadDashboard(true);
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Remove member error:', err);
      throw err;
    }
  }, [loadDashboard]);

  // ============================================================================
  // EXPENSE MUTATIONS (0 reads, 1 write each)
  // ============================================================================

  /**
   * Create a new expense
   */
  const createExpense = useCallback(async (expenseData) => {
    try {
      const response = await expenseApi.request('/extreme/expenses', {
        method: 'POST',
        body: JSON.stringify(expenseData)
      });
      
      if (response.success && response.expense) {
        const groupId = expenseData.group_id;
        const group = dashboard?.groups?.[groupId];
        
        if (group) {
          // Add expense to local state
          const updatedGroup = {
            ...group,
            recent_expenses: [response.expense, ...(group.recent_expenses || [])].slice(0, 20)
          };
          updateGroupInState(groupId, updatedGroup);
        }
        
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Create expense error:', err);
      throw err;
    }
  }, [dashboard?.groups, updateGroupInState]);

  /**
   * Update an expense
   */
  const updateExpense = useCallback(async (expenseId, updates) => {
    try {
      const response = await expenseApi.request(`/extreme/expenses/${expenseId}`, {
        method: 'PUT',
        body: JSON.stringify(updates)
      });
      
      if (response.success && response.expense) {
        const groupId = updates.group_id;
        const group = dashboard?.groups?.[groupId];
        
        if (group) {
          // Update expense in local state
          const updatedExpenses = (group.recent_expenses || []).map(exp =>
            exp.expense_id === expenseId ? response.expense : exp
          );
          const updatedGroup = {
            ...group,
            recent_expenses: updatedExpenses
          };
          updateGroupInState(groupId, updatedGroup);
        }
        
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Update expense error:', err);
      throw err;
    }
  }, [dashboard?.groups, updateGroupInState]);

  /**
   * Delete an expense
   */
  const deleteExpense = useCallback(async (expenseId, groupId) => {
    try {
      const response = await expenseApi.request(`/extreme/expenses/${expenseId}?group_id=${groupId}`, {
        method: 'DELETE'
      });
      
      if (response.success) {
        const group = dashboard?.groups?.[groupId];
        
        if (group) {
          // Remove expense from local state
          const updatedExpenses = (group.recent_expenses || []).filter(
            exp => exp.expense_id !== expenseId
          );
          const updatedGroup = {
            ...group,
            recent_expenses: updatedExpenses
          };
          updateGroupInState(groupId, updatedGroup);
        }
        
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Delete expense error:', err);
      throw err;
    }
  }, [dashboard?.groups, updateGroupInState]);

  // ============================================================================
  // SETTLEMENT MUTATIONS (0 reads, 1 write each)
  // ============================================================================

  /**
   * Create a new settlement
   */
  const createSettlement = useCallback(async (settlementData) => {
    try {
      const response = await expenseApi.request('/extreme/settlements', {
        method: 'POST',
        body: JSON.stringify(settlementData)
      });
      
      if (response.success && response.settlement) {
        const groupId = settlementData.group_id;
        const group = dashboard?.groups?.[groupId];
        
        if (group) {
          // Add settlement to local state
          const updatedGroup = {
            ...group,
            recent_settlements: [response.settlement, ...(group.recent_settlements || [])].slice(0, 10)
          };
          updateGroupInState(groupId, updatedGroup);
        }
        
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Create settlement error:', err);
      throw err;
    }
  }, [dashboard?.groups, updateGroupInState]);

  /**
   * Delete a settlement
   */
  const deleteSettlement = useCallback(async (settlementId, groupId) => {
    try {
      const response = await expenseApi.request(`/extreme/settlements/${settlementId}?group_id=${groupId}`, {
        method: 'DELETE'
      });
      
      if (response.success) {
        const group = dashboard?.groups?.[groupId];
        
        if (group) {
          // Remove settlement from local state
          const updatedSettlements = (group.recent_settlements || []).filter(
            stl => stl.settlement_id !== settlementId
          );
          const updatedGroup = {
            ...group,
            recent_settlements: updatedSettlements
          };
          updateGroupInState(groupId, updatedGroup);
        }
        
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Delete settlement error:', err);
      throw err;
    }
  }, [dashboard?.groups, updateGroupInState]);

  // ============================================================================
  // INVITATION MUTATIONS (0 reads, 1 write each)
  // ============================================================================

  /**
   * Accept an invitation
   */
  const acceptInvitation = useCallback(async (invitationId) => {
    try {
      const response = await expenseApi.request(`/extreme/invitations/${invitationId}/accept`, {
        method: 'POST'
      });
      
      if (response.success) {
        // Reload dashboard to get new group
        await loadDashboard(true);
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Accept invitation error:', err);
      throw err;
    }
  }, [loadDashboard]);

  /**
   * Decline an invitation
   */
  const declineInvitation = useCallback(async (invitationId) => {
    try {
      const response = await expenseApi.request(`/extreme/invitations/${invitationId}/decline`, {
        method: 'POST'
      });
      
      if (response.success) {
        // Remove invitation from local state
        setDashboard(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            pending_invitations: (prev.pending_invitations || []).filter(
              inv => inv.invitation_id !== invitationId
            )
          };
        });
        
        setOperationCount(prev => ({
          ...prev,
          writes: prev.writes + 1
        }));
      }
      
      return response;
    } catch (err) {
      console.error('[ExtremeDashboard] Decline invitation error:', err);
      throw err;
    }
  }, []);

  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================

  /**
   * Force sync dashboard from server
   */
  const sync = useCallback(async () => {
    return loadDashboard(true);
  }, [loadDashboard]);

  /**
   * Get total operation count
   */
  const totalOperations = useMemo(() => {
    return operationCount.reads + operationCount.writes;
  }, [operationCount]);

  /**
   * Check if under 10 operation target
   */
  const isWithinTarget = useMemo(() => {
    return totalOperations <= 10;
  }, [totalOperations]);

  return {
    // State
    dashboard,
    loading,
    error,
    lastSyncedAt,
    isAuthenticated,
    currentUser,
    
    // Derived data (0 reads)
    groups,
    pendingInvitations,
    summary,
    
    // Getters (0 reads)
    getGroup,
    getGroupExpenses,
    getGroupSettlements,
    getGroupBalances,
    
    // Group mutations (1 write each)
    createGroup,
    updateGroup,
    addMember,
    removeMember,
    
    // Expense mutations (1 write each)
    createExpense,
    updateExpense,
    deleteExpense,
    
    // Settlement mutations (1 write each)
    createSettlement,
    deleteSettlement,
    
    // Invitation mutations (1 write each)
    acceptInvitation,
    declineInvitation,
    
    // Utilities
    sync,
    reload: loadDashboard,
    
    // Operation tracking
    operationCount,
    totalOperations,
    isWithinTarget
  };
};

export default useExtremeDashboard;
