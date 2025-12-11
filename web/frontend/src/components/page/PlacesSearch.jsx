/**
 * PlacesSearch Component - Professional Implementation
 * 
 * Features:
 * - Real-time search with autocomplete for country/state/city/place
 * - Configuration-driven behavior (no hardcoding)
 * - Debounced search for performance (300ms)
 * - Complete 34-field place data handling
 * - Professional error handling and loading states
 * - Responsive design with keyboard navigation
 * - Full accessibility support
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import placesService, { API_CONFIG } from '../../services/placesServiceProfessional';
import { Search, MapPin, Globe, AlertCircle } from 'lucide-react';
import './PlacesSearch.css';

const PlacesSearch = ({ onResultSelect, placeholder = 'Search places, cities, or countries...' }) => {
  // ========================
  // STATE MANAGEMENT
  // ========================

  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [searchResult, setSearchResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);

  // Refs
  const debounceTimer = useRef(null);
  const searchInputRef = useRef(null);
  const suggestionsRef = useRef(null);

  // ========================
  // HANDLERS
  // ========================

  /**
   * Handle autocomplete search with debouncing
   * Uses configuration-driven API_CONFIG for all constants
   */
  const handleAutocomplete = useCallback(async (searchQuery) => {
    if (!searchQuery || searchQuery.trim().length < API_CONFIG.autocomplete.minQueryLength) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const result = await placesService.getAutocompleteSuggestions(
        searchQuery,
        API_CONFIG.autocomplete.maxSuggestions
      );

      if (result.success) {
        setSuggestions(result.suggestions || []);
        setShowSuggestions(result.suggestions?.length > 0);
      } else {
        setSuggestions([]);
      }
    } catch (err) {
      setError(err.message || 'Error fetching suggestions');
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Debounced search input handler
   * Uses API_CONFIG.autocomplete.debounceMs for debounce timing
   */
  const handleQueryChange = useCallback((e) => {
    const value = e.target.value;
    setQuery(value);
    setSelectedIndex(-1);
    setError(null);

    // Clear previous timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Set new debounced search using configuration
    debounceTimer.current = setTimeout(() => {
      handleAutocomplete(value);
    }, API_CONFIG.autocomplete.debounceMs);
  }, [handleAutocomplete]);

  /**
   * Handle suggestion click - search for selected location
   */
  const handleSuggestionClick = useCallback(async (suggestion) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    setSelectedIndex(-1);

    try {
      setIsLoading(true);
      setError(null);

      const result = await placesService.searchByLocation(suggestion);

      if (result && result.success) {
        setSearchResult(result);
        setPerformanceMetrics({
          firebaseReads: result.firebaseReads,
          responseTime: result.responseTime,
          cacheHit: result.cacheHit,
        });

        if (onResultSelect) {
          onResultSelect(result);
        }
      } else {
        setError('Location not found');
      }
    } catch (err) {
      setError(err.message || 'Error loading location');
      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [onResultSelect]);

  /**
   * Handle search form submission
   * Searches with complete 34-field place data support
   */
  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery || trimmedQuery.length < API_CONFIG.search.minQueryLength) {
      setError(`Please enter at least ${API_CONFIG.search.minQueryLength} characters`);
      return;
    }

    if (trimmedQuery.length > API_CONFIG.search.maxQueryLength) {
      setError(`Query must not exceed ${API_CONFIG.search.maxQueryLength} characters`);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      setShowSuggestions(false);

      const result = await placesService.searchByLocation(trimmedQuery);

      if (result && result.success) {
        setSearchResult(result);
        setPerformanceMetrics({
          firebaseReads: result.firebaseReads,
          responseTime: result.responseTime,
          cacheHit: result.cacheHit,
          placeCount: result.count,
        });

        if (onResultSelect) {
          onResultSelect(result);
        }
      } else {
        setError('Location not found. Try searching by country, state, or city name.');
      }
    } catch (err) {
      const errorMessage = err.message || 'Search failed. Please try again.';
      setError(errorMessage);
      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [query, onResultSelect]);

  /**
   * Keyboard navigation for suggestions
   * Supports arrow keys, enter, and escape
   */
  const handleKeyDown = useCallback((e) => {
    if (!showSuggestions || suggestions.length === 0) {
      if (e.key === 'Enter') {
        handleSubmit(e);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev =>
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => (prev > 0 ? prev - 1 : -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleSuggestionClick(suggestions[selectedIndex]);
        } else {
          handleSubmit(e);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedIndex(-1);
        break;
      default:
        break;
    }
  }, [showSuggestions, suggestions, selectedIndex, handleSuggestionClick, handleSubmit]);

  /**
   * Handle click outside to close suggestions
   */
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(e.target) &&
        !searchInputRef.current?.contains(e.target)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  /**
   * Cleanup debounce timer on unmount
   */
  useEffect(() => {
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, []);

  /**
   * Configuration-driven icon mapping for location types
   */
  const getTypeIcon = useCallback((type) => {
    const iconMap = {
      country: <Globe className="icon-small" />,
      state: <Globe className="icon-small" />,
      city: <MapPin className="icon-small" />,
      place: <MapPin className="icon-small" />,
    };
    return iconMap[type] || <MapPin className="icon-small" />;
  }, []);

  return (
    <div className="places-search-container">
      <form onSubmit={handleSubmit} className="search-form">
        {/* Search Input with Loading State */}
        <div className="search-input-wrapper">
          <Search className="search-icon" size={20} />
          <input
            ref={searchInputRef}
            type="text"
            value={query}
            onChange={handleQueryChange}
            onKeyDown={handleKeyDown}
            onFocus={() => query && suggestions.length > 0 && setShowSuggestions(true)}
            placeholder={placeholder}
            className="search-input"
            disabled={isLoading}
            aria-label="Search places, cities, or countries"
            autoComplete="off"
          />
          {isLoading && <div className="search-loader" />}
          <button
            type="submit"
            className="search-button"
            disabled={isLoading}
            aria-label="Search"
          >
            Search
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message" role="alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Suggestions Dropdown - Configuration-driven */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="suggestions-dropdown" ref={suggestionsRef} role="listbox">
            {suggestions.map((suggestion, index) => (
              <div
                key={`${suggestion}-${index}`}
                className={`suggestion-item ${index === selectedIndex ? 'selected' : ''}`}
                onClick={() => handleSuggestionClick(suggestion)}
                role="option"
                aria-selected={index === selectedIndex}
              >
                <div className="suggestion-icon">
                  {getTypeIcon('place')}
                </div>
                <div className="suggestion-content">
                  <div className="suggestion-name">{suggestion}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Performance Metrics Display */}
        {performanceMetrics && (
          <div className="performance-metrics">
            <span className="metric-item">
              <small>Firebase Reads: {performanceMetrics.firebaseReads}</small>
            </span>
            <span className="metric-item">
              <small>Response: {performanceMetrics.responseTime.toFixed(0)}ms</small>
            </span>
            {performanceMetrics.cacheHit && (
              <span className="metric-item cache-hit">
                <small>✓ Cached</small>
              </span>
            )}
          </div>
        )}

        {/* Search Result Preview - Shows matched location info */}
        {searchResult && searchResult.success && (
          <div className="search-result-preview">
            <div className="result-header">
              <h3>{searchResult.matched?.name || searchResult.query}</h3>
              <span className="result-type">{searchResult.matchType}</span>
            </div>
            <div className="result-stats">
              <span className="stat">{searchResult.count} places found</span>
              {searchResult.matched?.state_count && (
                <span className="stat">{searchResult.matched.state_count} states</span>
              )}
            </div>
          </div>
        )}
      </form>
    </div>
  );
};

export default PlacesSearch;
