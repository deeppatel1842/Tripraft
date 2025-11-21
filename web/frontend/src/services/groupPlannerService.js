/**
 * Group Planner Service Layer
 * Handles all API calls and caching for group trip planning
 * 
 * Features:
 * - Cache-aside pattern (like backend)
 * - Proper error handling
 * - Retry logic
 * - Professional logging
 * - Type documentation
 */

import authService from '../firebase/authService';
import { ApiConfig, getApiUrl, CacheConfig, getCacheKey, LogConfig } from '../config/groupPlannerConfig';
import groupPlannerApi from './groupPlannerApi';

/**
 * Local cache for storing API responses
 * Implements cache-aside pattern
 */
class CacheManager {
  constructor() {
    this.memoryCache = {};
    this.expirationTimes = {};
  }

  /**
   * Get value from cache
   * @param {string} key - Cache key
   * @returns {any|null} - Cached value or null if expired/missing
   */
  get(key) {
    const now = Date.now();
    
    // Check if expired
    if (this.expirationTimes[key] && this.expirationTimes[key] < now) {
      this.invalidate(key);
      return null;
    }

    return this.memoryCache[key] || null;
  }

  /**
   * Set value in cache
   * @param {string} key - Cache key
   * @param {any} value - Value to cache
   * @param {number} ttl - Time to live in milliseconds
   */
  set(key, value, ttl) {
    this.memoryCache[key] = value;
    this.expirationTimes[key] = Date.now() + ttl;
    this.log('set', key);
  }

  /**
   * Invalidate cache entry
   * @param {string} key - Cache key
   */
  invalidate(key) {
    delete this.memoryCache[key];
    delete this.expirationTimes[key];
    this.log('invalidate', key);
  }

  /**
   * Invalidate multiple cache entries by pattern
   * @param {string} pattern - Pattern to match (e.g., "groupplanner:group:%")
   */
  invalidateByPattern(pattern) {
    const regex = new RegExp(pattern.replace('%s', '.*'));
    Object.keys(this.memoryCache).forEach(key => {
      if (regex.test(key)) {
        this.invalidate(key);
      }
    });
  }

  /**
   * Clear all cache
   */
  clear() {
    this.memoryCache = {};
    this.expirationTimes = {};
    this.log('clear', 'all');
  }

  /**
   * Log cache operations (dev only)
   */
  log(operation, key) {
    if (LogConfig.ENABLED && LogConfig.CONSOLE) {
      console.debug(`[Cache] ${operation.toUpperCase()}: ${key}`);
    }
  }
}

/**
 * Retry mechanism for failed requests
 */
async function retryRequest(fn, attempts = ApiConfig.RETRY_ATTEMPTS) {
  let lastError;

  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      // Don't retry on client errors (4xx)
      if (error.response?.status >= 400 && error.response?.status < 500) {
        throw error;
      }

      // Wait before retry (exponential backoff)
      if (i < attempts - 1) {
        await new Promise(resolve => 
          setTimeout(resolve, ApiConfig.RETRY_DELAY * Math.pow(2, i))
        );
      }
    }
  }

  throw lastError;
}

/**
 * Initialize cache and API service
 */
const cache = new CacheManager();

/**
 * Get authentication token from Firebase
 * @returns {Promise<string>} - Auth token
 */
async function getAuthToken() {
  const user = authService.auth.currentUser;
  if (!user) {
    throw new Error('User not authenticated');
  }
  return await user.getIdToken();
}

/**
 * Make authenticated API request with retry logic
 * @param {string} endpoint - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<object>} - API response
 */
