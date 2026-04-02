import { useQuery, useMutation, useQueryClient, keepPreviousData, useInfiniteQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useState, useRef } from 'react';
import expenseApi from '../services/expenseApi';
import authService from '../services/sqlAuthService';
import GlobalConfig from '../config/globalConfig';

/**
 * Unwrap the standard backend response envelope.
 * Backend returns { success, data, meta } — hooks expect the inner `data` object.
 * Safe for both envelope and pre-unwrapped (manual cache set) formats.
 */
function unwrapEnvelope(response) {
  if (response && typeof response === 'object' && 'success' in response && 'data' in response) {
    return response.data;
  }
  return response;
}

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
  expenseEditHistory: (expenseId) => ['expense-edit-history', expenseId],
};

// ── Balance Delta Helpers ───────────────────────────────────────────────────

function applyBalanceDeltas(existingBalances, deltas) {
  if (!existingBalances || !deltas) return existingBalances;
  return existingBalances.map(b => {
    const delta = deltas[b.user_id];
    if (delta !== undefined && delta !== null) {
      const newBalance = (parseFloat(b.balance) || 0) + parseFloat(delta);
      return { ...b, balance: newBalance, net_balance: newBalance };
    }
    return b;
  });
}

function addHistoryEntry(existingHistory, historyEntry, maxItems = 50) {
  if (!historyEntry) return existingHistory;
  if (!existingHistory) return [historyEntry];
  const filtered = existingHistory.filter(h => h.id !== historyEntry.id);
  return [historyEntry, ...filtered].slice(0, maxItems);
}

// ── Background Sync ─────────────────────────────────────────────────────────

export function useBackgroundSync(groupId, options = {}) {
  const queryClient = useQueryClient();
  const [failureCount, setFailureCount] = useState(0);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isVisible, setIsVisible] = useState(!document.hidden);
  const intervalRef = useRef(null);

  const {
    enabled = true,
    baseInterval = GlobalConfig.BACKGROUND_SYNC_BASE_INTERVAL,
    maxInterval = GlobalConfig.BACKGROUND_SYNC_MAX_INTERVAL,
  } = options;

  const currentInterval = Math.min(
    baseInterval * Math.pow(2, failureCount),
    maxInterval
  );

  const sync = useCallback(async () => {
    if (!enabled || !isOnline || !isVisible) return;
    try {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.megaBootstrap(groupId),
        refetchType: 'active'
      });
      setFailureCount(0);
    } catch (error) {
      setFailureCount(prev => prev + 1);
    }
  }, [enabled, isOnline, isVisible, groupId, currentInterval, queryClient]);

  useEffect(() => {
    const handleOnline = () => { setIsOnline(true); setFailureCount(0); sync(); };
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [sync]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      const visible = !document.hidden;
      setIsVisible(visible);
      if (visible) sync();
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [sync]);

  useEffect(() => {
    if (!enabled || !isOnline || !isVisible) {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
      return;
    }
    intervalRef.current = setInterval(sync, currentInterval);
    return () => { if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; } };
  }, [enabled, isOnline, isVisible, currentInterval, sync]);

  return { isOnline, isVisible, failureCount, currentInterval, forceSync: sync };
}

// ── Query Hooks ─────────────────────────────────────────────────────────────

export function useUserQuery() {
  return useQuery({
    queryKey: queryKeys.user,
    queryFn: () => expenseApi.getUserData(),
    staleTime: 10 * 60 * 1000,
  });
}

/**
 * Fetches groups. Skips API when mega-bootstrap has hydrated cache.
 */
export function useGroupsQuery() {
  const queryClient = useQueryClient();
  const cachedGroups = queryClient.getQueryData(queryKeys.groups);
  const hasCachedData = cachedGroups?.groups?.length >= 0;

  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: async () => unwrapEnvelope(await expenseApi.getUserGroups(1, 20)),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    refetchInterval: false,
    placeholderData: keepPreviousData,
    enabled: !hasCachedData,
  });
}

/**
 * Fetches a single group with full details. Fallback only when mega-bootstrap cache is empty.
 */
export function useGroupQuery(groupId, options = {}) {
  const queryClient = useQueryClient();
  const cachedGroup = queryClient.getQueryData(queryKeys.group(groupId));
  const hasCachedData = !!cachedGroup;

  return useQuery({
    queryKey: queryKeys.group(groupId),
    queryFn: async () => unwrapEnvelope(await expenseApi.getGroupFull(groupId, false)),
    enabled: !!groupId && (options.enabled !== false),
    staleTime: 5 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchOnMount: hasCachedData ? false : true,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });
}

/**
 * Prefetch handler for hovering over groups in navigation.
 */
export function usePrefetchGroups(groups, prefetchCount = 3) {
  const queryClient = useQueryClient();

  const prefetchOnHover = useCallback((groupId) => {
    if (!groupId) return;
    const cached = queryClient.getQueryData(queryKeys.group(groupId));
    if (cached) return;
    queryClient.prefetchQuery({
      queryKey: queryKeys.group(groupId),
      queryFn: async () => unwrapEnvelope(await expenseApi.getGroupFull(groupId, false)),
      staleTime: 5 * 60 * 1000,
    });
  }, [queryClient]);

  return { prefetchOnHover };
}

