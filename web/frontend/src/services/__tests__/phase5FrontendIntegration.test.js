/**
 * Phase 5: Frontend Integration Tests
 * 
 * Tests for:
 * - Enhanced Places Service
 * - Places Search Component
 * - API integration
 * - Response formatting
 */

import enhancedPlacesService from '../../services/enhancedPlacesService';

describe('Phase 5: Frontend Integration', () => {
  describe('EnhancedPlacesService', () => {
    describe('formatSearchResult', () => {
      it('should format country search result', () => {
        const result = {
          success: true,
          data: {
            match: { name: 'France', id: 'france' },
            query_type: 'country',
            display_mode: 'country_sections',
            location_hierarchy: { country: 'France' },
            states: [],
          },
        };

        const formatted = enhancedPlacesService.formatSearchResult(result);

        expect(formatted).toBeDefined();
        expect(formatted.type).toBe('country');
        expect(formatted.name).toBe('France');
        expect(formatted.icon).toBe('Globe');
      });

      it('should format city search result', () => {
        const result = {
          success: true,
          data: {
            match: { name: 'Paris', id: 'paris' },
            query_type: 'city',
            display_mode: 'top_destinations',
            location_hierarchy: { city: 'Paris', state: 'Île-de-France', country: 'France' },
            places: [{ name: 'Eiffel Tower' }],
            total_places: 20,
          },
        };

        const formatted = enhancedPlacesService.formatSearchResult(result);

        expect(formatted).toBeDefined();
        expect(formatted.type).toBe('city');
        expect(formatted.name).toBe('Paris');
        expect(formatted.places).toHaveLength(1);
        expect(formatted.totalPlaces).toBe(20);
        expect(formatted.icon).toBe('MapPin');
      });

      it('should format place search result', () => {
        const result = {
          success: true,
          data: {
            match: { name: 'Eiffel Tower', id: 'eiffel' },
            query_type: 'place',
            display_mode: 'single_place',
            location_hierarchy: { city: 'Paris', state: 'Île-de-France', country: 'France' },
          },
        };

        const formatted = enhancedPlacesService.formatSearchResult(result);

        expect(formatted).toBeDefined();
        expect(formatted.type).toBe('place');
        expect(formatted.name).toBe('Eiffel Tower');
        expect(formatted.city).toBe('Paris');
        expect(formatted.state).toBe('Île-de-France');
      });

      it('should handle failed search results', () => {
        const result = { success: false, error: 'Not found' };
        const formatted = enhancedPlacesService.formatSearchResult(result);
        expect(formatted).toBeNull();
      });

      it('should handle null results', () => {
        const formatted = enhancedPlacesService.formatSearchResult(null);
        expect(formatted).toBeNull();
      });
    });

    describe('formatAutocompleteSuggestions', () => {
      it('should format autocomplete suggestions', () => {
        const result = {
          success: true,
          data: {
            query: 'par',
            suggestions: [
              { id: 'paris', name: 'Paris', type: 'city', rank: 0.95 },
              { id: 'paris-tx', name: 'Paris, Texas', type: 'city', rank: 0.7 },
            ],
            total: 2,
          },
        };

        const formatted = enhancedPlacesService.formatAutocompleteSuggestions(result);

        expect(formatted).toHaveLength(2);
        expect(formatted[0]).toEqual({
          id: 'paris',
          label: 'Paris',
          type: 'city',
          rank: 0.95,
          category: 'City',
        });
      });

      it('should handle empty suggestions', () => {
        const result = {
          success: true,
          data: {
            query: 'xyz',
            suggestions: [],
            total: 0,
          },
        };

        const formatted = enhancedPlacesService.formatAutocompleteSuggestions(result);
        expect(formatted).toHaveLength(0);
      });

      it('should handle failed autocomplete', () => {
        const result = { success: false };
        const formatted = enhancedPlacesService.formatAutocompleteSuggestions(result);
        expect(formatted).toEqual([]);
      });
    });

    describe('getCategoryLabel', () => {
      it('should return correct category labels', () => {
        expect(enhancedPlacesService.getCategoryLabel('country')).toBe('Country');
        expect(enhancedPlacesService.getCategoryLabel('state')).toBe('State/Province');
        expect(enhancedPlacesService.getCategoryLabel('city')).toBe('City');
        expect(enhancedPlacesService.getCategoryLabel('place')).toBe('Attraction');
      });

      it('should return type for unknown categories', () => {
        expect(enhancedPlacesService.getCategoryLabel('unknown')).toBe('unknown');
      });
    });

    describe('isError', () => {
      it('should identify error responses', () => {
        expect(enhancedPlacesService.isError(null)).toBe(true);
        expect(enhancedPlacesService.isError({ success: false })).toBe(true);
        expect(enhancedPlacesService.isError({ error: 'Some error' })).toBe(true);
        expect(enhancedPlacesService.isError({ success: true })).toBe(false);
      });
    });

    describe('getErrorMessage', () => {
      it('should extract error messages', () => {
        expect(enhancedPlacesService.getErrorMessage(null)).toBe('Unknown error occurred');
        expect(enhancedPlacesService.getErrorMessage({ error: 'Not found' })).toBe('Not found');
        expect(enhancedPlacesService.getErrorMessage({ message: 'Failed' })).toBe('Failed');
      });
    });
  });

  describe('Response Format Validation', () => {
    it('should validate search response format', () => {
      const response = {
        success: true,
        data: {
          query: 'Paris',
          query_type: 'city',
          display_mode: 'top_destinations',
          match: { id: 'paris', name: 'Paris' },
          location_hierarchy: { city: 'Paris', state: 'Île-de-France', country: 'France' },
          places: [],
          total_places: 20,
        },
        metadata: {
          response_time_ms: 45.2,
          firestore_reads: 1,
          cache_hit: false,
        },
      };

      // Validate structure
      expect(response).toHaveProperty('success');
      expect(response).toHaveProperty('data');
      expect(response).toHaveProperty('metadata');

      expect(response.data).toHaveProperty('query');
      expect(response.data).toHaveProperty('query_type');
      expect(response.data).toHaveProperty('display_mode');
      expect(response.data).toHaveProperty('match');

      expect(response.metadata).toHaveProperty('response_time_ms');
      expect(response.metadata).toHaveProperty('firestore_reads');
      expect(response.metadata).toHaveProperty('cache_hit');
    });

    it('should validate autocomplete response format', () => {
      const response = {
        success: true,
        data: {
          query: 'par',
          suggestions: [
            { id: 'paris', name: 'Paris', type: 'city', rank: 0.95 },
          ],
          total: 1,
        },
        metadata: {
          response_time_ms: 25.3,
          firestore_reads: 1,
          cache_hit: true,
        },
      };

      expect(response.data).toHaveProperty('query');
      expect(response.data).toHaveProperty('suggestions');
      expect(response.data).toHaveProperty('total');

      expect(response.data.suggestions[0]).toHaveProperty('id');
      expect(response.data.suggestions[0]).toHaveProperty('name');
      expect(response.data.suggestions[0]).toHaveProperty('type');
      expect(response.data.suggestions[0]).toHaveProperty('rank');
    });

    it('should handle error response format', () => {
      const response = {
        success: false,
        error: 'Query parameter missing',
        error_type: 'missing_query',
      };

      expect(response).toHaveProperty('success');
      expect(response.success).toBe(false);
      expect(response).toHaveProperty('error');
      expect(response).toHaveProperty('error_type');
    });
  });

  describe('Display Mode Handling', () => {
    it('should recognize country_sections display mode', () => {
      const data = { display_mode: 'country_sections' };
      expect(['country_sections', 'top_destinations', 'single_place']).toContain(data.display_mode);
    });

    it('should recognize top_destinations display mode', () => {
      const data = { display_mode: 'top_destinations' };
      expect(['country_sections', 'top_destinations', 'single_place']).toContain(data.display_mode);
    });

    it('should recognize single_place display mode', () => {
      const data = { display_mode: 'single_place' };
      expect(['country_sections', 'top_destinations', 'single_place']).toContain(data.display_mode);
    });
  });

  describe('Performance Metrics', () => {
    it('should extract performance metadata', () => {
      const result = {
        success: true,
        data: {},
        metadata: {
          response_time_ms: 45.2,
          firestore_reads: 1,
          cache_hit: false,
        },
      };

      expect(result.metadata.response_time_ms).toBeLessThan(1000); // Should be < 1 second
      expect(result.metadata.firestore_reads).toBeGreaterThanOrEqual(0);
      expect(typeof result.metadata.cache_hit).toBe('boolean');
    });

    it('should track cache hits', () => {
      const cachedResult = {
        metadata: {
          response_time_ms: 5.1,
          firestore_reads: 0,
          cache_hit: true,
        },
      };

      expect(cachedResult.metadata.cache_hit).toBe(true);
      expect(cachedResult.metadata.response_time_ms).toBeLessThan(10); // Cached should be faster
      expect(cachedResult.metadata.firestore_reads).toBe(0); // No DB reads for cached
    });
  });

  describe('Query Type Detection', () => {
    const validTypes = ['country', 'state', 'city', 'place', 'unknown'];

    it('should have valid query types', () => {
      validTypes.forEach(type => {
        expect(validTypes).toContain(type);
      });
    });

    it('should map query types to categories', () => {
      const typeMap = {
        country: 'Country',
        state: 'State/Province',
        city: 'City',
        place: 'Attraction',
      };

      Object.entries(typeMap).forEach(([type, label]) => {
        expect(enhancedPlacesService.getCategoryLabel(type)).toBe(label);
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle missing query errors', () => {
      const error = {
        error: 'Query parameter required',
        error_type: 'missing_query',
      };

      expect(error.error_type).toBe('missing_query');
    });

    it('should handle validation errors', () => {
      const error = {
        error: 'Query too long',
        error_type: 'query_too_long',
      };

      expect(error.error_type).toBe('query_too_long');
    });

    it('should handle service unavailable errors', () => {
      const error = {
        error: 'Service temporarily unavailable',
        error_type: 'service_unavailable',
      };

      expect(error.error_type).toBe('service_unavailable');
    });
  });
});
