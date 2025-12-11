import { useQuery, useMutation, useQueryClient, keepPreviousData, useInfiniteQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useState, useRef } from 'react';
import expenseApi from '../services/expenseApi';

// Query keys for cache management
export const queryKeys = {
  user: ['user'],
  groups: ['groups'],
  group: (groupId) => ['group', groupId],
  expenses: (groupId) => ['expenses', groupId],
  expensesInfinite: (groupId) => ['expenses', groupId, 'infinite'],
  settlements: (groupId) => ['settlements', groupId],
  invitations: ['invitations'],
  megaBootstrap: (groupId) => ['mega-bootstrap', groupId || 'dashboard'],
  recentHistory: (groupId) => ['recent-history', groupId],
  // Phase 19.1: Individual expense history (for edit history modal)
  expenseEditHistory: (expenseId) => ['expense-edit-history', expenseId],
};

// =============================================================================
// PHASE 17: Balance Delta Helpers
// =============================================================================

/**
 * Apply balance_deltas from backend response to existing balances array.
 * Phase 17: Backend now returns deltas instead of full balances for efficiency.
 * 
 * @param {Array} existingBalances - Current balances array [{user_id, balance, ...}]
 * @param {Object} deltas - Balance deltas from backend {user_id: delta_value}
 * @returns {Array} - Updated balances array
 */
function applyBalanceDeltas(existingBalances, deltas) {
  if (!existingBalances || !deltas) return existingBalances;
  
  return existingBalances.map(b => {
    const delta = deltas[b.user_id];
    if (delta !== undefined && delta !== null) {
      const newBalance = (parseFloat(b.balance) || 0) + parseFloat(delta);
      return {
        ...b,
        balance: newBalance,
        net_balance: newBalance
      };
    }
    return b;
  });
}

/**
 * Add a history entry to the recent_history array in cache.
 * Phase 17: Backend returns history_entry with mutations for instant UI update.
 * 
 * @param {Array} existingHistory - Current history array
 * @param {Object} historyEntry - New history entry from backend
 * @param {number} maxItems - Maximum items to keep (default 50)
 * @returns {Array} - Updated history array
 */
function addHistoryEntry(existingHistory, historyEntry, maxItems = 50) {
  if (!historyEntry) return existingHistory;
  if (!existingHistory) return [historyEntry];
  
  // Add at beginning, remove duplicates, limit size
  const filtered = existingHistory.filter(h => h.id !== historyEntry.id);
  return [historyEntry, ...filtered].slice(0, maxItems);
}

/**
 * 🚀 PHASE 17 Week 5: Background Sync Hook
 * 
 * Provides intelligent background polling with exponential backoff.
 * Syncs data in the background without blocking the UI.
 * 
 * Features:
 * - Exponential backoff on failures (30s -> 60s -> 120s -> max 5min)
 * - Pauses when tab is hidden (visibility API)
 * - Resumes immediately when tab becomes visible
 * - Tracks online/offline status
 * 
 * @param {string} groupId - Active group ID to sync
 * @param {Object} options - Configuration options
 * @param {boolean} options.enabled - Enable/disable sync (default: true)
 * @param {number} options.baseInterval - Base polling interval in ms (default: 60000)
 * @param {number} options.maxInterval - Maximum polling interval in ms (default: 300000)
 */
