/**
 * Place Search API Service
 *
 * Handles all API calls to the place search backend.
 * Uses apiClient for consistent HTTP handling.
 */

import GlobalConfig from '../config/globalConfig';
import apiClient from '../utils/apiClient';

const ENDPOINT = GlobalConfig.ENDPOINTS.PLACE_SEARCH;

/**
 * Search for places
 */
export const searchPlaces = async (query, options = {}) => {
  const {
    limit = GlobalConfig.PLACE_SEARCH_DEFAULT_LIMIT,
    offset = 0,
    sortBy = GlobalConfig.PLACE_SEARCH_DEFAULT_SORT_BY,
    sortOrder = GlobalConfig.PLACE_SEARCH_DEFAULT_SORT_ORDER,
    costFilter = [],
    ratingFilter = null,
  } = options;

  const params = new URLSearchParams({
    q: query,
    limit: limit.toString(),
    offset: offset.toString(),
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  if (costFilter.length > 0) {
    params.append('cost', costFilter.join(','));
  }
  if (ratingFilter) {
    params.append('rating', ratingFilter.toString());
  }

  return apiClient.get(`${ENDPOINT}/search?${params}`);
};

/**
 * Get autocomplete suggestions
 */
export const getAutocompleteSuggestions = async (query, limit = GlobalConfig.AUTOCOMPLETE_DEFAULT_LIMIT, { signal } = {}) => {
  if (!query || query.length < GlobalConfig.AUTOCOMPLETE_MIN_CHARS) {
    return [];
  }

  const params = new URLSearchParams({
    q: query,
    limit: limit.toString(),
  });

  const data = await apiClient.get(`${ENDPOINT}/autocomplete?${params}`, { signal });
  return data.suggestions || [];
};

/**
 * Get place details by ID
 */
export const getPlaceDetails = async (placeId) => {
  const data = await apiClient.get(`${ENDPOINT}/place/${placeId}`);
  return data.data || data.place || null;
};

/**
 * Get database statistics
 */
export const getStats = async () => {
  return apiClient.get(`${ENDPOINT}/stats`);
};

export default {
  searchPlaces,
  getAutocompleteSuggestions,
  getPlaceDetails,
  getStats,
};
