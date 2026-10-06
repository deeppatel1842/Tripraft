// Purpose: Coordinates real place search, statistics and loading/error/empty states.
/**
 * PlaceSearchPage - Main Search Page Component
 * 
 * Features:
 * - Search bar with autocomplete suggestions
 * - Filter and sort options
 * - Responsive grid layout for results
 * - Place detail modal
 * - Professional styling
 * 
 * Connected to backend API for real search results.
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import Header from '../../../components/layout/jsx/Header';
import Footer from '../../../components/layout/jsx/Footer';
import SearchBar from './SearchBar';
import PlaceGrid from './PlaceGrid';
import GroupedPlaceGrid from './GroupedPlaceGrid';
import PlaceDetailModal from './PlaceDetailModal';
import { searchPlaces, getStats } from '../../../services/placeSearchService';

import '../css/PlaceSearchPage.css';

const PlaceSearchPage = () => {
  const navigate = useNavigate();
  const { currentUser, signOut } = useAuth();

  // Stats state
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [matchType, setMatchType] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  // Filter state
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [selectedState, setSelectedState] = useState(null);
  const [selectedCity, setSelectedCity] = useState(null);
  const [sortBy, setSortBy] = useState('rank_score');
  const [sortOrder, setSortOrder] = useState('desc');

  // Modal state
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [filters, setFilters] = useState({
    costRange: [],
    features: [],
  });

  // Load stats on mount
  useEffect(() => {
    let cancelled = false;
    getStats().then(data => { if (!cancelled) setStats(data); }).catch(() => { if (!cancelled) setStats(null); });
    return () => { cancelled = true; };
  }, []);

  /**
   * Handle search query change
   */
  const handleSearchChange = useCallback((query) => {
    setSearchQuery(query);
  }, []);

  /**
   * Execute search with current query
   * Shows real backend results or an error
   */
  const handleSearch = useCallback(async (query) => {
    if (!query || query.trim().length < 2) {
      return;
    }

    setIsSearching(true);
    setHasSearched(true);

    try {
      // Try backend API first
      const result = await searchPlaces(query, {
        limit: 50,
        sortBy,
        sortOrder,
        costFilter: filters.costRange,
      });

      if (result.success === false) throw new Error(result.error?.message || result.message || 'Search failed');
      setSearchResults(result.places || []);
      setMatchType(result.match_type || '');
      setError('');
    } catch (error) {
      setSearchResults([]);
      setMatchType('');
      setError(error.message || 'Unable to search places. Please try again.');
    } finally {
      setIsSearching(false);
    }
  }, [sortBy, sortOrder, filters]);

  /**
   * Handle suggestion selection from autocomplete
   */
  const handleSuggestionSelect = useCallback((suggestion) => {
    setSearchQuery(suggestion.name);
    handleSearch(suggestion.name);

    // Set location filters based on suggestion type
    if (suggestion.type === 'country') {
      setSelectedCountry(suggestion);
      setSelectedState(null);
      setSelectedCity(null);
    } else if (suggestion.type === 'state') {
      setSelectedState(suggestion);
      setSelectedCity(null);
    } else if (suggestion.type === 'city') {
      setSelectedCity(suggestion);
    }
  }, [handleSearch]);

  /**
   * Handle place card click
   */
  const handlePlaceClick = useCallback((place) => {
    setSelectedPlace(place);
    setIsModalOpen(true);
  }, []);

  /**
   * Close place detail modal
   */
  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setSelectedPlace(null);
  }, []);

  /**
   * Handle sort change
   */
  const handleSortChange = useCallback((newSortBy, newSortOrder) => {
    setSortBy(newSortBy);
    setSortOrder(newSortOrder);
  }, []);

  /**
   * Handle filter changes
   */
  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
  }, []);

  /**
   * Clear all filters
   */
  const handleClearFilters = useCallback(() => {
    setFilters({
      costRange: [],
      features: [],
    });
    setSelectedCountry(null);
    setSelectedState(null);
    setSelectedCity(null);
  }, []);

  /**
   * Apply sorting and filtering to results
   */
  const sortedAndFilteredResults = useMemo(() => {
    let results = [...searchResults];

    // Apply location filters
    if (selectedCountry) {
      results = results.filter(p => p.country_name === selectedCountry.name);
    }
    if (selectedState) {
      results = results.filter(p => p.state_name === selectedState.name);
    }
    if (selectedCity) {
      results = results.filter(p => p.city_name === selectedCity.name);
    }

    // Apply cost filter (normalize: null/empty => paid, 'Free' => free)
    if (filters.costRange.length > 0) {
      results = results.filter(p => {
        const isFree = (p.cost || '').toLowerCase() === 'free';
        if (filters.costRange.includes('free') && isFree) return true;
        if (filters.costRange.includes('paid') && !isFree) return true;
        return false;
      });
    }

    // Apply feature filters
    if (filters.features.length > 0) {
      results = results.filter(p => 
        filters.features.every(feature => {
          if (feature === 'sunrise') return p.sunrise_view;
          if (feature === 'sunset') return p.sunset_view;
          if (feature === 'booking') return p.advanced_booking === 'recommended';
          return true;
        })
      );
    }

    // Apply sorting
    results.sort((a, b) => {
      let aVal, bVal;

      switch (sortBy) {
        case 'rank_score':
          aVal = a.rank_score || 0;
          bVal = b.rank_score || 0;
          break;
        case 'name':
          aVal = a.name.toLowerCase();
          bVal = b.name.toLowerCase();
          break;
        case 'rating':
          aVal = a.rating_tourist_priority || 0;
          bVal = b.rating_tourist_priority || 0;
          break;
        default:
          aVal = a.rank_score || 0;
          bVal = b.rank_score || 0;
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      }
      return aVal < bVal ? 1 : -1;
    });

    return results;
  }, [searchResults, selectedCountry, selectedState, selectedCity, filters, sortBy, sortOrder]);

  return (
    <div className="ps-page">
      <Header 
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={signOut}
      />
      
      <main className="ps-main">
        {/* Hero Section with Search */}
        <section className="ps-hero">
          <div className="ps-hero-content">
            <h1 className="ps-hero-title">Discover Amazing Places</h1>
            <p className="ps-hero-subtitle">
              {stats ? 'Search ' + (stats.total_places || 0).toLocaleString() + ' places' : 'Explore countries, cities and places'}
            </p>
            
            <SearchBar
              value={searchQuery}
              onChange={handleSearchChange}
              onSearch={handleSearch}
              onSuggestionSelect={handleSuggestionSelect}
              placeholder="Search for countries, cities, or places..."
              isLoading={isSearching}
            />
          </div>
        </section>

        {/* Results Section */}
        <section className="ps-results-section">
          <div className="ps-results-container">
            {/* Controls Row - only show when searched */}
            {hasSearched && (
              <div className="ps-results-controls">
                <div className="ps-results-info">
                  <span className="ps-results-count">
                    {sortedAndFilteredResults.length} places found
                    {searchQuery && ` for "${searchQuery}"`}
                  </span>
                </div>

                {/* Filter & Sort Bar */}
                <div className="ps-filter-bar">
                  {/* Sort */}
                  <select
                    className="ps-filter-select"
                    value={`${sortBy}-${sortOrder}`}
                    onChange={(e) => {
                      const [s, o] = e.target.value.split('-');
                      handleSortChange(s, o);
                    }}
                  >
                    <option value="rank_score-desc">Best Match</option>
                    <option value="rating-desc">Highest Rated</option>
                    <option value="rating-asc">Lowest Rated</option>
                    <option value="name-asc">Name A-Z</option>
                    <option value="name-desc">Name Z-A</option>
                  </select>

                  {/* Cost filter */}
                  <div className="ps-filter-group">
                    {['Free', 'Paid'].map(cost => (
                      <button
                        key={cost}
                        className={`ps-filter-chip ${filters.costRange.includes(cost.toLowerCase()) ? 'active' : ''}`}
                        onClick={() => {
                          const val = cost.toLowerCase();
                          const newCost = filters.costRange.includes(val)
                            ? filters.costRange.filter(c => c !== val)
                            : [...filters.costRange, val];
                          handleFilterChange({ ...filters, costRange: newCost });
                        }}
                      >
                        {cost}
                      </button>
                    ))}
                  </div>

                  {/* Feature toggles */}
                  <div className="ps-filter-group">
                    {[
                      { key: 'sunrise', icon: 'fa-sun', label: 'Sunrise' },
                      { key: 'sunset', icon: 'fa-moon', label: 'Sunset' },
                    ].map(f => (
                      <button
                        key={f.key}
                        className={`ps-filter-chip ${filters.features.includes(f.key) ? 'active' : ''}`}
                        onClick={() => {
                          const newFeatures = filters.features.includes(f.key)
                            ? filters.features.filter(x => x !== f.key)
                            : [...filters.features, f.key];
                          handleFilterChange({ ...filters, features: newFeatures });
                        }}
                      >
                        <i className={`fas ${f.icon}`}></i> {f.label}
                      </button>
                    ))}
                  </div>

                  {/* Clear all */}
                  {(filters.costRange.length > 0 || filters.features.length > 0) && (
                    <button className="ps-filter-clear" onClick={handleClearFilters}>
                      <i className="fas fa-times"></i> Clear
                    </button>
                  )}
                </div>
              </div>
            )}

            {error && <p role="alert">{error}</p>}
            {/* Results Grid */}
            {isSearching ? (
              <div className="ps-loading-state">
                <div className="ps-loading-spinner"></div>
                <p>Searching places...</p>
              </div>
            ) : hasSearched ? (
              sortedAndFilteredResults.length > 0 ? (
                // Use GroupedPlaceGrid for country (group by state) and state (group by city) searches
                matchType === 'country' ? (
                  <GroupedPlaceGrid
                    places={sortedAndFilteredResults}
                    groupBy="state"
                    onPlaceClick={handlePlaceClick}
                  />
                ) : matchType === 'state' ? (
                  <GroupedPlaceGrid
                    places={sortedAndFilteredResults}
                    groupBy="city"
                    onPlaceClick={handlePlaceClick}
                  />
                ) : (
                  <PlaceGrid
                    places={sortedAndFilteredResults}
                    onPlaceClick={handlePlaceClick}
                  />
                )
              ) : (
                <div className="ps-empty-state">
                  <i className="fas fa-map-marker-alt"></i>
                  <h3>No places found</h3>
                  <p>Try adjusting your search</p>
                </div>
              )
            ) : (
              <div className="ps-welcome-state">
                <i className="fas fa-compass"></i>
                <h3>Start your journey</h3>
                <p>Search for a country, city, or place to explore</p>
              </div>
            )}
          </div>
        </section>
      </main>

      {/* Place Detail Modal */}
      {isModalOpen && selectedPlace && (
        <PlaceDetailModal
          place={selectedPlace}
          onClose={handleCloseModal}
        />
      )}

      <Footer />
    </div>
  );
};

export default PlaceSearchPage;
