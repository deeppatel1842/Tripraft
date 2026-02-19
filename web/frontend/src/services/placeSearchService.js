/**
 * Place Search API Service
 *
 * Handles all API calls to the place search backend.
 * Falls back to empty/defaults if backend is unavailable.
 */

import GlobalConfig from '../config/globalConfig';

const PLACE_SEARCH_API = `${GlobalConfig.API_BASE_URL}/v1/place-search`;

/**
 * Search for places
 * @param {string} query - Search query
 * @param {Object} options - Search options
 * @returns {Promise<Object>} Search results
 */
export const searchPlaces = async (query, options = {}) => {
  const {
    limit = 500,
    offset = 0,
    sortBy = 'rank_score',
    sortOrder = 'desc',
    costFilter = [],
    ratingFilter = null,
  } = options;

  try {
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

    const response = await fetch(`${PLACE_SEARCH_API}/search?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      success: true,
      ...data,
    };
  } catch {
    return {
      success: false,
      error: 'Search unavailable',
      places: [],
      total_count: 0,
    };
  }
};

/**
 * Get autocomplete suggestions
 * @param {string} query - Partial search query
 * @param {number} limit - Max suggestions
 * @returns {Promise<Array>} Suggestions
 */
export const getAutocompleteSuggestions = async (query, limit = 10) => {
  if (!query || query.length < 2) {
    return [];
  }

  try {
    const params = new URLSearchParams({
      q: query,
      limit: limit.toString(),
    });

    const response = await fetch(`${PLACE_SEARCH_API}/autocomplete?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Autocomplete failed: ${response.statusText}`);
    }

    const data = await response.json();
    return data.suggestions || [];
  } catch {
    return [];
  }
};

/**
 * Get place details by ID
 * @param {number} placeId - Place ID
 * @returns {Promise<Object>} Place details
 */
export const getPlaceDetails = async (placeId) => {
  try {
    const response = await fetch(`${PLACE_SEARCH_API}/place/${placeId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Get place failed: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      success: true,
      place: data,
    };
  } catch {
    return {
      success: false,
      error: 'Place details unavailable',
      place: null,
    };
  }
};

/**
 * Get database statistics
 * @returns {Promise<Object>} Stats
 */
export const getStats = async () => {
  try {
    const response = await fetch(`${PLACE_SEARCH_API}/stats`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Get stats failed: ${response.statusText}`);
    }

    return await response.json();
  } catch {
    return {
      total_places: 0,
      total_countries: 0,
      total_states: 0,
      total_cities: 0,
    };
  }
};

export default {
  searchPlaces,
  getAutocompleteSuggestions,
  getPlaceDetails,
  getStats,
};