export function useFetchGroups() {
  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: async () => unwrapEnvelope(await expenseApi.getUserGroups()),
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

export function useExpensesQuery(groupId) {
  return useQuery({
    queryKey: queryKeys.expenses(groupId),
    queryFn: async () => unwrapEnvelope(await expenseApi.getGroupExpenses(groupId)),
    enabled: !!groupId,
    staleTime: 1 * 60 * 1000,
  });
}

export function useInfiniteExpensesQuery(groupId, pageSize = 10) {
  return useInfiniteQuery({
    queryKey: queryKeys.expensesInfinite(groupId),
    queryFn: async ({ pageParam = 0 }) => {
      const result = unwrapEnvelope(await expenseApi.getGroupExpenses(groupId, {
        limit: pageSize,
        offset: pageParam,
      }));
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
      return undefined;
    },
    initialPageParam: 0,
    enabled: !!groupId,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useSettlementsQuery(groupId) {
  return useQuery({
    queryKey: queryKeys.settlements(groupId),
    queryFn: async () => unwrapEnvelope(await expenseApi.getGroupSettlements(groupId)),
    enabled: !!groupId,
    staleTime: 60 * 1000,
    refetchOnWindowFocus: true,
    refetchInterval: 60 * 1000,
  });
}

// ── Mega Bootstrap ──────────────────────────────────────────────────────────

/**
 * Single API call that replaces 4-5 parallel calls (groups, group full, settlements,
 * invitations). Hydrates individual query caches for backward compatibility.
 */
export function useMegaBootstrap(activeGroupId, options = {}) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: queryKeys.megaBootstrap(activeGroupId),
    queryFn: async () => {
      const existingCache = queryClient.getQueryData(queryKeys.megaBootstrap(activeGroupId));
      if (existingCache?.data && !options.bypassCache) return existingCache;

      let result;

      // Extreme dashboard mode: single read for everything
      if (expenseApi.extremeMode) {
        const extremeResult = await expenseApi.getExtremeDashboard(options.bypassCache);
        const dashboard = extremeResult?.dashboard || {};
        const groups = Object.values(dashboard.groups || {});

        let activeGroup = null;
        if (activeGroupId && dashboard.groups?.[activeGroupId]) {
          const groupData = dashboard.groups[activeGroupId];
          activeGroup = {
            group: { group_id: activeGroupId, ...groupData },
            members: groupData.members || [],
            balances: groupData.balances || [],
            expenses: groupData.recent_expenses || [],
            settlements: groupData.recent_settlements || [],
            all_members_map: {}
          };
          (groupData.members || []).forEach(member => {
            activeGroup.all_members_map[member.user_id] = member;
          });
        }

        result = {
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
      } else {
        // Standard mega-bootstrap
        result = await expenseApi.getMegaBootstrap({
          activeGroupId,
          recentExpensesLimit: 20,
          bypassCache: options.bypassCache || false
        });
      }

      // Hydrate individual query caches for backward compatibility
      if (result?.data) {
        if (result.data.groups) {
          queryClient.setQueryData(queryKeys.groups, {
            success: true,
            groups: result.data.groups
          });
        }
        if (result.data.invitations) {
          queryClient.setQueryData(queryKeys.invitations, {
            success: true,
            invitations: result.data.invitations
          });
        }
        if (activeGroupId && result.data.active_group) {
          const groupData = result.data.active_group;
          queryClient.setQueryData(queryKeys.group(activeGroupId), {
            success: true,
            group: groupData.group,
            members: groupData.members,
            balances: groupData.balances,
            expenses: groupData.expenses,
            all_members_map: groupData.all_members_map,
            expenses_pagination: groupData.expenses_pagination || { has_more: false, total: (groupData.expenses || []).length }
          });
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
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
    refetchOnMount: false,
    refetchOnReconnect: true,
    refetchInterval: 120 * 1000,
    placeholderData: keepPreviousData,
    enabled: options.enabled !== false,
  });
}

/**
 * Fetches invitations. Skips API when mega-bootstrap has hydrated cache.
 */
export function useInvitationsQuery(options = {}) {
  const queryClient = useQueryClient();
  const cachedInvitations = queryClient.getQueryData(queryKeys.invitations);
  const hasCachedData = cachedInvitations?.invitations?.length >= 0;

  return useQuery({
    queryKey: queryKeys.invitations,
    queryFn: async () => unwrapEnvelope(await expenseApi.getPendingInvitations('pending', 1, 20)),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnMount: hasCachedData ? false : true,
    refetchInterval: false,
    placeholderData: keepPreviousData,
    enabled: options.enabled !== false,
  });
}

/**
 * Reads expense history from mega-bootstrap cache. No direct API call.
 */
export function useExpenseHistory(groupId) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: queryKeys.recentHistory(groupId),
    queryFn: () => {
      const megaData = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));
      if (megaData?.data?.active_group?.recent_history) {
        return megaData.data.active_group.recent_history;
      }
      return expenseApi.getExpenseHistory(groupId);
    },
    enabled: !!groupId,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    placeholderData: [],
  });
}

export function useGroupHistory(groupId) {
  return useExpenseHistory(groupId);
}

/**
 * Fetches individual expense edit history (for ExpenseHistoryModal).
 */
export function useExpenseEditHistory(expenseId) {
  return useQuery({
    queryKey: queryKeys.expenseEditHistory(expenseId),
    queryFn: async () => {
      const response = await expenseApi.getExpenseHistory(expenseId);
      if (response && response.success === false) throw new Error(response.error || 'Failed to load history');
      return unwrapEnvelope(response);
    },
    enabled: !!expenseId,
    staleTime: 0,
    gcTime: 2 * 60 * 1000,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: 1,
  });
}

// ── Optimistic Update Helpers ───────────────────────────────────────────────

/** Build optimistic balance map from members and current balances */
function buildBalanceMaps(old) {
  const balancesMap = {};
  (old.balances || []).forEach(b => { balancesMap[b.user_id] = { ...b }; });
  const membersMap = {};
  (old.members || []).forEach(m => { membersMap[m.user_id] = m; });
  return { balancesMap, membersMap };
}

/** Ensure a user exists in the balance map */
function ensureBalance(balancesMap, membersMap, userId, defaultBalance = 0) {
  if (!balancesMap[userId]) {
    const member = membersMap[userId];
    balancesMap[userId] = {
      user_id: userId,
      display_name: member?.display_name || member?.user?.display_name || `User ${userId.slice(0, 6)}`,
      balance: defaultBalance,
      net_balance: defaultBalance,
      is_active: true
    };
  }
}