async function apiRequest(endpoint, options = {}) {
  return retryRequest(async () => {
    const token = await getAuthToken();
    // If endpoint starts with http, use it as-is, otherwise build URL
    const url = endpoint.startsWith('http') ? endpoint : getApiUrl(endpoint);
    
    console.log(`🔵 [API_REQUEST] ${options.method || 'GET'} ${url}`);
    console.log(`🔵 [API_REQUEST] Headers:`, { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.substring(0, 20)}...` });
    if (options.body) {
      console.log(`🔵 [API_REQUEST] Body:`, JSON.parse(options.body));
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
      },
      timeout: ApiConfig.REQUEST_TIMEOUT,
    });

    console.log(`🔵 [API_REQUEST] Response status:`, response.status);
    
    const data = await response.json();
    console.log(`🔵 [API_REQUEST] Response data:`, data);

    if (!response.ok) {
      const error = new Error(data.error || `API request failed (${response.status})`);
      error.response = { status: response.status, data };
      console.error(`🔴 [API_REQUEST] Request failed:`, error.message);
      throw error;
    }

    return data;
  });
}

// =========================================================================
// GROUP OPERATIONS
// =========================================================================

/**
 * Create a new travel group
 * @param {string} name - Group name
 * @param {string} description - Group description
 * @param {object} options - Optional: destination, trip_dates, budget_range
 * @returns {Promise<object>} - Created group
 */
async function createGroup(groupData) {
  try {
    console.log('🟢 [CREATE_GROUP] Starting group creation', groupData);
    
    // Use groupPlannerApi for actual API calls
    const groupPlannerApi = (await import('./groupPlannerApi')).default;
    
    // Get current user to set auth
    const currentUser = authService.getCurrentUser();
    if (currentUser) {
      groupPlannerApi.setCurrentUser(currentUser);
    }
    
    const response = await groupPlannerApi.createGroup(groupData);
    console.log('✅ [CREATE_GROUP] API Response:', response);

    // Optimistic cache update: add new group to cache immediately
    if (currentUser && response.data && response.data.group) {
      const cacheKey = CacheConfig.KEYS.USER_GROUPS.replace('%s', currentUser.uid);
      const currentGroups = cache.get(cacheKey) || [];
      const updatedGroups = [...currentGroups, response.data.group];
      cache.set(cacheKey, updatedGroups, CacheConfig.TTL.GROUPS);
      console.log('🟢 [CREATE_GROUP] Cache updated with new group:', response.data.group.group_id);
    } else {
      // If no group in response, just invalidate cache so next fetch gets fresh data
      if (currentUser) {
        const cacheKey = CacheConfig.KEYS.USER_GROUPS.replace('%s', currentUser.uid);
        cache.invalidate(cacheKey);
        console.log('🟢 [CREATE_GROUP] Cache invalidated:', cacheKey);
      }
    }

    return response;
  } catch (error) {
    console.error('❌ [CREATE_GROUP] Error creating group:', error);
    throw error;
  }
}

/**
 * Get all groups for current user (with caching)
 * @returns {Promise<array>} - List of groups
 */
async function getUserGroups() {
  // Get current user for cache key
  const currentUser = authService.getCurrentUser();
  if (!currentUser) {
    throw new Error('User not authenticated');
  }
  
  const cacheKey = CacheConfig.KEYS.USER_GROUPS.replace('%s', currentUser.uid);
  console.log('🟢 [GET_GROUPS] Fetching groups, cache key:', cacheKey);

  // Check cache first
  const cached = cache.get(cacheKey);
  if (cached) {
    console.log('🟢 [GET_GROUPS] Cache HIT: user groups', cached);
    return cached;
  }

  try {
    // Use groupPlannerApi for actual API calls
    const groupPlannerApi = (await import('./groupPlannerApi')).default;
    
    // Set auth (currentUser already declared above)
    groupPlannerApi.setCurrentUser(currentUser);
    
    const response = await groupPlannerApi.getUserGroups();
    console.log('✅ [GET_GROUPS] API Response:', response);
    // Backend returns {success: true, message: "...", data: {groups: [...]}}
    const groups = (response.data && response.data.groups) || response.groups || response.data || [];
    
    // Ensure it's an array
    const groupsList = Array.isArray(groups) ? groups : [];

    // Cache result
    cache.set(cacheKey, groupsList, CacheConfig.TTL.GROUPS);
    return groupsList;
  } catch (error) {
    console.error('Error fetching user groups:', error);
    throw error;
  }
}

/**
 * Get specific group with caching
 * @param {string} groupId - Group ID
 * @returns {Promise<object>} - Group data
 */
async function getGroup(groupId) {
  const cacheKey = getCacheKey(CacheConfig.KEYS.GROUP_DETAIL, groupId);

  // Check cache first
  const cached = cache.get(cacheKey);
  if (cached) {
    console.debug(`Cache HIT: group ${groupId}`);
    return cached;
  }

  try {
    const endpoint = ApiConfig.ENDPOINTS.GROUPS.replace(':groupId', groupId);
    const data = await apiRequest(`${endpoint}/${groupId}`);
    const group = data.data || data.group || data;

    // Cache result
    cache.set(cacheKey, group, CacheConfig.TTL.GROUP_DETAIL);
    return group;
  } catch (error) {
    console.error(`Error fetching group ${groupId}:`, error);
    throw error;
  }
}

/**
 * Update group information
 * @param {string} groupId - Group ID
 * @param {object} updates - Fields to update
 * @returns {Promise<object>} - Updated group
 */
async function updateGroup(groupId, updates) {
  try {
    const endpoint = ApiConfig.ENDPOINTS.GROUPS.replace(':groupId', groupId);
    const data = await apiRequest(`${endpoint}/${groupId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_DETAIL, groupId));

    return data.data || data;
  } catch (error) {
    console.error(`Error updating group ${groupId}:`, error);
    throw error;
  }
}

/**
 * Delete a group
 * @param {string} groupId - Group ID
 * @returns {Promise<object>} - Response
 */
async function deleteGroup(groupId) {
  try {
    const endpoint = ApiConfig.ENDPOINTS.GROUPS.replace(':groupId', groupId);
    const data = await apiRequest(`${endpoint}/${groupId}`, {
      method: 'DELETE',
    });

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_DETAIL, groupId));
    const currentUser = authService.getCurrentUser();
    if (currentUser) {
      cache.invalidate(CacheConfig.KEYS.USER_GROUPS.replace('%s', currentUser.uid));
    }

    return data;
  } catch (error) {
    console.error(`Error deleting group ${groupId}:`, error);
    throw error;
  }
}

