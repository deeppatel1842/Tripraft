// Purpose: Subscribes to cookie-authenticated trip workspace activity updates.
/**
 * useGroupSocket — React hook for real-time Group Planner collaboration.
 *
 * Connects to the Flask-SocketIO backend, joins the group room,
 * and exposes event listeners + an `emit` helper.
 *
 * Usage:
 *   const { isConnected, onlineMembers } = useGroupSocket(groupId, userId, {
 *     onPlaceAdded(data)  { ... },
 *     onPlaceVoted(data)  { ... },
 *     onPollVoted(data)   { ... },
 *     onChecklistToggled(data) { ... },
 *     onItineraryUpdated(data) { ... },
 *     onMemberJoined(data) { ... },
 *   });
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { io } from 'socket.io-client';
import GlobalConfig from '../config/globalConfig';
import { gpKeys } from './useGroupPlannerQuery';

// Derive socket URL from API base (strip /api suffix)
const SOCKET_URL =
  (GlobalConfig.API_BASE_URL || 'http://localhost:5000/api').replace(/\/api\/?$/, '');
const PRESENCE_HEARTBEAT_MS = 60_000;

/**
 * @param {string} groupId
 * @param {string} userId
 * @param {object}        handlers — optional event callbacks
 */
export default function useGroupSocket(groupId, userId, handlers = {}) {
  const [connectionError, setConnectionError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [onlineMembers, setOnlineMembers] = useState([]);
  const socketRef = useRef(null);
  const handlersRef = useRef(handlers);
  const queryClient = useQueryClient();
  useEffect(() => { handlersRef.current = handlers; }, [handlers]);

  useEffect(() => {
    if (!groupId || !userId) return;

    let presenceHeartbeat = null;
    const socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      withCredentials: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 10000,
    });
    socketRef.current = socket;

    socket.on('connect_error', error => {
      setIsConnected(false);
      setConnectionError(error.message || 'Real-time connection unavailable');
      if (/auth|unauthor|forbidden|401|403|refused/i.test(error.message || '')) { socket.io.opts.reconnection = false; socket.disconnect(); }
    });
    socket.on('connect', () => {
      setConnectionError(null);
      setIsConnected(true);
      socket.emit('join_group', { group_id: groupId, user_id: userId });
      clearInterval(presenceHeartbeat);
      presenceHeartbeat = setInterval(() => {
        socket.emit('presence:heartbeat', { group_id: groupId });
      }, PRESENCE_HEARTBEAT_MS);

      // On reconnect, invalidate all group caches to sync fresh state
      if (socketRef.current?.recovered === false) {
        queryClient.invalidateQueries({ queryKey: gpKeys.group(groupId) });
        queryClient.invalidateQueries({ queryKey: gpKeys.places(groupId) });
        queryClient.invalidateQueries({ queryKey: gpKeys.polls(groupId) });
        queryClient.invalidateQueries({ queryKey: gpKeys.members(groupId) });
      }
    });

    socket.on('disconnect', () => {
      clearInterval(presenceHeartbeat);
      presenceHeartbeat = null;
      setIsConnected(false);
    });

    // Presence
    socket.on('presence:update', (data) => {
      setOnlineMembers(data.online || []);
    });

    // Group events — invoke handlers AND invalidate relevant caches
    socket.on('place:added', (d) => {
      queryClient.invalidateQueries({ queryKey: gpKeys.places(groupId) });
      handlersRef.current.onPlaceAdded?.(d);
    });
    socket.on('place:voted', (d) => {
      queryClient.invalidateQueries({ queryKey: gpKeys.places(groupId) });
      handlersRef.current.onPlaceVoted?.(d);
    });
    socket.on('poll:created', (d) => {
      queryClient.invalidateQueries({ queryKey: gpKeys.polls(groupId) });
      handlersRef.current.onPollCreated?.(d);
    });
    socket.on('poll:voted', (d) => {
      queryClient.invalidateQueries({ queryKey: gpKeys.polls(groupId) });
      handlersRef.current.onPollVoted?.(d);
    });
    socket.on('checklist:toggled', (d) => {
      // Optimistic update from server-side event
      queryClient.setQueryData(gpKeys.group(groupId), (old) => {
        if (!old?.data?.checklist) return old;
        return {
          ...old,
          data: {
            ...old.data,
            checklist: old.data.checklist.map(item =>
              item.id === d.item_id ? { ...item, completed: d.is_completed } : item
            ),
          },
        };
      });
      handlersRef.current.onChecklistToggled?.(d);
    });
    socket.on('itinerary:updated', (d) => {
      queryClient.invalidateQueries({ queryKey: gpKeys.group(groupId) });
      handlersRef.current.onItineraryUpdated?.(d);
    });
    socket.on('member:joined', (d) => {
      queryClient.invalidateQueries({ queryKey: gpKeys.members(groupId) });
      queryClient.invalidateQueries({ queryKey: gpKeys.group(groupId) });
      handlersRef.current.onMemberJoined?.(d);
    });

    return () => {
      clearInterval(presenceHeartbeat);
      socket.emit('leave_group', { group_id: groupId, user_id: userId });
      socket.disconnect();
      socketRef.current = null;
    };
  }, [groupId, userId, queryClient]);

  const emit = useCallback((event, data) => {
    socketRef.current?.emit(event, data);
  }, []);

  return { isConnected, connectionError, onlineMembers, emit };
}