/** Apply expense impact (credit payer, debit splits) to balance map */
function applyExpenseToBalances(balancesMap, membersMap, paidBy, amount, splits, members, sign = 1) {
  ensureBalance(balancesMap, membersMap, paidBy);
  balancesMap[paidBy].balance += sign * amount;
  balancesMap[paidBy].net_balance = balancesMap[paidBy].balance;

  let effectiveSplits = splits || [];
  if (effectiveSplits.length === 0 && members) {
    const splitAmount = amount / members.length;
    effectiveSplits = members.map(m => ({ user_id: m.user_id, amount: splitAmount }));
  }

  effectiveSplits.forEach(split => {
    const userId = split.user_id;
    const splitAmount = parseFloat(split.amount) || 0;
    ensureBalance(balancesMap, membersMap, userId);
    balancesMap[userId].balance -= sign * splitAmount;
    balancesMap[userId].net_balance = balancesMap[userId].balance;
  });
}

/** Merge server balance data (deltas or full) into existing balances */
function mergeServerBalances(existingBalances, data) {
  if (data.balance_deltas) {
    return applyBalanceDeltas(existingBalances, data.balance_deltas);
  }
  if (data.balances) {
    return (existingBalances || []).map(b => {
      const newBalance = data.balances[b.user_id];
      if (newBalance !== undefined) return { ...b, balance: newBalance, net_balance: newBalance };
      return b;
    });
  }
  return existingBalances;
}

/** Update both group and megaBootstrap caches with a transform function */
function updateBothCaches(queryClient, groupId, groupTransform, megaTransform) {
  queryClient.setQueryData(queryKeys.group(groupId), groupTransform);
  queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
    if (!old?.data?.active_group) return old;
    const updated = megaTransform(old.data.active_group);
    return {
      ...old,
      data: { ...old.data, active_group: { ...old.data.active_group, ...updated } }
    };
  });
}

// ── Mutation Hooks ──────────────────────────────────────────────────────────

/**
 * Create expense with optimistic UI. Uses extreme API when enabled.
 */
export function useCreateExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (expenseData) => {
      if (expenseApi.extremeMode) return unwrapEnvelope(await expenseApi.createExpenseExtreme(expenseData));
      return unwrapEnvelope(await expenseApi.createExpense(expenseData));
    },

    onMutate: async (expenseData) => {
      const groupId = expenseData.group_id;
      await queryClient.cancelQueries({ queryKey: queryKeys.group(groupId) });
      await queryClient.cancelQueries({ queryKey: queryKeys.megaBootstrap(groupId) });

      const previousGroup = queryClient.getQueryData(queryKeys.group(groupId));
      const previousMega = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));

      const optimisticExpense = {
        ...expenseData,
        expense_id: `temp_${Date.now()}`,
        id: `temp_${Date.now()}`,
        created_at: new Date().toISOString(),
        is_deleted: false,
        _optimistic: true
      };

      // Update group cache
      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        if (!old) return old;
        const newExpenses = [optimisticExpense, ...(old.expenses || [])];
        const { balancesMap, membersMap } = buildBalanceMaps(old);
        applyExpenseToBalances(balancesMap, membersMap, expenseData.paid_by,
          parseFloat(expenseData.amount) || 0, expenseData.splits, old.members);
        return { ...old, expenses: newExpenses, balances: Object.values(balancesMap) };
      });

      // Update megaBootstrap cache
      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        const ag = old.data.active_group;
        const newExpenses = [optimisticExpense, ...(ag.expenses || [])];
        const balancesMap = {};
        (ag.balances || []).forEach(b => { balancesMap[b.user_id] = { ...b }; });
        const membersMap = {};
        (ag.members || []).forEach(m => { membersMap[m.user_id] = m; });
        applyExpenseToBalances(balancesMap, membersMap, expenseData.paid_by,
          parseFloat(expenseData.amount) || 0, expenseData.splits, ag.members);
        return {
          ...old,
          data: {
            ...old.data,
            active_group: { ...ag, expenses: newExpenses, balances: Object.values(balancesMap) }
          }
        };
      });

      return { previousGroup, previousMega, groupId };
    },

    onError: (err, variables, context) => {
      if (context?.groupId) {
        if (context.previousGroup) queryClient.setQueryData(queryKeys.group(context.groupId), context.previousGroup);
        if (context.previousMega) queryClient.setQueryData(queryKeys.megaBootstrap(context.groupId), context.previousMega);
      }
    },

    onSuccess: (data, variables) => {
      const groupId = variables.group_id;
      if (!groupId || !data?.expense) return;

      const replaceOptimistic = (expenses) => {
        const newExpenses = (expenses || []).filter(e => !e._optimistic).concat([data.expense]);
        newExpenses.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        return newExpenses;
      };

      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        if (!old) return old;
        return {
          ...old,
          expenses: replaceOptimistic(old.expenses),
          balances: mergeServerBalances(old.balances, data),
          recent_history: data.history_entry ? addHistoryEntry(old.recent_history, data.history_entry) : old.recent_history
        };
      });

      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        const ag = old.data.active_group;
        return {
          ...old,
          data: {
            ...old.data,
            active_group: {
              ...ag,
              expenses: replaceOptimistic(ag.expenses),
              balances: mergeServerBalances(ag.balances, data),
              recent_history: data.history_entry ? addHistoryEntry(ag.recent_history, data.history_entry) : ag.recent_history
            }
          }
        };
      });
    }
  });
}

/**
 * Update expense with optimistic UI. Uses extreme API when enabled.
 */
