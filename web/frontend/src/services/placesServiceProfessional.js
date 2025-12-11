/**
 * Places API Service - Professional Implementation
 * Handles all place search queries with proper error handling and logging
 * 
 * Features:
 * - Country/State/Place searches with unified response format
 * - Complete 34-field place structure
 * - Professional error handling
 * - Performance metrics (firebase reads, response time)
 * - No hardcoded values - all configurable
 */

import apiClient from '../utils/apiClient';
import apiLogger from '../utils/apiLogger';

// ============================================================================
// CONFIGURATION - ALL SETTINGS IN ONE PLACE
// ============================================================================

const API_CONFIG = {
  // API endpoints
  endpoints: {
    v1: '/v1',
    v2Places: '/v2/places',
  },
  
  // Pagination defaults
  pagination: {
    defaultLimit: 20,
    maxLimit: 100,
    defaultPage: 1,
  },
  
  // Search limits
  search: {
    minQueryLength: 2,
    maxQueryLength: 100,
    defaultLimit: 20,
  },
  
  // Autocomplete settings
  autocomplete: {
    minQueryLength: 1,
    maxSuggestions: 10,
    debounceMs: 300,
  },
  
  // Performance thresholds
  performance: {
    slowResponseMs: 2000,
    warningFirebaseReads: 5,
  },
};

// ============================================================================
// PLACE DATA TRANSFORMATION - 34-FIELD STRUCTURE
// ============================================================================

/**
 * Transform place data from backend to frontend format
 * Ensures all 34 fields are present with proper defaults
 */
class PlaceTransformer {
  static transformPlace(place) {
    if (!place) return null;

    return {
      // Group 1: Identification (5 fields)
      id: place.id || '',
      name: place.name || 'Unknown Place',
      name_english: place.name_english || null,
      name_native: place.name_native || null,
      name_normalized: place.name_normalized || null,

      // Group 2: Location (9 fields)
      address: place.address || 'Address not available',
      city: place.city || 'Unknown City',
      city_normalized: place.city_normalized || (place.city ? place.city.toLowerCase() : ''),
      state: place.state || 'Unknown State',
      state_normalized: place.state_normalized || (place.state ? place.state.toLowerCase() : ''),
      country: place.country || 'Unknown Country',
      country_normalized: place.country_normalized || (place.country ? place.country.toLowerCase() : ''),
      coordinates: {
        latitude: place.coordinates?.latitude || 0,
        longitude: place.coordinates?.longitude || 0,
      },
      has_coordinates: place.has_coordinates === true,

      // Group 3: Cost & Duration (3 fields)
      cost: place.cost || 'Cost not available',
      suggested_duration: place.suggested_duration || 'Duration not specified',
      best_time_to_visit: place.best_time_to_visit || 'Year-round',

      // Group 4: Ratings (2 fields)
      rating_tourist_priority: typeof place.rating_tourist_priority === 'number' ? place.rating_tourist_priority : 0,
      rating_traveler_experience: typeof place.rating_traveler_experience === 'number' ? place.rating_traveler_experience : 0,

      // Group 5: Content (3 fields)
      ai_summary: place.ai_summary || place.summary || 'No description available',
      tags: Array.isArray(place.tags) ? place.tags : [],
      search_text: place.search_text || '',

      // Group 6: Contact & Hours (3 fields)
      official_website: place.official_website || null,
      advanced_booking: place.advanced_booking || 'Not required',
      opening_hours: PlaceTransformer.transformOpeningHours(place.opening_hours),

      // Group 7: Media (1 field)
      photos: PlaceTransformer.transformPhotos(place.photos),

      // Group 8: Time of Day (4 fields)
      sunrise_time: place.sunrise_time || null,
      sunset_time: place.sunset_time || null,
      sunrise_view: place.sunrise_view === true,
      sunset_view: place.sunset_view === true,

      // Group 9: Ranking & Metadata (4 fields)
      rank_score: typeof place.rank_score === 'number' ? place.rank_score : 0,
      place_tip: place.place_tip || null,
      created_at: place.created_at || null,
      updated_at: place.updated_at || null,
    };
  }