// =========================================================================
// MEMBER OPERATIONS
// =========================================================================

/**
 * Get group members with caching
 * @param {string} groupId - Group ID
 * @returns {Promise<array>} - List of members
 */
async function getGroupMembers(groupId) {
  const cacheKey = getCacheKey(CacheConfig.KEYS.GROUP_MEMBERS, groupId);

  // Check cache first
  const cached = cache.get(cacheKey);
  if (cached) {
    console.debug(`Cache HIT: group members ${groupId}`);
    return cached;
  }

  try {
    const endpoint = ApiConfig.ENDPOINTS.MEMBERS
      .replace(':groupId', groupId);
    const data = await apiRequest(endpoint);
    const members = (data.data && data.data.members) || data.members || data.data || [];

    // Cache result
    cache.set(cacheKey, members, CacheConfig.TTL.MEMBERS);
    return members;
  } catch (error) {
    console.error(`Error fetching group members ${groupId}:`, error);
    throw error;
  }
}

/**
 * Remove member from group
 * @param {string} groupId - Group ID
 * @param {string} userId - User ID to remove
 * @returns {Promise<object>} - Response
 */
async function removeMember(groupId, userId) {
  try {
    const endpoint = ApiConfig.ENDPOINTS.MEMBERS
      .replace(':groupId', groupId);
    const data = await apiRequest(`${endpoint}/${userId}`, {
      method: 'DELETE',
    });

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_MEMBERS, groupId));

    return data;
  } catch (error) {
    console.error(`Error removing member ${userId} from group ${groupId}:`, error);
    throw error;
  }
}

// =========================================================================
// PLACE OPERATIONS
// =========================================================================

/**
 * Add place to group
 * @param {string} groupId - Group ID
 * @param {string} placeName - Place name
 * @returns {Promise<object>} - Created place
 */
async function addPlace(groupId, placeName) {
  try {
    console.log('🟡 [SERVICE] Adding place:', { groupId, placeName });
    
    // Use backend API
    const response = await groupPlannerApi.addPlace(groupId, placeName);
    
    console.log('✅ [SERVICE] Place added:', response);

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_PLACES, groupId));

    return response.data || response;
  } catch (error) {
    // Check if it's a duplicate error
    if (error.message && error.message.includes('already added')) {
      console.log('⚠️ [SERVICE] Duplicate place detected:', placeName);
      const duplicateError = new Error('DUPLICATE_PLACE');
      duplicateError.placeName = placeName;
      throw duplicateError;
    }
    
    console.error(`❌ [SERVICE] Error adding place to group ${groupId}:`, error);
    throw error;
  }
}