export function useUpdateExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ expenseId, data }) => {
      if (expenseApi.extremeMode) return unwrapEnvelope(await expenseApi.updateExpenseExtreme(expenseId, data));
      return unwrapEnvelope(await expenseApi.updateExpense(expenseId, data));
    },

    onMutate: async ({ expenseId, data }) => {
      const groupId = data.group_id;
      await queryClient.cancelQueries({ queryKey: queryKeys.group(groupId) });

      const previousGroup = queryClient.getQueryData(queryKeys.group(groupId));
      const previousMega = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));

      const applyUpdate = (expenses, balances, members) => {
        const oldExpense = expenses?.find(e => e.expense_id === expenseId || e.id === expenseId);
        const newExpenses = (expenses || []).map(e =>
          (e.expense_id === expenseId || e.id === expenseId)
            ? { ...e, ...data, updated_at: new Date().toISOString(), _optimistic: true }
            : e
        );

        let newBalances = [...(balances || [])];
        if (oldExpense && (data.amount !== undefined || data.splits !== undefined || data.paid_by !== undefined)) {
          // Reverse old expense impact
          newBalances = newBalances.map(b => {
            const nb = { ...b };
            if (b.user_id === oldExpense.paid_by) nb.balance -= parseFloat(oldExpense.amount) || 0;
            const oldSplit = (oldExpense.splits || []).find(s => s.user_id === b.user_id);
            if (oldSplit) nb.balance += parseFloat(oldSplit.amount) || 0;
            return nb;
          });
          // Apply new expense impact
          const newAmount = parseFloat(data.amount ?? oldExpense.amount) || 0;
          const newPaidBy = data.paid_by ?? oldExpense.paid_by;
          const newSplits = data.splits ?? oldExpense.splits ?? [];
          newBalances = newBalances.map(b => {
            const nb = { ...b };
            if (b.user_id === newPaidBy) nb.balance += newAmount;
            const ns = newSplits.find(s => s.user_id === b.user_id);
            if (ns) nb.balance -= parseFloat(ns.amount) || 0;
            nb.net_balance = nb.balance;
            return nb;
          });
        }

        return { expenses: newExpenses, balances: newBalances };
      };

      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        if (!old?.expenses) return old;
        const updated = applyUpdate(old.expenses, old.balances, old.members);
        return { ...old, ...updated };
      });

      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        const ag = old.data.active_group;
        const updated = applyUpdate(ag.expenses, ag.balances, ag.members);
        return { ...old, data: { ...old.data, active_group: { ...ag, ...updated } } };
      });

      return { previousGroup, previousMega, groupId };
    },

    onError: (err, variables, context) => {
      if (context?.previousGroup && context?.groupId) {
        queryClient.setQueryData(queryKeys.group(context.groupId), context.previousGroup);
        if (context.previousMega) queryClient.setQueryData(queryKeys.megaBootstrap(context.groupId), context.previousMega);
      }
    },

    onSuccess: (data, variables) => {
      const groupId = data?.expense?.group_id || variables.data.group_id;
      if (!groupId) return;

      const updateWithServer = (expenses, balances, history) => {
        const newExpenses = (expenses || []).map(e =>
          (e.expense_id === variables.expenseId || e.id === variables.expenseId)
            ? { ...e, ...data.expense, _optimistic: false }
            : e
        );
        return {
          expenses: newExpenses,
          balances: mergeServerBalances(balances, data),
          recent_history: data.history_entry ? addHistoryEntry(history, data.history_entry) : history
        };
      };

      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        if (!old?.expenses) return old;
        return { ...old, ...updateWithServer(old.expenses, old.balances, old.recent_history) };
      });

      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        const ag = old.data.active_group;
        return { ...old, data: { ...old.data, active_group: { ...ag, ...updateWithServer(ag.expenses, ag.balances, ag.recent_history) } } };
      });
    }
  });
}

/**
 * Delete expense with optimistic UI (soft delete).
 * DON'T reverse balances optimistically - wait for server balance_deltas to avoid double-reversal bug.
 */
export function useDeleteExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ expenseId, groupId }) => {
      if (expenseApi.extremeMode) return unwrapEnvelope(await expenseApi.deleteExpenseExtreme(expenseId, groupId));
      return unwrapEnvelope(await expenseApi.deleteExpense(expenseId));
    },

    onMutate: async ({ expenseId, groupId }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.group(groupId) });
      const previousGroup = queryClient.getQueryData(queryKeys.group(groupId));
      const previousMega = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));

      const markDeleted = (expenses) =>
        (expenses || []).map(e =>
          (e.expense_id === expenseId || e.id === expenseId)
            ? { ...e, is_deleted: true, deleted_at: new Date().toISOString() }
            : e
        );

      // Only mark as deleted, DON'T touch balances (server balance_deltas handles it)
      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        if (!old?.expenses) return old;
        return { ...old, expenses: markDeleted(old.expenses) };
      });

      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        return {
          ...old,
          data: { ...old.data, active_group: { ...old.data.active_group, expenses: markDeleted(old.data.active_group.expenses) } }
        };
      });

      return { previousGroup, previousMega, groupId };
    },

    onError: (err, variables, context) => {
      if (context?.previousGroup && context?.groupId) {
        queryClient.setQueryData(queryKeys.group(context.groupId), context.previousGroup);
        if (context.previousMega) queryClient.setQueryData(queryKeys.megaBootstrap(context.groupId), context.previousMega);
      }
    },

    onSuccess: (data, { expenseId, groupId }) => {
      if (!groupId) return;

      const applyServerData = (balances, history) => ({
        balances: mergeServerBalances(balances, data || {}),
        recent_history: data?.history_entry ? addHistoryEntry(history, data.history_entry) : history
      });

      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        if (!old) return old;
        return { ...old, ...applyServerData(old.balances, old.recent_history) };
      });

      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        const ag = old.data.active_group;
        return { ...old, data: { ...old.data, active_group: { ...ag, ...applyServerData(ag.balances, ag.recent_history) } } };
      });
    },
  });
}

/**
 * Create settlement with optimistic balance updates.
 */
