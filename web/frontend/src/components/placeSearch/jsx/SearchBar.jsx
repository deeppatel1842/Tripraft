/**
 * SearchBar Component
 * 
 * Search input with autocomplete suggestions.
 * Connected to backend API for real suggestions.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import SearchSuggestions from './SearchSuggestions';
import { getAutocompleteSuggestions } from '../../../services/placeSearchService';
import { MOCK_SUGGESTIONS } from '../mockData';
import '../css/SearchBar.css';

const SearchBar = ({
  value = '',
  onChange,
  onSearch,
  onSuggestionSelect,
  placeholder = 'Search places...',
  isLoading = false,
  minQueryLength = 2,
  debounceMs = 300,
}) => {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [isFocused, setIsFocused] = useState(false);

  const inputRef = useRef(null);
  const containerRef = useRef(null);
  const debounceTimer = useRef(null);
  const abortControllerRef = useRef(null);

  /**
   * Generate suggestions from API or mock data.
   * Cancels any in-flight request before starting a new one.
   */
  const generateSuggestions = useCallback(async (query) => {
    // Cancel previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    if (!query || query.length < minQueryLength) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      // Try backend API first
      const apiSuggestions = await getAutocompleteSuggestions(query, 10, { signal: controller.signal });
      
      if (apiSuggestions && apiSuggestions.length > 0) {
        setSuggestions(apiSuggestions);
        setShowSuggestions(true);
        return;
      }
    } catch (error) {
      // If aborted, don't update state — a newer request supersedes this one
      if (error.name === 'AbortError') return;
    }

    // Fallback to mock suggestions
    const lowerQuery = query.toLowerCase();
    const filtered = MOCK_SUGGESTIONS.filter(item =>
      item.name.toLowerCase().includes(lowerQuery) ||
      (item.parent && item.parent.toLowerCase().includes(lowerQuery))
    ).slice(0, 8);

    setSuggestions(filtered);
    setShowSuggestions(filtered.length > 0);
  }, [minQueryLength]);

  /**
   * Handle input change with debounce
   */
  const handleInputChange = useCallback((e) => {
    const newValue = e.target.value;
    onChange(newValue);
    setSelectedIndex(-1);

    // Clear previous timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Debounce suggestion generation
    debounceTimer.current = setTimeout(() => {
      generateSuggestions(newValue);
    }, debounceMs);
  }, [onChange, debounceMs, generateSuggestions]);

  /**
   * Handle form submission
   */
  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    if (value.trim().length >= minQueryLength) {
      setShowSuggestions(false);
      onSearch(value);
    }
  }, [value, minQueryLength, onSearch]);

  /**
   * Handle keyboard navigation
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
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
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
  }, [showSuggestions, suggestions, selectedIndex, handleSubmit]);

  /**
   * Handle suggestion click
   */
  const handleSuggestionClick = useCallback((suggestion) => {
    onChange(suggestion.name);
    setShowSuggestions(false);
    setSelectedIndex(-1);
    onSuggestionSelect(suggestion);
  }, [onChange, onSuggestionSelect]);

  /**
   * Handle click outside to close suggestions
   */
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
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
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return (
    <div className="search-bar" ref={containerRef}>
      <form onSubmit={handleSubmit} className="search-bar-form">
        <div className={`search-bar-input-wrapper ${isFocused ? 'focused' : ''}`}>
          <i className="fas fa-search search-bar-icon"></i>
          
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              setIsFocused(true);
              if (suggestions.length > 0) setShowSuggestions(true);
            }}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            className="search-bar-input"
            autoComplete="off"
            aria-label="Search places"
            aria-autocomplete="list"
            aria-expanded={showSuggestions}
          />

          {isLoading && (
            <div className="search-bar-loader" aria-label="Loading">
              <span className="loader-spinner"></span>
            </div>
          )}

          {value && !isLoading && (
            <button
              type="button"
              className="search-bar-clear"
              onClick={() => {
                onChange('');
                setSuggestions([]);
                setShowSuggestions(false);
                inputRef.current?.focus();
              }}
              aria-label="Clear search"
            >
              <i className="fas fa-times"></i>
            </button>
          )}

          <button
            type="submit"
            className="search-bar-submit"
            disabled={isLoading || value.length < minQueryLength}
            aria-label="Submit search"
          >
            Search
          </button>
        </div>

        {showSuggestions && suggestions.length > 0 && (
          <SearchSuggestions
            suggestions={suggestions}
            selectedIndex={selectedIndex}
            onSelect={handleSuggestionClick}
          />
        )}
      </form>
    </div>
  );
};

export default SearchBar;
