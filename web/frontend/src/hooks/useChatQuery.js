/**
 * Chat React Query Hooks
 * useInfiniteQuery for cursor-paginated messages, mutations for send/delete/read.
 */

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import chatApi from '../services/chatApi';

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

  return useMutation({
    mutationFn: (payload) => chatApi.sendMessage(groupId, payload),
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: chatKeys.messages(groupId) });
      const previous = queryClient.getQueryData(chatKeys.messages(groupId));

      const optimistic = {
        id: -Date.now(),
        group_id: groupId,
        content: payload.content,
        type: payload.type || 'text',
        sender_type: 'user',
        is_deleted: false,
        created_at: new Date().toISOString(),
        _optimistic: true,
      };

      queryClient.setQueryData(chatKeys.messages(groupId), (old) => {
        if (!old) return old;
        const firstPage = old.pages[0];
        const msgs = firstPage?.data?.messages ?? firstPage?.messages ?? [];
        return {
          ...old,
          pages: [
            { ...firstPage, data: { ...firstPage.data, messages: [optimistic, ...msgs] } },
            ...old.pages.slice(1),
          ],
        };
      });

      return { previous };
    },
    onError: (_err, _payload, context) => {
      if (context?.previous) {
        queryClient.setQueryData(chatKeys.messages(groupId), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: chatKeys.messages(groupId) });
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
    select: (data) => data?.data?.unread_count ?? 0,
  });
}
