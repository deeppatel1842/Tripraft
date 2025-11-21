/**
 * Places API Service
 * Connects to the professional Flask backend for places data
 */

import apiClient from '../utils/apiClient';
import apiLogger from '../utils/apiLogger';

const API_BASE = '/v1';

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
   * Search places
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
   * Get thumbnail URL from photos object
   */
  getPlaceThumbnail(photos) {
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
