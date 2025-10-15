import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import PlaceCard from './PlaceCard';
import '../css/PlacesExplorer.css';

const PlacesExplorer = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const sortDropdownRef = useRef(null);
  const distancePanelRef = useRef(null);
  
  const [places, setPlaces] = useState([]);
  const [filteredPlaces, setFilteredPlaces] = useState([]);
  const [cityQuery, setCityQuery] = useState(searchParams.get('city') || 'San Diego');
  const [loading, setLoading] = useState(false);
  const [filteringLoading, setFilteringLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cacheHit, setCacheHit] = useState(false);
  const [lastSearchedCity, setLastSearchedCity] = useState('');
  const [selectedPlace, setSelectedPlace] = useState(null);
  
  // Filter and Sort States
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'rank_score');
  const [distanceFilter, setDistanceFilter] = useState(parseInt(searchParams.get('distance')) || 120);
  
  // Dropdown states
  const [showSortDropdown, setShowSortDropdown] = useState(false);
  const [showDistancePanel, setShowDistancePanel] = useState(false);

  useEffect(() => {
    // Load initial data from URL if city is in params
    const cityParam = searchParams.get('city');
    if (cityParam) {
      fetchPlaces(cityParam);
    }
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (sortDropdownRef.current && !sortDropdownRef.current.contains(event.target)) {
        setShowSortDropdown(false);
      }
      if (distancePanelRef.current && !distancePanelRef.current.contains(event.target)) {
        setShowDistancePanel(false);
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
      if (distanceFilter !== 120) params.set('distance', distanceFilter.toString());
      setSearchParams(params);
    }
  }, [sortBy, distanceFilter, lastSearchedCity]);

  // Apply filters and sorting whenever places or filter options change
  // Apply filters and sorting whenever places or filter options change
  useEffect(() => {
    if (places.length > 0) {
      applyFiltersAndSort();
    }
  }, [places, sortBy, distanceFilter]);

  const applyFiltersAndSort = () => {
    // Show glass loading effect
    setFilteringLoading(true);
    
    setTimeout(() => {
      let filtered = [...places];

      // Filter by distance
      filtered = filtered.filter(place => {
        const distance = place.distance_to_query || 0;
        return distance <= distanceFilter;
      });

      // Sort by selected criteria
      filtered.sort((a, b) => {
        switch (sortBy) {
          case 'rating':
            return (b.rating || 0) - (a.rating || 0);
          case 'review_count':
            return (b.userRatingCount || 0) - (a.userRatingCount || 0);
          case 'rank_score':
          default:
            return (b.rank_score || 0) - (a.rank_score || 0);
        }
      });

      setFilteredPlaces(filtered);
      setFilteringLoading(false);
    }, 1000); // 1 second delay for glass effect
  };

  const getSortLabel = () => {
    switch(sortBy) {
      case 'rating': return 'Highest Rating';
      case 'review_count': return 'Most Reviews';
      default: return 'Trending';
    }
  };

  const fetchPlaces = async (city) => {
    if (!city || city.trim() === '') {
      setError('Please enter a city name');
      return;
    }

    setLoading(true);
    setError(null);
    setCacheHit(false);
    
    try {
      const response = await fetch(`http://localhost:5000/api/places/search?city=${encodeURIComponent(city)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch places');
      }

      const data = await response.json();
      
      setPlaces(data.places || []);
      setCacheHit(data.cache_hit || false);
      setLastSearchedCity(city);
    } catch (err) {
      console.error('Error fetching places:', err);
      setError(err.message);
      setPlaces([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCitySearch = (e) => {
    e.preventDefault();
    fetchPlaces(cityQuery);
  };

  const handlePlaceClick = (place) => {
    setSelectedPlace(place);
  };

  const closeModal = () => {
    setSelectedPlace(null);
  };

  const getMapUrl = (placeId) => {
    return `https://www.google.com/maps/search/?api=1&query=Google&query_place_id=${placeId}`;
  };

  return (
    <div className="places-explorer-page">
      <Header />
      
      <div className="places-explorer-container">
        <div className="places-hero">
          <h1>
            <i className="fas fa-map-marked-alt"></i>
            Places Explorer
          </h1>
          <p className="places-subtitle">
            Discover the best-rated destinations around the globe. Enter a city name to explore!
          </p>
          
          <form className="city-search-form" onSubmit={handleCitySearch}>
            <div className="search-input-container">
              <i className="fas fa-map-marker-alt search-icon"></i>
              <input
                type="text"
                value={cityQuery}
                onChange={(e) => setCityQuery(e.target.value)}
                placeholder="Enter city name"
                className="city-search-input"
              />
              <button type="submit" className="search-city-button" disabled={loading}>
                <i className="fas fa-search"></i>
                {loading ? 'Searching...' : 'Search City'}
              </button>
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
            {/* Filters and Sort Controls */}
            <div className="filters-section">
              <div className="filters-container">
                {/* Sort Button with Dropdown */}
                <div className="filter-button-wrapper" ref={sortDropdownRef}>
                  <button 
                    className="filter-button"
                    onClick={() => {
                      setShowSortDropdown(!showSortDropdown);
                      setShowDistancePanel(false);
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
                          <div className="option-title">Trending</div>
                          <div className="option-subtitle">Expert ranking algorithm</div>
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
                          <div className="option-subtitle">Top rated places</div>
                        </div>
                      </div>
                      <div 
                        className={`dropdown-option ${sortBy === 'review_count' ? 'active' : ''}`}
                        onClick={() => {
                          setSortBy('review_count');
                          setShowSortDropdown(false);
                        }}
                      >
                        <i className="fas fa-circle-dot"></i>
                        <div>
                          <div className="option-title">Most Reviews</div>
                          <div className="option-subtitle">Most popular destinations</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Distance Button with Panel */}
                <div className="filter-button-wrapper" ref={distancePanelRef}>
                  <button 
                    className="filter-button"
                    onClick={() => {
                      setShowDistancePanel(!showDistancePanel);
                      setShowSortDropdown(false);
                    }}
                  >
                    <i className="fas fa-map-marker-alt"></i>
                    Distance
                    <i className="fas fa-chevron-down"></i>
                  </button>
                  
                  {showDistancePanel && (
                    <div className="filter-panel">
                      <div className="panel-header">
                        <span>Distance Range</span>
                        <span className="distance-value">{distanceFilter === 120 ? 'All' : `${distanceFilter} km`}</span>
                      </div>
                      <input 
                        type="range" 
                        min="10" 
                        max="120" 
                        step="10"
                        value={distanceFilter} 
                        onChange={(e) => setDistanceFilter(Number(e.target.value))}
                        className="distance-slider"
                      />
                      <div className="slider-labels">
                        <span>10 km</span>
                        <span>120 km</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Clear Filters Button */}
                <button 
                  className="clear-filters-btn"
                  onClick={() => {
                    setSortBy('rank_score');
                    setDistanceFilter(120);
                    setShowSortDropdown(false);
                    setShowDistancePanel(false);
                  }}
                >
                  Clear filters
                </button>
              </div>
            </div>

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
                      animationDelay={`${(index % 4) * 0.1}s`}
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
                        animationDelay={`${(index % 4) * 0.1}s`}
                        onClick={() => handlePlaceClick(place)}
                        isExpertChoice={false}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {selectedPlace && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>
              <i className="fas fa-times"></i>
            </button>
            
            <div className="modal-header">
              <img 
                src={selectedPlace.thumbnailUrl || 'https://placehold.co/600x400/e2e8f0/4a5568?text=No+Image'} 
                alt={selectedPlace.displayName?.text}
                className="modal-image"
              />
              <div className="modal-title-section">
                <h2>{selectedPlace.displayName?.text}</h2>
                <div className="modal-rating-info">
                  <span className="modal-rating">
                    <i className="fas fa-star"></i> {selectedPlace.rating ? selectedPlace.rating.toFixed(1) : 'N/A'}
                  </span>
                  {selectedPlace.userRatingCount && (
                    <span className="modal-review-count">
                      ({selectedPlace.userRatingCount.toLocaleString()} reviews)
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="modal-body">
              {/* Generative Summary Section */}
              {selectedPlace.generativeSummary?.overview?.text && (
                <div className="modal-section">
                  <h3><i className="fas fa-info-circle"></i> About</h3>
                  <p className="modal-description">
                    {selectedPlace.generativeSummary.overview.text}
                  </p>
                </div>
              )}

              {/* Review Summary Section */}
              {selectedPlace.reviewSummary?.text?.text && (
                <div className="modal-section">
                  <h3><i className="fas fa-comments"></i> What People Say</h3>
                  <p className="modal-description review-summary">
                    {selectedPlace.reviewSummary.text.text}
                  </p>
                </div>
              )}

              {/* If neither summary exists */}
              {!selectedPlace.generativeSummary?.overview?.text && !selectedPlace.reviewSummary?.text?.text && (
                <div className="modal-section">
                  <h3><i className="fas fa-info-circle"></i> About</h3>
                  <p className="modal-description">
                    No description available for this place.
                  </p>
                </div>
              )}

              {selectedPlace.regularOpeningHours?.weekdayDescriptions && (
                <div className="modal-section">
                  <h3><i className="fas fa-clock"></i> Opening Hours</h3>
                  <ul className="opening-hours-list">
                    {selectedPlace.regularOpeningHours.weekdayDescriptions.map((day, idx) => (
                      <li key={idx}>{day}</li>
                    ))}
                  </ul>
                </div>
              )}

              {(selectedPlace.goodForChildren || selectedPlace.paymentOptions) && (
                <div className="modal-section">
                  <h3><i className="fas fa-check-circle"></i> Amenities</h3>
                  <div className="amenities-grid">
                    {selectedPlace.goodForChildren && (
                      <div className="amenity-tag">
                        <i className="fas fa-child"></i> Good for Children
                      </div>
                    )}
                    {selectedPlace.paymentOptions?.acceptsCreditCards && (
                      <div className="amenity-tag">
                        <i className="fas fa-credit-card"></i> Credit Cards
                      </div>
                    )}
                    {selectedPlace.paymentOptions?.acceptsDebitCards && (
                      <div className="amenity-tag">
                        <i className="fas fa-credit-card"></i> Debit Cards
                      </div>
                    )}
                    {selectedPlace.paymentOptions?.acceptsNfc && (
                      <div className="amenity-tag">
                        <i className="fas fa-mobile-alt"></i> NFC Payments
                      </div>
                    )}
                    {selectedPlace.paymentOptions?.acceptsCashOnly && (
                      <div className="amenity-tag">
                        <i className="fas fa-money-bill-wave"></i> Cash Only
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="modal-actions">
                {selectedPlace.websiteUri && (
                  <a 
                    href={selectedPlace.websiteUri} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="modal-button primary"
                  >
                    <i className="fas fa-globe"></i> Visit Website
                  </a>
                )}
                <a 
                  href={getMapUrl(selectedPlace.id)} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="modal-button secondary"
                >
                  <i className="fas fa-map-marker-alt"></i> View in Map
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

    

      <Footer />
    </div>
  );
};

export default PlacesExplorer;
