/**
 * Redux Store Configuration
 * 
 * This file sets up the Redux store for the Travel Planner application.
 * It configures:
 * - Redux Toolkit store with middleware
 * - RTK Query API endpoints integration
 * - State persistence and rehydration
 * - Development tools integration
 * - Type-safe hooks for React components
 */

import { configureStore } from '@reduxjs/toolkit'

// Placeholder store configuration
// Slices will be added during Phase 1 implementation
export const store = configureStore({
  reducer: {
    // auth: authSlice,
    // trips: tripsSlice,
    // expenses: expensesSlice,
    // ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [],
      },
    }),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