export function useCreateSettlementMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (settlementData) => {
      if (expenseApi.extremeMode) return unwrapEnvelope(await expenseApi.createSettlementExtreme(settlementData));
      return unwrapEnvelope(await expenseApi.createSettlement(settlementData));
    },

    onMutate: async (settlement) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.group(settlement.group_id) });
      const previousGroup = queryClient.getQueryData(queryKeys.group(settlement.group_id));

      const calculateOptimisticBalances = (balances) => {
        if (!balances) return balances;
        const amount = parseFloat(settlement.amount);
        return balances.map(b => {
          const nb = { ...b };
          if (b.user_id === settlement.from_user) { nb.balance += amount; nb.net_balance += amount; }
          if (b.user_id === settlement.to_user) { nb.balance -= amount; nb.net_balance -= amount; }
          return nb;
        });
      };

      queryClient.setQueryData(queryKeys.group(settlement.group_id), (old) => {
        if (!old?.balances) return old;
        const newBalances = calculateOptimisticBalances(old.balances);
        return { ...old, balances: newBalances, is_settled: newBalances.every(b => Math.abs(b.balance) < 0.01) };
      });

      queryClient.setQueryData(queryKeys.megaBootstrap(settlement.group_id), (old) => {
        if (!old?.data?.active_group?.balances) return old;
        const newBalances = calculateOptimisticBalances(old.data.active_group.balances);
        return {
          ...old,
          data: {
            ...old.data,
            active_group: {
              ...old.data.active_group,
              balances: newBalances,
              is_settled: newBalances.every(b => Math.abs(b.balance) < 0.01)
            }
          }
        };
      });

      return { previousGroup };
    },

    onError: (err, settlement, context) => {
      if (context?.previousGroup) {
        queryClient.setQueryData(queryKeys.group(settlement.group_id), context.previousGroup);
      }
    },

    onSuccess: async (data, variables) => {
      const mergeBalances = (existingBalances) => {
        if (!data?.balances || !existingBalances) return existingBalances;
        return existingBalances.map(b => {
          const nb = data.balances[b.user_id];
          if (nb !== undefined) return { ...b, balance: nb, net_balance: nb };
          return b;
        });
      };

      if (data?.balances && variables.group_id) {
        queryClient.setQueryData(queryKeys.group(variables.group_id), (old) => {
          if (!old) return old;
          const updated = mergeBalances(old.balances);
          return { ...old, balances: updated, is_settled: updated?.every(b => Math.abs(b.balance) < 0.01) };
        });

        queryClient.setQueryData(queryKeys.megaBootstrap(variables.group_id), (old) => {
          if (!old?.data?.active_group?.balances) return old;
          const updated = mergeBalances(old.data.active_group.balances);
          return {
            ...old,
            data: {
              ...old.data,
              active_group: {
                ...old.data.active_group,
                balances: updated,
                is_settled: updated?.every(b => Math.abs(b.balance) < 0.01)
              }
            }
          };
        });
      }

      await queryClient.invalidateQueries({
        queryKey: queryKeys.settlements(variables.group_id),
        refetchType: 'active'
      });
    },
  });
}

/**
 * Create group. Uses extreme API when enabled.
 */
export function useCreateGroupMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (groupData) => {
      if (expenseApi.extremeMode) return unwrapEnvelope(await expenseApi.createGroupExtreme(groupData));
      return unwrapEnvelope(await expenseApi.createGroup(groupData));
    },
    onSuccess: async (result) => {
      const newGroupId = result?.group?.group_id || result?.group_id;
      const newGroup = result?.group;

      if (newGroupId && newGroup) {
        const allMembersMap = {};
        if (newGroup.members && Array.isArray(newGroup.members)) {
          newGroup.members.forEach(member => {
            if (member.user_id) {
              allMembersMap[member.user_id] = {
                user_id: member.user_id,
                display_name: member.user?.display_name || member.display_name || 'Unknown',
                email: member.user?.email || member.email,
                role: member.role
              };
            }
          });
        }

        // Pre-populate mega-bootstrap cache for the new group
        queryClient.setQueryData(queryKeys.megaBootstrap(newGroupId), {
          success: true,
          data: {
            groups: [],
            invitations: [],
            active_group: {
              group: newGroup,
              members: newGroup.members || [],
              balances: newGroup.balances || [],
              expenses: [],
              settlements: [],
              invitations: [],
              all_members_map: allMembersMap
            }
          },
          meta: { source: 'create_group_optimistic' }
        });
      }

      await queryClient.invalidateQueries({ queryKey: queryKeys.groups, refetchType: 'active' });
      await queryClient.invalidateQueries({ queryKey: ['mega-bootstrap'], refetchType: 'active' });
    },
  });
}

/**
 * Delete group and clean up all related caches.
 */
export function useDeleteGroupMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (groupId) => unwrapEnvelope(await expenseApi.deleteGroup(groupId)),
    onSuccess: async (data, groupId) => {
      queryClient.removeQueries({ queryKey: queryKeys.group(groupId) });
      queryClient.removeQueries({ queryKey: queryKeys.megaBootstrap(groupId) });
      queryClient.removeQueries({ queryKey: queryKeys.expenses(groupId) });
      queryClient.removeQueries({ queryKey: queryKeys.settlements(groupId) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.groups, refetchType: 'active' });
      await queryClient.invalidateQueries({ queryKey: queryKeys.megaBootstrap(), refetchType: 'active' });
    },
    onError: () => {},
  });
}

/**
 * Accept invitation with optimistic removal from list.
 */
export function useAcceptInvitationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (invitationId) => {
      if (expenseApi.extremeMode) return unwrapEnvelope(await expenseApi.acceptInvitationExtreme(invitationId));
      return unwrapEnvelope(await expenseApi.acceptInvitation(invitationId));
    },

    onMutate: async (invitationId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.invitations });
      const previousInvitations = queryClient.getQueryData(queryKeys.invitations);
      queryClient.setQueryData(queryKeys.invitations, (old) => {
        if (!old?.invitations) return old;
        return { ...old, invitations: old.invitations.filter(inv => (inv.id || inv.invitation_id) !== invitationId) };
      });
      return { previousInvitations };
    },

    onError: (err, invitationId, context) => {
      if (context?.previousInvitations) queryClient.setQueryData(queryKeys.invitations, context.previousInvitations);
    },

    onSuccess: async (data) => {
      const groupId = data?.group_id || data?.group?.group_id || data?.group?.id;
      await queryClient.invalidateQueries({ queryKey: queryKeys.invitations, refetchType: 'active' });
      await queryClient.invalidateQueries({ queryKey: queryKeys.groups, refetchType: 'active' });
      if (groupId) {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: queryKeys.group(groupId), refetchType: 'active' }),
          queryClient.invalidateQueries({ queryKey: queryKeys.megaBootstrap(groupId), refetchType: 'active' })
        ]);
      }
      await queryClient.invalidateQueries({ queryKey: ['mega-bootstrap'], refetchType: 'active' });
    },
  });
}

