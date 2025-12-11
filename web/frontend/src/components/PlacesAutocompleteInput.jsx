/**
 * PlacesAutocompleteInput - Complete autocomplete component
 * 
 * Features:
 * - Real-time suggestions as you type
 * - 0 Firebase reads (all from JSON)
 * - <300ms response time
 * - Auto-dismisses on selection
 * - Keyboard navigation (arrow keys, enter)
 * 
 * Usage:
 * <PlacesAutocompleteInput 
 *   value={place}
 *   onChange={setPlace}
 *   onSelect={handleSelectPlace}
 * />
 */

import React, { useState, useRef, useEffect } from 'react';
import usePlacesAutocomplete from '../hooks/usePlacesAutocomplete';

const PlacesAutocompleteInput = ({ value, onChange, onSelect, placeholder = 'Search places...' }) => {
  const { query, setQuery, suggestions, showSuggestions, isLoading, selectSuggestion, clearSuggestions } =
    usePlacesAutocomplete();

  const [selectedIndex, setSelectedIndex] = useState(-1);
  const suggestionsRef = useRef(null);

  // Sync external value
  useEffect(() => {
    if (value !== query) {
      setQuery(value);
    }
  }, [value]);

  const handleInputChange = (e) => {
    const newValue = e.target.value;
    setQuery(newValue);
    onChange?.(newValue);
    setSelectedIndex(-1);
  };

  const handleSelectSuggestion = (suggestion) => {
    selectSuggestion(suggestion);
    onChange?.(suggestion.name);
    onSelect?.(suggestion);
    clearSuggestions();
  };

  const handleKeyDown = (e) => {
    if (!showSuggestions) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;

      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;

      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          handleSelectSuggestion(suggestions[selectedIndex]);
        }
        break;

      case 'Escape':
        e.preventDefault();
        clearSuggestions();
        setSelectedIndex(-1);
        break;

      default:
        break;
    }
  };

  return (
    <div className="relative w-full">
      <input
        type="text"
        value={query}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => query.length >= 2 && suggestions.length > 0}
        placeholder={placeholder}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
      />

      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute right-3 top-2.5">
          <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
        </div>
      )}

      {/* Suggestions dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto"
        >
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              onClick={() => handleSelectSuggestion(suggestion)}
              onMouseEnter={() => setSelectedIndex(index)}
              className={`w-full text-left px-4 py-2 flex justify-between items-center border-b last:border-b-0 transition ${
                selectedIndex === index
                  ? 'bg-blue-50 border-l-4 border-l-blue-500'
                  : 'hover:bg-gray-50'
              }`}
            >
              <div>
                <div className="font-medium text-gray-900">{suggestion.name}</div>
                <div className="text-xs text-gray-500">
                  {suggestion.type === 'place' &&
                    `📍 ${suggestion.city || suggestion.state}, ${suggestion.country}`}
                  {suggestion.type === 'city' &&
                    `🏙️ ${suggestion.state}, ${suggestion.country}`}
                  {suggestion.type === 'country' && `🌍 ${suggestion.code || ''}`}
                </div>
              </div>
              {suggestion.rank_score && (
                <span className="text-xs text-gray-400 ml-2">
                  ⭐{suggestion.rank_score.toFixed(1)}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Empty state */}
      {query.length >= 2 && !isLoading && showSuggestions === false && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-4 text-center text-gray-500 text-sm">
          No places found
        </div>
      )}

      {/* Info text */}
      {query && (
        <div className="text-xs text-gray-400 mt-1">
          ⚡ Instant suggestions • 0 Firebase reads
        </div>
      )}
    </div>
  );
};

export default PlacesAutocompleteInput;