  static transformOpeningHours(hours) {
    if (!hours) {
      return {
        monday: null,
        tuesday: null,
        wednesday: null,
        thursday: null,
        friday: null,
        saturday: null,
        sunday: null,
        notes: 'Hours not specified',
      };
    }

    return {
      monday: hours.monday || null,
      tuesday: hours.tuesday || null,
      wednesday: hours.wednesday || null,
      thursday: hours.thursday || null,
      friday: hours.friday || null,
      saturday: hours.saturday || null,
      sunday: hours.sunday || null,
      notes: hours.notes || 'Check website for details',
    };
  }

  static transformPhotos(photos) {
    if (!photos) {
      return {
        thumbnail_url: null,
        thumbnail_width: 800,
        thumbnail_height: 600,
        has_valid_photo: false,
        attribution: {
          author: 'Unknown',
          credit: 'Unknown',
          license: 'Unknown',
          license_url: null,
          source_url: null,
          title: 'Unknown',
          description: 'Unknown',
          usage_terms: 'Unknown',
        },
      };
    }

    return {
      thumbnail_url: photos.thumbnail_url || null,
      thumbnail_width: photos.thumbnail_width || 800,
      thumbnail_height: photos.thumbnail_height || 600,
      has_valid_photo: photos.has_valid_photo === true,
      attribution: photos.attribution || {
        author: 'Unknown',
        credit: 'Unknown',
        license: 'Unknown',
        license_url: null,
        source_url: null,
        title: 'Unknown',
        description: 'Unknown',
        usage_terms: 'Unknown',
      },
    };
  }
}

// ============================================================================
// PLACES SERVICE CLASS
// ============================================================================

