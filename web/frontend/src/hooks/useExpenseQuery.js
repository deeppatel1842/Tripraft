import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import expenseApi from '../services/expenseApi';

// Query keys for cache management
export const queryKeys = {
  user: ['user'],
  groups: ['groups'],
  group: (groupId) => ['group', groupId],
  expenses: (groupId) => ['expenses', groupId],
  settlements: (groupId) => ['settlements', groupId],
  invitations: ['invitations'],
};

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
 * After mutations, removeQueries() forces fresh fetch
 * 
 * Multi-User Sync Strategy:
 * - staleTime: 0 = Always consider data stale
 * - refetchOnWindowFocus: true = Check server when user returns to tab
 * - refetchInterval: 30s = Background polling for multi-user changes
 * 
 * This ensures User B sees when User A deletes a group within 30 seconds
 * without manual refresh. Backend Redis cache is already invalidated for all members.
 */
export function useGroupsQuery() {
  return useQuery({
    queryKey: queryKeys.groups,
    queryFn: () => expenseApi.getUserGroups(true, true), // summary mode + bypass cache
    staleTime: 0, // CRITICAL: Always consider data stale
    gcTime: 5 * 60 * 1000, // 5 minutes retention
    refetchOnWindowFocus: true, // Refetch when user returns to tab
    refetchInterval: 30 * 1000, // MULTI-USER FIX: Poll every 30 seconds for group changes
    placeholderData: keepPreviousData, // Prevent flicker during refetch
  });
}

/**
 * Hook for fetching a single group with full details
 * 
 * Strategy: Always bypass backend cache to ensure fresh data after mutations
 * Frontend cache (1s stale time) handles speed for quick re-visits
 */
export function useGroupQuery(groupId, options = {}) {
  return useQuery({
    queryKey: queryKeys.group(groupId),
    queryFn: async () => {
      // Always bypass backend cache to ensure fresh data
      // Frontend React Query cache (1s stale) handles performance
      const result = await expenseApi.getGroupFull(groupId, true);
      console.log('📥 Fetched group data: 🔥 FRESH', result?.balances?.length || 0, 'balances');
      return result;
    },
    enabled: !!groupId, // Only run if groupId exists
    staleTime: 1 * 1000, // 1 second - frontend cache for quick re-visits
    gcTime: 5 * 60 * 1000, // 5 minutes - keep data in cache
    placeholderData: keepPreviousData, // Keep previous data during refetch to prevent flicker
  });
}

/**
 * Hook for fetching expenses for a group
 */
export function useExpensesQuery(groupId) {
  return useQuery({
    queryKey: queryKeys.expenses(groupId),
    queryFn: () => expenseApi.getExpenses(groupId),
    enabled: !!groupId,
    staleTime: 1 * 60 * 1000, // 1 minute
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
 * Hook for fetching pending invitations
 * After acceptance, removeQueries() forces fresh fetch
 * 
 * Multi-User Sync Strategy:
 * - staleTime: 0 = Always fetch fresh data
 * - refetchOnWindowFocus: true = Check server when owner returns to tab
 * - refetchInterval: 20s = Poll for invitation changes (accepts/rejects)
 * 
 * This ensures group owner sees updated pending list when member accepts
 */
export function useInvitationsQuery() {
  return useQuery({
    queryKey: queryKeys.invitations,
    queryFn: () => expenseApi.getPendingInvitations(),
    staleTime: 0, // CRITICAL: Always fetch fresh data (no caching)
    gcTime: 5 * 60 * 1000, // 5 minutes retention
    refetchOnWindowFocus: true, // Refetch when user returns to tab
    refetchInterval: 20 * 1000, // MULTI-USER FIX: Poll every 20 seconds for invitation changes
  });
}

/**
 * Hook for creating a new expense
 */
export function useCreateExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (expenseData) => expenseApi.createExpense(expenseData),
    onSuccess: async (data, variables) => {
      console.log('💾 Expense created, forcing fresh data fetch...');
      
      if (variables.group_id) {
        // Force clear cached data by setting to undefined
        queryClient.setQueryData(queryKeys.group(variables.group_id), undefined);
        queryClient.setQueryData(queryKeys.expenses(variables.group_id), undefined);
        
        // Invalidate and force immediate refetch
        await Promise.all([
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.group(variables.group_id),
            refetchType: 'active'
          }),
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.expenses(variables.group_id),
            refetchType: 'active'
          }),
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.groups,
            refetchType: 'active'
          })
        ]);
      }
      
      console.log('✅ Fresh data loaded after create');
    },
  });
}

/**
 * Hook for updating an expense
 */
export function useUpdateExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ expenseId, data }) => expenseApi.updateExpense(expenseId, data),
    onSuccess: async (data, variables) => {
      console.log('✏️ Expense updated, forcing fresh data fetch...');
      
      // Get group_id from response (reliable) or variables (fallback)
      const groupId = data?.expense?.group_id || variables.data.group_id;
      
      if (groupId) {
        // Force clear cached data by setting to undefined
        queryClient.setQueryData(queryKeys.group(groupId), undefined);
        queryClient.setQueryData(queryKeys.expenses(groupId), undefined);
        
        // Invalidate and force immediate refetch
        await Promise.all([
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.group(groupId),
            refetchType: 'active'
          }),
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.expenses(groupId),
            refetchType: 'active'
          }),
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.groups,
            refetchType: 'active'
          })
        ]);
      }
      
      console.log('✅ Fresh data loaded after edit');
    },
  });
}

