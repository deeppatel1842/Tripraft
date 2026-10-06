// Purpose: Provides trip Planner Service logic and exports for apps\web\src\services.
/**
 * Trip Planner API Service
 * Connects to the Flask backend for AI-powered trip itinerary generation
 */

import apiClient from '../utils/apiClient';
import apiLogger from '../utils/apiLogger';
import { placeRating } from '../utils/placeRating';
import GlobalConfig from '../config/globalConfig';

const API_BASE = GlobalConfig.ENDPOINTS.TRIP_PLANNER;

/**
 * TripPlannerService
 * Handles all trip planning API interactions
 */
/**
 * The API always answers with a {success, data, meta} envelope and apiClient
 * passes it through untouched, so the payload lives under `data`.
 */
function unwrap(response) {
  return response?.data ?? response;
}

class TripPlannerService {
  /**
   * Generate a trip itinerary
   * @param {Object} params - Trip parameters
   * @param {string} params.city - City name (required)
   * @param {number} params.days - Number of days (1-14, default 3)
   * @param {string} params.pacing - Pacing code: R=Relaxed, M=Moderate, P=Packed
   * @returns {Promise<Object>} Generated itinerary
   */
  async generateTrip(params) {
    const startTime = performance.now();
    
    try {
      const response = await apiClient.post(`${API_BASE}/generate`, {
        city: params.city,
        days: params.days || GlobalConfig.TRIP_DEFAULT_DAYS,
        pacing: params.pacing || GlobalConfig.TRIP_DEFAULT_PACING
      });
      
      const duration = performance.now() - startTime;
      const payload = unwrap(response);

      if (response.success) {
        apiLogger.logSuccess('Trip generated', {
          city: params.city,
          days: params.days,
          stops: (payload?.itinerary || []).reduce(
            (acc, day) => acc + (day?.stops?.length || 0),
            0
          ),
          duration: `${duration.toFixed(0)}ms`
        });

        return this._transformItinerary(payload, response);
      }

      throw new Error(response.error?.message || response.error || 'Failed to generate trip');
    } catch (error) {
      apiLogger.logError('Trip generation failed', {
        city: params.city,
        error: error.message
      });
      throw error;
    }
  }
  
  /**
   * Search for cities
   * @param {string} query - Search query
   * @param {number} limit - Max results (default 10)
   * @returns {Promise<Array>} Matching cities
   */
  async searchCities(query, limit = GlobalConfig.CITY_SEARCH_LIMIT) {
    try {
      const response = await apiClient.get(
        `${API_BASE}/cities/search?q=${encodeURIComponent(query)}&limit=${limit}`
      );
      
      if (response.success) {
        const payload = unwrap(response);
        return Array.isArray(payload) ? payload : payload?.cities || [];
      }

      throw new Error(response.error?.message || response.error || 'City search failed');
    } catch (error) {
      apiLogger.logWarning('City search failed', { query, error: error.message });
      throw error;
    }
  }
  
  /**
   * Get list of available cities
   * @param {Object} options - Filter options
   * @param {string} options.country - Filter by country
   * @param {number} options.limit - Max results
   * @returns {Promise<Array>} List of cities
   */
  async getCities(options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.country) params.append('country', options.country);
      if (options.limit) params.append('limit', options.limit);
      
      const queryString = params.toString();
      const endpoint = queryString ? `${API_BASE}/cities?${queryString}` : `${API_BASE}/cities`;
      
      const response = await apiClient.get(endpoint);
      
      if (response.success) {
        const payload = unwrap(response);
        return Array.isArray(payload) ? payload : payload?.cities || [];
      }

      throw new Error(response.error?.message || response.error || 'Failed to fetch cities');
    } catch (error) {
      apiLogger.logWarning('Failed to fetch cities', error);
      throw error;
    }
  }
  
  /**
   * Get pacing options
   * @returns {Promise<Array>} Pacing options with descriptions
   */
  async getPacingOptions() {
    try {
      const response = await apiClient.get(`${API_BASE}/pacing-options`);
      
      if (response.success) {
        const payload = unwrap(response);
        const options = Array.isArray(payload) ? payload : payload?.options;
        if (options?.length) return options;
      }
      
      return [
        { code: 'R', name: 'Relaxed', description: 'Start at 10:00, up to 3 activities/day' },
        { code: 'M', name: 'Moderate', description: 'Start at 9:00, up to 4 activities/day' },
        { code: 'P', name: 'Packed', description: 'Start at 8:00, up to 5 activities/day' }
      ];
    } catch (error) {
      // Return defaults if API fails
      return [
        { code: 'R', name: 'Relaxed', description: 'Start at 10:00, up to 3 activities/day' },
        { code: 'M', name: 'Moderate', description: 'Start at 9:00, up to 4 activities/day' },
        { code: 'P', name: 'Packed', description: 'Start at 8:00, up to 5 activities/day' }
      ];
    }
  }
  
  /**
   * Transform API response to frontend format
   * @private
   */
  _transformItinerary(response, envelope = null) {
    return {
      success: envelope ? envelope.success : response.success,
      title: response.title,
      city: response.city,
      airport: response.airport ? {
        name: response.airport.name,
        iata: response.airport.iata,
        distance_km: response.airport.distance_km || null
      } : null,
      pacing: response.pacing,
      days: response.days,
      itinerary: response.itinerary || [],
      highRankedPlaces: (response.highRankedPlaces || []).map(place => ({
        ...place,
        name: place.name,
        rating: placeRating(place),
        reviewCount: place.reviewCount || 0,
        rank_score: place.rank_score
      })),
      specialPlaces: {
        early_morning: (response.specialPlaces?.early_morning || []).map(p => ({
          name: p.name,
          time: p.time || 'Early morning'
        })),
        late_night: (response.specialPlaces?.late_night || []).map(p => ({
          name: p.name,
          time: p.time || 'Evening'
        }))
      },
      totalPlaces: response.total_places ?? envelope?.meta?.count,
      responseTime: response.response_time_ms ?? envelope?.meta?.response_time_ms
    };
  }
}

// Export singleton instance
const tripPlannerService = new TripPlannerService();
export default tripPlannerService;

// Named export for direct access
export { TripPlannerService };