class PlacesService {
  /**
   * Search for places by location (Country, State, or City)
   * Returns unified format for all three types
   *
   * @param {string} query - Location name (country, state, or city)
   * @param {number} limit - Max results to return
   * @param {number} page - Page number for pagination
   * @returns {Promise<Object>} Search results with places array
   */
  async searchByLocation(query, limit = API_CONFIG.search.defaultLimit, page = API_CONFIG.pagination.defaultPage) {
    try {
      // Validate input
      if (!query || query.trim().length < API_CONFIG.search.minQueryLength) {
        throw new Error(`Query must be at least ${API_CONFIG.search.minQueryLength} characters`);
      }

      if (query.length > API_CONFIG.search.maxQueryLength) {
        throw new Error(`Query must not exceed ${API_CONFIG.search.maxQueryLength} characters`);
      }

      // Constrain limit
      const constrainedLimit = Math.min(Math.max(1, limit), API_CONFIG.pagination.maxLimit);

      // Make API call
      const response = await apiClient.get(
        `${API_CONFIG.endpoints.v2Places}/location?q=${encodeURIComponent(query)}&limit=${constrainedLimit}&page=${page}`
      );

      // Check response
      if (!response) {
        throw new Error('No response from server');
      }

      if (!response.success) {
        throw new Error(response.error || response.message || 'Search failed');
      }

      // Transform places with complete 34-field structure
      const transformedPlaces = (response.places || []).map(place =>
        PlaceTransformer.transformPlace(place)
      );

      // Prepare result object
      const result = {
        // Query info
        query: query,
        success: true,
        matchType: response.match_type || 'unknown',
        matched: response.matched || {},

        // Data
        places: transformedPlaces,
        count: response.count || transformedPlaces.length,

        // Performance metrics
        cacheHit: response.cache_hit === true,
        firebaseReads: response.firebase_reads || 0,
        responseTime: response.response_time_ms || 0,

        // Pagination
        page: page,
        limit: constrainedLimit,
      };

      // Log success
      apiLogger.logSuccess('Location search completed', {
        query,
        matchType: result.matchType,
        count: result.count,
        firebaseReads: result.firebaseReads,
        responseTime: result.responseTime,
        cacheHit: result.cacheHit,
      });

      // Warn if slow response
      if (result.responseTime > API_CONFIG.performance.slowResponseMs) {
        apiLogger.logWarning('Slow search response', {
          query,
          responseTime: result.responseTime,
        });
      }

      // Warn if too many reads
      if (result.firebaseReads > API_CONFIG.performance.warningFirebaseReads) {
        apiLogger.logWarning('High Firebase read count', {
          query,
          firebaseReads: result.firebaseReads,
        });
      }

      return result;
    } catch (error) {
      // Extract error message safely
      let errorMessage = 'Failed to search places';
      
      // Try different error structures
      if (error?.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (error?.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error?.response?.status === 404) {
        errorMessage = `Location "${query}" not found. Try searching by country, state, or city.`;
      } else if (error?.message) {
        errorMessage = error.message;
      }

      apiLogger.logError('Location search failed', {
        query,
        error: errorMessage,
        status: error?.response?.status,
      });

      // Throw proper error
      const searchError = new Error(errorMessage);
      searchError.originalError = error;
      searchError.status = error?.response?.status;
      throw searchError;
    }
  }

  /**
   * Search for a specific place by ID (from autocomplete)
   * Used when user clicks on an autocomplete suggestion with a known place ID
   *
   * @param {string} placeId - Place ID from autocomplete suggestion
   * @returns {Promise<Object>} Search results with single place
   */
  async searchByLocationId(placeId) {
    try {
      // Validate input
      if (!placeId || placeId.trim().length === 0) {
        throw new Error('Place ID is required');
      }

      console.log('🔍 Fetching place by ID:', placeId);

      // Make API call to get specific place
      const response = await apiClient.get(
        `${API_CONFIG.endpoints.v2Places}/place/${encodeURIComponent(placeId)}`
      );

      // Check response
      if (!response) {
        throw new Error('No response from server');
      }

      if (!response.success && response.status !== 404) {
        throw new Error(response.error || response.message || 'Failed to fetch place');
      }

      // If place not found via ID, fall back to empty result
      if (!response.place) {
        return {
          query: placeId,
          success: false,
          matchType: 'unknown',
          places: [],
          count: 0,
          error: 'Place not found',
          firebaseReads: 0,
          responseTime: 0,
        };
      }

      // Transform place with complete 34-field structure
      const transformedPlace = PlaceTransformer.transformPlace(response.place);

      // Prepare result object
      const result = {
        // Query info
        query: placeId,
        success: true,
        matchType: response.match_type || response.place.type || 'place',
        matched: {
          id: response.place.id,
          name: response.place.name,
          country: response.place.country,
          state: response.place.state,
          city: response.place.city,
        },

        // Data
        places: [transformedPlace],
        count: 1,

        // Performance metrics
        cacheHit: response.cache_hit === true,
        firebaseReads: response.firebase_reads || 1,
        responseTime: response.response_time_ms || 0,
      };

      // Log success
      apiLogger.logSuccess('Place fetched by ID', {
        placeId,
        placeName: response.place.name,
        firebaseReads: result.firebaseReads,
        responseTime: result.responseTime,
        cacheHit: result.cacheHit,
      });

      return result;
    } catch (error) {
      // Extract error message safely
      let errorMessage = 'Failed to fetch place';
      
      if (error?.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (error?.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error?.response?.status === 404) {
        errorMessage = `Place not found. Please try a different search.`;
      } else if (error?.message) {
        errorMessage = error.message;
      }

      apiLogger.logError('Place fetch by ID failed', {
        placeId,
        error: errorMessage,
        status: error?.response?.status,
      });

      // Return empty result instead of throwing for ID not found
      return {
        query: placeId,
        success: false,
        matchType: 'unknown',
        places: [],
        count: 0,
        error: errorMessage,
        firebaseReads: 0,
        responseTime: 0,
      };
    }
  }

  /**
   * Get autocomplete suggestions
   *
   * @param {string} query - Partial query
   * @param {number} limit - Max suggestions
   * @returns {Promise<Object>} Suggestions array
   */
  async getAutocompleteSuggestions(
    query,
    limit = API_CONFIG.autocomplete.maxSuggestions
  ) {
    try {
      // Validate input
      if (!query || query.trim().length < API_CONFIG.autocomplete.minQueryLength) {
        return {
          success: true,
          suggestions: [],
          query: query,
        };
      }

      // Make API call
      const response = await apiClient.get(
        `${API_CONFIG.endpoints.v2Places}/autocomplete?q=${encodeURIComponent(query)}&limit=${limit}`
      );

      if (!response) {
        return {
          success: true,
          suggestions: [],
          query: query,
        };
      }

      return {
        success: true,
        suggestions: response.suggestions || [],
        query: query,
        firebaseReads: response.firebase_reads || 0,
        responseTime: response.response_time_ms || 0,
      };
    } catch (error) {
      apiLogger.logWarning('Autocomplete failed', {
        query,
        error: error.message,
      });

      return {
        success: false,
        suggestions: [],
        query: query,
        error: error.message,
      };
    }
  }

  /**
   * Get countries list
   *
   * @returns {Promise<Array>} Countries array
   */
  async getCountries() {
    try {
      const response = await apiClient.get(`${API_CONFIG.endpoints.v1}/countries/`);

      if (!response.success) {
        throw new Error(response.message || 'Failed to fetch countries');
      }

      apiLogger.logSuccess('Countries loaded', {
        count: response.data?.length || 0,
      });

      return response.data || [];
    } catch (error) {
      apiLogger.logWarning('Failed to fetch countries', { error: error.message });
      throw error;
    }
  }

  /**
   * Get states by country
   *
   * @param {string} countryId - Country ID
   * @returns {Promise<Array>} States array
   */
  async getStatesByCountry(countryId) {
    try {
      const response = await apiClient.get(
        `${API_CONFIG.endpoints.v1}/states/country/${encodeURIComponent(countryId)}`
      );

      if (!response.success) {
        throw new Error(response.message || 'Failed to fetch states');
      }

      apiLogger.logSuccess('States loaded', {
        country: countryId,
        count: response.data?.length || 0,
      });

      return response.data || [];
    } catch (error) {
      apiLogger.logWarning('Failed to fetch states', {
        country: countryId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get cities by country
   *
   * @param {string} countryId - Country ID
   * @returns {Promise<Array>} Cities array
   */
  async getCitiesByCountry(countryId) {
    try {
      const response = await apiClient.get(
        `${API_CONFIG.endpoints.v1}/cities/country/${encodeURIComponent(countryId)}`
      );

      if (!response.success) {
        throw new Error(response.message || 'Failed to fetch cities');
      }

      apiLogger.logSuccess('Cities loaded', {
        country: countryId,
        count: response.data?.length || 0,
      });

      return response.data || [];
    } catch (error) {
      apiLogger.logWarning('Failed to fetch cities', {
        country: countryId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Format place data for display (adds computed properties)
   *
   * @param {Object} place - Place object with 34 fields
   * @returns {Object} Formatted place for UI
   */
  formatPlaceForDisplay(place) {
    if (!place) return null;

    return {
      ...place,
      // Computed properties for UI
      displayName: place.name,
      displayLocation: `${place.city}, ${place.state}, ${place.country}`,
      averageRating: (place.rating_tourist_priority + place.rating_traveler_experience) / 2,
      rankPercentage: Math.round(place.rank_score * 100),
      hasWebsite: !!place.official_website,
      hasCoordinates: place.has_coordinates && place.coordinates.latitude !== 0 && place.coordinates.longitude !== 0,
      hasSunrise: place.sunrise_view,
      hasSunset: place.sunset_view,
      hasPhoto: place.photos?.has_valid_photo === true,
    };
  }

  /**
   * Get country overview with all states and top 5 places per state
   *
   * @param {string} countryName - Country name
   * @returns {Promise<Object>} Country data with states and places
   */
  async getCountryOverview(countryName) {
    try {
      if (!countryName || countryName.trim().length < 2) {
        throw new Error('Country name required');
      }

      const response = await apiClient.get(
        `${API_CONFIG.endpoints.v2Places}/country/${encodeURIComponent(countryName)}`
      );

      if (!response || !response.success) {
        throw new Error(response?.error || 'Country not found');
      }

      // Transform all places in all states
      const processedStates = (response.states || []).map(state => ({
        ...state,
        top_places: (state.top_places || []).map(place => PlaceTransformer.transformPlace(place)),
      }));

      const result = {
        success: true,
        country: response.country || countryName,
        states: processedStates,
        stateCount: response.state_count || processedStates.length,
        placeCount: response.place_count || 0,
        
        // Performance metrics
        firebaseReads: response.firebase_reads || 0,
        responseTime: response.response_time_ms || 0,
        cacheHit: response.cache_hit === true,
      };

      apiLogger.logSuccess('Country overview loaded', {
        country: countryName,
        states: result.stateCount,
        firebaseReads: result.firebaseReads,
        responseTime: result.responseTime,
      });

      return result;
    } catch (error) {
      apiLogger.logError('Country overview failed', {
        country: countryName,
        error: error.message,
      });
      return {
        success: false,
        error: error.message,
        states: [],
      };
    }
  }

  /**
   * Get state overview with top 20 places
   *
   * @param {string} stateName - State name
   * @param {string} countryName - Country name (optional, for disambiguation)
   * @returns {Promise<Object>} State data with places
   */
  async getStateOverview(stateName, countryName = null) {
    try {
      if (!stateName || stateName.trim().length < 2) {
        throw new Error('State name required');
      }

      let url = `${API_CONFIG.endpoints.v2Places}/location?q=${encodeURIComponent(stateName)}&limit=20`;
      
      const response = await apiClient.get(url);

      if (!response || !response.success) {
        throw new Error(response?.error || 'State not found');
      }

      const transformedPlaces = (response.places || []).map(place =>
        PlaceTransformer.transformPlace(place)
      );

      const result = {
        success: true,
        state: stateName,
        country: countryName,
        places: transformedPlaces,
        count: response.count || transformedPlaces.length,
        matchType: response.match_type || 'state',
        
        // Performance metrics
        firebaseReads: response.firebase_reads || 0,
        responseTime: response.response_time_ms || 0,
        cacheHit: response.cache_hit === true,
      };

      apiLogger.logSuccess('State overview loaded', {
        state: stateName,
        count: result.count,
        firebaseReads: result.firebaseReads,
        responseTime: result.responseTime,
      });

      return result;
    } catch (error) {
      apiLogger.logError('State overview failed', {
        state: stateName,
        error: error.message,
      });
      return {
        success: false,
        error: error.message,
        places: [],
      };
    }
  }

  /**
   * Get a single place by name/city
   *
   * @param {string} placeName - Place name
   * @param {string} cityName - City name
   * @returns {Promise<Object>} Place data
   */
  async getSinglePlace(placeName, cityName) {
    try {
      // Search by city first to get that city's places
      const cityResult = await this.searchByLocation(cityName, 50, 1);
      
      if (!cityResult.success || !cityResult.places) {
        throw new Error(`No places found in ${cityName}`);
      }

      // Find the specific place by name
      const place = cityResult.places.find(p => 
        p.name.toLowerCase() === placeName.toLowerCase()
      );

      if (!place) {
        throw new Error(`Place '${placeName}' not found in ${cityName}`);
      }

      apiLogger.logSuccess('Single place fetched', {
        place: placeName,
        city: cityName,
      });

      return {
        success: true,
        place: place,
        count: 1,
      };
    } catch (error) {
      apiLogger.logError('Single place fetch failed', {
        place: placeName,
        city: cityName,
        error: error.message,
      });
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Format multiple places for display
   *
   * @param {Array} places - Places array
   * @returns {Array} Formatted places
   */
  formatPlacesForDisplay(places) {
    return (places || []).map(place => this.formatPlaceForDisplay(place));
  }
}

// Export singleton instance
const placesService = new PlacesService();

export default placesService;
export { PlaceTransformer, API_CONFIG };

