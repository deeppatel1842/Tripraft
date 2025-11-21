import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import PlaceCard from './PlaceCard';
import placesService from '../../services/placesService';
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
  const [cityQuery, setCityQuery] = useState(searchParams.get('city') || 'Los Angeles');
  const [loading, setLoading] = useState(false);
  const [filteringLoading, setFilteringLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastSearchedCity, setLastSearchedCity] = useState('');
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [availableCities, setAvailableCities] = useState([]);
  
  // Filter and Sort States
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'rank_score');
  
  // Dropdown states
  const [showSortDropdown, setShowSortDropdown] = useState(false);

  useEffect(() => {
    // Load available cities on mount
    loadAvailableCities();
    
    // Load initial data from URL if city is in params
    const cityParam = searchParams.get('city');
    if (cityParam) {
      fetchPlacesByCity(cityParam);
    }
  }, []);

  const loadAvailableCities = async () => {
    try {
      // Load cities from USA (most populated in our database)
      const cities = await placesService.getCitiesByCountry('usa');
      setAvailableCities(cities);
    } catch (error) {
      console.error('Error loading cities:', error);
    }
  };

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
  }, [places, sortBy]);

  const getSortLabel = () => {
    switch(sortBy) {
      case 'rating': return 'Highest Rating';
      case 'name': return 'Alphabetical';
      default: return 'Best Rated';
    }
  };

  const fetchPlacesByCity = async (cityInput) => {
    if (!cityInput || cityInput.trim() === '') {
      setError('Please enter a city name');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      // Normalize city name to match our database IDs (lowercase, hyphenated)
      const cityId = cityInput.toLowerCase().replace(/\s+/g, '-');
      
      // Try to fetch places by city ID (limit to 20)
      const result = await placesService.getPlacesByCity(cityId, 20, 0);
      
      if (result.places && result.places.length > 0) {
        // Places are already transformed and filtered in the service
        setPlaces(result.places);
        setPagination(result.pagination);
        setLastSearchedCity(cityInput);
      } else {
        // If no results, try searching by name
        await searchPlacesByName(cityInput);
      }
    } catch (err) {
      console.error('Error fetching places:', err);
      // Try search as fallback
      await searchPlacesByName(cityInput);
    } finally {
      setLoading(false);
    }
  };

  const searchPlacesByName = async (query) => {
    try {
      const result = await placesService.searchPlaces(query, 20, 0);
      
      if (result.places && result.places.length > 0) {
        // Places are already transformed and filtered in the service
        setPlaces(result.places);
        setPagination(result.pagination);
        setLastSearchedCity(query);
      } else {
        setError(`No places found for "${query}". Try searching for a city like "Los Angeles", "New York", or "San Francisco".`);
        setPlaces([]);
      }
    } catch (err) {
      console.error('Error searching places:', err);
      setError(err.message || 'An error occurred while searching places');
      setPlaces([]);
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
            {/* Database Info Badge */}
            <div className="cache-status cache-hit">
              <i className="fas fa-database"></i>
              <span>Showing {pagination?.total || places.length} places from our curated database</span>
            </div>

            {/* Filters and Sort Controls */}
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
              </div>

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
                </div>
              </div>

              {/* Special Features */}
              {(selectedPlace.sunrise_view || selectedPlace.sunset_view) && (
                <div className="modal-section">
                  <h3><i className="fas fa-sun"></i> Special Features</h3>
                  <div className="special-features-grid">
                    {selectedPlace.sunrise_view && (
                      <div className="feature-tag sunrise">
                        <i className="fas fa-sunrise"></i> Sunrise View
                      </div>
                    )}
                    {selectedPlace.sunset_view && (
                      <div className="feature-tag sunset">
                        <i className="fas fa-sunset"></i> Sunset View
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Location & Actions */}
              <div className="modal-section modal-actions-section">
                <h3><i className="fas fa-map-pin"></i> Location & Links</h3>
                {selectedPlace.formattedAddress && (
                  <p className="modal-address">
                    <strong>Address:</strong> {selectedPlace.formattedAddress}
                  </p>
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
                </div>
              </div>

            </div>

            {/* Photo Attribution - Only show if we have real photos with URLs */}
            {(() => {
              const photos = selectedPlace.photos;
              
              // Check if we have any real photo URLs (non-empty strings)
              const hasRealPhotos = 
                (photos?.wikimedia_commons?.thumbnail?.url && photos.wikimedia_commons.thumbnail.url.trim() !== '') ||
                (photos?.wikimedia_commons?.gallery && Array.isArray(photos.wikimedia_commons.gallery) && 
                  photos.wikimedia_commons.gallery.some(img => img?.url && img.url.trim() !== '')) ||
                (photos?.primary?.url && photos.primary.url.trim() !== '') ||
                (photos?.gallery && Array.isArray(photos.gallery) && 
                  photos.gallery.some(img => img?.url && img.url.trim() !== ''));
              
              console.log('Has real photos for attribution:', hasRealPhotos);
              
              // Only show attribution if we have real photos
              if (!hasRealPhotos) {
                console.log('No real photos - hiding attribution');
                return null;
              }
              
              return (
                <div className="modal-section photo-attribution-section">
                  <details className="attribution-details" open>
                    <summary>
                      <i className="fas fa-camera"></i> Photo Attribution
                    </summary>
                    <ul className="attribution-list">
                      {/* NEW STRUCTURE: Wikimedia Commons thumbnail */}
                      {selectedPlace.photos.wikimedia_commons?.thumbnail?.attribution && (
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
