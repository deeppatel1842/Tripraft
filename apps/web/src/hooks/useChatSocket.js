// Purpose: Connects cookie-authenticated live chat and reports socket authentication/connection failures.
/**
 * Chat WebSocket Hook
 * Manages Socket.IO connection for real-time chat: messages, typing, read receipts.
 *
 * Owned by the GroupPlannerManager so the connection persists across tab switches.
 * Returns helpers that ChatPanel consumes.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { io } from 'socket.io-client';
import sqlAuthService from '../services/sqlAuthService';
import GlobalConfig from '../config/globalConfig';
import { chatKeys } from './useChatQuery';
import { mergeMessage } from '../lib/chatCache';

const TYPING_EXPIRE_MS = 3_000;
const TYPING_THROTTLE_MS = 2_000;
const PRESENCE_HEARTBEAT_MS = 60_000;

/**
 * @param {string|null} groupId  - active group (null = no connection)
 * @param {string|null} userId   - current user id
 */
export default function useChatSocket(groupId, userId) {
  const queryClient = useQueryClient();
  const socketRef = useRef(null);
  const lastTypingEmitRef = useRef(0);
  const [typingUsers, setTypingUsers] = useState([]);
  const [connected, setConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const lastReadRef = useRef({ id: null, time: 0 });

  // Typing expiry timers per user
  const typingTimersRef = useRef({});

  // --- Connect / disconnect lifecycle ---
  useEffect(() => {
    if (!groupId || !userId) return;
    lastReadRef.current = { id: null, time: 0 };
    setConnectionError(null);

    let cancelled = false;
    let presenceHeartbeat = null;

    const connect = async () => {
      const token = await sqlAuthService.getIdToken();
      // Derive base URL from API base (strip /api suffix)
      const baseUrl = (GlobalConfig.API_BASE_URL || '').replace(/\/api\/?$/, '') || 'http://localhost:5000';

      const opts = {
        transports: ['websocket', 'polling'],
        withCredentials: true,
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 10,
      };

      // In cookie-mode auth, token is null - backend reads httpOnly cookie instead
      if (token) {
        opts.auth = { token };
      }

      const socket = io(baseUrl, opts);
      socket.on('connect_error', error => {
        setConnected(false);
        setConnectionError(error.message || 'Real-time connection unavailable');
        if (/auth|unauthor|forbidden|401|403|refused/i.test(error.message || '')) {
          socket.io.opts.reconnection = false;
          socket.disconnect();
        }
      });

      if (cancelled) { socket.disconnect(); return; }
      socketRef.current = socket;

      socket.on('connect', () => {
        setConnected(true);
        setConnectionError(null);
        queryClient.invalidateQueries({ queryKey: chatKeys.messages(groupId) });
        socket.emit('join_group', { group_id: groupId });
        // The server uses a TTL-based presence record. Refresh it while the
        // tab is active so an idle, connected member does not disappear.
        clearInterval(presenceHeartbeat);
        presenceHeartbeat = setInterval(() => {
          socket.emit('presence:heartbeat', { group_id: groupId });
        }, PRESENCE_HEARTBEAT_MS);
      });

      socket.on('disconnect', () => {
        clearInterval(presenceHeartbeat);
        presenceHeartbeat = null;
        setConnected(false);
      });

      // --- Chat events ---
      socket.on('chat:message', (msg) => {
        // Content cannot identify a send: another device can post the same text.
        // Keep every server UUID; the POST acknowledgement replaces its temp ID.
        queryClient.setQueryData(chatKeys.messages(groupId), old => mergeMessage(old, msg));
        // Bump unread
        queryClient.invalidateQueries({ queryKey: chatKeys.unread(groupId) });
      });

      socket.on('chat:deleted', (data) => {
        queryClient.setQueryData(chatKeys.messages(groupId), (old) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => {
              const msgs = page?.data?.messages ?? page?.messages ?? [];
              return {
                ...page,
                data: {
                  ...page.data,
                  messages: msgs.map((m) =>
                    m.id === data.message_id ? { ...m, is_deleted: true, content: '' } : m
                  ),
                },
              };
            }),
          };
        });
      });

      socket.on('chat:typing', (data) => {
        if (data.user_id === userId) return;
        setTypingUsers((prev) => {
          if (prev.some((u) => u.user_id === data.user_id)) return prev;
          return [...prev, { user_id: data.user_id, email: data.email, is_ai: !!data.is_ai }];
        });
        // Clear after expiry (longer for AI since processing takes time)
        const expiry = data.is_ai ? 30_000 : TYPING_EXPIRE_MS;
        if (typingTimersRef.current[data.user_id]) {
          clearTimeout(typingTimersRef.current[data.user_id]);
        }
        typingTimersRef.current[data.user_id] = setTimeout(() => {
          setTypingUsers((prev) => prev.filter((u) => u.user_id !== data.user_id));
          delete typingTimersRef.current[data.user_id];
        }, expiry);
      });

      socket.on('chat:typing_stop', (data) => {
        setTypingUsers((prev) => prev.filter((u) => u.user_id !== data.user_id));
        if (typingTimersRef.current[data.user_id]) {
          clearTimeout(typingTimersRef.current[data.user_id]);
          delete typingTimersRef.current[data.user_id];
        }
      });

      socket.on('chat:read', (data) => {
        queryClient.invalidateQueries({ queryKey: chatKeys.unread(groupId) });
      });
    };

    connect().catch(error => { if (!cancelled) setConnectionError(error.message || 'Real-time connection unavailable'); });

    return () => {
      cancelled = true;
      clearInterval(presenceHeartbeat);
      if (socketRef.current) {
        socketRef.current.emit('leave_group', { group_id: groupId });
        socketRef.current.disconnect();
        socketRef.current = null;
      }
      setConnected(false);
      setTypingUsers([]);
      Object.values(typingTimersRef.current).forEach(clearTimeout);
      typingTimersRef.current = {};
    };
  }, [groupId, userId, queryClient]);

  // --- Emit helpers ---
  const emitTyping = useCallback(() => {
    if (!socketRef.current || !groupId) return;
    const now = Date.now();
    if (now - lastTypingEmitRef.current < TYPING_THROTTLE_MS) return;
    lastTypingEmitRef.current = now;
    socketRef.current.emit('chat:typing', { group_id: groupId });
  }, [groupId]);

  const emitRead = useCallback((messageId) => {
    if (!socketRef.current || !groupId || !messageId || String(messageId).startsWith('temp-')) return;
    const now = Date.now();
    if (lastReadRef.current.id === messageId || now - lastReadRef.current.time < 1000) return;
    lastReadRef.current = { id: messageId, time: now };
    socketRef.current.emit('chat:read', { group_id: groupId, message_id: messageId });
  }, [groupId]);

  return { connected, connectionError, typingUsers, emitTyping, emitRead, socketRef };
}
