/**
 * SearchSuggestions Component
 * 
 * Dropdown list of autocomplete suggestions.
 * Supports keyboard navigation and different item types.
 * Only shows COUNTRY tag, other types show simple name without tag.
 */

import React from 'react';
import '../css/SearchSuggestions.css';

const SearchSuggestions = ({
  suggestions,
  selectedIndex,
  onSelect,
}) => {
  /**
   * Get icon for suggestion type - only used for countries
   */
  const getTypeIcon = (type) => {
    switch (type) {
      case 'country':
        return 'fa-globe';
      default:
        return 'fa-map-marker-alt';
    }
  };

  return (
    <div className="search-suggestions" role="listbox">
      {suggestions.map((suggestion, index) => (
        <div
          key={`${suggestion.type}-${suggestion.id}`}
          className={`suggestion-item ${index === selectedIndex ? 'selected' : ''} ${suggestion.type === 'country' ? 'is-country' : ''}`}
          onClick={() => onSelect(suggestion)}
          role="option"
          aria-selected={index === selectedIndex}
        >
          <div className="suggestion-icon">
            <i className={`fas ${getTypeIcon(suggestion.type)}`}></i>
          </div>
          
          <div className="suggestion-content">
            <span className="suggestion-name">{suggestion.name}</span>
            {suggestion.parent && (
              <span className="suggestion-parent">{suggestion.parent}</span>
            )}
          </div>
          
          {/* Only show COUNTRY tag, no tags for city/state/place */}
          {suggestion.type === 'country' && (
            <span className="suggestion-type country-tag">
              COUNTRY
            </span>
          )}
        </div>
      ))}
    </div>
  );
};

export default SearchSuggestions;
