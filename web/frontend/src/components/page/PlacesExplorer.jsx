import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import PlaceCard from './PlaceCard';
import placesService from '../../services/placesServiceProfessional';
import { API_CONFIG } from '../../services/placesServiceProfessional';
import '../css/PlacesExplorer.css';

// Debounce helper
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

const PlacesExplorer = () => {
  const { currentUser, signOut } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const sortDropdownRef = useRef(null);
  
  const [places, setPlaces] = useState([]);
  const [filteredPlaces, setFilteredPlaces] = useState([]);
  const [cityQuery, setCityQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [filteringLoading, setFilteringLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastSearchedCity, setLastSearchedCity] = useState('');
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [availableCities, setAvailableCities] = useState([]);
  const [matchInfo, setMatchInfo] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMorePlaces, setHasMorePlaces] = useState(false);
  const [searchType, setSearchType] = useState(null); // 'country', 'state', or 'place'
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState([]); // Autocomplete suggestions
  const [showAutocompleteSuggestions, setShowAutocompleteSuggestions] = useState(false); // Show/hide suggestions
  const [autocompleteLoading, setAutocompleteLoading] = useState(false); // Loading state for autocomplete
  const PLACES_PER_PAGE = 20;
  
  // Filter and Sort States
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'rank_score');
  
  // Dropdown states
  const [showSortDropdown, setShowSortDropdown] = useState(false);

  useEffect(() => {
    // Load initial data from URL if city is in params
    const cityParam = searchParams.get('city');
    if (cityParam) {
      fetchPlacesByCity(cityParam);
    }
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (sortDropdownRef.current && !sortDropdownRef.current.contains(event.target)) {
        setShowSortDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Update URL when filters change
  useEffect(() => {
    if (lastSearchedCity) {
      const params = new URLSearchParams();
      params.set('city', lastSearchedCity);
      if (sortBy !== 'rank_score') params.set('sort', sortBy);
      setSearchParams(params);
    }
  }, [sortBy, lastSearchedCity]);

  // Apply filters and sorting whenever places or filter options change
  useEffect(() => {
    if (places.length > 0) {
      applyFiltersAndSort();
    }
  }, [places, sortBy]);

  const applyFiltersAndSort = useCallback(() => {
    // Don't apply filters/sort for country searches (we're displaying states, not places)
    if (searchType === 'country') {
      setFilteredPlaces(places);
      return;
    }
    
    // Show glass loading effect
    setFilteringLoading(true);
    
    requestAnimationFrame(() => {
      let filtered = [...places];

      // Sort by selected criteria
      filtered.sort((a, b) => {
        switch (sortBy) {
          case 'rating':
            return (b.rating || 0) - (a.rating || 0);
          case 'name':
            return (a.displayName?.text || '').localeCompare(b.displayName?.text || '');
          case 'rank_score':
          default:
            return (b.rank_score || 0) - (a.rank_score || 0);
        }
      });

      setFilteredPlaces(filtered);
      setFilteringLoading(false);
    });
  }, [places, sortBy, searchType]);

  const getSortLabel = () => {
    switch(sortBy) {
      case 'rating': return 'Highest Rating';
      case 'name': return 'Alphabetical';
      default: return 'Best Rated';
    }
  };

  const handleCityInputChange = async (value) => {
    setCityQuery(value);
    
    // Show autocomplete if query is long enough (use config minimum)
    if (value && value.trim().length >= API_CONFIG.autocomplete.minQueryLength) {
      setAutocompleteLoading(true);
      try {
        // Use professional service autocomplete with config settings
        const suggestions = await placesService.getAutocompleteSuggestions(
          value,
          API_CONFIG.autocomplete.maxSuggestions
        );
        if (suggestions.success && suggestions.suggestions.length > 0) {
          setAutocompleteSuggestions(suggestions.suggestions);
          setShowAutocompleteSuggestions(true);
        } else {
          setAutocompleteSuggestions([]);
          setShowAutocompleteSuggestions(false);
        }
      } catch (err) {
        console.error('Autocomplete error:', err);
        setAutocompleteSuggestions([]);
      } finally {
        setAutocompleteLoading(false);
      }
    } else {
      setAutocompleteSuggestions([]);
      setShowAutocompleteSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    // Extract display name from suggestion object or string
    const displayName = typeof suggestion === 'string' ? suggestion : suggestion.name || suggestion;
    setCityQuery(displayName);
    setShowAutocompleteSuggestions(false);
    // Pass full suggestion object for direct place ID search if available
    setTimeout(() => {
      fetchPlacesByCity(displayName, 1, suggestion);
    }, 100);
  };

  const fetchPlacesByCity = async (cityInput, page = 1, suggestionObject = null) => {
    if (!cityInput || cityInput.trim() === '') {
      setError('Please enter a location name (city, state, or country)');
      return;
    }

    setLoading(true);
    setError(null);
    if (page === 1) {
      setMatchInfo(null);
      setCurrentPage(1);
    }
    
    try {
      let result = null;
      
      // Handle different suggestion types
      if (suggestionObject) {
        const type = suggestionObject.type?.toLowerCase();
        
        if (type === 'country') {
          // Country: Load all states with top 5 places each
          console.log('🌍 Country selected:', suggestionObject.name);
          result = await placesService.getCountryOverview(suggestionObject.name);
          
          if (result.success) {
            // Flatten states structure for display
            const allPlaces = [];
            const statesInfo = [];
            
            result.states.forEach(state => {
              statesInfo.push({
                name: state.state_name || state.name,
                placeCount: state.place_count || state.top_places?.length || 0,
              });
              allPlaces.push(...(state.top_places || []));
            });
            
            setPlaces(allPlaces);
            setSearchType('country');
            setLastSearchedCity(suggestionObject.name);
            setHasMorePlaces(false);
            
            setMatchInfo({
              matchType: 'country',
              matched: {
                name: result.country,
                stateCount: result.stateCount,
              },
              count: allPlaces.length,
              statesInfo: statesInfo,
              cacheHit: result.cacheHit,
              responseTime: result.responseTime,
              firebaseReads: result.firebaseReads
            });
            
            console.log('🔥 Country Search Firebase Tracking:', {
              country: suggestionObject.name,
              states: result.stateCount,
              total_places: allPlaces.length,
              firebase_reads: result.firebaseReads,
              response_time_ms: result.responseTime,
              cache_hit: result.cacheHit
            });
          }
        } 
        else if (type === 'state') {
          // State: Load top 20 places
          console.log('🏙️  State selected:', suggestionObject.name, 'Country:', suggestionObject.country);
          result = await placesService.getStateOverview(suggestionObject.name, suggestionObject.country);
          
          if (result.success) {
            setPlaces(result.places);
            setSearchType('state');
            setLastSearchedCity(suggestionObject.name);
            setHasMorePlaces(false);
            
            setMatchInfo({
              matchType: 'state',
              matched: {
                name: result.state,
                country: result.country,
              },
              count: result.count,
              cacheHit: result.cacheHit,
              responseTime: result.responseTime,
              firebaseReads: result.firebaseReads
            });
            
            console.log('🔥 State Search Firebase Tracking:', {
              state: suggestionObject.name,
              places: result.count,
              firebase_reads: result.firebaseReads,
              response_time_ms: result.responseTime,
              cache_hit: result.cacheHit
            });
          }
        } 
        else if (type === 'place') {
          // Single place: Get only that place from its city
          console.log('📍 Single place selected:', suggestionObject.name, 'City:', suggestionObject.city);
          result = await placesService.getSinglePlace(suggestionObject.name, suggestionObject.city);
          
          if (result.success) {
            setPlaces([result.place]);
            setSearchType('place');
            setLastSearchedCity(suggestionObject.city);
            setHasMorePlaces(false);
            
            setMatchInfo({
              matchType: 'place',
              matched: {
                name: result.place.name,
                city: result.place.city,
              },
              count: 1,
            });
            
            console.log('🔥 Single Place Search Firebase Tracking:', {
              place: suggestionObject.name,
              city: suggestionObject.city,
              found: true
            });
          }
        }
        else {
          // City or unknown: Regular search
          result = await placesService.searchByLocation(cityInput, PLACES_PER_PAGE, 1);
        }
      } else {
        // No suggestion object: Regular text search
        result = await placesService.searchByLocation(cityInput, PLACES_PER_PAGE, 1);
      }
      
      // Handle result
      if (result && result.success) {
        if (!suggestionObject || suggestionObject.type === 'city' || !suggestionObject.type) {
          // Regular city/state/country search
          const placesToDisplay = result.places || [];
          setPlaces(prevPlaces => page === 1 ? placesToDisplay : [...prevPlaces, ...placesToDisplay]);
          setLastSearchedCity(cityInput);
          setCurrentPage(page);
          setHasMorePlaces(placesToDisplay.length === PLACES_PER_PAGE);
          
          setMatchInfo({
            matchType: result.matchType,
            matched: result.matched,
            count: result.count,
            cacheHit: result.cacheHit,
            responseTime: result.responseTime,
            firebaseReads: result.firebaseReads
          });
          
          setSearchType(result.matchType?.toLowerCase() || 'unknown');
        }
        
        // Log Firebase API usage
        console.log('🔥 Firebase API Tracking:', {
          query: cityInput,
          match_type: result.matchType,
          cache_hit: result.cacheHit,
          firebase_reads: result.firebaseReads,
          places_returned: result.places?.length || 1,
          response_time_ms: result.responseTime,
          efficiency: result.cacheHit ? '✅ CACHED (0 Firebase reads)' : `📊 ${result.firebaseReads} Firebase reads`
        });
      } else {
        // Handle not found or empty results
        const notFoundMessage = result?.error || `No places found for "${cityInput}"`;
        setError(`${notFoundMessage}. Try searching by country (India), state (Agra), or city (Singapore).`);
        setPlaces([]);
        setSearchType(null);
      }
    } catch (err) {
      console.error('Error fetching places:', err);
      const errorMessage = err.message || 'An error occurred while searching places';
      setError(`Search failed: ${errorMessage}. Please check your spelling and try again.`);
      setPlaces([]);
      setSearchType(null);
    } finally {
      setLoading(false);
    }
  };

  const handleCitySearch = (e) => {
    e.preventDefault();
    fetchPlacesByCity(cityQuery);
  };

  const handlePlaceClick = (place) => {
    console.log('=== PLACE CLICKED ===');
    console.log('Place name:', place.displayName?.text || place.name);
    console.log('Full place object:', place);
    console.log('Photos object:', place.photos);
    console.log('Photos type:', typeof place.photos);
    
    if (place.photos) {
      console.log('Wikimedia commons:', place.photos.wikimedia_commons);
      if (place.photos.wikimedia_commons) {
        console.log('Thumbnail:', place.photos.wikimedia_commons.thumbnail);
        console.log('Gallery:', place.photos.wikimedia_commons.gallery);
        console.log('Gallery length:', place.photos.wikimedia_commons.gallery?.length);
      }
    }
    console.log('===================');
    
    setSelectedPlace(place);
  };

  const closeModal = () => {
    setSelectedPlace(null);
  };

  return (
    <div className="places-explorer-page">
      <Header 
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={signOut}
      />
      
      <div className="places-explorer-container">
        <div className="places-hero">
          <h1>
            <i className="fas fa-map-marked-alt"></i>
            Places Explorer
          </h1>
          <p className="places-subtitle">
            Discover 16,000+ places across 888 cities in 82 countries. Search by city, state, or country!
          </p>
          
          <form className="city-search-form" onSubmit={handleCitySearch}>
            <div className="search-input-container">
              <i className="fas fa-map-marker-alt search-icon"></i>
              <input
                type="text"
                value={cityQuery}
                onChange={(e) => handleCityInputChange(e.target.value)}
                placeholder="Search city, state, or country (e.g., Singapore, Chinatown, India)"
                className="city-search-input"
              />
              <button type="submit" className="search-city-button" disabled={loading}>
                <i className="fas fa-search"></i>
                {loading ? 'Searching...' : 'Search Places'}
              </button>
              
              {/* Autocomplete Suggestions Dropdown */}
              {showAutocompleteSuggestions && (autocompleteSuggestions.length > 0 || autocompleteLoading) && (
                <div className="autocomplete-suggestions-dropdown">
                  {autocompleteLoading ? (
                    <div className="autocomplete-loading">
                      <span className="autocomplete-spinner"></span>
                      <span>Finding suggestions...</span>
                    </div>
                  ) : (
                    <ul className="autocomplete-list">
                      {autocompleteSuggestions.map((suggestion, index) => {
                        // Handle both string and object formats
                        const suggestionName = typeof suggestion === 'string' ? suggestion : suggestion.name || suggestion;
                        const suggestionType = typeof suggestion === 'object' && suggestion.type ? suggestion.type : 'location';
                        const suggestionCity = typeof suggestion === 'object' && suggestion.city ? suggestion.city : '';
                        const suggestionState = typeof suggestion === 'object' && suggestion.state ? suggestion.state : '';
                        
                        return (
                          <li
                            key={index}
                            className="autocomplete-item"
                            onClick={() => handleSuggestionClick(suggestion)}
                          >
                            <div className="autocomplete-item-content">
                              <span className="autocomplete-item-name">{suggestionName}</span>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </form>
        </div>

        {loading && (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Discovering amazing places in {cityQuery}...</p>
          </div>
        )}

        {error && !loading && (
          <div className="error-container">
            <i className="fas fa-exclamation-circle"></i>
            <p>Error: {error}</p>
          </div>
        )}

        {!loading && places.length === 0 && !error && (
          <div className="no-results">
            <i className="fas fa-search-location"></i>
            <h2>Ready to Explore?</h2>
            <p>Enter a city name above to discover amazing places!</p>
          </div>
        )}

        {!loading && places.length > 0 && (
          <>
            {/* Filters and Sort Controls - Only show for state/city search */}
            {(searchType === 'state' || searchType === 'city' || searchType === 'city_fuzzy') && (
            <div className="filters-section">
              <div className="filters-container">
                {/* Sort Button with Dropdown */}
                <div className="filter-button-wrapper" ref={sortDropdownRef}>
                  <button 
                    className="filter-button"
                    onClick={() => {
                      setShowSortDropdown(!showSortDropdown);
                    }}
                  >
                    <i className="fas fa-arrow-down-arrow-up"></i>
                    {getSortLabel()}
                    <i className="fas fa-chevron-down"></i>
                  </button>
                  
                  {showSortDropdown && (
                    <div className="filter-dropdown">
                      <div 
                        className={`dropdown-option ${sortBy === 'rank_score' ? 'active' : ''}`}
                        onClick={() => {
                          setSortBy('rank_score');
                          setShowSortDropdown(false);
                        }}
                      >
                        <i className="fas fa-circle-dot"></i>
                        <div>
                          <div className="option-title">Best Rated</div>
                          <div className="option-subtitle">Top quality destinations</div>
                        </div>
                      </div>
                      <div 
                        className={`dropdown-option ${sortBy === 'rating' ? 'active' : ''}`}
                        onClick={() => {
                          setSortBy('rating');
                          setShowSortDropdown(false);
                        }}
                      >
                        <i className="fas fa-circle-dot"></i>
                        <div>
                          <div className="option-title">Highest Rating</div>
                          <div className="option-subtitle">By rating score</div>
                        </div>
                      </div>
                      <div 
                        className={`dropdown-option ${sortBy === 'name' ? 'active' : ''}`}
                        onClick={() => {
                          setSortBy('name');
                          setShowSortDropdown(false);
                        }}
                      >
                        <i className="fas fa-circle-dot"></i>
                        <div>
                          <div className="option-title">Alphabetical</div>
                          <div className="option-subtitle">Sort by name</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Clear Filters Button */}
                <button 
                  className="clear-filters-btn"
                  onClick={() => {
                    setSortBy('rank_score');
                    setShowSortDropdown(false);
                  }}
                >
                  Reset sorting
                </button>
              </div>
            </div>
            )}

            {/* Places Content Wrapper with Loading Overlay */}
            <div style={{ position: 'relative' }}>
              {/* Glass Loading Overlay - Only covers places section */}
              {filteringLoading && (
                <div className="filter-loading-overlay">
                  <div className="filter-loading-content">
                    <div className="filter-loading-spinner"></div>
                    <p>Applying filters...</p>
                  </div>
                </div>
              )}

              {/* COUNTRY SEARCH VIEW - Show all states with their top 5 places */}
              {searchType === 'country' && places.length > 0 && (
                <div className="country-view">
                  <div className="country-header">
                    <h2>{matchInfo?.matched?.name}</h2>
                    <p className="country-info">
                      Exploring {matchInfo?.matched?.place_count || 0} top places
                    </p>
                  </div>
                  
                  {/* States Grid View */}
                  <div className="states-container">
                    {places && places.length > 0 && places.map((state, stateIndex) => (
                      <div key={`state-${stateIndex}`} className="state-section">
                        <div className="state-header">
                          <h3 className="state-name">
                            <i className="fas fa-map"></i>
                            {state.state_name || state.stateName}
                          </h3>
                          <p className="state-info">
                            {state.place_count || state.placeCount || 0} places • Top 5 shown
                          </p>
                        </div>
                        
                        <div className="state-places-grid">
                          {(state.top_places || state.topPlaces || []).slice(0, 5).map((place, placeIndex) => (
                            <PlaceCard
                              key={`${state.state_id || stateIndex}-${place.id || placeIndex}`}
                              place={place}
                              animationDelay={`${(placeIndex * 0.05) % 0.25}s`}
                              onClick={() => handlePlaceClick(place)}
                              isExpertChoice={false}
                            />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SINGLE PLACE SEARCH VIEW - Show single place card */}
              {searchType === 'place' && filteredPlaces.length === 1 && (
                <div className="single-place-view">
                  <div className="single-place-container">
                    <PlaceCard 
                      place={filteredPlaces[0]}
                      animationDelay="0s"
                      onClick={() => handlePlaceClick(filteredPlaces[0])}
                      isExpertChoice={false}
                    />
                  </div>
                </div>
              )}

              {/* STATE/CITY SEARCH VIEW - Show current UI with Expert's Choice */}
              {(searchType === 'state' || searchType === 'city' || searchType === 'city_fuzzy') && filteredPlaces.length > 0 && (
                <>
                  {/* Expert's Choice - Top 10 */}
                  <div className="expert-section">
                    <div className="section-header">
                      <div className="section-title">
                        <i className="fas fa-crown"></i>
                        <h2>Expert's Choice Recommendations</h2>
                      </div>
                      <p className="section-subtitle">Top 10 highest-rated destinations based on our expert ranking system</p>
                    </div>
                    
                    <div className="places-grid expert-grid">
                      {filteredPlaces.slice(0, 10).map((place, index) => (
                        <PlaceCard 
                          key={place.id || index} 
                          place={place}
                          animationDelay={`${(index % 8) * 0.05}s`}
                          onClick={() => handlePlaceClick(place)}
                          isExpertChoice={true}
                          rank={index + 1}
                        />
                      ))}
                    </div>
                  </div>

                  {/* All Places - Excluding Top 10 */}
                  {filteredPlaces.length > 10 && (
                    <div className="all-places-section">
                      <div className="section-header">
                        <div className="section-title">
                          <i className="fas fa-map-marked-alt"></i>
                          <h2>All Destinations</h2>
                        </div>
                        <p className="section-subtitle">Explore {filteredPlaces.length - 10} more amazing places in {lastSearchedCity}</p>
                      </div>
                      
                      <div className="places-grid">
                        {filteredPlaces.slice(10).map((place, index) => (
                          <PlaceCard 
                            key={place.id || index} 
                            place={place}
                            animationDelay={`${(index % 8) * 0.05}s`}
                            onClick={() => handlePlaceClick(place)}
                            isExpertChoice={false}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </div>

      {selectedPlace && (
        <div className="modal-overlay show" onClick={closeModal}>
          <button className="modal-close" onClick={closeModal} aria-label="Close details">
            <i className="fas fa-times" aria-hidden="true"></i>
          </button>
          
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            {/* Photo Gallery - Only show if we have at least 1 real photo */}
            {(() => {
              // Count real photos
              const photos = selectedPlace.photos;
              const realPhotos = [];
              
              // New structure: wikimedia_commons
              if (photos?.wikimedia_commons?.thumbnail?.url && photos.wikimedia_commons.thumbnail.url.trim() !== '') {
                realPhotos.push(photos.wikimedia_commons.thumbnail.url);
              }
              if (photos?.wikimedia_commons?.gallery && Array.isArray(photos.wikimedia_commons.gallery)) {
                photos.wikimedia_commons.gallery.forEach(img => {
                  if (img?.url && img.url.trim() !== '') realPhotos.push(img.url);
                });
              }
              
              // Old structure: primary and gallery
              if (photos?.primary?.url && photos.primary.url.trim() !== '') {
                realPhotos.push(photos.primary.url);
              }
              if (photos?.gallery && Array.isArray(photos.gallery)) {
                photos.gallery.forEach(img => {
                  if (img?.url && img.url.trim() !== '') realPhotos.push(img.url);
                });
              }
              
              console.log('Real photos count:', realPhotos.length);
              console.log('Real photos URLs:', realPhotos);
              
              // Only show images if we have at least one real photo
              if (realPhotos.length === 0) {
                console.log('No real photos - hiding gallery');
                return null; // No images to display
              }
              
              // Show gallery grid if we have 2+ photos
              if (realPhotos.length >= 2) {
                return (
                  <div className="modal-gallery-grid">
                    <div className="gallery-main-image">
                      <img 
                        src={realPhotos[0]} 
                        alt={selectedPlace.displayName?.text || selectedPlace.name}
                      />
                    </div>
                    <div className="gallery-side-images">
                      <img 
                        src={realPhotos[1] || 'https://placehold.co/512x300/7c3aed/ffffff?text=Place+Image'} 
                        alt={`${selectedPlace.displayName?.text || selectedPlace.name} - View 2`}
                      />
                      <img 
                        src={realPhotos[2] || 'https://placehold.co/512x300/6d28d9/ffffff?text=Place+Image'} 
                        alt={`${selectedPlace.displayName?.text || selectedPlace.name} - View 3`}
                      />
                    </div>
                  </div>
                );
              } else {
                // Show single image if we have exactly 1 photo
                return (
                  <div className="modal-single-image">
                    <img 
                      src={realPhotos[0]}
                      alt={selectedPlace.displayName?.text || selectedPlace.name}
                    />
                  </div>
                );
              }
            })()}
            
            <div className="modal-header">
              <h2 id="modalTitle">{selectedPlace.displayName?.text || selectedPlace.name}</h2>
              {(selectedPlace.city_name || selectedPlace.state_name) && (
                <p className="modal-location">
                  <i className="fas fa-map-marker-alt"></i>
                  {selectedPlace.city_name && selectedPlace.state_name 
                    ? `${selectedPlace.city_name}, ${selectedPlace.state_name}` 
                    : selectedPlace.city_name || selectedPlace.state_name}
                </p>
              )}
            </div>

            <div className="modal-body">
              {/* About Section */}
              <div className="modal-section">
                <h3><i className="fas fa-info-circle"></i> About</h3>
                <p className="modal-description">
                  {selectedPlace.summary || 
                   selectedPlace.generativeSummary?.overview?.text || 
                   selectedPlace.reviewSummary?.text?.text || 
                   'Discover this amazing destination and create unforgettable memories.'}
                </p>
                
                {/* Editorial Summary */}
                {selectedPlace.editorialSummary?.text && (
                  <div className="modal-editorial">
                    <p className="editorial-text">
                      <i className="fas fa-quote-left"></i>
                      {selectedPlace.editorialSummary.text}
                    </p>
                  </div>
                )}

                {/* Place Types */}
                {selectedPlace.place_types && selectedPlace.place_types.length > 0 && (
                  <div className="modal-types">
                    <strong>Categories:</strong>{' '}
                    {selectedPlace.place_types.map(type => 
                      type.replace(/_/g, ' ')
                    ).join(', ')}
                  </div>
                )}
              </div>

              {/* Ratings & Reviews Section */}
              {(selectedPlace.rating || selectedPlace.rating_value) && (
                <div className="modal-section">
                  <h3><i className="fas fa-star"></i> Ratings & Reviews</h3>
                  <div className="ratings-info">
                    <div className="rating-display">
                      <div className="rating-score">
                        {selectedPlace.rating || selectedPlace.rating_value}
                        <i className="fas fa-star"></i>
                      </div>
                      {(selectedPlace.userRatingCount || selectedPlace.total_reviews) && (
                        <div className="rating-count">
                          Based on {(selectedPlace.userRatingCount || selectedPlace.total_reviews).toLocaleString()} reviews
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Expert Tip Section */}
              {selectedPlace.place_tip && (
                <div className="modal-section">
                  <h3><i className="fas fa-lightbulb"></i> Expert Tip</h3>
                  <div className="modal-tip">
                    <i className="fas fa-lightbulb"></i>
                    <p>{selectedPlace.place_tip}</p>
                  </div>
                </div>
              )}

              {/* Quick Facts Section */}
              <div className="modal-section">
                <h3><i className="fas fa-list-check"></i> Quick Facts</h3>
                <div className="info-grid">
                  {selectedPlace.duration && (
                    <div className="info-item">
                      <i className="fas fa-clock"></i>
                      <div className="info-item-content">
                        <span className="info-item-label">Duration</span>
                        <span className="info-item-value">{selectedPlace.duration}</span>
                      </div>
                    </div>
                  )}
                  
                  {selectedPlace.cost && (
                    <div className="info-item">
                      <i className="fas fa-dollar-sign"></i>
                      <div className="info-item-content">
                        <span className="info-item-label">Cost</span>
                        <span className="info-item-value">{selectedPlace.cost}</span>
                      </div>
                    </div>
                  )}
                  
                  {selectedPlace.best_time && (
                    <div className="info-item">
                      <i className="fas fa-calendar-alt"></i>
                      <div className="info-item-content">
                        <span className="info-item-label">Best Time</span>
                        <span className="info-item-value">{selectedPlace.best_time}</span>
                      </div>
                    </div>
                  )}
                  
                  {selectedPlace.advance_booking && (
                    <div className="info-item">
                      <i className="fas fa-ticket-alt"></i>
                      <div className="info-item-content">
                        <span className="info-item-label">Booking</span>
                        <span className="info-item-value">{selectedPlace.advance_booking}</span>
                      </div>
                    </div>
                  )}

                  {selectedPlace.rating_tourist_priority && (
                    <div className="info-item">
                      <i className="fas fa-star"></i>
                      <div className="info-item-content">
                        <span className="info-item-label">Tourist Priority</span>
                        <span className="info-item-value">{selectedPlace.rating_tourist_priority} / 5</span>
                      </div>
                    </div>
                  )}

                  {selectedPlace.rating_traveler_experience && (
                    <div className="info-item">
                      <i className="fas fa-heart"></i>
                      <div className="info-item-content">
                        <span className="info-item-label">Experience Rating</span>
                        <span className="info-item-value">{selectedPlace.rating_traveler_experience} / 5</span>
                      </div>
                    </div>
                  )}

                  {selectedPlace.rank_score && (
                    <div className="info-item">
                      <i className="fas fa-trophy"></i>
                      <div className="info-item-content">
                        <span className="info-item-label">Rank Score</span>
                        <span className="info-item-value">{(selectedPlace.rank_score * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  )}

                  {selectedPlace.nearest_airport && (
                    <div className="info-item">
                      <i className="fas fa-plane"></i>
                      <div className="info-item-content">
                        <span className="info-item-label">Nearest Airport</span>
                        <span className="info-item-value">{selectedPlace.nearest_airport}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Opening Hours Section */}
              {selectedPlace.opening_hours && typeof selectedPlace.opening_hours === 'object' && (
                <div className="modal-section">
                  <h3><i className="fas fa-clock"></i> Opening Hours</h3>
                  <div className="opening-hours-container">
                    {Object.entries(selectedPlace.opening_hours).map(([day, hours]) => {
                      if (day === 'notes') return null;
                      const dayName = day.charAt(0).toUpperCase() + day.slice(1);
                      return (
                        <div key={day} className="hours-row">
                          <span className="day-label">{dayName}</span>
                          <span className="hours-value">{hours || 'Closed'}</span>
                        </div>
                      );
                    })}
                  </div>
                  {selectedPlace.opening_hours.notes && (
                    <div className="hours-notes">
                      <i className="fas fa-info-circle"></i> {selectedPlace.opening_hours.notes}
                    </div>
                  )}
                </div>
              )}

              {/* Tags/Categories Section */}
              {selectedPlace.tags && selectedPlace.tags.length > 0 && (
                <div className="modal-section">
                  <h3><i className="fas fa-tags"></i> Categories</h3>
                  <div className="modal-tags">
                    {selectedPlace.tags.map((tag, index) => (
                      <span key={index} className="modal-tag">
                        {typeof tag === 'string' ? tag.replace(/_/g, ' ') : tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Special Features */}
              {(selectedPlace.sunrise_view || selectedPlace.sunset_view || selectedPlace.sunrise_time || selectedPlace.sunset_time) && (
                <div className="modal-section">
                  <h3><i className="fas fa-sun"></i> Special Features</h3>
                  <div className="special-features-grid">
                    {selectedPlace.sunrise_view && (
                      <div className="feature-tag sunrise">
                        <i className="fas fa-sunrise"></i> 
                        <div>
                          <strong>Sunrise View</strong>
                          {selectedPlace.sunrise_time && selectedPlace.sunrise_time !== 'N/A' && (
                            <small style={{display: 'block', marginTop: '4px'}}>
                              {selectedPlace.sunrise_time}
                            </small>
                          )}
                        </div>
                      </div>
                    )}
                    {selectedPlace.sunset_view && (
                      <div className="feature-tag sunset">
                        <i className="fas fa-sunset"></i>
                        <div>
                          <strong>Sunset View</strong>
                          {selectedPlace.sunset_time && selectedPlace.sunset_time !== 'N/A' && (
                            <small style={{display: 'block', marginTop: '4px'}}>
                              {selectedPlace.sunset_time}
                            </small>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Location & Actions */}
              <div className="modal-section modal-actions-section">
                <h3><i className="fas fa-map-pin"></i> Location & Details</h3>
                
                {/* Full Location Hierarchy */}
                <div className="location-hierarchy">
                  {selectedPlace.city_name && (
                    <div className="location-item">
                      <i className="fas fa-building"></i>
                      <span><strong>City:</strong> {selectedPlace.city_name}</span>
                    </div>
                  )}
                  {selectedPlace.state_name && (
                    <div className="location-item">
                      <i className="fas fa-map"></i>
                      <span><strong>State:</strong> {selectedPlace.state_name}</span>
                    </div>
                  )}
                  {selectedPlace.country_name && (
                    <div className="location-item">
                      <i className="fas fa-flag"></i>
                      <span><strong>Country:</strong> {selectedPlace.country_name}</span>
                    </div>
                  )}
                </div>

                {selectedPlace.formattedAddress && (
                  <p className="modal-address">
                    <i className="fas fa-map-marker-alt"></i>
                    <strong>Full Address:</strong> {selectedPlace.formattedAddress}
                  </p>
                )}

                {/* Coordinates */}
                {selectedPlace.location && (selectedPlace.location.latitude || selectedPlace.latitude) && (
                  <p className="modal-coordinates">
                    <i className="fas fa-crosshairs"></i>
                    <strong>Coordinates:</strong> {' '}
                    {selectedPlace.location?.latitude || selectedPlace.latitude}°N, {' '}
                    {selectedPlace.location?.longitude || selectedPlace.longitude}°E
                  </p>
                )}

                {/* Place Identifiers */}
                {(selectedPlace.slug || selectedPlace.place_id || selectedPlace.google_place_id) && (
                  <div className="modal-identifiers">
                    {selectedPlace.slug && (
                      <p className="modal-slug">
                        <i className="fas fa-link"></i>
                        <strong>Slug:</strong> {selectedPlace.slug}
                      </p>
                    )}
                    {selectedPlace.place_id && (
                      <p className="modal-place-id">
                        <i className="fas fa-fingerprint"></i>
                        <strong>Place ID:</strong> <code>{selectedPlace.place_id}</code>
                      </p>
                    )}
                    {selectedPlace.google_place_id && (
                      <p className="modal-google-id">
                        <i className="fab fa-google"></i>
                        <strong>Google ID:</strong> <code>{selectedPlace.google_place_id}</code>
                      </p>
                    )}
                  </div>
                )}

                <div className="modal-actions">
                  {(selectedPlace.website || selectedPlace.websiteUri) && (
                    <a 
                      href={selectedPlace.website || selectedPlace.websiteUri} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="modal-action-button primary"
                    >
                      <i className="fas fa-globe"></i> Visit Website
                    </a>
                  )}
                  {(selectedPlace.location?.latitude || selectedPlace.latitude) && (
                    <a 
                      href={`https://www.google.com/maps?q=${selectedPlace.location?.latitude || selectedPlace.latitude},${selectedPlace.location?.longitude || selectedPlace.longitude}`}
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="modal-action-button secondary"
                    >
                      <i className="fas fa-map-marked-alt"></i> Open in Maps
                    </a>
                  )}
                </div>
              </div>

            </div>

            {/* Complete Data - All 34 Fields */}
            <div className="modal-section">
              <h3><i className="fas fa-database"></i> Complete Data (All 34 Fields)</h3>
              <details className="complete-data-details">
                <summary>View Full JSON Structure</summary>
                <div className="complete-data-table">
                  {/* IDENTIFICATION FIELDS (5) */}
                  <div className="data-category">
                    <h4>Identification</h4>
                    <div className="data-fields">
                      <div className="data-field">
                        <span className="field-name">id</span>
                        <span className="field-value">{selectedPlace.id}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">name</span>
                        <span className="field-value">{selectedPlace.name}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">name_english</span>
                        <span className="field-value">{selectedPlace.name_english || selectedPlace.name}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">name_native</span>
                        <span className="field-value">{selectedPlace.name_native || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">name_normalized</span>
                        <span className="field-value">{selectedPlace.name_normalized || selectedPlace.name}</span>
                      </div>
                    </div>
                  </div>

                  {/* LOCATION FIELDS (9) */}
                  <div className="data-category">
                    <h4>Location</h4>
                    <div className="data-fields">
                      <div className="data-field">
                        <span className="field-name">address</span>
                        <span className="field-value">{selectedPlace.address || selectedPlace.formattedAddress || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">city</span>
                        <span className="field-value">{selectedPlace.city || selectedPlace.city_name || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">city_normalized</span>
                        <span className="field-value">{selectedPlace.city_normalized || selectedPlace.city || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">state</span>
                        <span className="field-value">{selectedPlace.state || selectedPlace.state_name || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">state_normalized</span>
                        <span className="field-value">{selectedPlace.state_normalized || selectedPlace.state || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">country</span>
                        <span className="field-value">{selectedPlace.country || selectedPlace.country_name || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">country_normalized</span>
                        <span className="field-value">{selectedPlace.country_normalized || selectedPlace.country || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">coordinates</span>
                        <span className="field-value">
                          {selectedPlace.coordinates?.latitude && selectedPlace.coordinates?.longitude 
                            ? `${selectedPlace.coordinates.latitude}, ${selectedPlace.coordinates.longitude}`
                            : selectedPlace.latitude && selectedPlace.longitude
                            ? `${selectedPlace.latitude}, ${selectedPlace.longitude}`
                            : 'N/A'}
                        </span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">has_coordinates</span>
                        <span className="field-value">{selectedPlace.has_coordinates ? 'true' : 'false'}</span>
                      </div>
                    </div>
                  </div>

                  {/* COST & DURATION FIELDS (3) */}
                  <div className="data-category">
                    <h4>Cost & Duration</h4>
                    <div className="data-fields">
                      <div className="data-field">
                        <span className="field-name">cost</span>
                        <span className="field-value">{selectedPlace.cost || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">suggested_duration</span>
                        <span className="field-value">{selectedPlace.suggested_duration || selectedPlace.duration || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">best_time_to_visit</span>
                        <span className="field-value">{selectedPlace.best_time_to_visit || selectedPlace.best_time || 'N/A'}</span>
                      </div>
                    </div>
                  </div>

                  {/* RATINGS FIELDS (2) */}
                  <div className="data-category">
                    <h4>Ratings</h4>
                    <div className="data-fields">
                      <div className="data-field">
                        <span className="field-name">rating_tourist_priority</span>
                        <span className="field-value">{selectedPlace.rating_tourist_priority || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">rating_traveler_experience</span>
                        <span className="field-value">{selectedPlace.rating_traveler_experience || 'N/A'}</span>
                      </div>
                    </div>
                  </div>

                  {/* CONTENT FIELDS (3) */}
                  <div className="data-category">
                    <h4>Content</h4>
                    <div className="data-fields">
                      <div className="data-field">
                        <span className="field-name">ai_summary</span>
                        <span className="field-value">{selectedPlace.ai_summary || selectedPlace.summary || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">tags</span>
                        <span className="field-value">{selectedPlace.tags?.join(', ') || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">search_text</span>
                        <span className="field-value">{selectedPlace.search_text || 'N/A'}</span>
                      </div>
                    </div>
                  </div>

                  {/* CONTACT & HOURS FIELDS (3) */}
                  <div className="data-category">
                    <h4>Contact & Hours</h4>
                    <div className="data-fields">
                      <div className="data-field">
                        <span className="field-name">official_website</span>
                        <span className="field-value">
                          {selectedPlace.official_website || selectedPlace.website ? (
                            <a href={selectedPlace.official_website || selectedPlace.website} target="_blank" rel="noopener noreferrer">
                              {selectedPlace.official_website || selectedPlace.website}
                            </a>
                          ) : 'N/A'}
                        </span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">advanced_booking</span>
                        <span className="field-value">{selectedPlace.advanced_booking || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">opening_hours</span>
                        <span className="field-value">{selectedPlace.opening_hours ? 'Available' : 'N/A'}</span>
                      </div>
                    </div>
                  </div>

                  {/* MEDIA FIELDS (1) */}
                  <div className="data-category">
                    <h4>Media</h4>
                    <div className="data-fields">
                      <div className="data-field">
                        <span className="field-name">photos</span>
                        <span className="field-value">{selectedPlace.photos ? 'Available' : 'N/A'}</span>
                      </div>
                    </div>
                  </div>

                  {/* TIME OF DAY FIELDS (4) */}
                  <div className="data-category">
                    <h4>Time of Day</h4>
                    <div className="data-fields">
                      <div className="data-field">
                        <span className="field-name">sunrise_time</span>
                        <span className="field-value">{selectedPlace.sunrise_time || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">sunset_time</span>
                        <span className="field-value">{selectedPlace.sunset_time || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">sunrise_view</span>
                        <span className="field-value">{selectedPlace.sunrise_view ? 'Yes' : 'No'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">sunset_view</span>
                        <span className="field-value">{selectedPlace.sunset_view ? 'Yes' : 'No'}</span>
                      </div>
                    </div>
                  </div>

                  {/* RANKING & METADATA FIELDS (4) */}
                  <div className="data-category">
                    <h4>Ranking & Metadata</h4>
                    <div className="data-fields">
                      <div className="data-field">
                        <span className="field-name">rank_score</span>
                        <span className="field-value">{selectedPlace.rank_score ? `${(selectedPlace.rank_score * 100).toFixed(1)}%` : 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">place_tip</span>
                        <span className="field-value">{selectedPlace.place_tip || 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">created_at</span>
                        <span className="field-value">{selectedPlace.created_at ? new Date(selectedPlace.created_at).toLocaleString() : 'N/A'}</span>
                      </div>
                      <div className="data-field">
                        <span className="field-name">updated_at</span>
                        <span className="field-value">{selectedPlace.updated_at ? new Date(selectedPlace.updated_at).toLocaleString() : 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </details>
            </div>

            {/* Photo Attribution - Only show if we have real photos with URLs */}
            {(() => {
              const photos = selectedPlace.photos;
              
              // Check if we have any real photo URLs (non-empty strings)
              const hasRealPhotos = 
                (photos?.thumbnail_url && photos.thumbnail_url.trim() !== '') ||
                (photos?.wikimedia_commons?.thumbnail?.url && photos.wikimedia_commons.thumbnail.url.trim() !== '') ||
                (photos?.wikimedia_commons?.gallery && Array.isArray(photos.wikimedia_commons.gallery) && 
                  photos.wikimedia_commons.gallery.some(img => img?.url && img.url.trim() !== '')) ||
                (photos?.primary?.url && photos.primary.url.trim() !== '') ||
                (photos?.gallery && Array.isArray(photos.gallery) && 
                  photos.gallery.some(img => img?.url && img.url.trim() !== ''));
              
              console.log('Has real photos for attribution:', hasRealPhotos);
              console.log('Photos object:', photos);
              
              // Only show attribution if we have real photos
              if (!hasRealPhotos) {
                console.log('No real photos - hiding attribution');
                return null;
              }
              
              // Check if we have attribution data
              const hasAttribution = 
                photos?.attribution ||
                photos?.wikimedia_commons?.thumbnail?.attribution ||
                (photos?.wikimedia_commons?.gallery && photos.wikimedia_commons.gallery.some(p => p?.attribution));
              
              if (!hasAttribution) {
                console.log('No attribution data available');
                return null;
              }
              
              return (
                <div className="modal-section photo-attribution-section">
                  <details className="attribution-details" open>
                    <summary>
                      <i className="fas fa-camera"></i> Photo Credit
                    </summary>
                    <ul className="attribution-list">
                      {/* DIRECT ATTRIBUTION (New Structure) */}
                      {photos?.attribution && (
                        <li>
                          <strong>Photo:</strong> "{photos.attribution.title || 'Untitled'}"
                          {photos.attribution.description && (
                            <div style={{ fontSize: '0.8125rem', color: '#64748b', marginTop: '0.25rem' }}>
                              {photos.attribution.description}
                            </div>
                          )}
                          <div style={{ marginTop: '0.5rem' }}>
                            <strong>Author:</strong> {photos.attribution.author || 'Unknown'}
                            {photos.attribution.credit && (
                              <span style={{ marginLeft: '0.5rem', fontSize: '0.8125rem', color: '#64748b' }}>
                                ({photos.attribution.credit})
                              </span>
                            )}
                          </div>
                          {photos.attribution.license && (
                            <div style={{ marginTop: '0.25rem' }}>
                              <strong>License:</strong>{' '}
                              {photos.attribution.license_url ? (
                                <a 
                                  href={photos.attribution.license_url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                >
                                  {photos.attribution.license}
                                </a>
                              ) : (
                                <span>{photos.attribution.license}</span>
                              )}
                              {photos.attribution.usage_terms && photos.attribution.usage_terms !== photos.attribution.license && (
                                <span style={{ marginLeft: '0.5rem', fontSize: '0.8125rem', color: '#64748b' }}>
                                  ({photos.attribution.usage_terms})
                                </span>
                              )}
                            </div>
                          )}
                          {photos.attribution.source_url && (
                            <div style={{ marginTop: '0.25rem' }}>
                              <strong>Source:</strong>{' '}
                              <a 
                                href={photos.attribution.source_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                              >
                                View Original
                              </a>
                            </div>
                          )}
                        </li>
                      )}
                      
                      {/* LEGACY: Wikimedia Commons thumbnail */}
                      {!photos?.attribution && selectedPlace.photos.wikimedia_commons?.thumbnail?.attribution && (
                        <li>
                          "{selectedPlace.photos.wikimedia_commons.thumbnail.attribution.title}" by{' '}
                          {selectedPlace.photos.wikimedia_commons.thumbnail.attribution.author}
                          {selectedPlace.photos.wikimedia_commons.thumbnail.attribution.license && (
                            <>
                              {' '}(
                              <a 
                                href={selectedPlace.photos.wikimedia_commons.thumbnail.attribution.license_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                              >
                                {selectedPlace.photos.wikimedia_commons.thumbnail.attribution.license}
                              </a>
                              )
                            </>
                          )}
                        </li>
                      )}
                      
                      {/* NEW STRUCTURE: Wikimedia Commons gallery */}
                      {selectedPlace.photos.wikimedia_commons?.gallery && 
                       selectedPlace.photos.wikimedia_commons.gallery.length > 0 && 
                       selectedPlace.photos.wikimedia_commons.gallery.map((photo, idx) => (
                        photo?.attribution && (
                          <li key={`wmc-${idx}`}>
                            "{photo.attribution.title}" by{' '}
                            {photo.attribution.author}
                            {photo.attribution.license && (
                              <>
                                {' '}(
                                <a 
                                  href={photo.attribution.license_url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                >
                                  {photo.attribution.license}
                                </a>
                                )
                              </>
                            )}
                          </li>
                        )
                      ))}
                      
                      {/* OLD STRUCTURE: Primary photo */}
                      {selectedPlace.photos.primary?.attribution && (
                        <li>
                          "{selectedPlace.photos.primary.title || 'Primary Photo'}" 
                          {selectedPlace.photos.primary.attribution.includes('by') 
                            ? ` ${selectedPlace.photos.primary.attribution}` 
                            : ` - ${selectedPlace.photos.primary.attribution}`}
                          {selectedPlace.photos.primary.license && ` (${selectedPlace.photos.primary.license})`}
                        </li>
                      )}
                      
                      {/* OLD STRUCTURE: Gallery photos */}
                      {selectedPlace.photos.gallery && 
                       selectedPlace.photos.gallery.length > 0 && 
                       selectedPlace.photos.gallery.map((photo, idx) => {
                         // Extract author from attribution string (e.g., "Wikimedia Commons - Frank Schulenburg")
                         const attributionParts = photo?.attribution?.split(' - ') || [];
                         const author = attributionParts.length > 1 ? attributionParts[attributionParts.length - 1] : photo?.attribution;
                         
                         return photo?.attribution && (
                           <li key={`gallery-${idx}`}>
                             "{photo.title || `Gallery Image ${idx + 1}`}" by {author}
                             {photo.license && (
                               <> (<a href="#" target="_blank" rel="noopener noreferrer">{photo.license}</a>)</>
                             )}
                           </li>
                         );
                       })}
                    </ul>
                  </details>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      <Footer />
    </div>
  );
};

export default PlacesExplorer;
