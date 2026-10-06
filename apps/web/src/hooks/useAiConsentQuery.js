// Purpose: Provides reusable React state/query behavior for Ai Consent Query.
/**
 * AI Consent React Query Hooks
 * Query + mutations for Scout consent state per group.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import aiConsentApi from '../services/aiConsentApi';

export const aiConsentKeys = {
  all: ['aiConsent'],
  group: (groupId) => [...aiConsentKeys.all, groupId],
};

/**
 * Fetch consent status for the current user in a group.
 * Backend GET returns { allowed, needs_prompt, consented_member_count }.
 */
export function useAiConsent(groupId) {
  return useQuery({
    queryKey: aiConsentKeys.group(groupId),
    queryFn: async () => {
      const res = await aiConsentApi.getConsent(groupId);
      const raw = res?.data ?? res;
      return {
        has_consent: raw.needs_prompt === false,
        needs_prompt: Boolean(raw.needs_prompt),
        allowed: Boolean(raw.allowed),
        consented_member_count: raw.consented_member_count ?? 0,
      };
    },
    enabled: !!groupId,
    staleTime: 60_000,
    retry: 1,
  });
}

/**
 * Submit consent (grant or decline).
 */
export function useSubmitAiConsent(groupId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ granted }) => aiConsentApi.submitConsent(groupId, { granted }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiConsentKeys.group(groupId) });
    },
  });
}

/**
 * Revoke consent and delete all preference data.
 */
export function useRevokeAiConsent(groupId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => aiConsentApi.revokeConsent(groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiConsentKeys.group(groupId) });
    },
  });
}
