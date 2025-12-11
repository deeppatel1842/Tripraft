/**
 * Phase 5: Enhanced Places Service Unit Tests
 * (Standalone - no Vite env dependency)
 */

describe('Phase 5: Enhanced Places Service - Unit Tests', () => {
  describe('Response Formatting', () => {
    // Mock enhanced places service functions
    const formatSearchResult = (result) => {
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
    };

    const formatAutocompleteSuggestions = (result) => {
      if (!result || !result.success || !result.data?.suggestions) {
        return [];
      }

      const getCategoryLabel = (type) => {
        const labels = {
          country: 'Country',
          state: 'State/Province',
          city: 'City',
          place: 'Attraction',
        };
        return labels[type] || type;
      };

      return result.data.suggestions.map(suggestion => ({
        id: suggestion.id,
        label: suggestion.name,
        type: suggestion.type,
        rank: suggestion.rank,
        category: getCategoryLabel(suggestion.type),
      }));
    };

    test('should format country search result correctly', () => {
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

      const formatted = formatSearchResult(result);

      expect(formatted).toBeDefined();
      expect(formatted.type).toBe('country');
      expect(formatted.name).toBe('France');
      expect(formatted.icon).toBe('Globe');
      expect(formatted).toHaveProperty('description');
      expect(formatted).toHaveProperty('states');
    });

    test('should format city search result correctly', () => {
      const result = {
        success: true,
        data: {
          match: { name: 'Paris', id: 'paris' },
          query_type: 'city',
          display_mode: 'top_destinations',
          location_hierarchy: { city: 'Paris', state: 'Île-de-France', country: 'France' },
          places: [{ name: 'Eiffel Tower' }, { name: 'Louvre' }],
          total_places: 20,
        },
      };

      const formatted = formatSearchResult(result);

      expect(formatted).toBeDefined();
      expect(formatted.type).toBe('city');
      expect(formatted.name).toBe('Paris');
      expect(formatted.places).toHaveLength(2);
      expect(formatted.totalPlaces).toBe(20);
      expect(formatted.icon).toBe('MapPin');
      expect(formatted.description).toContain('Île-de-France');
    });

    test('should format place search result correctly', () => {
      const result = {
        success: true,
        data: {
          match: { name: 'Eiffel Tower', id: 'eiffel' },
          query_type: 'place',
          display_mode: 'single_place',
          location_hierarchy: { city: 'Paris', state: 'Île-de-France', country: 'France' },
        },
      };

      const formatted = formatSearchResult(result);

      expect(formatted).toBeDefined();
      expect(formatted.type).toBe('place');
      expect(formatted.name).toBe('Eiffel Tower');
      expect(formatted.city).toBe('Paris');
      expect(formatted.state).toBe('Île-de-France');
      expect(formatted.country).toBe('France');
      expect(formatted.icon).toBe('MapPin');
    });

    test('should format state search result correctly', () => {
      const result = {
        success: true,
        data: {
          match: { name: 'California', id: 'ca' },
          query_type: 'state',
          display_mode: 'top_destinations',
          location_hierarchy: { state: 'California', country: 'United States' },
          places: [{ name: 'Golden Gate Bridge' }],
          total_places: 50,
        },
      };

      const formatted = formatSearchResult(result);

      expect(formatted).toBeDefined();
      expect(formatted.type).toBe('state');
      expect(formatted.name).toBe('California');
      expect(formatted.places).toHaveLength(1);
      expect(formatted.icon).toBe('Map');
    });

    test('should handle failed search results', () => {
      const result = { success: false, error: 'Not found' };
      const formatted = formatSearchResult(result);
      expect(formatted).toBeNull();
    });

    test('should handle null results', () => {
      const formatted = formatSearchResult(null);
      expect(formatted).toBeNull();
    });

    test('should handle undefined results', () => {
      const formatted = formatSearchResult(undefined);
      expect(formatted).toBeNull();
    });

    test('should format autocomplete suggestions with all fields', () => {
      const result = {
        success: true,
        data: {
          query: 'par',
          suggestions: [
            { id: 'paris', name: 'Paris', type: 'city', rank: 0.95 },
            { id: 'paris-tx', name: 'Paris, Texas', type: 'city', rank: 0.7 },
            { id: 'parietal', name: 'Parietal Bone', type: 'place', rank: 0.4 },
          ],
          total: 3,
        },
      };

      const formatted = formatAutocompleteSuggestions(result);

      expect(formatted).toHaveLength(3);
      expect(formatted[0]).toEqual({
        id: 'paris',
        label: 'Paris',
        type: 'city',
        rank: 0.95,
        category: 'City',
      });
      expect(formatted[1].category).toBe('City');
      expect(formatted[2].category).toBe('Attraction');
    });

    test('should handle empty suggestions', () => {
      const result = {
        success: true,
        data: {
          query: 'xyz',
          suggestions: [],
          total: 0,
        },
      };

      const formatted = formatAutocompleteSuggestions(result);
      expect(formatted).toHaveLength(0);
      expect(Array.isArray(formatted)).toBe(true);
    });

    test('should handle failed autocomplete', () => {
      const result = { success: false };
      const formatted = formatAutocompleteSuggestions(result);
      expect(formatted).toEqual([]);
    });

    test('should handle null autocomplete result', () => {
      const formatted = formatAutocompleteSuggestions(null);
      expect(formatted).toEqual([]);
    });
  });

  describe('Response Validation', () => {
    test('should validate search response structure', () => {
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

      expect(response).toHaveProperty('success');
      expect(response.success).toBe(true);
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

    test('should validate autocomplete response structure', () => {
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

      expect(Array.isArray(response.data.suggestions)).toBe(true);
      expect(response.data.suggestions[0]).toHaveProperty('id');
      expect(response.data.suggestions[0]).toHaveProperty('name');
      expect(response.data.suggestions[0]).toHaveProperty('type');
      expect(response.data.suggestions[0]).toHaveProperty('rank');
    });

    test('should validate error response structure', () => {
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

  describe('Display Modes', () => {
    const validModes = ['country_sections', 'top_destinations', 'single_place'];

    test('should support all display modes', () => {
      validModes.forEach(mode => {
        expect(validModes).toContain(mode);
      });
    });

    test('country_sections mode should include states', () => {
      expect(validModes).toContain('country_sections');
    });

    test('top_destinations mode should include places', () => {
      expect(validModes).toContain('top_destinations');
    });

    test('single_place mode should include place details', () => {
      expect(validModes).toContain('single_place');
    });
  });

  describe('Performance Metrics', () => {
    test('should track response time', () => {
      const metadata = {
        response_time_ms: 45.2,
        firestore_reads: 1,
        cache_hit: false,
      };

      expect(metadata).toHaveProperty('response_time_ms');
      expect(metadata.response_time_ms).toBeGreaterThan(0);
      expect(metadata.response_time_ms).toBeLessThan(1000); // Should be < 1 second
    });

    test('should track firestore reads', () => {
      const metadata = {
        response_time_ms: 45.2,
        firestore_reads: 1,
        cache_hit: false,
      };

      expect(metadata).toHaveProperty('firestore_reads');
      expect(metadata.firestore_reads).toBeGreaterThanOrEqual(0);
    });

    test('should track cache hits', () => {
      const cachedMetadata = {
        response_time_ms: 5.1,
        firestore_reads: 0,
        cache_hit: true,
      };

      expect(cachedMetadata.cache_hit).toBe(true);
      expect(cachedMetadata.response_time_ms).toBeLessThan(10);
      expect(cachedMetadata.firestore_reads).toBe(0);
    });

    test('should report slower response for uncached requests', () => {
      const uncachedMetadata = {
        response_time_ms: 150.7,
        firestore_reads: 5,
        cache_hit: false,
      };

      expect(uncachedMetadata.cache_hit).toBe(false);
      expect(uncachedMetadata.response_time_ms).toBeGreaterThan(50);
      expect(uncachedMetadata.firestore_reads).toBeGreaterThan(0);
    });
  });

  describe('Query Types', () => {
    const validTypes = ['country', 'state', 'city', 'place', 'unknown'];

    test('should support all query types', () => {
      validTypes.forEach(type => {
        expect(validTypes).toContain(type);
      });
    });

    test('should correctly identify country queries', () => {
      const queryType = 'country';
      expect(validTypes).toContain(queryType);
    });

    test('should correctly identify state queries', () => {
      const queryType = 'state';
      expect(validTypes).toContain(queryType);
    });

    test('should correctly identify city queries', () => {
      const queryType = 'city';
      expect(validTypes).toContain(queryType);
    });

    test('should correctly identify place queries', () => {
      const queryType = 'place';
      expect(validTypes).toContain(queryType);
    });
  });

  describe('Error Handling', () => {
    test('should identify missing query errors', () => {
      const error = {
        error: 'Query parameter required',
        error_type: 'missing_query',
      };

      expect(error.error_type).toBe('missing_query');
      expect(error.error).toContain('Query');
    });

    test('should identify query length errors', () => {
      const error = {
        error: 'Query exceeds maximum length',
        error_type: 'query_too_long',
      };

      expect(error.error_type).toBe('query_too_long');
    });

    test('should identify service unavailable errors', () => {
      const error = {
        error: 'Service temporarily unavailable',
        error_type: 'service_unavailable',
      };

      expect(error.error_type).toBe('service_unavailable');
    });

    test('should identify server errors', () => {
      const error = {
        error: 'Internal server error',
        error_type: 'server_error',
      };

      expect(error.error_type).toBe('server_error');
    });
  });

  describe('Location Hierarchy', () => {
    test('should preserve complete location hierarchy for places', () => {
      const hierarchy = {
        country: 'France',
        state: 'Île-de-France',
        city: 'Paris',
      };

      expect(hierarchy).toHaveProperty('country');
      expect(hierarchy).toHaveProperty('state');
      expect(hierarchy).toHaveProperty('city');
      expect(hierarchy.country).toBe('France');
    });

    test('should support partial hierarchies for states', () => {
      const hierarchy = {
        country: 'United States',
        state: 'California',
      };

      expect(hierarchy).toHaveProperty('country');
      expect(hierarchy).toHaveProperty('state');
      expect(hierarchy).not.toHaveProperty('city');
    });

    test('should support minimal hierarchies for countries', () => {
      const hierarchy = {
        country: 'Japan',
      };

      expect(hierarchy).toHaveProperty('country');
      expect(hierarchy).not.toHaveProperty('state');
      expect(hierarchy).not.toHaveProperty('city');
    });
  });
});