/**
 * Get group places with caching
 * @param {string} groupId - Group ID
 * @returns {Promise<array>} - List of places
 */
async function getGroupPlaces(groupId) {
  const cacheKey = getCacheKey(CacheConfig.KEYS.GROUP_PLACES, groupId);

  // Check cache first
  const cached = cache.get(cacheKey);
  if (cached) {
    console.debug(`Cache HIT: group places ${groupId}`);
    return cached;
  }

  try {
    const endpoint = ApiConfig.ENDPOINTS.PLACES
      .replace(':groupId', groupId);
    const data = await apiRequest(endpoint);
    const places = (data.data && data.data.places) || data.places || data.data || [];

    // Cache result
    cache.set(cacheKey, places, CacheConfig.TTL.PLACES);
    return places;
  } catch (error) {
    console.error(`Error fetching group places ${groupId}:`, error);
    throw error;
  }
}

/**
 * Delete place from group
 * @param {string} groupId - Group ID
 * @param {string} placeId - Place ID
 * @returns {Promise<object>} - Response
 */
async function deletePlace(groupId, placeId) {
  try {
    console.log('🟡 [SERVICE] Deleting place:', { groupId, placeId });
    
    // Use backend API
    const response = await groupPlannerApi.deletePlace(groupId, placeId);
    
    console.log('✅ [SERVICE] Place deleted:', response);

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_PLACES, groupId));

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error deleting place ${placeId}:`, error);
    throw error;
  }
}

/**
 * Vote on a place (toggle)
 * @param {string} groupId - Group ID
 * @param {string} placeId - Place ID
 * @returns {Promise<object>} - Response
 */
async function voteOnPlace(groupId, placeId) {
  try {
    console.log('🟡 [SERVICE] Voting on place:', { groupId, placeId });
    
    // Use backend API
    const response = await groupPlannerApi.voteOnPlace(groupId, placeId);
    
    console.log('✅ [SERVICE] Vote recorded:', response);

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_PLACES, groupId));

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error voting on place ${placeId}:`, error);
    throw error;
  }
}

/**
 * Update remark for a place
 * @param {string} groupId - Group ID
 * @param {string} placeId - Place ID
 * @param {string} remarks - Remarks text
 * @returns {Promise<object>} - Response
 */
async function addPlaceRemark(groupId, placeId, remarks) {
  try {
    console.log('🟡 [SERVICE] Updating place remarks:', { groupId, placeId });
    
    // Use backend API
    const response = await groupPlannerApi.updatePlaceRemarks(groupId, placeId, remarks);
    
    console.log('✅ [SERVICE] Remarks updated:', response);

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_PLACES, groupId));

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error updating remarks for place ${placeId}:`, error);
    throw error;
  }
}

/**
 * Update place details (date, duration, notes)
 * @param {string} groupId - Group ID
 * @param {string} placeId - Place ID
 * @param {object} updates - { visit_date, suggested_duration, remarks }
 * @returns {Promise<object>} - Response
 */
async function updatePlaceDetails(groupId, placeId, updates) {
  try {
    console.log('🟡 [SERVICE] Updating place details:', { groupId, placeId, updates });
    
    const response = await apiRequest(`/group-planner/groups/${groupId}/places/${placeId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
    
    console.log('✅ [SERVICE] Place details updated:', response);

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_PLACES, groupId));

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error updating place details ${placeId}:`, error);
    throw error;
  }
}

/**
 * Update itinerary document
 * @param {string} groupId - Group ID
 * @param {string} content - Document content
 * @returns {Promise<object>} - Response
 */
async function updateItineraryDocument(groupId, content) {
  try {
    console.log('🟡 [SERVICE] Updating itinerary document:', { groupId });
    
    const response = await apiRequest(`/group-planner/groups/${groupId}/itinerary-document`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
    
    console.log('✅ [SERVICE] Itinerary document updated');

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error updating itinerary document:`, error);
    throw error;
  }
}

// =========================================================================
// POLL OPERATIONS
// =========================================================================