/**
 * Hook for deleting an expense
 */
export function useDeleteExpenseMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (expenseId) => expenseApi.deleteExpense(expenseId),
    onSuccess: async (data, expenseId, context) => {
      console.log('❌ Expense deleted, forcing fresh data fetch...');
      
      // Get group_id from response (added in backend update) or context
      const groupId = data?.group_id || context?.groupId;
      
      if (groupId) {
        // Force clear cached data by setting to undefined
        queryClient.setQueryData(queryKeys.group(groupId), undefined);
        queryClient.setQueryData(queryKeys.expenses(groupId), undefined);
        
        // Invalidate and force immediate refetch
        await Promise.all([
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.group(groupId),
            refetchType: 'active'
          }),
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.expenses(groupId),
            refetchType: 'active'
          }),
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.groups,
            refetchType: 'active'
          })
        ]);
      }
      
      console.log('✅ Cache invalidated after delete');
    },
  });
}

/**
 * Hook for creating a settlement
 */
export function useCreateSettlementMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (settlementData) => expenseApi.createSettlement(settlementData),
    onSuccess: async (data, variables) => {
      console.log('💰 Settlement created, forcing fresh data fetch...');
      
      // Force clear cached data
      queryClient.setQueryData(queryKeys.group(variables.group_id), undefined);
      queryClient.setQueryData(queryKeys.expenses(variables.group_id), undefined);
      queryClient.setQueryData(queryKeys.settlements(variables.group_id), undefined);
      
      // Invalidate and force immediate refetch
      await Promise.all([
        queryClient.invalidateQueries({ 
          queryKey: queryKeys.group(variables.group_id),
          refetchType: 'active'
        }),
        queryClient.invalidateQueries({ 
          queryKey: queryKeys.settlements(variables.group_id),
          refetchType: 'active'
        }),
        queryClient.invalidateQueries({ 
          queryKey: queryKeys.groups,
          refetchType: 'active'
        })
      ]);
      
      console.log('✅ Fresh data loaded after settlement');
    },
  });
}

/**
 * Hook for creating a new group
 */
export function useCreateGroupMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (groupData) => expenseApi.createGroup(groupData),
    onSuccess: async () => {
      console.log('👥 Group created, forcing fresh data fetch...');
      
      // Force clear cached groups list
      queryClient.setQueryData(queryKeys.groups, undefined);
      
      // Invalidate and force immediate refetch
      await queryClient.invalidateQueries({ 
        queryKey: queryKeys.groups,
        refetchType: 'active'
      });
      
      console.log('✅ Fresh groups list loaded');
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
      console.log('🗑️ Group deleted, clearing all caches...');
      
      // Step 1: Remove specific group data
      queryClient.removeQueries({ queryKey: queryKeys.group(groupId) });
      queryClient.removeQueries({ queryKey: queryKeys.expenses(groupId) });
      queryClient.removeQueries({ queryKey: queryKeys.settlements(groupId) });
      
      // Step 2: Invalidate groups list
      await queryClient.invalidateQueries({ queryKey: queryKeys.groups });
      
      // Step 3: Force immediate refetch
      await queryClient.refetchQueries({ 
        queryKey: queryKeys.groups,
        type: 'active'
      });
      
      console.log('✅ Groups list refreshed');
    },
    onError: (err) => {
      console.error('❌ Failed to delete group:', err);
    }
  });
}

/**
 * Hook for accepting an invitation
 */
export function useAcceptInvitationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (invitationId) => expenseApi.acceptInvitation(invitationId),
    onSuccess: async () => {
      console.log('💌 Invitation accepted, clearing all caches...');
      
      // Step 1: Invalidate all related caches FIRST
      await queryClient.invalidateQueries({ queryKey: queryKeys.invitations });
      await queryClient.invalidateQueries({ queryKey: queryKeys.groups });
      
      // Step 2: Force immediate refetch (no background)
      await queryClient.refetchQueries({ 
        queryKey: queryKeys.invitations,
        type: 'active'
      });
      
      await queryClient.refetchQueries({ 
        queryKey: queryKeys.groups,
        type: 'active'
      });
      
      console.log('✅ Invitations and groups refetched successfully');
    },
    onError: (err) => {
      console.error('❌ Failed to accept invitation:', err);
    }
  });
}

/**
 * Hook for declining an invitation
 */
export function useDeclineInvitationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (invitationId) => expenseApi.declineInvitation(invitationId),
    onSuccess: async () => {
      console.log('❌ Invitation declined, refreshing list...');
      
      // Force clear cached invitations
      queryClient.setQueryData(queryKeys.invitations, undefined);
      
      // Force immediate refetch
      await queryClient.invalidateQueries({ 
        queryKey: queryKeys.invitations,
        refetchType: 'active'
      });
      
      console.log('✅ Invitations list refreshed');
    },
  });
}
