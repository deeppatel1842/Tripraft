// Purpose: Provides global Config logic and exports for apps\web\src\config.
/**
 * Global Configuration for Frontend
 * 
 * This file loads configuration from environment variables and provides
 * a centralized configuration object for the entire frontend application.
 * 
 * Brand name and other settings can be easily changed via .env file.
 */

const GlobalConfig = {
  // Brand Configuration
  APP_NAME: import.meta.env.VITE_APP_NAME || 'Tripraft',
  APP_DESCRIPTION: import.meta.env.VITE_APP_DESCRIPTION || 'AI-powered travel planning platform',
  APP_TAGLINE: import.meta.env.VITE_APP_TAGLINE || 'Discover. Plan. Explore.',
  
  // API Configuration
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  API_TIMEOUT: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000'),
  API_MAX_RETRIES: 2,
  RETRY_BACKOFF_BASE_MS: 500,
  
  // Endpoint Prefixes
  ENDPOINTS: {
    AUTH: '/v1/auth',
    EXPENSE: '/v1/expenses',
    GROUP_PLANNER: '/v1/group-planner',
    PLACE_SEARCH: '/v1/places',
    TRIP_PLANNER: '/v1/trip-planner',
  },
  
  // localStorage Keys
  STORAGE_KEYS: {
    ACCESS_TOKEN: 'accessToken',
    REFRESH_TOKEN: 'refreshToken',
    CURRENT_USER: 'currentUser',
    PENDING_INVITATION: 'pendingInvitation',
    INVITATION_EMAIL: 'invitationEmail',
    PENDING_GROUP_INVITATION: 'pendingGroupInvitation',
    GROUP_INVITATION_EMAIL: 'groupInvitationEmail',
    GROUP_INVITATION_CREATED_BY: 'groupInvitationCreatedBy',
  },
  
  // Token Management
  TOKEN_REFRESH_THRESHOLD_S: 60,
  
  // Place Search Defaults
  PLACE_SEARCH_DEFAULT_LIMIT: 500,
  PLACE_SEARCH_DEFAULT_SORT_BY: 'rank_score',
  PLACE_SEARCH_DEFAULT_SORT_ORDER: 'desc',
  AUTOCOMPLETE_DEBOUNCE_MS: 300,
  AUTOCOMPLETE_MIN_CHARS: 2,
  AUTOCOMPLETE_DEFAULT_LIMIT: 10,
  
  // Trip Planner Defaults
  TRIP_DEFAULT_DAYS: 3,
  TRIP_DEFAULT_PACING: 'M',
  CITY_SEARCH_LIMIT: 10,
  
  // Expense Defaults
  EXPENSE_RECENT_LIMIT: 20,
  EVENTS_DEFAULT_LIMIT: 20,
  
  // Background Sync
  BACKGROUND_SYNC_BASE_INTERVAL: 60000,
  BACKGROUND_SYNC_MAX_INTERVAL: 300000,
  
  // PDF Export Theme
  PDF_THEME: {
    PRIMARY: '#667eea',
    SECONDARY: '#764ba2',
    SUCCESS: '#059669',
    DANGER: '#dc2626',
    TEXT: '#111827',
    TEXT_LIGHT: '#6b7280',
    BORDER: '#e5e7eb',
    PAGE_MARGIN: 15,
    HEADER_FONT_SIZE: 28,
    TAGLINE_FONT_SIZE: 10,
    SECTION_TITLE_FONT_SIZE: 13,
  },
  
  // Asset Paths
  STATIC_ASSETS_PATH: '/',
  
  // Feature Flags
  ENABLE_ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  ENABLE_DEBUG_MODE: import.meta.env.VITE_ENABLE_DEBUG_MODE === 'true',
}

export default GlobalConfig