export function useBackgroundSync(groupId, options = {}) {
  const queryClient = useQueryClient();
  const [failureCount, setFailureCount] = useState(0);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isVisible, setIsVisible] = useState(!document.hidden);
  const intervalRef = useRef(null);
  
  const {
    enabled = true,
    baseInterval = 60000, // 1 minute
    maxInterval = 300000, // 5 minutes
  } = options;
  
  // Calculate current interval with exponential backoff
  const currentInterval = Math.min(
    baseInterval * Math.pow(2, failureCount),
    maxInterval
  );
  
  // Background sync function
  const sync = useCallback(async () => {
    if (!enabled || !isOnline || !isVisible) {
      console.log('⏸️ Background sync skipped:', { enabled, isOnline, isVisible });
      return;
    }
    
    try {
      console.log(`🔄 Background sync (interval: ${currentInterval / 1000}s)`);
      
      // Invalidate and refetch mega-bootstrap
      await queryClient.invalidateQueries({
        queryKey: queryKeys.megaBootstrap(groupId),
        refetchType: 'active'
      });
      
      // Reset failure count on success
      setFailureCount(0);
      console.log('✅ Background sync complete');
    } catch (error) {
      console.error('❌ Background sync failed:', error);
      setFailureCount(prev => prev + 1);
    }
  }, [enabled, isOnline, isVisible, groupId, currentInterval, queryClient]);
  
  // Track online/offline status
  useEffect(() => {
    const handleOnline = () => {
      console.log('🌐 Back online - resuming sync');
      setIsOnline(true);
      setFailureCount(0); // Reset backoff
      sync(); // Immediate sync when back online
    };
    
    const handleOffline = () => {
      console.log('📴 Gone offline - pausing sync');
      setIsOnline(false);
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [sync]);
  
  // Track visibility changes
  useEffect(() => {
    const handleVisibilityChange = () => {
      const visible = !document.hidden;
      setIsVisible(visible);
      
      if (visible) {
        console.log('👁️ Tab visible - resuming sync');
        sync(); // Immediate sync when tab becomes visible
      } else {
        console.log('😴 Tab hidden - pausing sync');
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [sync]);
  
  // Set up polling interval
  useEffect(() => {
    if (!enabled || !isOnline || !isVisible) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }
    
    intervalRef.current = setInterval(sync, currentInterval);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [enabled, isOnline, isVisible, currentInterval, sync]);
  
  return {
    isOnline,
    isVisible,
    failureCount,
    currentInterval,
    forceSync: sync,
  };
}

/**
 * Hook for fetching user data
 */
export function useUserQuery() {
  return useQuery({
    queryKey: queryKeys.user,
    queryFn: () => expenseApi.getUserData(),
    staleTime: 10 * 60 * 1000, // 10 minutes - user data changes rarely
  });
}

/**
 * Hook for fetching all groups
 * 
 * 🚀 PHASE 17.5: Smart query that SKIPS API when mega-bootstrap has hydrated cache
 * - Uses stale cache from mega-bootstrap to avoid duplicate API calls
 * - Only fetches from API if cache is empty (initial load fallback)
 * - refetchOnWindowFocus: false = mega-bootstrap handles refresh
 * 
 * DATA FLOW:
 * 1. mega-bootstrap fetches groups → hydrates queryKeys.groups cache
 * 2. useGroupsQuery reads from cache → NO API call
 * 3. Firestore listeners update cache directly → NO API call
 */
export function useGroupsQuery() {
  const queryClient = useQueryClient();
  
  // Phase 17.5: Check if groups already exist in cache (from mega-bootstrap)
  const cachedGroups = queryClient.getQueryData(queryKeys.groups);
  const hasCachedData = cachedGroups?.groups?.length >= 0;
  
  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: () => {
      console.log('📥 useGroupsQuery: Fetching groups from API (cache miss)');
      return expenseApi.getUserGroups(1, 20);
    },
    // Phase 18.1: Aggressive caching to reduce API calls
    staleTime: 10 * 60 * 1000, // 10 minutes - data stays fresh longer
    gcTime: 30 * 60 * 1000, // 30 minutes retention
    refetchOnWindowFocus: false, // NEVER refetch on window focus
    refetchOnMount: false, // NEVER refetch on mount - mega-bootstrap hydrates cache
    refetchOnReconnect: false, // NEVER refetch on reconnect
    refetchInterval: false, // No polling - Firestore handles real-time
    placeholderData: keepPreviousData,
    // Phase 18.2: Only enable if no cache exists (first load only)
    enabled: !hasCachedData,
  });
}

/**
 * Hook for fetching a single group with full details
 * 
 * 🚀 PHASE 17.5: FALLBACK ONLY - Do not use when mega-bootstrap is active
 * - mega-bootstrap hydrates queryKeys.group(groupId) cache directly
 * - This hook ONLY fetches from API if cache is empty (fallback mode)
 * - In normal operation, cache is always populated by mega-bootstrap
 * 
 * USAGE: Only enabled when mega-bootstrap fails or is disabled
 */
export function useGroupQuery(groupId, options = {}) {
  const queryClient = useQueryClient();
  
  // Phase 17.5: Check if group already exists in cache (from mega-bootstrap)
  const cachedGroup = queryClient.getQueryData(queryKeys.group(groupId));
  const hasCachedData = !!cachedGroup;
  
  return useQuery({
    queryKey: queryKeys.group(groupId),
    queryFn: async () => {
      console.log('📥 useGroupQuery: Fetching group from API (cache miss, groupId:', groupId, ')');
      const result = await expenseApi.getGroupFull(groupId, false);
      console.log('📥 Fetched group data:', result?.balances?.length || 0, 'balances');
      return result;
    },
    enabled: !!groupId && (options.enabled !== false), // Only run if groupId exists
    staleTime: 5 * 60 * 1000, // 5 minutes - mega-bootstrap keeps it fresh
    gcTime: 5 * 60 * 1000, // 5 minutes - keep data in cache
    refetchOnMount: hasCachedData ? false : true, // Skip API if cache exists from mega-bootstrap
    refetchOnWindowFocus: false, // mega-bootstrap handles refresh
    placeholderData: keepPreviousData, // Keep previous data during refetch to prevent flicker
    retry: 2, // Retry failed requests twice
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000), // Exponential backoff
  });
}

/**
 * 🚀 PHASE 17.5: Prefetch Hook for Adjacent Groups
 * 
 * DISABLED AUTO-PREFETCH: mega-bootstrap already fetches active group
 * - Removed auto-prefetch on mount (was causing duplicate API calls)
 * - Keep hover prefetch for navigation to OTHER groups only
 * - Only prefetches if group is NOT already in cache
 * 
 * @param {Array} groups - Array of group objects with group_id
 * @param {number} prefetchCount - DEPRECATED (no longer used)
 */
export function usePrefetchGroups(groups, prefetchCount = 3) {
  const queryClient = useQueryClient();
  
  // Phase 17.5: REMOVED auto-prefetch - mega-bootstrap handles active group
  // Auto-prefetching multiple groups was causing duplicate API calls
  
  // Return hover handler for remaining groups (only when navigating to different group)
  const prefetchOnHover = useCallback((groupId) => {
    if (!groupId) return;
    
    // Don't prefetch if already in cache (from mega-bootstrap or previous load)
    const cached = queryClient.getQueryData(queryKeys.group(groupId));
    if (cached) {
      console.log(`✅ Group ${groupId} already in cache, skipping prefetch`);
      return;
    }
    
    console.log(`🔮 Prefetching group ${groupId} on hover (not in cache)`);
    queryClient.prefetchQuery({
      queryKey: queryKeys.group(groupId),
      queryFn: () => expenseApi.getGroupFull(groupId, false),
      staleTime: 5 * 60 * 1000, // Keep prefetched data fresh for 5 minutes
    });
  }, [queryClient]);
  
  return { prefetchOnHover };
}

/**
 * Hook for fetching expenses for a group
 */
export function useExpensesQuery(groupId) {
  return useQuery({
    queryKey: queryKeys.expenses(groupId),
    queryFn: () => expenseApi.getGroupExpenses(groupId),
    enabled: !!groupId,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

/**
 * 🚀 PHASE 17 Week 3: Infinite Scroll for Expenses
 * 
 * Loads expenses in pages of 10 for faster initial load.
 * Use fetchNextPage() to load more expenses on scroll.
 * 
 * @param {string} groupId - The group ID to fetch expenses for
 * @param {number} pageSize - Number of expenses per page (default: 10)
 */
export function useInfiniteExpensesQuery(groupId, pageSize = 10) {
  return useInfiniteQuery({
    queryKey: queryKeys.expensesInfinite(groupId),
    queryFn: async ({ pageParam = 0 }) => {
      console.log(`📜 Loading expenses page: offset=${pageParam}, limit=${pageSize}`);
      const result = await expenseApi.getGroupExpenses(groupId, {
        limit: pageSize,
        offset: pageParam,
      });
      return {
        expenses: result?.expenses || [],
        has_more: result?.has_more || (result?.expenses?.length === pageSize),
        offset: pageParam,
      };
    },
    getNextPageParam: (lastPage, allPages) => {
      if (lastPage.has_more) {
        return allPages.reduce((acc, page) => acc + page.expenses.length, 0);
      }
      return undefined; // No more pages
    },
    initialPageParam: 0,
    enabled: !!groupId,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

/**
 * Hook for fetching settlements for a group
 */
export function useSettlementsQuery(groupId) {
  return useQuery({
    queryKey: queryKeys.settlements(groupId),
    queryFn: () => expenseApi.getSettlements(groupId),
    enabled: !!groupId,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

/**
 * 🚀 PHASE 16: MEGA BOOTSTRAP HOOK
 * 
 * Replaces 4-5 parallel API calls with a single call:
 * - GET /user/groups
 * - GET /groups/{id}/full  
 * - GET /settlements/group/{id}
 * - GET /invitations/group/{id}
 * - GET /invitations/user
 * 
 * Benefits:
 * - Reduces API calls from 5 to 1
 * - Reduces Firestore ops from ~20 to ~5
 * - Single cache key with smart invalidation
 * - Faster page loads (1 round-trip vs 5)
 * 
 * 🚀 PHASE 21: Uses extreme dashboard when extreme mode is enabled
 * - Only 1 Firestore read per session (from Redis cache thereafter)
 * - All mutations use cache-only (0 reads)
 */
export function useMegaBootstrap(activeGroupId, options = {}) {
  const queryClient = useQueryClient();
  
  return useQuery({
    queryKey: queryKeys.megaBootstrap(activeGroupId),
    queryFn: async () => {
      // Phase 18.3: Double-check cache before fetching (belt and suspenders)
      const existingCache = queryClient.getQueryData(queryKeys.megaBootstrap(activeGroupId));
      if (existingCache?.data && !options.bypassCache) {
        console.log('🔄 MEGA BOOTSTRAP: Using existing cache (skipped fetch)');
        return existingCache;
      }
      
      // Phase 21: Use extreme dashboard when extreme mode is enabled
      if (expenseApi.extremeMode) {
        console.log('🚀 EXTREME DASHBOARD: Fetching all data in ONE read');
        const extremeResult = await expenseApi.getExtremeDashboard(options.bypassCache);
        
        // Transform extreme dashboard format to mega-bootstrap format
        const dashboard = extremeResult?.dashboard || {};
        const groups = Object.values(dashboard.groups || {});
        
        // Find active group data if activeGroupId is provided
        let activeGroup = null;
        if (activeGroupId && dashboard.groups?.[activeGroupId]) {
          const groupData = dashboard.groups[activeGroupId];
          activeGroup = {
            group: {
              group_id: activeGroupId,
              ...groupData
            },
            members: groupData.members || [],
            balances: groupData.balances || [],
            expenses: groupData.recent_expenses || [],
            settlements: groupData.recent_settlements || [],
            all_members_map: {}
          };
          
          // Build all_members_map
          (groupData.members || []).forEach(member => {
            activeGroup.all_members_map[member.user_id] = member;
          });
        }
        
        // Format result to match mega-bootstrap structure
        const result = {
          success: true,
          data: {
            groups: groups.map(g => ({
              group_id: g.group_id || g.id,
              name: g.name,
              currency: g.currency,
              member_count: (g.members || []).length,
              total_balance: g.total_balance || 0
            })),
            invitations: dashboard.pending_invitations || [],
            active_group: activeGroup
          },
          meta: {
            fetch_time_ms: 0,
            source: 'extreme_dashboard',
            operations: extremeResult._operations || { reads: 1, writes: 0 }
          }
        };
        
        console.log('📦 Extreme dashboard response:', {
          groups: result?.data?.groups?.length || 0,
          invitations: result?.data?.invitations?.length || 0,
          activeGroup: result?.data?.active_group ? 'loaded' : 'none',
          members: result?.data?.active_group?.members?.length || 0,
          expenses: result?.data?.active_group?.expenses?.length || 0,
          operations: result?.meta?.operations
        });
        
        // Hydrate individual query caches for backward compatibility
        if (result?.data) {
          // Cache groups
          if (result.data.groups) {
            queryClient.setQueryData(queryKeys.groups, {
              success: true,
              groups: result.data.groups
            });
          }
          
          // Cache invitations  
          if (result.data.invitations) {
            queryClient.setQueryData(queryKeys.invitations, {
              success: true,
              invitations: result.data.invitations
            });
          }
          
          // Cache active group data
          if (activeGroupId && result.data.active_group) {
            const groupData = result.data.active_group;
            queryClient.setQueryData(queryKeys.group(activeGroupId), {
              success: true,
              group: groupData.group,
              members: groupData.members,
              balances: groupData.balances,
              expenses: groupData.expenses,
              all_members_map: groupData.all_members_map,
              expenses_pagination: { has_more: false, total: (groupData.expenses || []).length }
            });
            
            // Cache settlements
            if (groupData.settlements) {
              queryClient.setQueryData(queryKeys.settlements(activeGroupId), {
                success: true,
                settlements: groupData.settlements
              });
            }
          }
        }
        
        return result;
      }
      
      // Standard mega-bootstrap path (non-extreme mode)
      console.log('🚀 MEGA BOOTSTRAP: Fetching all data in ONE call');
      const result = await expenseApi.getMegaBootstrap({
        activeGroupId,
        recentExpensesLimit: 20,
        bypassCache: options.bypassCache || false
      });
      
      console.log('📦 Mega bootstrap response:', {
        groups: result?.data?.groups?.length || 0,
        invitations: result?.data?.invitations?.length || 0,
        activeGroup: result?.data?.active_group ? 'loaded' : 'none',
        members: result?.data?.active_group?.members?.length || 0,
        expenses: result?.data?.active_group?.expenses?.length || 0,
        settlements: result?.data?.active_group?.settlements?.length || 0,
        fetchTime: result?.meta?.fetch_time_ms || 0
      });
      
      // Hydrate individual query caches for backward compatibility
      if (result?.data) {
        // Cache groups
        if (result.data.groups) {
          queryClient.setQueryData(queryKeys.groups, {
            success: true,
            groups: result.data.groups
          });
        }
        
        // Cache invitations  
        if (result.data.invitations) {
          queryClient.setQueryData(queryKeys.invitations, {
            success: true,
            invitations: result.data.invitations
          });
        }
        
        // Cache active group data
        if (activeGroupId && result.data.active_group) {
          const groupData = result.data.active_group;
          queryClient.setQueryData(queryKeys.group(activeGroupId), {
            success: true,
            group: groupData.group,
            members: groupData.members,
            balances: groupData.balances,
            expenses: groupData.expenses,
            all_members_map: groupData.all_members_map,
            expenses_pagination: groupData.expenses_pagination
          });
          
          // Cache settlements
          if (groupData.settlements) {
            queryClient.setQueryData(queryKeys.settlements(activeGroupId), {
              success: true,
              settlements: groupData.settlements
            });
          }
        }
      }
      
      return result;
    },
    // Phase 18.3: Aggressive caching - 10 min stale, no refetch triggers
    staleTime: 10 * 60 * 1000, // 10 minutes - data stays fresh much longer
    gcTime: 30 * 60 * 1000, // 30 minutes - keep in memory longer
    refetchOnWindowFocus: false, // NEVER refetch on window focus
    refetchOnMount: false, // NEVER refetch on mount - Firestore listeners update cache
    refetchOnReconnect: false, // NEVER refetch on reconnect
    refetchInterval: false, // No automatic polling
    placeholderData: keepPreviousData,
    enabled: options.enabled !== false, // Only disabled if explicitly set to false
  });
}

/**
 * Hook for fetching pending invitations
 * 
 * 🚀 PHASE 17.5: Smart query that SKIPS API when mega-bootstrap has hydrated cache
 * - Uses stale cache from mega-bootstrap to avoid duplicate API calls
 * - Only fetches from API if cache is empty (initial load fallback)
 * - refetchOnWindowFocus: false = mega-bootstrap handles refresh
 * 
 * DATA FLOW:
 * 1. mega-bootstrap fetches invitations → hydrates queryKeys.invitations cache
 * 2. useInvitationsQuery reads from cache → NO API call
 * 3. Firestore listeners update cache directly → NO API call
 * 
 * @param {Object} options - Query options
 * @param {boolean} options.enabled - Whether to enable the query (default: true)
 */
export function useInvitationsQuery(options = {}) {
  const queryClient = useQueryClient();
  
  // Phase 17.5: Check if invitations already exist in cache (from mega-bootstrap)
  const cachedInvitations = queryClient.getQueryData(queryKeys.invitations);
  const hasCachedData = cachedInvitations?.invitations?.length >= 0;
  
  return useQuery({
    queryKey: queryKeys.invitations,
    queryFn: () => {
      console.log('📥 useInvitationsQuery: Fetching invitations from API (cache miss)');
      return expenseApi.getPendingInvitations('pending', 1, 20);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - mega-bootstrap keeps it fresh
    gcTime: 30 * 60 * 1000, // 30 minutes retention
    refetchOnWindowFocus: false, // mega-bootstrap handles refresh
    refetchOnMount: hasCachedData ? false : true, // Skip API if cache exists
    refetchInterval: false, // No polling - Firestore handles real-time
    placeholderData: keepPreviousData,
    enabled: options.enabled !== false,
  });
}

/**
 * 🚀 PHASE 17.5: Hook for expense history from mega-bootstrap cache
 * 
 * Reads expense history directly from the mega-bootstrap cache.
 * NO API CALL - data is already available from mega-bootstrap.
 * 
 * DATA FLOW:
 * 1. mega-bootstrap fetches recent_history → hydrates cache
 * 2. useExpenseHistory() reads from cache → instant data
 * 3. Mutations update cache via addHistoryEntry() → instant updates
 * 
 * @param {string} groupId - The group ID to get history for
 * @returns {Object} - { data: history[], isLoading: false }
 */
export function useExpenseHistory(groupId) {
  const queryClient = useQueryClient();
  
  return useQuery({
    queryKey: queryKeys.recentHistory(groupId),
    queryFn: () => {
      // Try to get history from mega-bootstrap cache first
      const megaData = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));
      if (megaData?.data?.active_group?.recent_history) {
        console.log('📜 useExpenseHistory: Reading from mega-bootstrap cache');
        return megaData.data.active_group.recent_history;
      }
      
      // Fallback: fetch from API (should rarely happen if mega-bootstrap is used)
      console.log('📜 useExpenseHistory: Cache miss, fetching from API');
      return expenseApi.getExpenseHistory(groupId);
    },
    enabled: !!groupId,
    staleTime: 5 * 60 * 1000, // 5 minutes - history is updated via mutations
    gcTime: 30 * 60 * 1000, // 30 minutes retention
    refetchOnMount: false, // Data comes from mega-bootstrap
    refetchOnWindowFocus: false,
    placeholderData: [],
  });
}

/**
 * 🚀 PHASE 17.5: Hook for group activity history from mega-bootstrap cache
 * 
 * Alias for useExpenseHistory - returns the same recent_history data.
 * The history includes all group activity: creates, edits, deletes.
 * 
 * @param {string} groupId - The group ID to get history for
 * @returns {Object} - { data: history[], isLoading: false }
 */
export function useGroupHistory(groupId) {
  // Group history and expense history are the same - recent_history
  return useExpenseHistory(groupId);
}

/**
 * 🚀 PHASE 19.1: Hook for individual expense edit history
 * 
 * Fetches edit history for a specific expense (used in ExpenseHistoryModal).
 * Uses React Query with aggressive caching to prevent duplicate calls.
 * 
 * KEY OPTIMIZATION:
 * - staleTime: 2 minutes - prevents re-fetch when modal reopens
 * - gcTime: 10 minutes - keeps data cached even after modal closes
 * - refetchOnWindowFocus: false - no re-fetch on tab switch
 * - refetchOnMount: false - use cached data if available
 * 
 * This fixes the duplicate GET /expenses/{id}/history calls from Phase 18 logs.
 * 
 * @param {string} expenseId - The expense ID to get history for
 * @returns {Object} - { data: { history: [], is_edited: boolean, edit_count: number }, isLoading, error }
 */
export function useExpenseEditHistory(expenseId) {
  return useQuery({
    queryKey: queryKeys.expenseEditHistory(expenseId),
    queryFn: async () => {
      console.log('📜 useExpenseEditHistory: Fetching history for expense:', expenseId);
      const response = await expenseApi.getExpenseHistory(expenseId);
      if (!response.success) {
        throw new Error(response.error || 'Failed to load history');
      }
      return response;
    },
    enabled: !!expenseId,
    // Phase 19.1: Aggressive caching to prevent duplicate calls
    staleTime: 2 * 60 * 1000, // 2 minutes - history rarely changes after initial view
    gcTime: 10 * 60 * 1000, // 10 minutes - keep in cache even after modal closes
    refetchOnMount: false, // Use cached data when modal reopens
    refetchOnWindowFocus: false, // No re-fetch on tab switch
    refetchOnReconnect: false, // No re-fetch on reconnect
    retry: 1, // Single retry on failure
  });
}

/**
 * Hook for creating a new expense
 * 
 * 🚀 PHASE 17 BUG FIX: Optimistic UI for instant feedback
 * - Immediately shows the new expense in the list
 * - Updates balances optimistically
 * - Rolls back on error
 * 
 * 🚀 PHASE 21: Uses extreme API when enabled (0 reads, 1 batch write)
 */
export function useCreateExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (expenseData) => {
      // Phase 21: Use extreme API for 0-read mutations
      if (expenseApi.extremeMode) {
        console.log('🚀 EXTREME: Creating expense with 0 reads');
        return expenseApi.createExpenseExtreme(expenseData);
      }
      return expenseApi.createExpense(expenseData);
    },
    
    // OPTIMISTIC UPDATE: Instantly show expense in UI
    onMutate: async (expenseData) => {
      console.log('✨ OPTIMISTIC CREATE: Adding expense instantly');
      
      const groupId = expenseData.group_id;
      
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.group(groupId) });
      await queryClient.cancelQueries({ queryKey: queryKeys.megaBootstrap(groupId) });
      
      // Snapshot previous values for rollback
      const previousGroup = queryClient.getQueryData(queryKeys.group(groupId));
      const previousMega = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));
      
      // Create optimistic expense with temporary ID
      const optimisticExpense = {
        ...expenseData,
        expense_id: `temp_${Date.now()}`,
        id: `temp_${Date.now()}`,
        created_at: new Date().toISOString(),
        is_deleted: false,
        _optimistic: true  // Mark as optimistic for UI styling
      };
      
      // Update group data cache
      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        if (!old) return old;
        
        // Add new expense at the top of the list
        const newExpenses = [optimisticExpense, ...(old.expenses || [])];
        
        // Calculate optimistic balance changes
        const amount = parseFloat(expenseData.amount) || 0;
        const paidBy = expenseData.paid_by;
        
        // Ensure splits exist and calculate them if not provided
        let splits = expenseData.splits || [];
        if (splits.length === 0 && old.members) {
          // Default: equal split among all members
          const splitAmount = amount / old.members.length;
          splits = old.members.map(m => ({
            user_id: m.user_id,
            amount: splitAmount
          }));
        }
        
        // Create a map of existing balances
        const existingBalancesMap = {};
        (old.balances || []).forEach(b => {
          existingBalancesMap[b.user_id] = { ...b };
        });
        
        // Create a map of members for display names
        const membersMap = {};
        (old.members || []).forEach(m => {
          membersMap[m.user_id] = m;
        });
        
        // Credit the payer
        if (existingBalancesMap[paidBy]) {
          existingBalancesMap[paidBy].balance += amount;
          existingBalancesMap[paidBy].net_balance = existingBalancesMap[paidBy].balance;
        } else {
          const member = membersMap[paidBy];
          existingBalancesMap[paidBy] = {
            user_id: paidBy,
            display_name: member?.display_name || member?.user?.display_name || `User ${paidBy.slice(0, 6)}`,
            balance: amount,
            net_balance: amount,
            is_active: true
          };
        }
        
        // Debit each person in the split
        splits.forEach(split => {
          const userId = split.user_id;
          const splitAmount = parseFloat(split.amount) || 0;
          
          if (existingBalancesMap[userId]) {
            existingBalancesMap[userId].balance -= splitAmount;
            existingBalancesMap[userId].net_balance = existingBalancesMap[userId].balance;
          } else {
            const member = membersMap[userId];
            existingBalancesMap[userId] = {
              user_id: userId,
              display_name: member?.display_name || member?.user?.display_name || `User ${userId.slice(0, 6)}`,
              balance: -splitAmount,
              net_balance: -splitAmount,
              is_active: true
            };
          }
        });
        
        const newBalances = Object.values(existingBalancesMap);
        
        console.log(`  ✅ Added optimistic expense, now ${newExpenses.length} total`);
        
        return {
          ...old,
          expenses: newExpenses,
          balances: newBalances
        };
      });
      
      // Also update mega-bootstrap cache if it exists (CRITICAL: include balances!)
      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        
        const newExpenses = [optimisticExpense, ...(old.data.active_group.expenses || [])];
        
        // PHASE 17 FIX: Also update balances optimistically in megaBootstrap
        // This is where the UI reads from!
        const amount = parseFloat(expenseData.amount) || 0;
        const paidBy = expenseData.paid_by;
        
        let splits = expenseData.splits || [];
        if (splits.length === 0 && old.data.active_group.members) {
          const splitAmount = amount / old.data.active_group.members.length;
          splits = old.data.active_group.members.map(m => ({
            user_id: m.user_id,
            amount: splitAmount
          }));
        }
        
        // Create a map of existing balances
        const existingBalancesMap = {};
        (old.data.active_group.balances || []).forEach(b => {
          existingBalancesMap[b.user_id] = { ...b };
        });
        
        // Create a map of members for display names
        const membersMap = {};
        (old.data.active_group.members || []).forEach(m => {
          membersMap[m.user_id] = m;
        });
        
        // Update existing balances and track which users we've processed
        const processedUsers = new Set();
        
        // Credit the payer
        if (existingBalancesMap[paidBy]) {
          existingBalancesMap[paidBy].balance += amount;
          existingBalancesMap[paidBy].net_balance = existingBalancesMap[paidBy].balance;
        } else {
          // Create new balance entry for payer
          const member = membersMap[paidBy];
          existingBalancesMap[paidBy] = {
            user_id: paidBy,
            display_name: member?.display_name || member?.user?.display_name || `User ${paidBy.slice(0, 6)}`,
            balance: amount,
            net_balance: amount,
            is_active: true
          };
        }
        processedUsers.add(paidBy);
        
        // Debit each person in the split
        splits.forEach(split => {
          const userId = split.user_id;
          const splitAmount = parseFloat(split.amount) || 0;
          
          if (existingBalancesMap[userId]) {
            existingBalancesMap[userId].balance -= splitAmount;
            existingBalancesMap[userId].net_balance = existingBalancesMap[userId].balance;
          } else {
            // Create new balance entry for this participant
            const member = membersMap[userId];
            existingBalancesMap[userId] = {
              user_id: userId,
              display_name: member?.display_name || member?.user?.display_name || `User ${userId.slice(0, 6)}`,
              balance: -splitAmount,
              net_balance: -splitAmount,
              is_active: true
            };
          }
          processedUsers.add(userId);
        });
        
        // Convert map back to array
        const newBalances = Object.values(existingBalancesMap);
        
        console.log(`  ✅ Updated optimistic balances: ${newBalances.length} entries`);
        
        return {
          ...old,
          data: {
            ...old.data,
            active_group: {
              ...old.data.active_group,
              expenses: newExpenses,
              balances: newBalances
            }
          }
        };
      });
      
      return { previousGroup, previousMega, groupId };
    },
    
    onError: (err, variables, context) => {
      console.error('❌ Create expense failed, rolling back:', err);
      // Rollback on error
      if (context?.groupId) {
        if (context.previousGroup) {
          queryClient.setQueryData(
            queryKeys.group(context.groupId),
            context.previousGroup
          );
        }
        if (context.previousMega) {
          queryClient.setQueryData(
            queryKeys.megaBootstrap(context.groupId),
            context.previousMega
          );
        }
      }
    },
    
    onSuccess: async (data, variables, context) => {
      console.log('✅ Expense created successfully, syncing with server data...');
      
      const groupId = variables.group_id;
      
      if (groupId && data?.expense) {
        // Replace optimistic expense with real server data in BOTH caches
        
        // Update group cache
        queryClient.setQueryData(queryKeys.group(groupId), (old) => {
          if (!old || !old.expenses) return old;
          
          // Remove optimistic expense and add real one
          const newExpenses = old.expenses
            .filter(e => !e._optimistic)
            .concat([data.expense]);
          
          // Sort by created_at descending
          newExpenses.sort((a, b) => 
            new Date(b.created_at) - new Date(a.created_at)
          );
          
          // Phase 17: Use balance_deltas from server (more efficient than full balances)
          let updatedBalances = old.balances;
          if (data.balance_deltas) {
            // Apply deltas to existing balances
            updatedBalances = applyBalanceDeltas(old.balances, data.balance_deltas);
            console.log('✅ Applied balance_deltas from server');
          } else if (data.balances) {
            // Fallback: use full balances if provided (backward compatibility)
            updatedBalances = old.balances.map(b => {
              const newBalance = data.balances[b.user_id];
              if (newBalance !== undefined) {
                return { ...b, balance: newBalance, net_balance: newBalance };
              }
              return b;
            });
          }
          
          // Phase 17: Add history entry if provided
          const updatedHistory = data.history_entry 
            ? addHistoryEntry(old.recent_history, data.history_entry)
            : old.recent_history;
          
          return {
            ...old,
            expenses: newExpenses,
            balances: updatedBalances,
            recent_history: updatedHistory
          };
        });
        
        // CRITICAL: Also update megaBootstrap cache with real server data
        // This prevents the "shows then disappears" issue
        queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
          if (!old?.data?.active_group) return old;
          
          // Remove optimistic expense and add real one
          const newExpenses = (old.data.active_group.expenses || [])
            .filter(e => !e._optimistic)
            .concat([data.expense]);
          
          // Sort by created_at descending
          newExpenses.sort((a, b) => 
            new Date(b.created_at) - new Date(a.created_at)
          );
          
          // Phase 17: Use balance_deltas from server
          let updatedBalances = old.data.active_group.balances;
          if (data.balance_deltas) {
            updatedBalances = applyBalanceDeltas(old.data.active_group.balances, data.balance_deltas);
          } else if (data.balances) {
            updatedBalances = (old.data.active_group.balances || []).map(b => {
              const newBalance = data.balances[b.user_id];
              if (newBalance !== undefined) {
                return { ...b, balance: newBalance, net_balance: newBalance };
              }
              return b;
            });
          }
          
          // Phase 17: Add history entry if provided
          const updatedHistory = data.history_entry
            ? addHistoryEntry(old.data.active_group.recent_history, data.history_entry)
            : old.data.active_group.recent_history;
          
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                expenses: newExpenses,
                balances: updatedBalances,
                recent_history: updatedHistory
              }
            }
          };
        });
        
        // REMOVED: Background sync setTimeout - Firestore listeners handle this
        // This was causing 3-4 extra re-renders per expense action
        console.log('✅ Server data merged - Firestore listeners will sync');
      }
    }
  });
}

