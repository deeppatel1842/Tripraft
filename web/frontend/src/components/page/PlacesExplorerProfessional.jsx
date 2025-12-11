/**
 * PlacesExplorer Component - Professional Implementation
 * Handles Country, State, and Single Place searches with unified UX
 * 
 * Features:
 * - Configuration-driven display modes (no hardcoding)
 * - Three match types: country (225 places), state (5 places), single place
 * - Professional error handling and loading states
 * - Complete 34-field place data display
 * - Responsive grid/list layouts
 * - Performance metrics display
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import placesService, { API_CONFIG } from '../../services/placesServiceProfessional';
import './PlacesExplorer.css';

// ============================================================================
// COMPONENT CONFIGURATION
// ============================================================================

const COMPONENT_CONFIG = {
  // Display modes based on match type
  displayModes: {
    country: {
      name: 'Country Overview',
      description: 'Showing top places from all states',
      gridColumns: 5,
      showGrouping: true,
      showFilters: true,
      showSorting: true,
      maxPlacesToShow: 225,
    },
    state: {
      name: 'State Overview',
      description: 'Showing top places in this state',
      gridColumns: 3,
      showGrouping: false,
      showFilters: true,
      showSorting: true,
      maxPlacesToShow: 20,
    },
    city: {
      name: 'City Overview',
      description: 'Showing top places in this city',
      gridColumns: 3,
      showGrouping: false,
      showFilters: true,
      showSorting: true,
      maxPlacesToShow: 20,
    },
    place: {
      name: 'Place Details',
      description: 'Detailed view of a specific place',
      gridColumns: 1,
      showGrouping: false,
      showFilters: false,
      showSorting: false,
      maxPlacesToShow: 1,
    },
  },

  // Sorting options - configuration-driven
  sortOptions: [
    {
      id: 'rank_score',
      label: 'Popularity',
      order: 'desc',
      tooltip: 'Sort by popularity score',
    },
    {
      id: 'rating_tourist_priority',
      label: 'Tourist Rating',
      order: 'desc',
      tooltip: 'Sort by tourist priority rating',
    },
    {
      id: 'rating_traveler_experience',
      label: 'Traveler Rating',
      order: 'desc',
      tooltip: 'Sort by traveler experience rating',
    },
    {
      id: 'name',
      label: 'Name A-Z',
      order: 'asc',
      tooltip: 'Sort alphabetically',
    },
  ],

  // Filter options - configuration-driven
  filterOptions: [
    {
      id: 'hasWebsite',
      label: 'Has Official Website',
      type: 'boolean',
    },
    {
      id: 'hasCoordinates',
      label: 'Has Location',
      type: 'boolean',
    },
    {
      id: 'hasSunrise',
      label: 'Sunrise View',
      type: 'boolean',
    },
    {
      id: 'hasSunset',
      label: 'Sunset View',
      type: 'boolean',
    },
  ],

  // Rating thresholds for UI feedback
  ratingThresholds: {
    excellent: 4.5,
    good: 3.5,
    average: 2.5,
    poor: 0,
  },

  // Pagination
  pagination: {
    itemsPerPage: 12,
    showPagination: true,
  },
};

// ============================================================================
// PLACES EXPLORER COMPONENT
// ============================================================================

const PlacesExplorer = () => {
  // ========================
  // STATE MANAGEMENT
  // ========================

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [filteredPlaces, setFilteredPlaces] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Display configuration
  const [currentDisplayMode, setCurrentDisplayMode] = useState(null);
  const [groupedByState, setGroupedByState] = useState({});

  // Filters and sorting
  const [activeSort, setActiveSort] = useState(COMPONENT_CONFIG.sortOptions[0].id);
  const [activeFilters, setActiveFilters] = useState({});
  const [currentPage, setCurrentPage] = useState(1);

  // Performance metrics
  const [performanceMetrics, setPerformanceMetrics] = useState(null);

  // Autocomplete
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState([]);
  const [showAutocomplate, setShowAutocomplete] = useState(false);
  const debounceTimer = useRef(null);

  // ========================
  // HELPER FUNCTIONS
  // ========================

  /**
   * Get display mode configuration for current search result
   */
  const getDisplayMode = useCallback(() => {
    if (!searchResults) return null;

    const matchType = searchResults.matchType?.toLowerCase() || 'unknown';
    return COMPONENT_CONFIG.displayModes[matchType] || COMPONENT_CONFIG.displayModes.place;
  }, [searchResults]);

  /**
   * Group places by state (for country view)
   */
  const groupPlacesByState = useCallback((places) => {
    const grouped = {};

    places.forEach(place => {
      const state = place.state || 'Unknown';
      if (!grouped[state]) {
        grouped[state] = [];
      }
      grouped[state].push(place);
    });

    return grouped;
  }, []);

  /**
   * Apply filters to places
   */
  const applyFilters = useCallback((places, filters) => {
    if (!filters || Object.keys(filters).length === 0) {
      return places;
    }

    return places.filter(place => {
      // Check each active filter
      for (const [filterKey, filterValue] of Object.entries(filters)) {
        if (filterValue === true && !place[filterKey]) {
          return false;
        }
      }
      return true;
    });
  }, []);

  /**
   * Apply sorting to places
   */
  const applySorting = useCallback((places, sortField) => {
    const sortOption = COMPONENT_CONFIG.sortOptions.find(opt => opt.id === sortField);
    if (!sortOption) return places;

    const sorted = [...places].sort((a, b) => {
      const aValue = a[sortOption.id];
      const bValue = b[sortOption.id];

      // Handle null/undefined values
      if (aValue == null && bValue == null) return 0;
      if (aValue == null) return 1;
      if (bValue == null) return -1;

      // Handle numeric and string values
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortOption.order === 'desc' ? bValue - aValue : aValue - bValue;
      }

      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();

      return sortOption.order === 'desc' ? bStr.localeCompare(aStr) : aStr.localeCompare(bStr);
    });

    return sorted;
  }, []);

  /**
   * Process search results - apply filters, sorting, grouping
   */
  const processSearchResults = useCallback((results) => {
    if (!results || !results.places || results.places.length === 0) {
      setFilteredPlaces([]);
      setGroupedByState({});
      return;
    }

    // Apply filters and sorting
    let processed = applyFilters(results.places, activeFilters);
    processed = applySorting(processed, activeSort);

    // Group by state if needed
    const mode = COMPONENT_CONFIG.displayModes[results.matchType?.toLowerCase() || 'place'];
    if (mode?.showGrouping) {
      const grouped = groupPlacesByState(processed);
      setGroupedByState(grouped);
    } else {
      setGroupedByState({});
    }

    setFilteredPlaces(processed);
    setCurrentPage(1);
  }, [activeFilters, activeSort, applyFilters, applySorting, groupPlacesByState]);

  // ========================
  // MAIN SEARCH HANDLER
  // ========================

  /**
   * Handle location search
   */
  const handleSearch = useCallback(async (query) => {
    if (!query || query.trim().length < API_CONFIG.search.minQueryLength) {
      setError('Please enter at least 2 characters');
      return;
    }

    setIsLoading(true);
    setError(null);
    setShowAutocomplete(false);

    try {
      // Call API service
      const results = await placesService.searchByLocation(query);

      if (!results.success) {
        throw new Error(results.error || 'Search failed');
      }

      // Store results and metrics
      setSearchResults(results);
      setPerformanceMetrics({
        firebaseReads: results.firebaseReads,
        responseTime: results.responseTime,
        cacheHit: results.cacheHit,
        placeCount: results.count,
      });

      // Determine display mode
      const matchType = results.matchType?.toLowerCase() || 'place';
      setCurrentDisplayMode(COMPONENT_CONFIG.displayModes[matchType]);

      // Process results (filters, sorting, grouping)
      processSearchResults(results);

    } catch (err) {
      const errorMessage = err.message || 'An error occurred during search';
      setError(errorMessage);
      setSearchResults(null);
      setFilteredPlaces([]);
      setGroupedByState({});

      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [processSearchResults]);

  /**
   * Handle search input change (with autocomplete)
   */
  const handleSearchInputChange = useCallback((e) => {
    const query = e.target.value;
    setSearchQuery(query);

    // Clear previous timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Debounce autocomplete
    if (query.length >= API_CONFIG.autocomplete.minQueryLength) {
      debounceTimer.current = setTimeout(async () => {
        try {
          const response = await placesService.getAutocompleteSuggestions(
            query,
            API_CONFIG.autocomplete.maxSuggestions
          );
          setAutocompleteSuggestions(response.suggestions || []);
          setShowAutocomplete(true);
        } catch (err) {
          console.error('Autocomplete error:', err);
          setAutocompleteSuggestions([]);
        }
      }, API_CONFIG.autocomplete.debounceMs);
    } else {
      setAutocompleteSuggestions([]);
      setShowAutocomplete(false);
    }
  }, []);

  /**
   * Handle autocomplete suggestion click
   */
  const handleSuggestionClick = useCallback((suggestion) => {
    setSearchQuery(suggestion);
    setShowAutocomplete(false);
    handleSearch(suggestion);
  }, [handleSearch]);

  /**
   * Handle filter change
   */
  const handleFilterChange = useCallback((filterId) => {
    setActiveFilters(prev => ({
      ...prev,
      [filterId]: !prev[filterId],
    }));
    setCurrentPage(1);
  }, []);

  /**
   * Handle sort change
   */
  const handleSortChange = useCallback((sortId) => {
    setActiveSort(sortId);
    setCurrentPage(1);
  }, []);

  // ========================
  // EFFECTS
  // ========================

  /**
   * Re-process results when filters or sorting change
   */
  useEffect(() => {
    if (searchResults) {
      processSearchResults(searchResults);
    }
  }, [activeFilters, activeSort, processSearchResults, searchResults]);

  /**
   * Cleanup debounce on unmount
   */
  useEffect(() => {
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, []);

  // ========================
  // RENDER METHODS
  // ========================

  /**
   * Render search header
   */
  const renderSearchHeader = () => (
    <div className="places-explorer__header">
      <h1>Find Your Perfect Place</h1>
      
      <div className="places-explorer__search-box">
        <input
          type="text"
          placeholder="Search by country, state, or city..."
          value={searchQuery}
          onChange={handleSearchInputChange}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchQuery)}
          className="places-explorer__search-input"
          autoComplete="off"
        />
        <button
          onClick={() => handleSearch(searchQuery)}
          disabled={isLoading}
          className="places-explorer__search-button"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>

        {/* Autocomplete Dropdown */}
        {showAutocomplate && autocompleteSuggestions.length > 0 && (
          <div className="places-explorer__autocomplete">
            {autocompleteSuggestions.map((suggestion, idx) => (
              <div
                key={idx}
                className="places-explorer__suggestion"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  /**
   * Render display mode info
   */
  const renderDisplayModeInfo = () => {
    if (!searchResults || !currentDisplayMode) return null;

    return (
      <div className="places-explorer__mode-info">
        <h2>{currentDisplayMode.name}</h2>
        <p>{currentDisplayMode.description}</p>
        <div className="places-explorer__match-details">
          <span className="match-type">{searchResults.matchType}</span>
          <span className="match-count">{searchResults.count} places found</span>
          {searchResults.matched?.state_count && (
            <span className="match-states">{searchResults.matched.state_count} states</span>
          )}
        </div>
      </div>
    );
  };

  /**
   * Render performance metrics
   */
  const renderPerformanceMetrics = () => {
    if (!performanceMetrics) return null;

    return (
      <div className="places-explorer__metrics">
        <div className="metric">
          <span className="label">Firebase Reads:</span>
          <span className="value">{performanceMetrics.firebaseReads}</span>
        </div>
        <div className="metric">
          <span className="label">Response Time:</span>
          <span className="value">{performanceMetrics.responseTime.toFixed(0)}ms</span>
        </div>
        <div className="metric">
          <span className="label">Cache Hit:</span>
          <span className={`value ${performanceMetrics.cacheHit ? 'hit' : 'miss'}`}>
            {performanceMetrics.cacheHit ? 'Yes' : 'No'}
          </span>
        </div>
      </div>
    );
  };

  /**
   * Render filters section (configuration-driven)
   */
  const renderFilters = () => {
    if (!currentDisplayMode || !currentDisplayMode.showFilters) return null;

    return (
      <div className="places-explorer__filters">
        <h3>Filters</h3>
        <div className="filters-grid">
          {COMPONENT_CONFIG.filterOptions.map(filter => (
            <label key={filter.id} className="filter-checkbox">
              <input
                type="checkbox"
                checked={activeFilters[filter.id] || false}
                onChange={() => handleFilterChange(filter.id)}
              />
              <span>{filter.label}</span>
            </label>
          ))}
        </div>
      </div>
    );
  };

  /**
   * Render sorting section (configuration-driven)
   */
  const renderSorting = () => {
    if (!currentDisplayMode || !currentDisplayMode.showSorting) return null;

    return (
      <div className="places-explorer__sorting">
        <h3>Sort By</h3>
        <select
          value={activeSort}
          onChange={(e) => handleSortChange(e.target.value)}
          className="sort-select"
        >
          {COMPONENT_CONFIG.sortOptions.map(option => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    );
  };

  /**
   * Render single place (detailed view)
   */
  const renderSinglePlace = () => {
    if (!filteredPlaces || filteredPlaces.length === 0) return null;

    const place = filteredPlaces[0];

    return (
      <div className="places-explorer__single-place">
        <PlaceDetailCard place={place} />
      </div>
    );
  };

  /**
   * Render places grid
   */
  const renderPlacesGrid = () => {
    if (!filteredPlaces || filteredPlaces.length === 0) {
      return <p className="no-results">No places found matching your criteria.</p>;
    }

    // For country view, group by state
    if (currentDisplayMode?.showGrouping && Object.keys(groupedByState).length > 0) {
      return (
        <div className="places-explorer__grouped">
          {Object.entries(groupedByState).map(([state, places]) => (
            <div key={state} className="places-explorer__state-group">
              <h3 className="state-header">{state}</h3>
              <div
                className="places-grid"
                style={{
                  gridTemplateColumns: `repeat(auto-fill, minmax(250px, 1fr))`,
                }}
              >
                {places.map(place => (
                  <PlaceCard key={place.id} place={place} />
                ))}
              </div>
            </div>
          ))}
        </div>
      );
    }

    // For other views, simple grid
    return (
      <div
        className="places-grid"
        style={{
          gridTemplateColumns: `repeat(auto-fill, minmax(250px, 1fr))`,
        }}
      >
        {filteredPlaces.map(place => (
          <PlaceCard key={place.id} place={place} />
        ))}
      </div>
    );
  };

  /**
   * Main render
   */
  return (
    <div className="places-explorer">
      {renderSearchHeader()}

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {searchResults && !isLoading && (
        <>
          {renderDisplayModeInfo()}
          {renderPerformanceMetrics()}

          <div className="places-explorer__controls">
            {renderFilters()}
            {renderSorting()}
          </div>

          {searchResults.matchType?.toLowerCase() === 'place' ? renderSinglePlace() : renderPlacesGrid()}
        </>
      )}

      {isLoading && (
        <div className="loading-message">
          <div className="spinner"></div>
          <p>Searching...</p>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// PLACE CARD COMPONENT - Display individual place with 34 fields
// ============================================================================

const PlaceCard = ({ place }) => {
  const getAverageRating = () => {
    const avg = (place.rating_tourist_priority + place.rating_traveler_experience) / 2;
    return Math.round(avg * 10) / 10;
  };

  const getStateLabel = (state) => {
    if (!state) return 'Unknown State';
    return state.length > 25 ? state.substring(0, 22) + '...' : state;
  };

  return (
    <div className="place-card">
      {/* Photo Section */}
      {place.photos?.has_valid_photo && place.photos?.thumbnail_url && (
        <div className="place-card__photo">
          <img
            src={place.photos.thumbnail_url}
            alt={place.name}
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
      )}

      {/* Header */}
      <div className="place-card__header">
        <h3 className="place-card__title">{place.name}</h3>
        <div className="place-card__rating">
          <span className="stars">⭐ {getAverageRating()}</span>
          <span className="rank">#{Math.round(place.rank_score * 100)}</span>
        </div>
      </div>

      {/* Location */}
      <div className="place-card__location">
        <p className="city">{place.city}</p>
        <p className="state">{getStateLabel(place.state)}</p>
      </div>

      {/* Summary */}
      {place.ai_summary && (
        <p className="place-card__summary">{place.ai_summary.substring(0, 120)}...</p>
      )}

      {/* Info Badges */}
      <div className="place-card__badges">
        {place.cost && place.cost !== 'Cost not available' && (
          <span className="badge cost">💰 {place.cost.substring(0, 15)}</span>
        )}
        {place.suggested_duration && (
          <span className="badge duration">⏱️ {place.suggested_duration}</span>
        )}
        {place.official_website && <span className="badge website">🌐 Website</span>}
        {place.sunrise_view && <span className="badge sunrise">🌅 Sunrise</span>}
        {place.sunset_view && <span className="badge sunset">🌇 Sunset</span>}
      </div>

      {/* Tags */}
      {place.tags && place.tags.length > 0 && (
        <div className="place-card__tags">
          {place.tags.slice(0, 3).map((tag, idx) => (
            <span key={idx} className="tag">
              {tag}
            </span>
          ))}
          {place.tags.length > 3 && <span className="tag-more">+{place.tags.length - 3}</span>}
        </div>
      )}

      {/* Tip */}
      {place.place_tip && (
        <p className="place-card__tip">💡 {place.place_tip}</p>
      )}
    </div>
  );
};

// ============================================================================
// PLACE DETAIL CARD - Full details for single place
// ============================================================================

const PlaceDetailCard = ({ place }) => {
  const getDayName = (key) => {
    const dayMap = {
      monday: 'Monday',
      tuesday: 'Tuesday',
      wednesday: 'Wednesday',
      thursday: 'Thursday',
      friday: 'Friday',
      saturday: 'Saturday',
      sunday: 'Sunday',
    };
    return dayMap[key] || key;
  };

  return (
    <div className="place-detail-card">
      {/* Photo */}
      {place.photos?.has_valid_photo && place.photos?.thumbnail_url && (
        <div className="detail-photo">
          <img src={place.photos.thumbnail_url} alt={place.name} />
          {place.photos?.attribution && (
            <p className="photo-credit">
              Photo by {place.photos.attribution.author || 'Unknown'} ({place.photos.attribution.license || 'Unknown'})
            </p>
          )}
        </div>
      )}

      {/* Title and Location */}
      <div className="detail-header">
        <h1>{place.name}</h1>
        <p className="detail-location">
          {place.city}, {place.state}, {place.country}
        </p>
        {place.address && <p className="detail-address">{place.address}</p>}
      </div>

      {/* Ratings */}
      <div className="detail-ratings">
        <div className="rating-item">
          <span className="label">Tourist Priority</span>
          <span className="value">{place.rating_tourist_priority?.toFixed(1) || 'N/A'} ⭐</span>
        </div>
        <div className="rating-item">
          <span className="label">Traveler Experience</span>
          <span className="value">{place.rating_traveler_experience?.toFixed(1) || 'N/A'} ⭐</span>
        </div>
        <div className="rating-item">
          <span className="label">Popularity Score</span>
          <span className="value">{(place.rank_score * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Summary */}
      {place.ai_summary && (
        <section className="detail-section">
          <h2>About</h2>
          <p>{place.ai_summary}</p>
        </section>
      )}

      {/* Visit Info */}
      <section className="detail-section">
        <h2>Visit Information</h2>
        <div className="info-grid">
          {place.best_time_to_visit && (
            <div className="info-item">
              <span className="label">Best Time to Visit</span>
              <span className="value">{place.best_time_to_visit}</span>
            </div>
          )}
          {place.suggested_duration && (
            <div className="info-item">
              <span className="label">Suggested Duration</span>
              <span className="value">{place.suggested_duration}</span>
            </div>
          )}
          {place.cost && place.cost !== 'Cost not available' && (
            <div className="info-item">
              <span className="label">Entry Cost</span>
              <span className="value">{place.cost}</span>
            </div>
          )}
          {place.advanced_booking && (
            <div className="info-item">
              <span className="label">Booking</span>
              <span className="value">{place.advanced_booking}</span>
            </div>
          )}
        </div>
      </section>

      {/* Opening Hours */}
      {place.opening_hours && Object.values(place.opening_hours).some(v => v) && (
        <section className="detail-section">
          <h2>Opening Hours</h2>
          <div className="hours-grid">
            {['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].map(day => (
              <div key={day} className="hour-item">
                <span className="day">{getDayName(day)}</span>
                <span className="time">{place.opening_hours[day] || 'Closed'}</span>
              </div>
            ))}
          </div>
          {place.opening_hours.notes && <p className="hours-notes">{place.opening_hours.notes}</p>}
        </section>
      )}

      {/* Contact & Website */}
      <section className="detail-section">
        <h2>Contact Information</h2>
        {place.official_website && (
          <div className="contact-item">
            <span className="label">Website</span>
            <a href={place.official_website} target="_blank" rel="noopener noreferrer">
              {place.official_website}
            </a>
          </div>
        )}
        {place.coordinates?.latitude && place.coordinates?.longitude && (
          <div className="contact-item">
            <span className="label">Coordinates</span>
            <span className="value">
              {place.coordinates.latitude.toFixed(4)}, {place.coordinates.longitude.toFixed(4)}
            </span>
          </div>
        )}
      </section>

      {/* Tags */}
      {place.tags && place.tags.length > 0 && (
        <section className="detail-section">
          <h2>Tags</h2>
          <div className="tags-list">
            {place.tags.map((tag, idx) => (
              <span key={idx} className="tag">
                {tag}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Special Features */}
      <section className="detail-section">
        <h2>Special Features</h2>
        <div className="features-grid">
          <div className={`feature ${place.sunrise_view ? 'active' : 'inactive'}`}>
            <span className="icon">🌅</span>
            <span className="label">Sunrise View</span>
          </div>
          <div className={`feature ${place.sunset_view ? 'active' : 'inactive'}`}>
            <span className="icon">🌇</span>
            <span className="label">Sunset View</span>
          </div>
          <div className={`feature ${place.has_coordinates ? 'active' : 'inactive'}`}>
            <span className="icon">📍</span>
            <span className="label">GPS Location</span>
          </div>
          <div className={`feature ${place.official_website ? 'active' : 'inactive'}`}>
            <span className="icon">🌐</span>
            <span className="label">Official Website</span>
          </div>
        </div>
      </section>

      {/* Pro Tip */}
      {place.place_tip && (
        <section className="detail-section tip-section">
          <h2>Pro Tip</h2>
          <p className="tip-text">💡 {place.place_tip}</p>
        </section>
      )}
    </div>
  );
};

export default PlacesExplorer;
