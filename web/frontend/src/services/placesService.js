/**
 * Places API Service
 * Connects to the professional Flask backend for places data
 */

import apiClient from '../utils/apiClient';
import apiLogger from '../utils/apiLogger';

const API_BASE = '/v1';
const API_V2_BASE = '/v2/places';

class PlacesService {
  /**
   * Get all countries
   */
  async getCountries() {
    try {
      const data = await apiClient.get(`${API_BASE}/countries/`);
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to fetch countries');
      }
      
      apiLogger.logSuccess('Countries loaded', { count: data.data?.length });
      return data.data;
    } catch (error) {
      apiLogger.logWarning('Failed to fetch countries', error);
      throw error;
    }
  }

  /**
   * Get states by country
   */
  async getStatesByCountry(countryId) {
    try {
      const data = await apiClient.get(`${API_BASE}/states/country/${countryId}`);
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to fetch states');
      }
      
      apiLogger.logSuccess('States loaded', { countryId, count: data.data?.length });
      return data.data;
    } catch (error) {
      apiLogger.logWarning('Failed to fetch states', { countryId, error });
      throw error;
    }
  }

  /**
   * Get cities by state
   */
  async getCitiesByState(stateId) {
    try {
      const data = await apiClient.get(`${API_BASE}/cities/state/${stateId}`);
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to fetch cities');
      }
      
      apiLogger.logSuccess('Cities loaded', { stateId, count: data.data?.length });
      return data.data;
    } catch (error) {
      apiLogger.logWarning('Failed to fetch cities', { stateId, error });
      throw error;
    }
  }

  /**
   * Get cities by country
   */
  async getCitiesByCountry(countryId) {
    try {
      const data = await apiClient.get(`${API_BASE}/cities/country/${countryId}`);
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to fetch cities');
      }
      
      apiLogger.logSuccess('Cities loaded', { countryId, count: data.data?.length });
      return data.data;
    } catch (error) {
      apiLogger.logWarning('Failed to fetch cities', { countryId, error });
      throw error;
    }
  }

  /**
   * Get places by city
   */
  async getPlacesByCity(cityId, limit = 20, offset = 0) {
    try {
      const data = await apiClient.get(`${API_BASE}/places/city/${cityId}?limit=${limit}&offset=${offset}`);
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to fetch places');
      }
      
      // Transform all places
      const transformedPlaces = (data.data || []).map(place => this.transformPlaceData(place));
      
      apiLogger.logSuccess('Places loaded', { 
        cityId, 
        count: transformedPlaces.length
      });
      
      return {
        places: transformedPlaces,
        pagination: data.pagination
      };
    } catch (error) {
      apiLogger.logWarning('Failed to fetch places by city', { cityId, error });
      throw error;
    }
  }

  /**
   * Get places by state
   */
  async getPlacesByState(stateId, limit = 20, offset = 0) {
    try {
      const data = await apiClient.get(`${API_BASE}/places/state/${stateId}?limit=${limit}&offset=${offset}`);
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to fetch places');
      }
      
      // Transform all places
      const transformedPlaces = (data.data || []).map(place => this.transformPlaceData(place));
      
      apiLogger.logSuccess('Places loaded', { 
        stateId, 
        count: transformedPlaces.length
      });
      
      return {
        places: transformedPlaces,
        pagination: data.pagination
      };
    } catch (error) {
      apiLogger.logWarning('Failed to fetch places by state', { stateId, error });
      throw error;
    }
  }

  /**
   * Search places by location (city or state) - V2 API
   * This is the primary search method that returns 20 places in 1 Firebase read
   */
  async searchByLocation(query, limit = 20, page = 1) {
    try {
      const data = await apiClient.get(`${API_V2_BASE}/location?q=${encodeURIComponent(query)}&limit=${limit}&page=${page}`);
      
      if (!data) {
        throw new Error('No response from server');
      }
      
      if (!data.success) {
        throw new Error(data.error || data.message || 'Failed to search places');
      }
      
      // Transform all places from V2 format
      const transformedPlaces = (data.places || []).map(place => this.transformV2PlaceData(place));
      
      // For country search, also transform states data
      const transformedStates = (data.states || []).map(state => ({
        state_id: state.state_id,
        state_name: state.state_name,
        place_count: state.place_count,
        top_places: (state.top_places || []).map(place => this.transformV2PlaceData(place))
      }));
      
      // Handle both snake_case (from backend) and camelCase (from older code)
      const matchType = data.match_type || data.matchType;
      const cacheHit = data.cache_hit || data.cacheHit;
      const responseTime = data.response_time_ms || data.responseTime;
      const firebaseReads = data.firebase_reads || data.firebaseReads;
      
      apiLogger.logSuccess('Location search results', { 
        query, 
        matchType: matchType,
        count: transformedPlaces.length,
        cacheHit: cacheHit,
        responseTime: responseTime
      });
      
      return {
        places: transformedPlaces,
        states: transformedStates,
        matchType: matchType,
        match_type: matchType, // Also return snake_case for backward compatibility
        matched: data.matched,
        count: data.count,
        cacheHit: cacheHit,
        cache_hit: cacheHit, // Also return snake_case for backward compatibility
        responseTime: responseTime,
        response_time_ms: responseTime, // Also return snake_case for backward compatibility
        firebaseReads: firebaseReads,
        firebase_reads: firebaseReads // Also return snake_case for backward compatibility
      };
    } catch (error) {
      // Extract meaningful error message
      const errorMessage = error.response?.data?.error || error.response?.data?.message || error.message || 'Failed to search places';
      
      // Create proper error object
      const apiError = new Error(errorMessage);
      if (error.response) {
        apiError.response = error.response;
      }
      
      throw apiError;
    }
  }

  /**
   * Get country overview with states and top 5 places per state - V2 API
   */
  async getCountryOverview(countryName) {
    try {
      const data = await apiClient.get(`${API_V2_BASE}/country/${encodeURIComponent(countryName)}`);
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch country overview');
      }
      
      apiLogger.logSuccess('Country overview loaded', { 
        country: data.country,
        stateCount: data.state_count,
        totalPlaces: data.total_places,
        cacheHit: data.cache_hit
      });
      
      return {
        country: data.country,
        stateCount: data.state_count,
        totalPlaces: data.total_places,
        states: data.states,
        cacheHit: data.cache_hit,
        responseTime: data.response_time_ms
      };
    } catch (error) {
      apiLogger.logWarning('Country overview failed', { countryName, error });
      throw error;
    }
  }

  /**
   * Get autocomplete suggestions - V2 API
   */
  async getAutocompleteSuggestions(query) {
    try {
      const data = await apiClient.get(`${API_V2_BASE}/autocomplete?q=${encodeURIComponent(query)}`);
      
      if (!data.success) {
        return { suggestions: [] };
      }
      
      return {
        suggestions: data.suggestions || [],
        cacheHit: data.cache_hit
      };
    } catch (error) {
      console.warn('Autocomplete failed:', error);
      return { suggestions: [] };
    }
  }

  /**
   * Search places (legacy V1 method - kept for backward compatibility)
   */
  async searchPlaces(query, limit = 20, offset = 0) {
    try {
      const data = await apiClient.get(`${API_BASE}/places/search?q=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}`);
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to search places');
      }
      
      // Transform all places
      const transformedPlaces = (data.data || []).map(place => this.transformPlaceData(place));
      
      apiLogger.logSuccess('Search results', { 
        query, 
        count: transformedPlaces.length
      });
      
      return {
        places: transformedPlaces,
        pagination: data.pagination,
        query: data.message
      };
    } catch (error) {
      apiLogger.logWarning('Search failed', { query, error });
      throw error;
    }
  }

  /**
   * Get a single place by ID
   */
  async getPlaceById(placeId) {
    try {
      const data = await apiClient.get(`${API_BASE}/places/${placeId}`);
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to fetch place');
      }
      
      apiLogger.logSuccess('Place loaded', { placeId });
      return data.data;
    } catch (error) {
      apiLogger.logWarning('Failed to fetch place', { placeId, error });
      throw error;
    }
  }

  /**
   * Transform backend place data to frontend format
   * Maps our database fields to the format expected by PlaceCard component
   */
  transformPlaceData(place) {
    // Handle coordinates - they might be an object, string, or null
    let coordinates = null;
    
    if (place.coordinates) {
      if (typeof place.coordinates === 'string') {
        try {
          coordinates = JSON.parse(place.coordinates);
        } catch (e) {
          coordinates = null;
        }
      } else if (typeof place.coordinates === 'object') {
        coordinates = place.coordinates;
      }
    }
    
    // Handle photos - might be object or string
    let photos = {};
    if (place.photos) {
      if (typeof place.photos === 'string') {
        try {
          photos = JSON.parse(place.photos);
        } catch (e) {
          photos = {};
        }
      } else if (typeof place.photos === 'object') {
        photos = place.photos;
      }
    }
    
    // Handle tags - might be array or string
    let tags = [];
    if (place.tags) {
      if (typeof place.tags === 'string') {
        try {
          tags = JSON.parse(place.tags);
        } catch (e) {
          tags = [];
        }
      } else if (Array.isArray(place.tags)) {
        tags = place.tags;
      }
    }
    
    // Handle opening_hours - might be object or string
    let openingHours = null;
    if (place.opening_hours) {
      if (typeof place.opening_hours === 'string') {
        openingHours = place.opening_hours;
      } else if (typeof place.opening_hours === 'object') {
        // Convert object to readable string
        if (place.opening_hours.notes) {
          openingHours = place.opening_hours.notes;
        } else {
          openingHours = JSON.stringify(place.opening_hours);
        }
      }
    }

    // Get thumbnail URL
    const thumbnailUrl = this.getPlaceThumbnail(photos);

    // Build the transformed place object
    return {
      id: place.id,
      displayName: {
        text: place.name || place.name_native || 'Unknown Place',
        languageCode: 'en'
      },
      // Coordinates are optional now
      location: coordinates ? {
        latitude: coordinates.lat || 0,
        longitude: coordinates.lng || 0
      } : null,
      types: Array.isArray(tags) ? tags.map(tag => tag.toLowerCase().replace(/\s+/g, '_')) : [],
      rating: place.rating || 0,
      userRatingCount: 0,
      thumbnailUrl: thumbnailUrl,
      formattedAddress: place.address || '',
      
      // Summary
      summary: place.summary || '',
      
      // Opening hours
      opening_hours: openingHours,
      
      // Duration and cost
      duration: place.duration || null,
      cost: place.cost || null,
      
      // Website
      website: place.website || null,
      
      // Best time to visit
      best_time: place.best_time || null,
      
      // Booking info
      advance_booking: place.advance_booking || null,
      
      // Tips
      place_tip: place.place_tip || null,
      
      // Special features
      sunrise_view: place.sunrise_view || false,
      sunset_view: place.sunset_view || false,
      
      // Location context
      city_name: place.city_name || '',
      state_name: place.state_name || '',
      country_name: place.country_name || '',
      
      // Photos object with full structure including attribution
      photos: photos,
      
      // Legacy fields for compatibility
      distance_to_query: 0,
      rank_score: place.rating || 0
    };
  }

  /**
   * Transform V2 API place data to frontend format
   * V2 API returns cleaner, more structured data from Firestore
   */
  transformV2PlaceData(place) {
    // V2 API already returns clean coordinates object
    const coordinates = place.coordinates || null;
    
    // Get thumbnail URL from photos
    const thumbnailUrl = this.getPlaceThumbnail(place.photos || {});
    
    // Debug logging for photo issues
    if (place.name && place.name.includes('Alamo')) {
      console.log('🖼️ Transform Alamo:', {
        name: place.name,
        photos: place.photos,
        extractedUrl: thumbnailUrl
      });
    }

    return {
      id: place.id,
      displayName: {
        text: place.name || 'Unknown Place',
        languageCode: 'en'
      },
      name: place.name,
      location: coordinates ? {
        latitude: coordinates.latitude || 0,
        longitude: coordinates.longitude || 0
      } : null,
      types: place.tags || [],
      tags: place.tags || [],
      rating: place.rating_tourist_priority || place.rank_score || 0,
      rank_score: place.rank_score || 0,
      userRatingCount: 0,
      thumbnailUrl: thumbnailUrl,
      formattedAddress: place.address || '',
      
      // Summary
      summary: place.ai_summary || place.description || '',
      
      // Opening hours
      opening_hours: place.opening_hours,
      
      // Duration and cost
      duration: place.suggested_duration || null,
      cost: place.cost || null,
      
      // Website
      website: place.official_website || null,
      websiteUri: place.official_website || null,
      
      // Best time to visit
      best_time: place.best_time_to_visit || null,
      
      // Booking info
      advance_booking: place.advanced_booking ? 'Recommended' : 'Not Required',
      
      // Tips
      place_tip: place.place_tip || null,
      
      // Special features
      sunrise_view: place.sunrise_view || false,
      sunset_view: place.sunset_view || false,
      sunrise_time: place.sunrise_time || null,
      sunset_time: place.sunset_time || null,
      
      // Location context
      city_name: place.city || '',
      state_name: place.state || '',
      country_name: place.country || '',
      
      // Photos object with full structure
      photos: place.photos || {},
      
      // V2 specific fields
      slug: place.slug,
      search_text: place.search_text,
      created_at: place.created_at,
      updated_at: place.updated_at
    };
  }

  /**
   * Get thumbnail URL from photos object
   */
  getPlaceThumbnail(photos) {
    // Handle null/undefined photos
    if (!photos || typeof photos !== 'object') {
      return null;
    }
    
    // V2 API: Direct thumbnail_url field (most common)
    if (photos.thumbnail_url) {
      // Only skip if explicitly marked as invalid
      if (photos.has_valid_photo === false) {
        return null;
      }
      return photos.thumbnail_url;
    }
    
    // Try different photo sources
    if (photos.primary?.url) {
      return photos.primary.url;
    }
    
    if (photos.wikimedia_commons?.thumbnail?.url) {
      return photos.wikimedia_commons.thumbnail.url;
    }
    
    if (photos.gallery && photos.gallery.length > 0) {
      return photos.gallery[0].url;
    }
    
    if (photos.wikipedia && photos.wikipedia.length > 0) {
      return photos.wikipedia[0];
    }
    
    if (photos.osm && photos.osm.length > 0) {
      return photos.osm[0];
    }
    
    return null;
  }

  /**
   * Get autocomplete suggestions while typing
   */
  async getAutocompleteSuggestions(query, limit = 10) {
    try {
      if (!query || query.trim().length < 2) {
        return {
          success: true,
          suggestions: []
        };
      }

      const data = await apiClient.get(`${API_V2_BASE}/autocomplete?q=${encodeURIComponent(query)}&limit=${limit}`);
      
      if (!data || !data.suggestions) {
        return {
          success: true,
          suggestions: []
        };
      }

      // Extract suggestion names from objects
      const suggestionNames = data.suggestions.map(item => {
        // Handle both string and object formats
        return typeof item === 'string' ? item : item.name || item;
      });

      apiLogger.logSuccess('Autocomplete suggestions', { 
        query, 
        count: suggestionNames.length
      });

      return {
        success: true,
        suggestions: suggestionNames || []
      };
    } catch (error) {
      apiLogger.logWarning('Failed to fetch autocomplete suggestions', { query, error });
      return {
        success: false,
        suggestions: [],
        error: error.message
      };
    }
  }

  /**
   * Calculate distance between two coordinates (Haversine formula)
   */
  calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in km
    const dLat = this.toRad(lat2 - lat1);
    const dLon = this.toRad(lon2 - lon1);
    const a = 
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  toRad(degrees) {
    return degrees * (Math.PI / 180);
  }
}

export default new PlacesService();