/**
 * Decline invitation with optimistic removal from list.
 */
export function useDeclineInvitationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (invitationId) => unwrapEnvelope(await expenseApi.declineInvitation(invitationId)),

    onMutate: async (invitationId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.invitations });
      const previousInvitations = queryClient.getQueryData(queryKeys.invitations);
      queryClient.setQueryData(queryKeys.invitations, (old) => {
        if (!old?.invitations) return old;
        return { ...old, invitations: old.invitations.filter(inv => (inv.id || inv.invitation_id) !== invitationId) };
      });
      return { previousInvitations };
    },

    onError: (err, invitationId, context) => {
      if (context?.previousInvitations) queryClient.setQueryData(queryKeys.invitations, context.previousInvitations);
    },

    onSuccess: async () => {
      setTimeout(async () => {
        await queryClient.invalidateQueries({ queryKey: queryKeys.invitations });
      }, 500);
    },
  });
}

/**
 * Send invitation with optimistic pending list update.
 */
export function useSendInvitationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (invitationData) => {
      if (expenseApi.extremeMode) {
        return unwrapEnvelope(await expenseApi.addMemberExtreme(invitationData.group_id, { email: invitationData.invited_email }));
      }
      return unwrapEnvelope(await expenseApi.sendInvitation(invitationData));
    },

    onMutate: async (invitationData) => {
      const groupId = invitationData.group_id;
      await queryClient.cancelQueries({ queryKey: queryKeys.megaBootstrap(groupId) });
      const previousMega = queryClient.getQueryData(queryKeys.megaBootstrap(groupId));

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

      queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
        if (!old?.data?.active_group) return old;
        return {
          ...old,
          data: {
            ...old.data,
            active_group: {
              ...old.data.active_group,
              invitations: [...(old.data.active_group.invitations || []), optimisticInvitation]
            }
          }
        };
      });

      return { previousMega, groupId };
    },

    onError: (err, variables, context) => {
      if (context?.previousMega && context?.groupId) {
        queryClient.setQueryData(queryKeys.megaBootstrap(context.groupId), context.previousMega);
      }
    },

    onSuccess: async (data, variables) => {
      const groupId = variables.group_id;
      if (groupId && data?.invitation) {
        queryClient.setQueryData(queryKeys.megaBootstrap(groupId), (old) => {
          if (!old?.data?.active_group) return old;
          const newInvitations = (old.data.active_group.invitations || [])
            .filter(inv => !inv._optimistic)
            .concat([{
              ...data.invitation,
              id: data.invitation.invitation_id || data.invitation.id,
              invitation_id: data.invitation.invitation_id || data.invitation.id
            }]);
          return {
            ...old,
            data: { ...old.data, active_group: { ...old.data.active_group, invitations: newInvitations } }
          };
        });
      }

      await queryClient.invalidateQueries({
        queryKey: ['mega-bootstrap'],
        refetchType: 'none'
      });
    }
  });
}

// ============================================================================
// LEGACY-COMPATIBLE ADAPTER HOOKS
// Backward-compatible wrappers around the React Query hooks above.
// These present the same API surface as the old useExpenseData.js hooks
// so ExpenseManager.jsx can swap imports without any code changes.
// ============================================================================

/**
 * Auth state hook. Listens to sqlAuthService and syncs token into expenseApi.
 */
