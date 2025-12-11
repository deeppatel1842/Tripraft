/**
 * useClientSideSearch - Load places data once, search zero times
 * 
 * Benefits:
 * - 1 Firebase read on app startup
 * - 0 Firebase reads for all subsequent searches
 * - <50ms response time for any search
 * - Works offline with cached data
 * - Instant autocomplete
 * 
 * Usage:
 * const { search, isLoading, error } = useClientSideSearch();
 * const results = search('taj mahal');
 */

import { useEffect, useState, useCallback } from 'react';

const CACHE_KEY = 'places_autocomplete_data';
const CACHE_EXPIRY_KEY = 'places_autocomplete_expiry';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

export const useClientSideSearch = () => {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load data on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        // Check if data is cached and still valid
        const cachedData = localStorage.getItem(CACHE_KEY);
        const cachedExpiry = localStorage.getItem(CACHE_EXPIRY_KEY);

        if (
          cachedData &&
          cachedExpiry &&
          new Date().getTime() < parseInt(cachedExpiry)
        ) {
          // Use cached data
          console.log('📦 Using cached places data');
          setData(JSON.parse(cachedData));
          setIsLoading(false);
          return;
        }

        // Fetch from server (1 Firebase read)
        console.log('📥 Fetching places data from server...');
        const response = await fetch(
          `${process.env.REACT_APP_API_URL || 'http://localhost:5000'}/api/v2/places/data/all`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const json = await response.json();
        if (!json.success) {
          throw new Error(json.message || 'Failed to load data');
        }

        const placesData = json.data;

        // Cache the data
        localStorage.setItem(CACHE_KEY, JSON.stringify(placesData));
        localStorage.setItem(
          CACHE_EXPIRY_KEY,
          (new Date().getTime() + CACHE_DURATION).toString()
        );

        console.log(`✅ Loaded and cached: ${placesData.countries.length} countries, ${placesData.cities.length} cities, ${placesData.places.length} places`);
        setData(placesData);
      } catch (err) {
        console.error('❌ Error loading places data:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // Search function (0 Firebase reads)
  const search = useCallback(
    (query, options = {}) => {
      if (!data) return [];

      const {
        limit = 10,
        type = 'all', // 'all', 'places', 'cities', 'countries'
        fuzzy = true, // fuzzy matching vs exact prefix
      } = options;

      const q = query.toLowerCase().trim();
      if (!q) return [];

      const results = [];

      // Helper function to add results with deduplication
      const addResult = (item, category) => {
        const key = `${category}_${item.id}`;
        if (!results.find((r) => r._key === key)) {
          results.push({
            ...item,
            _key: key,
            _category: category,
            _match_score: calculateMatchScore(item, q, fuzzy),
          });
        }
      };

      // Search places
      if (type === 'all' || type === 'places') {
        data.places
          .filter(
            (p) =>
              p.name_lower.includes(q) ||
              (fuzzy && fuzzyMatch(p.name_lower, q))
          )
          .forEach((p) => addResult(p, 'place'));
      }

      // Search cities
      if (type === 'all' || type === 'cities') {
        data.cities
          .filter(
            (c) =>
              c.name_lower.includes(q) ||
              (fuzzy && fuzzyMatch(c.name_lower, q))
          )
          .forEach((c) => addResult(c, 'city'));
      }

      // Search countries
      if (type === 'all' || type === 'countries') {
        data.countries
          .filter(
            (c) =>
              c.name_lower.includes(q) ||
              (fuzzy && fuzzyMatch(c.name_lower, q))
          )
          .forEach((c) => addResult(c, 'country'));
      }

      // Sort by match score and limit
      return results
        .sort((a, b) => b._match_score - a._match_score)
        .slice(0, limit);
    },
    [data]
  );

  // Autocomplete function (0 Firebase reads, instant)
  const autocomplete = useCallback(
    (prefix, limit = 10) => {
      if (!data || !prefix) return [];

      const p = prefix.toLowerCase().trim();

      // Check if it's a multi-word query (likely a place)
      const isMultiWord = p.split(' ').length > 1;

      let results = [];

      if (isMultiWord) {
        // Multi-word: search places primarily
        results = search(p, { limit, type: 'places' });
        if (results.length < limit) {
          results.push(
            ...search(p, { limit: limit - results.length, type: 'cities' })
          );
        }
      } else {
        // Single word: search all, prioritize by category
        const places = search(p, { limit, type: 'places', fuzzy: false });
        const cities = search(p, { limit, type: 'cities', fuzzy: false });
        const countries = search(p, {
          limit,
          type: 'countries',
          fuzzy: false,
        });

        // Combine with priority: exact matches first
        results = [
          ...places.filter((r) => r.name_lower.startsWith(p)),
          ...cities.filter((r) => r.name_lower.startsWith(p)),
          ...countries.filter((r) => r.name_lower.startsWith(p)),
          ...places.filter((r) => !r.name_lower.startsWith(p)),
          ...cities.filter((r) => !r.name_lower.startsWith(p)),
          ...countries.filter((r) => !r.name_lower.startsWith(p)),
        ].slice(0, limit);
      }

      return results;
    },
    [data, search]
  );

  return {
    search,
    autocomplete,
    isLoading,
    error,
    data,
  };
};

// Helper functions
function calculateMatchScore(item, query, fuzzy) {
  const name = item.name_lower;

  // Exact prefix match: highest score
  if (name.startsWith(query)) return 100;

  // Contains match: medium score
  if (name.includes(query)) return 50;

  // Fuzzy match: low score
  if (fuzzy && fuzzyMatch(name, query)) return 25;

  return 0;
}

function fuzzyMatch(str, query) {
  let queryIdx = 0;
  for (let i = 0; i < str.length && queryIdx < query.length; i++) {
    if (str[i] === query[queryIdx]) queryIdx++;
  }
  return queryIdx === query.length;
}

export default useClientSideSearch;
