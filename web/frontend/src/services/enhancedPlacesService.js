/**
 * Phase 5: Enhanced Places Service for Frontend Integration
 * 
 * Integrates with Phase 4 API helpers to provide optimized search and autocomplete
 * - Intelligent search (country/state/city/place detection)
 * - Autocomplete with prefix matching
 * - Consistent response formatting
 * - Performance tracking
 * - Error handling
 */

import apiClient from '../utils/apiClient';
import apiLogger from '../utils/apiLogger';

const API_V1 = '/v1';
const SEARCH_API = '/v1/places/search';
const AUTOCOMPLETE_API = '/v1/places/autocomplete';

class EnhancedPlacesService {
  /**
   * Intelligent search across all location types
   * Automatically detects query type (country/state/city/place)
   * 
   * @param {string} query - Search query
   * @param {string} type - Optional type override: 'country', 'state', 'city', 'place'
   * @returns {Promise} Search result with location hierarchy and places
   */
  async intelligentSearch(query, type = null) {
    try {
      // Validate input
      if (!query || query.trim().length === 0) {
        throw new Error('Search query is required');
      }

      const params = new URLSearchParams();
      params.append('q', query.trim());
      
      if (type) {
        params.append('type', type);
      }

      const url = `${SEARCH_API}?${params.toString()}`;
      const response = await apiClient.get(url);

      // Log performance metrics
      if (response.metadata) {
        apiLogger.logSuccess('Intelligent search completed', {
          query,
          type: response.data?.query_type,
          responseTime: response.metadata.response_time_ms,
          firestoreReads: response.metadata.firestore_reads,
          cacheHit: response.metadata.cache_hit,
        });
      }

      return {
        success: response.success,
        data: response.data,
        metadata: response.metadata,
      };
    } catch (error) {
      apiLogger.logError('Intelligent search failed', {
        query,
        type,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Autocomplete suggestions with prefix matching
   * 
   * @param {string} query - Partial query for suggestions
   * @param {number} limit - Maximum suggestions to return (default: 10)
   * @returns {Promise} Array of suggestions with ranking
   */
  async autocomplete(query, limit = 10) {
    try {
      // Validate input
      if (!query || query.trim().length === 0) {
        return {
          success: true,
          data: {
            query: '',
            suggestions: [],
            total: 0,
          },
          metadata: {
            response_time_ms: 0,
            firestore_reads: 0,
            cache_hit: false,
          },
        };
      }

      const params = new URLSearchParams();
      params.append('q', query.trim());
      params.append('limit', Math.min(limit, 50)); // Cap at 50 suggestions

      const url = `${AUTOCOMPLETE_API}?${params.toString()}`;
      const response = await apiClient.get(url);

      // Log performance metrics
      if (response.metadata) {
        apiLogger.logSuccess('Autocomplete completed', {
          query,
          suggestionsCount: response.data?.suggestions?.length || 0,
          responseTime: response.metadata.response_time_ms,
          cacheHit: response.metadata.cache_hit,
        });
      }

      return {
        success: response.success,
        data: response.data,
        metadata: response.metadata,
      };
    } catch (error) {
      apiLogger.logError('Autocomplete failed', {
        query,
        limit,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get country details with embedded states and top places
   */
  async getCountry(countryId) {
    try {
      const response = await apiClient.get(`${API_V1}/countries/${countryId}`);
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to fetch country');
      }

      apiLogger.logSuccess('Country loaded', {
        countryId,
        stateCount: response.data?.state_count,
        placeCount: response.data?.place_count,
      });

      return response.data;
    } catch (error) {
      apiLogger.logError('Failed to fetch country', {
        countryId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get state details with embedded cities and top places
   */
  async getState(stateId) {
    try {
      const response = await apiClient.get(`${API_V1}/states/${stateId}`);
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to fetch state');
      }

      apiLogger.logSuccess('State loaded', {
        stateId,
        cityCount: response.data?.city_count,
        placeCount: response.data?.place_count,
      });

      return response.data;
    } catch (error) {
      apiLogger.logError('Failed to fetch state', {
        stateId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get city details with top places
   */
  async getCity(cityId) {
    try {
      const response = await apiClient.get(`${API_V1}/cities/${cityId}`);
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to fetch city');
      }

      apiLogger.logSuccess('City loaded', {
        cityId,
        placeCount: response.data?.place_count,
      });

      return response.data;
    } catch (error) {
      apiLogger.logError('Failed to fetch city', {
        cityId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get place details
   */
  async getPlace(placeId) {
    try {
      const response = await apiClient.get(`${API_V1}/places/${placeId}`);
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to fetch place');
      }

      apiLogger.logSuccess('Place loaded', {
        placeId,
        name: response.data?.name,
      });

      return response.data;
    } catch (error) {
      apiLogger.logError('Failed to fetch place', {
        placeId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Format display for different query types
   * Converts API response to display-friendly format
   */
  formatSearchResult(result) {
    if (!result || !result.success) {
      return null;
    }

    const { data } = result;

    switch (data?.display_mode) {
      case 'country_sections':
        return {
          type: 'country',
          name: data.match?.name,
          description: `${data.location_hierarchy?.country}`,
          states: data.states || [],
          icon: 'Globe',
        };

      case 'top_destinations':
        return {
          type: data.location_hierarchy?.city ? 'city' : 'state',
          name: data.match?.name,
          description: `${data.location_hierarchy?.state || data.location_hierarchy?.country}`,
          places: data.places || [],
          totalPlaces: data.total_places,
          icon: data.location_hierarchy?.city ? 'MapPin' : 'Map',
        };

      case 'single_place':
        return {
          type: 'place',
          name: data.match?.name,
          city: data.location_hierarchy?.city,
          state: data.location_hierarchy?.state,
          country: data.location_hierarchy?.country,
          details: data.match,
          icon: 'MapPin',
        };

      default:
        return null;
    }
  }

  /**
   * Format autocomplete suggestions for dropdown display
   */
  formatAutocompleteSuggestions(result) {
    if (!result || !result.success || !result.data?.suggestions) {
      return [];
    }

    return result.data.suggestions.map(suggestion => ({
      id: suggestion.id,
      label: suggestion.name,
      type: suggestion.type,
      rank: suggestion.rank,
      category: this.getCategoryLabel(suggestion.type),
    }));
  }

  /**
   * Get human-readable category label
   */
  getCategoryLabel(type) {
    const labels = {
      country: 'Country',
      state: 'State/Province',
      city: 'City',
      place: 'Attraction',
    };
    return labels[type] || type;
  }

  /**
   * Check if response indicates an error
   */
  isError(response) {
    return !response || !response.success || response.error;
  }

  /**
   * Extract error message from response
   */
  getErrorMessage(response) {
    if (!response) return 'Unknown error occurred';
    return response.error || response.message || 'An error occurred';
  }
}

export default new EnhancedPlacesService();