/**
 * Hook for updating an expense
 * 
 * 🚀 PHASE 17 BUG FIX: Optimistic UI for instant feedback
 * - Immediately shows the updated expense in the list
 * - Recalculates balances optimistically
 * - Rolls back on error
 * 
 * 🚀 PHASE 21: Uses extreme API when enabled (0 reads, 1 batch write)
 */
export function useUpdateExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ expenseId, data }) => {
      // Phase 21: Use extreme API for 0-read mutations
      if (expenseApi.extremeMode) {
        console.log('🚀 EXTREME: Updating expense with 0 reads');
        return expenseApi.updateExpenseExtreme(expenseId, data);
      }
      return expenseApi.updateExpense(expenseId, data);
    },
    
    // OPTIMISTIC UPDATE: Instantly show updated expense in UI
    onMutate: async ({ expenseId, data }) => {
      console.log('✨ OPTIMISTIC UPDATE: Updating expense instantly');
      
      const groupId = data.group_id;
      
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.group(groupId) });
      
      // Snapshot previous value for rollback
      const previousGroup = queryClient.getQueryData(queryKeys.group(groupId));
      
      // Get the old expense for balance reversal
      const oldExpense = previousGroup?.expenses?.find(
        e => e.expense_id === expenseId || e.id === expenseId
      );
      
      // Update expense in cache
      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        if (!old || !old.expenses) return old;
        
        // Update the expense with new data
        const newExpenses = old.expenses.map(e => {
          if (e.expense_id === expenseId || e.id === expenseId) {
            return {
              ...e,
              ...data,
              updated_at: new Date().toISOString(),
              _optimistic: true
            };
          }
          return e;
        });
        
        // Recalculate balances if amount/splits changed
        let newBalances = [...(old.balances || [])];
        
        if (oldExpense && (data.amount !== undefined || data.splits !== undefined || data.paid_by !== undefined)) {
          // First, reverse the old expense's impact
          const oldAmount = parseFloat(oldExpense.amount) || 0;
          const oldPaidBy = oldExpense.paid_by;
          const oldSplits = oldExpense.splits || [];
          
          newBalances = newBalances.map(b => {
            const newBalance = { ...b };
            
            // Reverse old payer credit
            if (b.user_id === oldPaidBy) {
              newBalance.balance -= oldAmount;
            }
            
            // Reverse old split debits
            const oldSplit = oldSplits.find(s => s.user_id === b.user_id);
            if (oldSplit) {
              newBalance.balance += parseFloat(oldSplit.amount) || 0;
            }
            
            return newBalance;
          });
          
          // Then apply the new expense's impact
          const newAmount = parseFloat(data.amount ?? oldExpense.amount) || 0;
          const newPaidBy = data.paid_by ?? oldExpense.paid_by;
          const newSplits = data.splits ?? oldExpense.splits ?? [];
          
          newBalances = newBalances.map(b => {
            const newBalance = { ...b };
            
            // Add new payer credit
            if (b.user_id === newPaidBy) {
              newBalance.balance += newAmount;
            }
            
            // Add new split debits
            const newSplit = newSplits.find(s => s.user_id === b.user_id);
            if (newSplit) {
              newBalance.balance -= parseFloat(newSplit.amount) || 0;
            }
            
            newBalance.net_balance = newBalance.balance;
            return newBalance;
          });
        }
        
        console.log(`  ✅ Updated optimistic expense`);
        
        return {
          ...old,
          expenses: newExpenses,
          balances: newBalances
        };
      });
      
      // PHASE 17 FIX: Also update megaBootstrap cache (UI reads from here!)
      const previousMega = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));
      
      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        
        // Get old expense for balance reversal
        const megaOldExpense = old.data.active_group.expenses?.find(
          e => e.expense_id === expenseId || e.id === expenseId
        );
        
        // Update the expense
        const newExpenses = (old.data.active_group.expenses || []).map(e => {
          if (e.expense_id === expenseId || e.id === expenseId) {
            return { ...e, ...data, updated_at: new Date().toISOString(), _optimistic: true };
          }
          return e;
        });
        
        // Recalculate balances
        let newBalances = [...(old.data.active_group.balances || [])];
        
        if (megaOldExpense && (data.amount !== undefined || data.splits !== undefined || data.paid_by !== undefined)) {
          // Reverse old expense impact
          const oldAmount = parseFloat(megaOldExpense.amount) || 0;
          const oldPaidBy = megaOldExpense.paid_by;
          const oldSplits = megaOldExpense.splits || [];
          
          newBalances = newBalances.map(b => {
            const newBalance = { ...b };
            if (b.user_id === oldPaidBy) newBalance.balance -= oldAmount;
            const oldSplit = oldSplits.find(s => s.user_id === b.user_id);
            if (oldSplit) newBalance.balance += parseFloat(oldSplit.amount) || 0;
            return newBalance;
          });
          
          // Apply new expense impact
          const newAmount = parseFloat(data.amount ?? megaOldExpense.amount) || 0;
          const newPaidBy = data.paid_by ?? megaOldExpense.paid_by;
          const newSplits = data.splits ?? megaOldExpense.splits ?? [];
          
          newBalances = newBalances.map(b => {
            const newBalance = { ...b };
            if (b.user_id === newPaidBy) newBalance.balance += newAmount;
            const newSplit = newSplits.find(s => s.user_id === b.user_id);
            if (newSplit) newBalance.balance -= parseFloat(newSplit.amount) || 0;
            newBalance.net_balance = newBalance.balance;
            return newBalance;
          });
        }
        
        return {
          ...old,
          data: {
            ...old.data,
            active_group: {
              ...old.data.active_group,
              expenses: newExpenses,
              balances: newBalances
            }
          }
        };
      });
      
      return { previousGroup, previousMega, groupId };
    },

    onError: (err, variables, context) => {
      console.error('❌ Update expense failed, rolling back:', err);
      // Rollback on error
      if (context?.previousGroup && context?.groupId) {
        queryClient.setQueryData(
          queryKeys.group(context.groupId),
          context.previousGroup
        );
        if (context.previousMega) {
          queryClient.setQueryData(
            queryKeys.megaBootstrap(context.groupId),
            context.previousMega
          );
        }
      }
    },
    
    onSuccess: async (data, variables) => {
      console.log('✅ Expense updated successfully');
      
      const groupId = data?.expense?.group_id || variables.data.group_id;
      
      if (groupId) {
        // Update group cache with server data (remove optimistic flag)
        queryClient.setQueryData(queryKeys.group(groupId), (old) => {
          if (!old || !old.expenses) return old;
          
          const newExpenses = old.expenses.map(e => {
            if (e.expense_id === variables.expenseId || e.id === variables.expenseId) {
              return {
                ...e,
                ...data.expense,
                _optimistic: false
              };
            }
            return e;
          });
          
          // Phase 17: Use balance_deltas from server (more efficient)
          let updatedBalances = old.balances;
          if (data.balance_deltas) {
            updatedBalances = applyBalanceDeltas(old.balances, data.balance_deltas);
            console.log('✅ Applied balance_deltas from server');
          } else if (data.balances) {
            // Fallback: use full balances if provided
            updatedBalances = old.balances.map(b => {
              const newBalance = data.balances[b.user_id];
              if (newBalance !== undefined) {
                return { ...b, balance: newBalance, net_balance: newBalance };
              }
              return b;
            });
          }
          
          // Phase 17: Add history entry if provided
          const updatedHistory = data.history_entry
            ? addHistoryEntry(old.recent_history, data.history_entry)
            : old.recent_history;
          
          return {
            ...old,
            expenses: newExpenses,
            balances: updatedBalances,
            recent_history: updatedHistory
          };
        });
        
        // CRITICAL: Also update megaBootstrap cache with real server data
        queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
          if (!old?.data?.active_group) return old;
          
          const newExpenses = (old.data.active_group.expenses || []).map(e => {
            if (e.expense_id === variables.expenseId || e.id === variables.expenseId) {
              return {
                ...e,
                ...data.expense,
                _optimistic: false
              };
            }
            return e;
          });
          
          // Phase 17: Use balance_deltas from server
          let updatedBalances = old.data.active_group.balances;
          if (data.balance_deltas) {
            updatedBalances = applyBalanceDeltas(old.data.active_group.balances, data.balance_deltas);
          } else if (data.balances) {
            updatedBalances = (old.data.active_group.balances || []).map(b => {
              const newBalance = data.balances[b.user_id];
              if (newBalance !== undefined) {
                return { ...b, balance: newBalance, net_balance: newBalance };
              }
              return b;
            });
          }
          
          // Phase 17: Add history entry if provided
          const updatedHistory = data.history_entry
            ? addHistoryEntry(old.data.active_group.recent_history, data.history_entry)
            : old.data.active_group.recent_history;
          
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                expenses: newExpenses,
                balances: updatedBalances,
                recent_history: updatedHistory
              }
            }
          };
        });
        
        // REMOVED: Background sync setTimeout - Firestore listeners handle this
        // This was causing 3-4 extra re-renders per expense action
        console.log('✅ Server data merged - Firestore listeners will sync');
      }
    }
  });
}