/**
 * Create poll in group
 * @param {string} groupId - Group ID
 * @param {object} pollData - Poll information (name, options)
 * @returns {Promise<object>} - Created poll
 */
async function createPoll(groupId, pollData) {
  try {
    console.log('🟡 [SERVICE] Creating poll:', { groupId, pollData });
    
    // Use backend API
    const response = await groupPlannerApi.createPoll(groupId, pollData);
    
    console.log('✅ [SERVICE] Poll created:', response);

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_POLLS, groupId));

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error creating poll in group ${groupId}:`, error);
    throw error;
  }
}

/**
 * Get group polls with caching
 * @param {string} groupId - Group ID
 * @returns {Promise<array>} - List of polls
 */
async function getGroupPolls(groupId) {
  const cacheKey = getCacheKey(CacheConfig.KEYS.GROUP_POLLS, groupId);

  // Check cache first
  const cached = cache.get(cacheKey);
  if (cached) {
    console.debug(`Cache HIT: group polls ${groupId}`);
    return cached;
  }

  try {
    const endpoint = ApiConfig.ENDPOINTS.POLLS
      .replace(':groupId', groupId);
    const data = await apiRequest(endpoint);
    const polls = (data.data && data.data.polls) || data.polls || data.data || [];

    // Cache result
    cache.set(cacheKey, polls, CacheConfig.TTL.POLLS);
    return polls;
  } catch (error) {
    console.error(`Error fetching group polls ${groupId}:`, error);
    throw error;
  }
}

/**
 * Vote on poll option
 * @param {string} groupId - Group ID
 * @param {string} pollId - Poll ID
 * @param {string} option - Option to vote for
 * @returns {Promise<object>} - Response
 */
async function voteOnPoll(groupId, pollId, option) {
  try {
    console.log('🟡 [SERVICE] Voting on poll:', { groupId, pollId, option });
    
    // Use backend API
    const response = await groupPlannerApi.voteOnPoll(groupId, pollId, option);
    
    console.log('✅ [SERVICE] Vote recorded:', response);

    // Invalidate related caches
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_POLLS, groupId));

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error voting on poll ${pollId}:`, error);
    throw error;
  }
}

/**
 * Delete poll from group
 * @param {string} groupId - Group ID
 * @param {string} pollId - Poll ID
 * @returns {Promise<object>} - Response
 */
async function deletePoll(groupId, pollId) {
  try {
    console.log('🟡 [SERVICE] Deleting poll:', { groupId, pollId });
    
    // Use backend API
    const response = await groupPlannerApi.deletePoll(groupId, pollId);
    
    console.log('✅ [SERVICE] Poll deleted:', response);

    // Invalidate cache
    cache.invalidate(getCacheKey(CacheConfig.KEYS.GROUP_POLLS, groupId));

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error deleting poll ${pollId}:`, error);
    throw error;
  }
}

// =========================================================================
// INVITATION OPERATIONS
// =========================================================================

/**
 * Create and send invitation
 * @param {string} groupId - Group ID
 * @param {string} email - Email to invite
 * @returns {Promise<object>} - Invitation details
 */
async function createInvitation(groupId, email) {
  try {
    console.log('🟡 [SERVICE] Creating invitation:', { groupId, email });
    
    // Use backend API
    const response = await groupPlannerApi.createInvitation(groupId, email);
    
    console.log('✅ [SERVICE] Invitation resent:', response);
    
    // Invalidate user invitations cache
    const currentUser = authService.getCurrentUser();
    if (currentUser) {
      cache.invalidate(CacheConfig.KEYS.USER_INVITATIONS.replace('%s', currentUser.uid));
    }
    if (currentUser) {
      cache.invalidate(CacheConfig.KEYS.USER_INVITATIONS.replace('%s', currentUser.uid));
    }

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error creating invitation for ${email}:`, error);
    throw error;
  }
}

/**
 * Accept invitation
 * @param {string} invitationId - Invitation ID to accept
 * @returns {Promise<object>} - Response from backend
 */
