/**
 * Group Planner Frontend Configuration
 * Centralized config for API, caching, and logging.
 */

export const ApiConfig = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  ENDPOINTS: {
    GROUPS: '/group-planner/groups',
    MEMBERS: '/group-planner/groups/:groupId/members',
    PLACES: '/group-planner/groups/:groupId/places',
    POLLS: '/group-planner/groups/:groupId/polls',
    INVITATIONS: '/group-planner/invitations',
  },
  REQUEST_TIMEOUT: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000'),
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
};

export const CacheConfig = {
  KEYS: {
    GROUPS: 'groupplanner:groups',
    GROUP_DETAIL: 'groupplanner:group:%s',
    USER_GROUPS: 'groupplanner:user_groups:%s',
    GROUP_MEMBERS: 'groupplanner:group_members:%s',
    GROUP_PLACES: 'groupplanner:group_places:%s',
    GROUP_POLLS: 'groupplanner:group_polls:%s',
    USER_INVITATIONS: 'groupplanner:user_invitations:%s',
  },
  TTL: {
    GROUPS: 1800000,       // 30 minutes
    GROUP_DETAIL: 3600000, // 1 hour
    MEMBERS: 3600000,      // 1 hour
    PLACES: 1800000,       // 30 minutes
    POLLS: 900000,         // 15 minutes
    INVITATIONS: 300000,   // 5 minutes
  },
};

export const getCacheKey = (keyPattern, id) => keyPattern.replace('%s', id);

export const getApiUrl = (endpoint) => `${ApiConfig.BASE_URL}${endpoint}`;

export const getEndpoint = (endpoint, params = {}) => {
  let result = endpoint;
  Object.keys(params).forEach(key => {
    result = result.replace(`:${key}`, params[key]);
  });
  return result;
};

export default { ApiConfig, CacheConfig, getCacheKey, getEndpoint, getApiUrl };