/**
 * Hook for deleting an expense with OPTIMISTIC UPDATE
 * Instantly removes the expense from UI
 * 
 * Phase 17 Fix: Don't reverse balances optimistically - wait for server balance_deltas
 * to avoid double-reversal bug where balances show wrong temporarily.
 * 
 * 🚀 PHASE 21: Uses extreme API when enabled (0 reads, 1 batch write)
 */
export function useDeleteExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ expenseId, groupId }) => {
      // Phase 21: Use extreme API for 0-read mutations
      if (expenseApi.extremeMode) {
        console.log('🚀 EXTREME: Deleting expense with 0 reads');
        return expenseApi.deleteExpenseExtreme(expenseId, groupId);
      }
      return expenseApi.deleteExpense(expenseId);
    },
    
    // OPTIMISTIC UPDATE: Immediately mark expense as deleted in UI
    // Phase 17: DON'T touch balances here - server balance_deltas will handle it
    onMutate: async ({ expenseId, groupId }) => {
      console.log('🗑️ OPTIMISTIC DELETE: Marking expense as deleted instantly');
      
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.group(groupId) });
      
      // Snapshot previous value for rollback
      const previousGroup = queryClient.getQueryData(queryKeys.group(groupId));
      
      // Optimistically mark the expense as deleted (soft delete)
      // Phase 17 Fix: Only mark as deleted, DON'T reverse balances
      // Server will return balance_deltas in onSuccess
      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        if (!old || !old.expenses) return old;
        
        // Mark expense as deleted instead of removing (Phase 12: show in history)
        const newExpenses = old.expenses.map(e => {
          if (e.expense_id === expenseId || e.id === expenseId) {
            return {
              ...e,
              is_deleted: true,
              deleted_at: new Date().toISOString()
            };
          }
          return e;
        });
        
        console.log(`  ✅ Marked expense as deleted, ${newExpenses.filter(e => !e.is_deleted).length} active remaining`);
        
        // Phase 17: Return with SAME balances - server balance_deltas will update them
        return {
          ...old,
          expenses: newExpenses
          // DON'T modify balances here - causes double-reversal bug
        };
      });
      
      // PHASE 17 FIX: Also update megaBootstrap cache (UI reads from here!)
      // Phase 17: DON'T reverse balances here either - wait for server
      const previousMega = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));
      
      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        
        // Mark expense as deleted (Phase 17: don't touch balances)
        const newExpenses = (old.data.active_group.expenses || []).map(e => {
          if (e.expense_id === expenseId || e.id === expenseId) {
            return { ...e, is_deleted: true, deleted_at: new Date().toISOString() };
          }
          return e;
        });
        
        // Phase 17 Fix: DON'T reverse balances here - server balance_deltas will handle it
        return {
          ...old,
          data: {
            ...old.data,
            active_group: {
              ...old.data.active_group,
              expenses: newExpenses
              // DON'T modify balances - causes double-reversal bug
            }
          }
        };
      });
      
      return { previousGroup, previousMega, groupId };
    },
    
    onError: (err, variables, context) => {
      console.error('❌ Delete failed, rolling back:', err);
      // Rollback on error
      if (context?.previousGroup && context?.groupId) {
        queryClient.setQueryData(
          queryKeys.group(context.groupId),
          context.previousGroup
        );
        if (context.previousMega) {
          queryClient.setQueryData(
            queryKeys.megaBootstrap(context.groupId),
            context.previousMega
          );
        }
      }
    },
    
    onSuccess: async (data, { expenseId, groupId }, context) => {
      console.log('✅ Expense deleted successfully');
      
      // Phase 17: Update cache with balance_deltas and history_entry from server
      if (groupId) {
        queryClient.setQueryData(queryKeys.group(groupId), (old) => {
          if (!old) return old;
          
          // Phase 17: Use balance_deltas from server (this is the ONLY place balances change)
          let updatedBalances = old.balances;
          if (data?.balance_deltas) {
            updatedBalances = applyBalanceDeltas(old.balances, data.balance_deltas);
            console.log('✅ Applied balance_deltas from delete response');
          } else if (data?.balances && old.balances) {
            // Fallback: use full balances if provided
            updatedBalances = old.balances.map(b => {
              const newBalance = data.balances[b.user_id];
              if (newBalance !== undefined) {
                return { ...b, balance: newBalance, net_balance: newBalance };
              }
              return b;
            });
          }
          
          // Phase 17: Add history entry if provided
          const updatedHistory = data?.history_entry
            ? addHistoryEntry(old.recent_history, data.history_entry)
            : old.recent_history;
          
          return {
            ...old,
            balances: updatedBalances,
            recent_history: updatedHistory
          };
        });
        
        // Phase 17: Also update megaBootstrap cache
        queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
          if (!old?.data?.active_group) return old;
          
          let updatedBalances = old.data.active_group.balances;
          if (data?.balance_deltas) {
            updatedBalances = applyBalanceDeltas(old.data.active_group.balances, data.balance_deltas);
          } else if (data?.balances) {
            updatedBalances = (old.data.active_group.balances || []).map(b => {
              const newBalance = data.balances[b.user_id];
              if (newBalance !== undefined) {
                return { ...b, balance: newBalance, net_balance: newBalance };
              }
              return b;
            });
          }
          
          const updatedHistory = data?.history_entry
            ? addHistoryEntry(old.data.active_group.recent_history, data.history_entry)
            : old.data.active_group.recent_history;
          
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                balances: updatedBalances,
                recent_history: updatedHistory
              }
            }
          };
        });
        
        console.log('✅ Balances and history updated from server response');
      }
    },
  });
}