async function acceptInvitation(invitationId) {
  try {
    console.log('🟡 [SERVICE] Accepting invitation:', invitationId);
    
    // Use backend API
    const response = await groupPlannerApi.acceptInvitation(invitationId);
    
    console.log('✅ [SERVICE] Invitation accepted:', response);
    
    // Invalidate caches
    const currentUser = authService.getCurrentUser();
    if (currentUser) {
      cache.invalidate(CacheConfig.KEYS.USER_INVITATIONS.replace('%s', currentUser.uid));
      cache.invalidate(CacheConfig.KEYS.USER_GROUPS.replace('%s', currentUser.uid));
    }

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error accepting invitation ${invitationId}:`, error);
    throw error;
  }
}

/**
 * Get user's pending invitations with caching
 * @returns {Promise<array>} - List of invitations
 */
async function getUserInvitations() {
  // Get current user for cache key
  const currentUser = authService.getCurrentUser();
  if (!currentUser) {
    throw new Error('User not authenticated');
  }
  
  const cacheKey = CacheConfig.KEYS.USER_INVITATIONS.replace('%s', currentUser.uid);

  // Check cache first
  const cached = cache.get(cacheKey);
  if (cached) {
    console.debug('Cache HIT: user invitations');
    return cached;
  }

  try {
    console.log('🟡 [SERVICE] Fetching user invitations from backend...');
    
    // Use backend API
    const response = await groupPlannerApi.getUserInvitations();
    const invitations = response.data || response;

    // Cache result
    cache.set(cacheKey, invitations, CacheConfig.TTL.INVITATIONS);
    console.log(`✅ [SERVICE] Found ${invitations.length} invitations`);
    return invitations;
  } catch (error) {
    console.error('❌ Error fetching user invitations:', error);
    throw error;
  }
}

/**
 * Resend an existing pending invitation
 * @param {string} invitationId - Invitation ID to resend
 * @returns {Promise<object>} - Updated invitation details
 */
async function resendInvitation(invitationId) {
  try {
    console.log('🟡 [SERVICE] Resending invitation:', invitationId);
    
    // Use backend API
    const response = await groupPlannerApi.resendInvitation(invitationId);
    
    console.log('✅ [SERVICE] Invitation resent:', response);
    
    // Invalidate user invitations cache to refresh
    cache.invalidate(CacheConfig.KEYS.USER_INVITATIONS);

    return response.data || response;
  } catch (error) {
    console.error(`❌ Error resending invitation ${invitationId}:`, error);
    throw error;
  }
}

/**
 * Get invitation details (public)
 * @param {string} invitationId - Invitation ID
 * @returns {Promise<object>} - Invitation details
 */
async function getInvitationDetails(invitationId) {
  try {
    console.log(`🟡 [SERVICE] Fetching invitation details: ${invitationId}`);
    const response = await fetch(getApiUrl(`${ApiConfig.ENDPOINTS.INVITATIONS}/${invitationId}`));
    const data = await response.json();

    if (!response.ok) {
      console.error(`❌ [SERVICE] Failed to get invitation ${invitationId}:`, data.error);
      throw new Error(data.error || 'Failed to get invitation');
    }

    console.log(`✅ [SERVICE] Invitation details fetched:`, data);
    // Backend returns invitation details directly (not nested in data property)
    return data;
  } catch (error) {
    console.error(`Error fetching invitation ${invitationId}:`, error);
    throw error;
  }
}

/**
 * Reject invitation
 * @param {string} invitationId - Invitation ID
 * @returns {Promise<object>} - Response
 */
async function rejectInvitation(invitationId) {
  try {
    const groupPlannerApi = (await import('./groupPlannerApi')).default;
    const currentUser = authService.getCurrentUser();
    if (currentUser) {
      groupPlannerApi.setCurrentUser(currentUser);
    }
    
    // Note: Backend doesn't have reject endpoint yet, can be added later
    console.warn('Reject invitation not yet implemented in backend');
    throw new Error('Reject endpoint not yet implemented');
  } catch (error) {
    console.error(`Error rejecting invitation ${invitationId}:`, error);
    throw error;
  }
}

// =========================================================================
// CACHE MANAGEMENT (Public)
// =========================================================================

/**
 * Manually clear all caches
 */
function clearCache() {
  cache.clear();
}

/**
 * Manually invalidate specific cache
 * @param {string} key - Cache key
 */
function invalidateCache(key) {
  cache.invalidate(key);
}

// =========================================================================
// EXPORT SERVICE
// =========================================================================

const groupPlannerService = {
  // Group operations
  createGroup,
  getGroups: getUserGroups, // Alias for consistency
  getUserGroups,
  getGroup,
  updateGroup,
  deleteGroup,

  // Member operations
  getGroupMembers,
  removeMember,

  // Place operations
  addPlace,
  getGroupPlaces,
  deletePlace,
  voteOnPlace,
  addPlaceRemark,
  updatePlaceDetails,
  updateItineraryDocument,

  // Poll operations
  createPoll,
  getGroupPolls,
  voteOnPoll,
  deletePoll,

  // Invitation operations
  createInvitation,
  getUserInvitations,
  resendInvitation,
  getInvitationDetails,
  acceptInvitation,
  rejectInvitation,

  // Checklist operations
  addChecklistItem: async (groupId, itemText) => {
    console.log('📝 [SERVICE] Adding checklist item:', { groupId, itemText });
    const response = await apiRequest(
      `${ApiConfig.BASE_URL}/group-planner/groups/${groupId}/checklist`,
      {
        method: 'POST',
        body: JSON.stringify({ item: itemText })
      }
    );
    // Invalidate group cache
    const cacheKey = getCacheKey('USER_GROUPS');
    invalidateCache(cacheKey);
    console.log('✅ [SERVICE] Checklist item added:', response);
    return response;
  },

  toggleChecklistItem: async (groupId, itemId) => {
    console.log('✅ [SERVICE] Toggling checklist item:', { groupId, itemId });
    const response = await apiRequest(
      `${ApiConfig.BASE_URL}/group-planner/groups/${groupId}/checklist/${itemId}/toggle`,
      {
        method: 'PATCH'
      }
    );
    // Invalidate group cache
    const cacheKey = getCacheKey('USER_GROUPS');
    invalidateCache(cacheKey);
    console.log('✅ [SERVICE] Checklist item toggled:', response);
    return response;
  },

  deleteChecklistItem: async (groupId, itemId) => {
    console.log('🗑️ [SERVICE] Deleting checklist item:', { groupId, itemId });
    const response = await apiRequest(
      `${ApiConfig.BASE_URL}/group-planner/groups/${groupId}/checklist/${itemId}`,
      {
        method: 'DELETE'
      }
    );
    // Invalidate group cache
    const cacheKey = getCacheKey('USER_GROUPS');
    invalidateCache(cacheKey);
    console.log('✅ [SERVICE] Checklist item deleted');
    return response;
  },

  // Budget operations
  updateBudget: async (groupId, budget) => {
    console.log('💰 [SERVICE] Updating budget:', { groupId, budget });
    const response = await apiRequest(
      `${ApiConfig.BASE_URL}/group-planner/groups/${groupId}/budget`,
      {
        method: 'PATCH',
        body: JSON.stringify({ estimated_budget: budget })
      }
    );
    // Invalidate group cache
    const cacheKey = getCacheKey('USER_GROUPS');
    invalidateCache(cacheKey);
    console.log('✅ [SERVICE] Budget updated:', response);
    return response;
  },

  /**
   * Link group to expense engine
   * Creates expense group with same name and members
   * @param {string} groupId - Group ID
   * @returns {Promise<{expense_group_id: string}>}
   */
  linkExpenseGroup: async (groupId) => {
    console.log('💰 [SERVICE] Linking to expense engine:', { groupId });
    const response = await apiRequest(
      `${ApiConfig.BASE_URL}/group-planner/groups/${groupId}/link-expense`,
      {
        method: 'POST'
      }
    );
    // Invalidate group cache to refresh with new expense_group_id
    const cacheKey = getCacheKey('USER_GROUPS');
    invalidateCache(cacheKey);
    console.log('✅ [SERVICE] Expense group linked:', response);
    return response;
  },

  // Cache management
  clearCache,
  invalidateCache,
  
  /**
   * Clear ALL cached data
   * CRITICAL: Must be called on logout to prevent cross-user data leaks
   */
  clearAllCache: () => {
    console.log('🗑️ [SERVICE] Clearing all Group Planner cache...');
    cache.clear();
    console.log('✅ [SERVICE] All cache cleared');
  }
};

export default groupPlannerService;