export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = authService.onAuthStateChanged(async (user) => {
      if (user) {
        setCurrentUser(user);
        setIsAuthenticated(true);
      } else {
        setCurrentUser(null);
        setIsAuthenticated(false);
      }
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  return { isAuthenticated, currentUser, loading };
}

/**
 * Groups list with instant-update helpers.
 * Wraps useGroupsQuery() and exposes setQueryData-based update callbacks.
 */
export function useGroups() {
  const queryClient = useQueryClient();
  const { data, isLoading, error, refetch } = useFetchGroups();
  const groups = data?.groups || [];

  const updateGroupsFromResponse = useCallback((responseGroups) => {
    if (responseGroups && Array.isArray(responseGroups)) {
      queryClient.setQueryData(queryKeys.groups, { success: true, groups: responseGroups });
    }
  }, [queryClient]);

  const setGroups = useCallback((newGroups) => {
    if (typeof newGroups === 'function') {
      queryClient.setQueryData(queryKeys.groups, (old) => ({
        ...old,
        groups: newGroups(old?.groups || [])
      }));
    } else {
      queryClient.setQueryData(queryKeys.groups, (old) => ({ ...old, groups: newGroups }));
    }
  }, [queryClient]);

  return {
    groups,
    loading: isLoading,
    error: error?.message || null,
    refetch,
    updateGroupsFromResponse,
    setGroups
  };
}

/**
 * Single group detail with instant-update helpers.
 * Wraps useGroupQuery() and exposes setQueryData-based update callbacks.
 */
export function useGroupDetail(groupId) {
  const queryClient = useQueryClient();
  const { data, isLoading, error, refetch } = useGroupQuery(groupId, { enabled: !!groupId });

  const group = data?.group || null;
  const members = data?.members || group?.members || [];
  const expenses = data?.expenses || group?.expenses || [];
  const balances = data?.balances || group?.balances || [];
  const settlements = data?.settlements || group?.settlements || [];
  const invitations = data?.invitations || group?.invitations || [];

  const updateFromResponse = useCallback((responseData) => {
    if (!responseData || !groupId) return;
    queryClient.setQueryData(queryKeys.group(groupId), (old) => {
      const resp = responseData.group ? responseData : { group: responseData, ...responseData };
      return { ...old, ...resp };
    });
  }, [queryClient, groupId]);

  const updateExpensesAndBalances = useCallback((newExpenses, newBalances) => {
    if (!groupId) return;
    queryClient.setQueryData(queryKeys.group(groupId), (old) => ({
      ...old,
      expenses: newExpenses || old?.expenses || [],
      balances: newBalances || old?.balances || []
    }));
  }, [queryClient, groupId]);

  const updateSettlementsAndBalances = useCallback((newSettlements, newBalances) => {
    if (!groupId) return;
    queryClient.setQueryData(queryKeys.group(groupId), (old) => ({
      ...old,
      settlements: newSettlements || old?.settlements || [],
      balances: newBalances || old?.balances || []
    }));
  }, [queryClient, groupId]);

  const updateMembers = useCallback((newMembers) => {
    if (!groupId) return;
    queryClient.setQueryData(queryKeys.group(groupId), (old) => ({
      ...old,
      members: newMembers || old?.members || []
    }));
  }, [queryClient, groupId]);

  const setData = useCallback((newData) => {
    if (!groupId) return;
    if (typeof newData === 'function') {
      queryClient.setQueryData(queryKeys.group(groupId), (old) => {
        const result = newData(old || {});
        return { ...old, ...result };
      });
    } else {
      queryClient.setQueryData(queryKeys.group(groupId), (old) => ({ ...old, ...newData }));
    }
  }, [queryClient, groupId]);

  return {
    group, members, expenses, balances, settlements, invitations,
    loading: isLoading,
    error: error?.message || null,
    refetch,
    updateFromResponse,
    updateExpensesAndBalances,
    updateSettlementsAndBalances,
    updateMembers,
    setData
  };
}

/**
 * Pending invitations with instant-update helpers.
 * Wraps useInvitationsQuery().
 */
export function useInvitations() {
  const queryClient = useQueryClient();
  const { data, isLoading, error, refetch } = useInvitationsQuery();
  const invitations = data?.invitations || [];

  const updateInvitationsFromResponse = useCallback((responseInvitations) => {
    if (responseInvitations && Array.isArray(responseInvitations)) {
      const pendingOnly = responseInvitations.filter(inv =>
        inv.status === 'pending' || inv.status === 'PENDING'
      );
      queryClient.setQueryData(queryKeys.invitations, { success: true, invitations: pendingOnly });
    }
  }, [queryClient]);

  const removeInvitation = useCallback((invitationId) => {
    queryClient.setQueryData(queryKeys.invitations, (old) => ({
      ...old,
      invitations: (old?.invitations || []).filter(inv =>
        inv.invitation_id !== invitationId && inv.id !== invitationId
      )
    }));
  }, [queryClient]);

  const setInvitations = useCallback((newInvitations) => {
    if (typeof newInvitations === 'function') {
      queryClient.setQueryData(queryKeys.invitations, (old) => ({
        ...old,
        invitations: newInvitations(old?.invitations || [])
      }));
    } else {
      queryClient.setQueryData(queryKeys.invitations, (old) => ({
        ...old,
        invitations: newInvitations
      }));
    }
  }, [queryClient]);

  return {
    invitations,
    loading: isLoading,
    error: error?.message || null,
    refetch,
    updateInvitationsFromResponse,
    removeInvitation,
    setInvitations
  };
}

/**
 * Personal expenses with optimistic delete / rollback.
 * Uses a dedicated React Query key since no existing hook covers this.
 */
export function usePersonalExpenses() {
  const queryClient = useQueryClient();
  const personalKey = ['personalExpenses'];

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: personalKey,
    queryFn: async () => unwrapEnvelope(await expenseApi.getUserExpenses({ personal_only: true })),
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });

  const expenses = data?.expenses || [];

  const setExpenses = useCallback((newExpenses) => {
    if (typeof newExpenses === 'function') {
      queryClient.setQueryData(personalKey, (old) => ({
        ...old,
        expenses: newExpenses(old?.expenses || [])
      }));
    } else {
      queryClient.setQueryData(personalKey, (old) => ({ ...old, expenses: newExpenses }));
    }
  }, [queryClient]);

  const markAsDeleted = useCallback((expenseId) => {
    queryClient.setQueryData(personalKey, (old) => ({
      ...old,
      expenses: (old?.expenses || []).map(e =>
        (e.id === expenseId || e.expense_id === expenseId)
          ? { ...e, is_deleted: true, deleted_at: new Date().toISOString() }
          : e
      )
    }));
  }, [queryClient]);

  const rollbackDelete = useCallback((expenseId) => {
    queryClient.setQueryData(personalKey, (old) => ({
      ...old,
      expenses: (old?.expenses || []).map(e => {
        if (e.id === expenseId || e.expense_id === expenseId) {
          const { is_deleted, deleted_at, ...rest } = e;
          return { ...rest, is_deleted: false };
        }
        return e;
      })
    }));
  }, [queryClient]);

  return {
    expenses,
    loading: isLoading,
    error: error?.message || null,
    refetch,
    setExpenses,
    markAsDeleted,
    rollbackDelete
  };
}

/**
 * Simple mutation wrappers (legacy interface).
 * These wrap the React Query mutation hooks above but present the
 * callback-style API that useExpenseData.js used.
 */
export function useGroupMutations(onSuccess) {
  const createMut = useCreateGroupMutation();
  const deleteMut = useDeleteGroupMutation();

  const createGroup = useCallback(async (groupData) => {
    const result = await createMut.mutateAsync(groupData);
    if (onSuccess) onSuccess('create', result);
    return result;
  }, [createMut, onSuccess]);

  const updateGroup = useCallback(async (groupId, updates) => {
    const result = await expenseApi.updateGroup(groupId, updates);
    if (onSuccess) onSuccess('update', result);
    return result;
  }, [onSuccess]);

  const deleteGroup = useCallback(async (groupId) => {
    const result = await deleteMut.mutateAsync(groupId);
    if (onSuccess) onSuccess('delete', result, groupId);
    return result;
  }, [deleteMut, onSuccess]);

  return {
    createGroup, updateGroup, deleteGroup,
    loading: createMut.isPending || deleteMut.isPending,
    error: createMut.error?.message || deleteMut.error?.message || null
  };
}