/**
 * Hook for creating a settlement with PHASE 1.4 OPTIMISTIC UPDATES
 * 
 * Instantly updates balances when a payment is recorded.
 * Shows immediate feedback to users.
 * 
 * 🚀 PHASE 21: Uses extreme API when enabled (0 reads, 1 batch write)
 */
export function useCreateSettlementMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (settlementData) => {
      // Phase 21: Use extreme API for 0-read mutations
      if (expenseApi.extremeMode) {
        console.log('🚀 EXTREME: Creating settlement with 0 reads');
        return expenseApi.createSettlementExtreme(settlementData);
      }
      return expenseApi.createSettlement(settlementData);
    },
    
    // PHASE 1.4: Optimistic update for settlement
    onMutate: async (settlement) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ 
        queryKey: queryKeys.group(settlement.group_id) 
      });

      // Snapshot previous value
      const previousGroup = queryClient.getQueryData(
        queryKeys.group(settlement.group_id)
      );

      // Helper to calculate optimistic balances
      const calculateOptimisticBalances = (balances) => {
        if (!balances) return balances;
        const amount = parseFloat(settlement.amount);
        return balances.map(b => {
          const newBalance = { ...b };
          if (b.user_id === settlement.from_user) {
            newBalance.balance += amount;
            newBalance.net_balance += amount;
          }
          if (b.user_id === settlement.to_user) {
            newBalance.balance -= amount;
            newBalance.net_balance -= amount;
          }
          return newBalance;
        });
      };
      
      console.log('💰 OPTIMISTIC SETTLEMENT: Updating balances instantly');

      // Update group cache
      queryClient.setQueryData(
        queryKeys.group(settlement.group_id),
        (old) => {
          if (!old || !old.balances) return old;
          const newBalances = calculateOptimisticBalances(old.balances);
          const isSettled = newBalances.every(b => Math.abs(b.balance) < 0.01);
          return { ...old, balances: newBalances, is_settled: isSettled };
        }
      );

      // PHASE 17 FIX: Also update megaBootstrap cache (UI reads from here)
      queryClient.setQueryData(
        queryKeys.megaBootstrap(settlement.group_id),
        (old) => {
          if (!old?.data?.active_group?.balances) return old;
          const newBalances = calculateOptimisticBalances(old.data.active_group.balances);
          const isSettled = newBalances.every(b => Math.abs(b.balance) < 0.01);
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                balances: newBalances,
                is_settled: isSettled
              }
            }
          };
        }
      );

      console.log('✅ Optimistic settlement applied to both caches');
      return { previousGroup };
    },
    
    // Rollback on error
    onError: (err, settlement, context) => {
      console.error('❌ Settlement failed, rolling back:', err);
      
      if (context?.previousGroup) {
        queryClient.setQueryData(
          queryKeys.group(settlement.group_id),
          context.previousGroup
        );
      }
    },
    
    // Backend confirms
    onSuccess: async (data, variables) => {
      console.log('💰 Backend confirmed settlement');
      
      // Helper to merge server balances
      const mergeServerBalances = (existingBalances) => {
        if (!data?.balances || !existingBalances) return existingBalances;
        return existingBalances.map(b => {
          const newBalance = data.balances[b.user_id];
          if (newBalance !== undefined) {
            return { ...b, balance: newBalance, net_balance: newBalance };
          }
          return b;
        });
      };
      
      // Phase 17.8: Update group cache with server balances
      if (data?.balances && variables.group_id) {
        queryClient.setQueryData(queryKeys.group(variables.group_id), (old) => {
          if (!old) return old;
          const updatedBalances = mergeServerBalances(old.balances);
          const isSettled = updatedBalances?.every(b => Math.abs(b.balance) < 0.01);
          return { ...old, balances: updatedBalances, is_settled: isSettled };
        });
        
        // PHASE 17 FIX: Also update megaBootstrap cache (UI reads from here)
        queryClient.setQueryData(queryKeys.megaBootstrap(variables.group_id), (old) => {
          if (!old?.data?.active_group?.balances) return old;
          const updatedBalances = mergeServerBalances(old.data.active_group.balances);
          const isSettled = updatedBalances?.every(b => Math.abs(b.balance) < 0.01);
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                balances: updatedBalances,
                is_settled: isSettled
              }
            }
          };
        });
        console.log('✅ Balances updated from server response');
      }
      
      // REMOVED: Background sync setTimeout - Firestore listeners handle this
      // This was causing 3-4 extra re-renders per settlement
      console.log('✅ Settlement complete - Firestore listeners will sync');
    },
  });
}

