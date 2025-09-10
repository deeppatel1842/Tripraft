/**
 * API Services Index
 * 
 * This file exports all RTK Query API slice configurations for the Travel Planner application.
 * These API services handle:
 * - authApi: User authentication, registration, and session management
 * - tripsApi: Trip CRUD operations, sharing, and collaboration
 * - usersApi: User profile management and preferences
 * - bookingApi: Third-party booking service integrations
 * - collaborationApi: Real-time collaboration and messaging features
 * 
 * Each API slice provides type-safe endpoints with automatic caching and state management.
 */

// API slice configurations
// These will be implemented during Phase 1-3

export { authApi } from './authApi'
export { tripsApi } from './tripsApi'
export { usersApi } from './usersApi'
export { bookingApi } from './bookingApi'
export { collaborationApi } from './collaborationApi'
