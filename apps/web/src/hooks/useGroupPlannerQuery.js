// Purpose: Provides reusable React state/query behavior for Group Planner Query.
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import groupPlannerApi from '../services/groupPlannerApi';

// Cache key factory — consistent keys for invalidation
export const gpKeys = {
  all:       ['group-planner'],
  groups:    () => [...gpKeys.all, 'groups'],
  group:     (id) => [...gpKeys.all, 'group', id],
  places:    (groupId) => [...gpKeys.all, 'places', groupId],
  polls:     (groupId) => [...gpKeys.all, 'polls', groupId],
  checklist: (groupId) => [...gpKeys.all, 'checklist', groupId],
  members:   (groupId) => [...gpKeys.all, 'members', groupId],
  expenses:  (groupId) => [...gpKeys.all, 'expenses', groupId],
  vault:     (groupId) => [...gpKeys.all, 'vault', groupId],
  activities:(groupId) => [...gpKeys.all, 'activities', groupId],
  destPlaces:(dest) => [...gpKeys.all, 'dest-places', dest],
  destEvents:(dest) => [...gpKeys.all, 'dest-events', dest],
};

// ── Query Hooks ─────────────────────────────────────────────────────────────

export function useGroups() {
  return useQuery({
    queryKey: gpKeys.groups(),
    queryFn: () => groupPlannerApi.getUserGroups(),
    staleTime: 30_000,
  });
}

export function useGroupDetail(groupId) {
  return useQuery({
    queryKey: gpKeys.group(groupId),
    queryFn: () => groupPlannerApi.getGroup(groupId),
    enabled: !!groupId,
    staleTime: 15_000,
  });
}

export function useGroupPlaces(groupId) {
  return useQuery({
    queryKey: gpKeys.places(groupId),
    queryFn: () => groupPlannerApi.getGroupPlaces(groupId),
    enabled: !!groupId,
    staleTime: 30_000,
  });
}

export function useGroupPolls(groupId) {
  return useQuery({
    queryKey: gpKeys.polls(groupId),
    queryFn: () => groupPlannerApi.getGroupPolls(groupId),
    enabled: !!groupId,
    staleTime: 30_000,
  });
}

export function useGroupMembers(groupId) {
  return useQuery({
    queryKey: gpKeys.members(groupId),
    queryFn: () => groupPlannerApi.getGroupMembers(groupId),
    enabled: !!groupId,
    staleTime: 30_000,
  });
}

export function useExpenseSummary(groupId) {
  return useQuery({
    queryKey: gpKeys.expenses(groupId),
    queryFn: () => groupPlannerApi.getExpenseSummary(groupId),
    enabled: !!groupId,
    staleTime: 60_000,
  });
}

// ── Mutation Hooks ──────────────────────────────────────────────────────────

export function useAddPlace(groupId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (placeData) => groupPlannerApi.addPlace(groupId, placeData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gpKeys.places(groupId) });
    },
  });
}

export function useCreatePoll(groupId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (pollData) => groupPlannerApi.createPoll(groupId, pollData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gpKeys.polls(groupId) });
    },
  });
}

export function useToggleChecklistItem(groupId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId) => groupPlannerApi.toggleChecklistItem(groupId, itemId),
    onMutate: async (itemId) => {
      await queryClient.cancelQueries({ queryKey: gpKeys.checklist(groupId) });
      const previous = queryClient.getQueryData(gpKeys.checklist(groupId));
      queryClient.setQueryData(gpKeys.checklist(groupId), (old) => {
        if (!old?.data?.checklist) return old;
        return {
          ...old,
          data: {
            ...old.data,
            checklist: old.data.checklist.map(item =>
              item.id === itemId ? { ...item, completed: !item.completed } : item
            ),
          },
        };
      });
      return { previous };
    },
    onError: (_err, _itemId, context) => {
      queryClient.setQueryData(gpKeys.checklist(groupId), context.previous);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: gpKeys.checklist(groupId) });
    },
  });
}

export function useCreateGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupData) => groupPlannerApi.createGroup(groupData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gpKeys.groups() });
    },
  });
}

export function useDeleteGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId) => groupPlannerApi.deleteGroup(groupId),
    onSuccess: (_data, groupId) => {
      queryClient.invalidateQueries({ queryKey: gpKeys.groups() });
      queryClient.removeQueries({ queryKey: gpKeys.group(groupId) });
    },
  });
}

// ── Checklist Query ─────────────────────────────────────────────────────────

export function useGroupChecklist(groupId) {
  return useQuery({
    queryKey: gpKeys.checklist(groupId),
    queryFn: () => groupPlannerApi.getGroupChecklist(groupId),
    enabled: !!groupId,
    staleTime: 10_000,
  });
}

// ── Vault Query ─────────────────────────────────────────────────────────────

export function useVaultFiles(groupId) {
  return useQuery({
    queryKey: gpKeys.vault(groupId),
    queryFn: () => groupPlannerApi.getVaultFiles(groupId),
    enabled: !!groupId,
    staleTime: 30_000,
  });
}

export function useUploadVaultFile(groupId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file) => groupPlannerApi.uploadVaultFile(groupId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gpKeys.vault(groupId) });
    },
  });
}

export function useDeleteVaultFile(groupId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (docId) => groupPlannerApi.deleteVaultFile(groupId, docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gpKeys.vault(groupId) });
    },
  });
}

// ── Activities Query ────────────────────────────────────────────────────────

export function useGroupActivities(groupId) {
  return useQuery({
    queryKey: gpKeys.activities(groupId),
    queryFn: () => groupPlannerApi.getGroupActivities(groupId),
    enabled: !!groupId,
    staleTime: 15_000,
  });
}

// ── Destination Library (places search DB) ──────────────────────────────────

export function useDestinationPlaces(destination) {
  return useQuery({
    queryKey: gpKeys.destPlaces(destination),
    queryFn: () => groupPlannerApi.searchDestinationPlaces(destination),
    enabled: !!destination,
    staleTime: 300_000, // 5 min — city data rarely changes
  });
}

export function useDestinationEvents(destination) {
  return useQuery({
    queryKey: gpKeys.destEvents(destination),
    queryFn: () => groupPlannerApi.getDestinationEvents(destination),
    enabled: !!destination,
    staleTime: 300_000,
  });
}
