// Purpose: Manages paginated chat queries and optimistic sends while preserving concurrent messages.
/**
 * Chat React Query Hooks
 * useInfiniteQuery for cursor-paginated messages, mutations for send/delete/read.
 */

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import chatApi from '../services/chatApi';
import { useAuth } from '../context/AuthContext';
import { mergeMessage, removeMessage } from '../lib/chatCache';

export const chatKeys = {
  all:        ['chat'],
  messages:   (groupId) => [...chatKeys.all, 'messages', groupId],
  unread:     (groupId) => [...chatKeys.all, 'unread', groupId],
};

/**
 * Infinite query: loads messages newest-first, scroll up for older.
 * Each page: { messages: [...], has_more: bool }
 */
export function useMessages(groupId) {
  return useInfiniteQuery({
    queryKey: chatKeys.messages(groupId),
    queryFn: ({ pageParam }) =>
      chatApi.getMessages(groupId, { beforeId: pageParam, limit: 50 }),
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => {
      const msgs = lastPage?.data?.messages ?? lastPage?.messages ?? [];
      if (!lastPage?.data?.has_more && !lastPage?.has_more) return undefined;
      if (msgs.length === 0) return undefined;
      return msgs[msgs.length - 1].id;
    },
    enabled: !!groupId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

/**
 * Optimistic send: prepend message to cache, roll back on error.
 */
export function useSendMessage(groupId) {
  const queryClient = useQueryClient();
  const { currentUser } = useAuth();

  return useMutation({
    mutationFn: (payload) => chatApi.sendMessage(groupId, payload),
    retry: 0,
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: chatKeys.messages(groupId) });

      const optimistic = {
        id: 'temp-' + (globalThis.crypto?.randomUUID?.() || Date.now().toString(36) + Math.random().toString(36).slice(2)),
        sender_id: currentUser?.uid,
        group_id: groupId,
        content: payload.content,
        type: payload.type || 'text',
        sender_type: 'user',
        is_deleted: false,
        created_at: new Date().toISOString(),
        _optimistic: true,
      };

      queryClient.setQueryData(chatKeys.messages(groupId), old => mergeMessage(old, optimistic));
      return { optimisticId: optimistic.id, groupId };
    },
    onError: (_err, _payload, context) => {
      queryClient.setQueryData(chatKeys.messages(context?.groupId ?? groupId), old => removeMessage(old, context?.optimisticId));
    },
    onSuccess: (response, _payload, context) => {
      const raw = response?.data ?? response;
      const message = raw?.message ?? raw;
      queryClient.setQueryData(chatKeys.messages(context?.groupId ?? groupId), old => mergeMessage(removeMessage(old, context?.optimisticId), message));
    },
    onSettled: (_data, _error, _payload, context) => {
      queryClient.invalidateQueries({ queryKey: chatKeys.messages(context?.groupId ?? groupId) });
    },
  });
}

/**
 * Delete a message (soft delete).
 */
export function useDeleteMessage(groupId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (messageId) => chatApi.deleteMessage(messageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: chatKeys.messages(groupId) });
    },
  });
}

/**
 * Mark messages as read.
 */
export function useMarkRead(groupId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (messageId) => chatApi.markRead(groupId, messageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: chatKeys.unread(groupId) });
    },
  });
}

/**
 * Unread count query.
 */
export function useUnreadCount(groupId) {
  return useQuery({
    queryKey: chatKeys.unread(groupId),
    queryFn: () => chatApi.getUnreadCount(groupId),
    enabled: !!groupId,
    staleTime: 30_000,
    select: (data) => {
      const count = (data?.data ?? data)?.unread_count;
      if (!Number.isInteger(count) || count < 0) throw new Error('Unable to read the unread message count');
      return count;
    },
  });
}