export function useExpenseMutations(onSuccess) {
  const createMut = useCreateExpenseMutation();
  const updateMut = useUpdateExpenseMutation();
  const deleteMut = useDeleteExpenseMutation();

  const createExpense = useCallback(async (expenseData) => {
    const result = await createMut.mutateAsync(expenseData);
    if (onSuccess) onSuccess('create', result);
    return result;
  }, [createMut, onSuccess]);

  const updateExpense = useCallback(async (expenseId, updates) => {
    const result = await updateMut.mutateAsync({ expenseId, data: updates });
    if (onSuccess) onSuccess('update', result);
    return result;
  }, [updateMut, onSuccess]);

  const deleteExpense = useCallback(async (expenseId, groupId) => {
    const result = await deleteMut.mutateAsync({ expenseId, groupId });
    if (onSuccess) onSuccess('delete', result, expenseId);
    return result;
  }, [deleteMut, onSuccess]);

  return {
    createExpense, updateExpense, deleteExpense,
    loading: createMut.isPending || updateMut.isPending || deleteMut.isPending,
    error: createMut.error?.message || updateMut.error?.message || deleteMut.error?.message || null
  };
}

export function useSettlementMutations(onSuccess) {
  const createMut = useCreateSettlementMutation();

  const createSettlement = useCallback(async (settlementData) => {
    const result = await createMut.mutateAsync(settlementData);
    if (onSuccess) onSuccess('create', result);
    return result;
  }, [createMut, onSuccess]);

  return {
    createSettlement,
    loading: createMut.isPending,
    error: createMut.error?.message || null
  };
}

export function useInvitationMutations(onSuccess) {
  const sendMut = useSendInvitationMutation();
  const acceptMut = useAcceptInvitationMutation();
  const declineMut = useDeclineInvitationMutation();

  const sendInvitation = useCallback(async (invitationData) => {
    const result = await sendMut.mutateAsync(invitationData);
    if (onSuccess) onSuccess('send', result);
    return result;
  }, [sendMut, onSuccess]);

  const acceptInvitation = useCallback(async (invitationId) => {
    const result = await acceptMut.mutateAsync(invitationId);
    if (onSuccess) onSuccess('accept', result, invitationId);
    return result;
  }, [acceptMut, onSuccess]);

  const declineInvitation = useCallback(async (invitationId) => {
    const result = await declineMut.mutateAsync(invitationId);
    if (onSuccess) onSuccess('decline', result, invitationId);
    return result;
  }, [declineMut, onSuccess]);

  return {
    sendInvitation, acceptInvitation, declineInvitation,
    loading: sendMut.isPending || acceptMut.isPending || declineMut.isPending,
    error: sendMut.error?.message || acceptMut.error?.message || declineMut.error?.message || null
  };
}

/**
 * Combined orchestrator hook (legacy interface).
 * Merges all sub-hooks into one flat object.
 */
export function useExpenseManager(activeGroupId = null) {
  const auth = useAuth();
  const groupsData = useGroups();
  const groupDetail = useGroupDetail(activeGroupId);
  const invitationsData = useInvitations();
  const personalExpensesData = usePersonalExpenses();

  const handleGroupMutationSuccess = useCallback(() => {
    groupsData.refetch();
  }, [groupsData]);

  const handleExpenseMutationSuccess = useCallback(() => {
    if (activeGroupId) groupDetail.refetch();
    else personalExpensesData.refetch();
  }, [activeGroupId, groupDetail, personalExpensesData]);

  const handleSettlementMutationSuccess = useCallback(() => {
    if (activeGroupId) groupDetail.refetch();
  }, [activeGroupId, groupDetail]);

  const handleInvitationMutationSuccess = useCallback(() => {
    invitationsData.refetch();
    groupsData.refetch();
    if (activeGroupId) groupDetail.refetch();
  }, [invitationsData, groupsData, activeGroupId, groupDetail]);

  const groupMutations = useGroupMutations(handleGroupMutationSuccess);
  const expenseMutations = useExpenseMutations(handleExpenseMutationSuccess);
  const settlementMutations = useSettlementMutations(handleSettlementMutationSuccess);
  const invitationMutations = useInvitationMutations(handleInvitationMutationSuccess);

  const refetchAll = useCallback(() => {
    groupsData.refetch();
    invitationsData.refetch();
    if (activeGroupId) groupDetail.refetch();
    else personalExpensesData.refetch();
  }, [groupsData, invitationsData, activeGroupId, groupDetail, personalExpensesData]);

  return {
    ...auth,
    groups: groupsData.groups,
    groupsLoading: groupsData.loading,
    refetchGroups: groupsData.refetch,
    activeGroup: groupDetail.group,
    members: groupDetail.members,
    expenses: groupDetail.expenses,
    balances: groupDetail.balances,
    settlements: groupDetail.settlements,
    groupInvitations: groupDetail.invitations,
    groupLoading: groupDetail.loading,
    refetchGroup: groupDetail.refetch,
    personalExpenses: personalExpensesData.expenses,
    personalExpensesLoading: personalExpensesData.loading,
    refetchPersonalExpenses: personalExpensesData.refetch,
    markPersonalAsDeleted: personalExpensesData.markAsDeleted,
    rollbackPersonalDelete: personalExpensesData.rollbackDelete,
    invitations: invitationsData.invitations,
    invitationsLoading: invitationsData.loading,
    refetchInvitations: invitationsData.refetch,
    ...groupMutations,
    ...expenseMutations,
    ...settlementMutations,
    ...invitationMutations,
    refetchAll
  };
}