/**
 * Hook for creating a new group
 * 
 * 🚀 PHASE 21: Uses extreme API when enabled (0 reads, 1 batch write)
 */
export function useCreateGroupMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (groupData) => {
      // Phase 21: Use extreme API for 0-read mutations
      if (expenseApi.extremeMode) {
        console.log('🚀 EXTREME: Creating group with 0 reads');
        return expenseApi.createGroupExtreme(groupData);
      }
      return expenseApi.createGroup(groupData);
    },
    onSuccess: async () => {
      console.log('👥 Group created, refreshing groups list...');
      
      // Immediately refetch groups list to show the new group
      await queryClient.invalidateQueries({ queryKey: queryKeys.groups });
      
      console.log('✅ Groups list refreshed');
    },
  });
}

/**
 * Hook for deleting a group
 */
export function useDeleteGroupMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (groupId) => expenseApi.deleteGroup(groupId),
    onSuccess: async (data, groupId) => {
      console.log('🗑️ Group deleted, cleaning up caches...');
      
      // Remove specific group data (deleted group)
      queryClient.removeQueries({ queryKey: queryKeys.group(groupId) });
      queryClient.removeQueries({ queryKey: queryKeys.megaBootstrap(groupId) });
      queryClient.removeQueries({ queryKey: queryKeys.expenses(groupId) });
      queryClient.removeQueries({ queryKey: queryKeys.settlements(groupId) });
      
      // Immediately refetch groups list to remove the deleted group
      await queryClient.invalidateQueries({ queryKey: queryKeys.groups });
      
      console.log('✅ Group deleted and caches refreshed');
    },
    onError: (err) => {
      console.error('❌ Failed to delete group:', err);
    }
  });
}

