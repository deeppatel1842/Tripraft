/**
 * usePlacesAutocomplete - Fast autocomplete using JSON data
 * 
 * - 0 Firebase reads (all from backend JSON)
 * - <300ms response time
 * - Works with autocomplete as you type
 * - Auto-dismisses when user submits
 * 
 * Usage:
 * const { query, setQuery, suggestions, showSuggestions } = usePlacesAutocomplete();
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export const usePlacesAutocomplete = (minChars = 2) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch suggestions as user types
  useEffect(() => {
    if (query.length < minChars) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const fetchSuggestions = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(
          `${API_URL}/api/v2/places/autocomplete?q=${encodeURIComponent(query)}&limit=10`
        );

        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            setSuggestions(data.suggestions || []);
            setShowSuggestions(data.suggestions.length > 0);
          }
        }
      } catch (error) {
        console.error('Error fetching suggestions:', error);
        setSuggestions([]);
      } finally {
        setIsLoading(false);
      }
    };

    // Debounce API call - wait 200ms before fetching
    const timer = setTimeout(fetchSuggestions, 200);
    return () => clearTimeout(timer);
  }, [query]);

  const selectSuggestion = useCallback((suggestion) => {
    setQuery(suggestion.name);
    setShowSuggestions(false);
  }, []);

  const clearSuggestions = useCallback(() => {
    setShowSuggestions(false);
  }, []);

  return {
    query,
    setQuery,
    suggestions,
    showSuggestions,
    isLoading,
    selectSuggestion,
    clearSuggestions,
  };
};

export default usePlacesAutocomplete;
