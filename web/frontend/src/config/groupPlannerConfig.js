/**
 * Group Planner Frontend Configuration
 * Centralized configuration management for group planner system
 * Following enterprise-grade configuration patterns
 * 
 * ALL values are environment-based or safe defaults
 * NO hardcoded secrets or production values
 */

/**
 * API Configuration
 * All URLs from environment variables with safe defaults
 */
export const ApiConfig = {
  // Base URL for API calls - should include /api prefix
  // The endpoints below will be appended to this
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  
  // Group Planner API endpoints (WITHOUT /api prefix since BASE_URL includes it)
  ENDPOINTS: {
    GROUPS: '/group-planner/groups',
    MEMBERS: '/group-planner/groups/:groupId/members',
    PLACES: '/group-planner/groups/:groupId/places',
    POLLS: '/group-planner/groups/:groupId/polls',
    INVITATIONS: '/group-planner/invitations',
  },
  
  // API Configuration
  REQUEST_TIMEOUT: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000'),
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // ms
};

/**
 * Frontend Configuration
 */
export const FrontendConfig = {
  // Frontend URL (used for redirects, links)
  FRONTEND_URL: import.meta.env.VITE_FRONTEND_URL || 'http://localhost:5173',
  
  // Application name
  APP_NAME: 'TripRaft',
  
  // Version
  VERSION: '1.0.0',
};

/**
 * Cache Configuration
 * Local storage and in-memory cache settings
 */
export const CacheConfig = {
  // Cache storage keys (prefixed for uniqueness)
  KEYS: {
    GROUPS: 'groupplanner:groups',
    GROUP_DETAIL: 'groupplanner:group:%s',
    USER_GROUPS: 'groupplanner:user_groups:%s',  // %s = user_id
    GROUP_MEMBERS: 'groupplanner:group_members:%s',
    GROUP_PLACES: 'groupplanner:group_places:%s',
    GROUP_POLLS: 'groupplanner:group_polls:%s',
    USER_INVITATIONS: 'groupplanner:user_invitations:%s',  // %s = user_id
  },
  
  // Cache TTL in milliseconds (same as backend for consistency)
  TTL: {
    GROUPS: 1800000,           // 30 minutes
    GROUP_DETAIL: 3600000,     // 1 hour
    MEMBERS: 3600000,          // 1 hour
    PLACES: 1800000,           // 30 minutes
    POLLS: 900000,             // 15 minutes
    INVITATIONS: 300000,       // 5 minutes
  },
};

/**
 * Feature Flags
 * Toggle features for A/B testing, gradual rollout, etc.
 */
export const FeatureFlags = {
  ENABLE_REAL_TIME_UPDATES: import.meta.env.VITE_FEATURE_REAL_TIME || false,
  ENABLE_ADVANCED_POLLS: import.meta.env.VITE_FEATURE_ADVANCED_POLLS || true,
  ENABLE_PLACE_SEARCH: import.meta.env.VITE_FEATURE_PLACE_SEARCH || true,
  ENABLE_ITINERARY_GENERATION: import.meta.env.VITE_FEATURE_ITINERARY || false,
  ENABLE_DOCUMENT_COLLABORATION: import.meta.env.VITE_FEATURE_COLLABORATION || false,
};

/**
 * UI Configuration
 */
export const UiConfig = {
  // Modal animation duration (ms)
  MODAL_ANIMATION_DURATION: 300,
  
  // Toast notification duration (ms)
  TOAST_DURATION: 3000,
  
  // Pagination
  ITEMS_PER_PAGE: 20,
  
  // Debounce delay for search input (ms)
  SEARCH_DEBOUNCE: 500,
};

/**
 * Authentication Configuration
 */
export const AuthConfig = {
  // Token storage key
  TOKEN_KEY: 'groupplanner:auth_token',
  
  // User data storage key
  USER_KEY: 'groupplanner:user_data',
  
  // Session timeout (ms) - 1 hour
  SESSION_TIMEOUT: 3600000,
};

/**
 * Map Configuration
 * OSM/Leaflet settings
 */
export const MapConfig = {
  // Default map center (lat, lng)
  DEFAULT_CENTER: [20.5937, 78.9629], // India center
  
  // Default zoom level
  DEFAULT_ZOOM: 4,
  
  // Max zoom
  MAX_ZOOM: 18,
  
  // Min zoom
  MIN_ZOOM: 2,
  
  // Tile provider
  TILE_PROVIDER: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  
  // Tile attribution
  ATTRIBUTION: '&copy; OpenStreetMap contributors',
  
  // Marker clustering
  CLUSTER_RADIUS: 50,
};

/**
 * Environment Detection
 */
export const Environment = {
  isDevelopment: () => import.meta.env.MODE === 'development',
  isProduction: () => import.meta.env.MODE === 'production',
  isTesting: () => import.meta.env.MODE === 'test',
};

/**
 * Logging Configuration
 */
export const LogConfig = {
  // Enable logging
  ENABLED: !Environment.isProduction(),
  
  // Log level: 'debug', 'info', 'warn', 'error'
  LEVEL: import.meta.env.VITE_LOG_LEVEL || 'info',
  
  // Log to console
  CONSOLE: true,
  
  // Log to external service (future)
  EXTERNAL: false,
};

/**
 * Helper function to get cache key with substitution
 * @param {string} keyPattern - Pattern with %s for ID
 * @param {string} id - ID to substitute
 * @returns {string} - Formatted cache key
 */
export const getCacheKey = (keyPattern, id) => {
  return keyPattern.replace('%s', id);
};

/**
 * Helper function to construct API endpoint with substitution
 * @param {string} endpoint - Endpoint pattern
 * @param {object} params - Parameters to substitute
 * @returns {string} - Full endpoint URL
 */
export const getEndpoint = (endpoint, params = {}) => {
  let result = endpoint;
  Object.keys(params).forEach(key => {
    result = result.replace(`:${key}`, params[key]);
  });
  return result;
};

/**
 * Helper function to get full API URL
 * @param {string} endpoint - API endpoint
 * @returns {string} - Full URL
 */
export const getApiUrl = (endpoint) => {
  return `${ApiConfig.BASE_URL}${endpoint}`;
};

/**
 * Development helpers
 */
export const DevHelpers = {
  // Log configuration (dev only)
  logConfig: () => {
    if (!Environment.isDevelopment()) return;
    console.table({
      API_BASE_URL: ApiConfig.BASE_URL,
      FRONTEND_URL: FrontendConfig.FRONTEND_URL,
      ENVIRONMENT: import.meta.env.MODE,
      VERSION: FrontendConfig.VERSION,
    });
  },
};

export default {
  ApiConfig,
  FrontendConfig,
  CacheConfig,
  FeatureFlags,
  UiConfig,
  AuthConfig,
  MapConfig,
  Environment,
  LogConfig,
  getCacheKey,
  getEndpoint,
  getApiUrl,
  DevHelpers,
};