/**
 * Hook for accepting an invitation
 * 
 * 🚀 PHASE 17 FIX: Optimistic UI for instant feedback
 * - Immediately removes invitation from list
 * - Invalidates ALL group caches so inviter sees new member instantly
 * - Invalidates mega-bootstrap for real-time sync
 * 
 * 🚀 PHASE 21: Uses extreme API when enabled (0 reads, 1 batch write)
 */
export function useAcceptInvitationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (invitationId) => {
      // Phase 21: Use extreme API for 0-read mutations
      if (expenseApi.extremeMode) {
        console.log('🚀 EXTREME: Accepting invitation with 0 reads');
        return expenseApi.acceptInvitationExtreme(invitationId);
      }
      return expenseApi.acceptInvitation(invitationId);
    },
    
    // OPTIMISTIC UPDATE: Instantly remove invitation from list
    onMutate: async (invitationId) => {
      console.log('✨ OPTIMISTIC ACCEPT: Removing invitation instantly');
      
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.invitations });
      
      // Snapshot previous value for rollback
      const previousInvitations = queryClient.getQueryData(queryKeys.invitations);
      
      // Optimistically remove the invitation from cache
      queryClient.setQueryData(queryKeys.invitations, (old) => {
        if (!old || !old.invitations) return old;
        return {
          ...old,
          invitations: old.invitations.filter(inv => 
            (inv.id || inv.invitation_id) !== invitationId
          )
        };
      });
      
      console.log('  ✅ Invitation removed from list optimistically');
      
      return { previousInvitations };
    },
    
    onError: (err, invitationId, context) => {
      console.error('❌ Accept invitation failed, rolling back:', err);
      // Rollback on error
      if (context?.previousInvitations) {
        queryClient.setQueryData(queryKeys.invitations, context.previousInvitations);
      }
    },
    
    onSuccess: async (data) => {
      console.log('🚀 PHASE 17: Invitation accepted, invalidating all caches for instant update...');
      
      const groupId = data?.group_id || data?.group?.group_id || data?.group?.id;
      
      // 1. Immediately refetch invitations (confirms removal)
      await queryClient.invalidateQueries({ 
        queryKey: queryKeys.invitations
        // NO refetchType: 'none' - triggers immediate refetch
      });
      
      // 2. Invalidate groups list (both users see updated member count)
      await queryClient.invalidateQueries({ 
        queryKey: queryKeys.groups
        // NO refetchType: 'none' - triggers immediate refetch
      });
      
      // 3. If we have group ID, invalidate that specific group's caches
      if (groupId) {
        console.log(`🔄 Invalidating group ${groupId} caches for instant member list update`);
        await Promise.all([
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.group(groupId)
            // NO refetchType: 'none' - triggers immediate refetch
          }),
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.megaBootstrap(groupId)
            // NO refetchType: 'none' - triggers immediate refetch
          })
        ]);
      }
      
      // 4. Invalidate all mega-bootstrap caches (for any active group view)
      await queryClient.invalidateQueries({ 
        queryKey: ['mega-bootstrap']
        // NO refetchType: 'none' - triggers immediate refetch
      });
      
      console.log('✅ All caches invalidated - both users see member list update instantly');
    },
    onError: (err) => {
      console.error('❌ Failed to accept invitation:', err);
    }
  });
}

