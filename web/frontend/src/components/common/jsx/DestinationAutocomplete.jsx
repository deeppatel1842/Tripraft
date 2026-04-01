import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Globe, Building, Landmark, Search } from 'lucide-react';
import GlobalConfig from '../../../config/globalConfig';
import '../css/DestinationAutocomplete.css';

/**
 * DestinationAutocomplete - Search and select destinations from travel database
 * Returns selected destination with coordinates for map centering
 *
 * @param {Object} props
 * @param {string} props.value - Current destination text value
 * @param {function} props.onChange - Callback when text changes (value)
 * @param {function} props.onSelect - Callback when destination selected ({name, type, coordinates, ...})
 * @param {string} props.placeholder - Input placeholder
 * @param {boolean} props.disabled - Disable input
 * @param {string} props.id - Input id
 * @param {string} props.name - Input name
 * @param {Array} props.allowedTypes - Filter results by type: ['country', 'state', 'city', 'place']
 * @param {string} props.className - Additional CSS class for wrapper
 * @param {string} props.variant - 'default' or 'tripPlanner' for different styling
 */
export default function DestinationAutocomplete({
  value = '',
  onChange,
  onSelect,
  placeholder = 'Search destinations...',
  disabled = false,
  id = 'destination',
  name = 'destination',
  allowedTypes = null,
  className = '',
  variant = 'default'
}) {
  const [inputValue, setInputValue] = useState(value);
  const [suggestions, setSuggestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);
  const debounceRef = useRef(null);
  const wrapperRef = useRef(null);

  // Check if this is trip planner variant (cities only)
  const isTripPlanner = variant === 'tripPlanner' || (allowedTypes && allowedTypes.length === 1 && allowedTypes[0] === 'city');

  // Sync with external value
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  // Fetch suggestions from API
  const fetchSuggestions = async (query) => {
    if (!query || query.length < 2) {
      setSuggestions([]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(
        `${GlobalConfig.API_BASE_URL}${GlobalConfig.ENDPOINTS.PLACE_SEARCH}/autocomplete?q=${encodeURIComponent(query)}&limit=15`,
        { credentials: 'include' }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch suggestions');
      }

      const data = await response.json();
      let results = data.data || [];

      // Filter by allowed types if specified
      if (allowedTypes && allowedTypes.length > 0) {
        results = results.filter(item => allowedTypes.includes(item.type));
      }

      // Ensure uniqueness by display_name to avoid duplicates
      const uniqueResults = [];
      const seen = new Set();
      for (const item of results) {
        const key = `${item.type}-${item.display_name}`;
        if (!seen.has(key)) {
          seen.add(key);
          uniqueResults.push(item);
        }
      }

      setSuggestions(uniqueResults);
    } catch (error) {
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Debounced search
  const handleInputChange = (e) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    setHighlightedIndex(-1);

    if (onChange) {
      onChange(newValue);
    }

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      fetchSuggestions(newValue);
      setShowSuggestions(true);
    }, 300);
  };

  // Handle suggestion selection
  const handleSelect = (suggestion) => {
    const displayValue = isTripPlanner ? suggestion.name : suggestion.display_name;
    setInputValue(displayValue);
    setShowSuggestions(false);
    setSuggestions([]);

    if (onChange) {
      onChange(displayValue);
    }

    if (onSelect) {
      onSelect(suggestion);
    }
  };

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev =>
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
          handleSelect(suggestions[highlightedIndex]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        break;
      default:
        break;
    }
  };

  // Close suggestions on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Get icon for destination type
  const getTypeIcon = (type) => {
    switch (type) {
      case 'country':
        return <Globe size={16} className="suggestion-icon country" />;
      case 'state':
        return <Building size={16} className="suggestion-icon state" />;
      case 'city':
        return <MapPin size={16} className="suggestion-icon city" />;
      case 'place':
        return <Landmark size={16} className="suggestion-icon place" />;
      default:
        return <MapPin size={16} className="suggestion-icon" />;
    }
  };

  // Get display name based on variant
  const getDisplayName = (suggestion) => {
    if (isTripPlanner) {
      return suggestion.country
        ? `${suggestion.name}, ${suggestion.country}`
        : suggestion.display_name;
    }
    return suggestion.display_name;
  };

  const containerClasses = `destination-autocomplete ${className} ${isTripPlanner ? 'trip-planner-variant' : ''}`;

  return (
    <div className={containerClasses} ref={wrapperRef}>
      <div className="autocomplete-input-wrapper">
        <Search size={18} className="input-icon" />
        <input
          ref={inputRef}
          type="text"
          id={id}
          name={name}
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => inputValue.length >= 2 && setShowSuggestions(true)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          className="autocomplete-input"
        />
        {isLoading && <span className="loading-indicator" />}
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <ul ref={suggestionsRef} className="suggestions-list">
          {suggestions.map((suggestion, index) => (
            <li
              key={`${suggestion.type}-${suggestion.id}`}
              className={`suggestion-item ${index === highlightedIndex ? 'highlighted' : ''}`}
              onClick={() => handleSelect(suggestion)}
              onMouseEnter={() => setHighlightedIndex(index)}
            >
              <div className="suggestion-content">
                {!isTripPlanner && getTypeIcon(suggestion.type)}
                <div className="suggestion-text">
                  <span className="suggestion-name">{getDisplayName(suggestion)}</span>
                  {!isTripPlanner && suggestion.type === 'country' && (
                    <span className="suggestion-badge country">COUNTRY</span>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {showSuggestions && inputValue.length >= 2 && suggestions.length === 0 && !isLoading && (
        <div className="no-suggestions">
          No destinations found matching "{inputValue}"
        </div>
      )}
    </div>
  );
}
