/**
 * Custom React Hooks Index
 * 
 * This file exports all custom React hooks for the Travel Planner application.
 * These hooks provide:
 * - useAuth: Authentication state management and user session handling
 * - useTrips: Trip data fetching, caching, and state management
 * - useCollaboration: Real-time collaboration features and WebSocket connections
 * - useLocalStorage: Browser storage management with React state synchronization
 * - useDebounce: Input debouncing for search and API calls optimization
 * - useApiCall: Generic API calling hook with loading states and error handling
 * 
 * Custom hooks encapsulate reusable stateful logic across components.
 */

// Custom React hooks
// These will be implemented during Phase 1-3

export { useAuth } from './useAuth'
export { useTrips } from './useTrips'
export { useCollaboration } from './useCollaboration'
export { useLocalStorage } from './useLocalStorage'
export { useDebounce } from './useDebounce'
export { useApiCall } from './useApiCall'