/**
 * Hook for declining an invitation
 * 
 * 🚀 PHASE 17 FIX: Optimistic UI for instant feedback
 */
export function useDeclineInvitationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (invitationId) => expenseApi.declineInvitation(invitationId),
    
    // OPTIMISTIC UPDATE: Instantly remove invitation from list
    onMutate: async (invitationId) => {
      console.log('✨ OPTIMISTIC DECLINE: Removing invitation instantly');
      
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.invitations });
      
      // Snapshot previous value for rollback
      const previousInvitations = queryClient.getQueryData(queryKeys.invitations);
      
      // Optimistically remove the invitation from cache
      queryClient.setQueryData(queryKeys.invitations, (old) => {
        if (!old || !old.invitations) return old;
        return {
          ...old,
          invitations: old.invitations.filter(inv => 
            (inv.id || inv.invitation_id) !== invitationId
          )
        };
      });
      
      console.log('  ✅ Invitation removed from list optimistically');
      
      return { previousInvitations };
    },
    
    onError: (err, invitationId, context) => {
      console.error('❌ Decline invitation failed, rolling back:', err);
      // Rollback on error
      if (context?.previousInvitations) {
        queryClient.setQueryData(queryKeys.invitations, context.previousInvitations);
      }
    },
    
    onSuccess: async () => {
      console.log('❌ Invitation declined, confirming removal...');
      
      // Background sync for eventual consistency
      setTimeout(async () => {
        await queryClient.invalidateQueries({ queryKey: queryKeys.invitations });
        console.log('✅ Invitations refreshed');
      }, 500);
      
      console.log('✅ Invitation removed');
    },
  });
}

/**
 * Hook for sending an invitation
 * 
 * 🚀 PHASE 17 FIX: Instant pending invitation visibility
 * - After sending invitation, invalidate sender's group cache
 * - The invitee needs to refresh their page or wait for background sync
 *   to see the invitation (backend invalidates their cache)
 * 
 * 🚀 PHASE 21: Uses extreme API when enabled (0 reads, 1 batch write)
 */
export function useSendInvitationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (invitationData) => {
      // Phase 21: Use extreme API for 0-read mutations
      if (expenseApi.extremeMode) {
        console.log('🚀 EXTREME: Sending invitation with 0 reads');
        return expenseApi.addMemberExtreme(invitationData.group_id, {
          email: invitationData.invited_email
        });
      }
      return expenseApi.sendInvitation(invitationData);
    },
    
    // OPTIMISTIC UPDATE: Instantly show invitation in pending list
    onMutate: async (invitationData) => {
      console.log('✨ OPTIMISTIC SEND: Adding invitation to pending list instantly');
      
      const groupId = invitationData.group_id;
      
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.megaBootstrap(groupId) });
      
      // Snapshot previous value for rollback
      const previousMega = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));
      
      // Create optimistic invitation
      const optimisticInvitation = {
        id: `temp_${Date.now()}`,
        invitation_id: `temp_${Date.now()}`,
        group_id: groupId,
        email: invitationData.invited_email,
        invited_email: invitationData.invited_email,
        status: 'pending',
        created_at: new Date().toISOString(),
        _optimistic: true
      };
      
      // Add to mega-bootstrap active_group.invitations (correct path)
      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        
        const currentInvitations = old.data.active_group.invitations || [];
        return {
          ...old,
          data: {
            ...old.data,
            active_group: {
              ...old.data.active_group,
              invitations: [...currentInvitations, optimisticInvitation]
            }
          }
        };
      });
      
      console.log('  ✅ Invitation added to pending list optimistically');
      
      return { previousMega, groupId };
    },
    
    onError: (err, variables, context) => {
      console.error('❌ Send invitation failed, rolling back:', err);
      // Rollback on error
      if (context?.previousMega && context?.groupId) {
        queryClient.setQueryData(
          queryKeys.megaBootstrap(context.groupId),
          context.previousMega
        );
      }
    },
    
    onSuccess: async (data, variables, context) => {
      console.log('📨 PHASE 17: Invitation sent, syncing with server...');
      
      const groupId = variables.group_id;
      
      if (groupId) {
        // Replace optimistic invitation with real server data
        if (data?.invitation) {
          queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
            if (!old?.data?.active_group) return old;
            
            // Remove optimistic invitations and add real one
            const newInvitations = (old.data.active_group.invitations || [])
              .filter(inv => !inv._optimistic)
              .concat([{
                ...data.invitation,
                id: data.invitation.invitation_id || data.invitation.id,
                invitation_id: data.invitation.invitation_id || data.invitation.id
              }]);
            
            return {
              ...old,
              data: {
                ...old.data,
                active_group: {
                  ...old.data.active_group,
                  invitations: newInvitations
                }
              }
            };
          });
        }
        
        // REMOVED: Background sync setTimeout - Firestore listeners handle this
        // This was causing extra re-renders and overwriting cache
      }
      
      console.log('✅ Server data merged - pending invitations updated');
      return data;
    }
  });
}
