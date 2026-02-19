import React, { useState, useMemo } from 'react';
import { Search, PlusCircle, MapPin, Utensils, Calendar, Music, Trophy, Theater, Loader } from 'lucide-react';
import '../css/PlacesSidebar.css';

// Default images for categories
const DEFAULT_IMAGES = {
  restaurant: 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=300&q=80',
  restaurants: 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=300&q=80',
  attraction: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=300&q=80',
  places: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=300&q=80',
  event: 'https://images.unsplash.com/photo-1540039155733-5bb30b53aa14?auto=format&fit=crop&w=300&q=80',
  default: 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=300&q=80',
};

// Get event type icon
const getEventIcon = (eventType) => {
  const type = (eventType || '').toLowerCase();
  if (type.includes('music') || type.includes('concert')) return <Music size={10} />;
  if (type.includes('sport')) return <Trophy size={10} />;
  if (type.includes('art') || type.includes('theatre') || type.includes('theater')) return <Theater size={10} />;
  return <Calendar size={10} />;
};

// Get appropriate image for a place
const getPlaceImage = (place) => {
  // If place has a valid image, use it
  if (place.image && place.image.startsWith('http')) {
    return place.image;
  }
  if (place.photo_url && place.photo_url.startsWith('http')) {
    return place.photo_url;
  }
  if (place.image_url && place.image_url.startsWith('http')) {
    return place.image_url;
  }
  
  // Return default based on category
  const category = (place.category || '').toLowerCase();
  return DEFAULT_IMAGES[category] || DEFAULT_IMAGES.default;
};

// Format event date/time for display
const formatEventDateTime = (date, time) => {
  if (!date) return '';
  try {
    const d = new Date(date);
    const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    if (time) {
      const [hours, minutes] = time.split(':');
      const h = parseInt(hours);
      const ampm = h >= 12 ? 'PM' : 'AM';
      const hour12 = h % 12 || 12;
      return `${dateStr} at ${hour12}:${minutes} ${ampm}`;
    }
    return dateStr;
  } catch {
    return date;
  }
};

export default function PlacesSidebar({
  places = [],
  events = [],
  isLoadingEvents = false,
  onAddPlace,
  activeFilter = 'all',
  onFilterChange,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [imageErrors, setImageErrors] = useState({});

  const filters = [
    { id: 'all', label: 'All' },
    { id: 'places', label: 'Places' },
    { id: 'restaurants', label: 'Restaurants' },
    { id: 'events', label: 'Events' },
  ];

  const handleFilterChange = (filterId) => {
    if (onFilterChange) onFilterChange(filterId);
  };

  const handleSearch = (e) => {
    setSearchQuery(e.target.value);
  };

  const handleImageError = (placeId, category) => {
    setImageErrors(prev => ({
      ...prev,
      [placeId]: DEFAULT_IMAGES[category] || DEFAULT_IMAGES.default
    }));
  };

  // Count places and restaurants (memoized)
  const placesCount = useMemo(() => places.filter(p => p.category === 'places' || p.category === 'attraction').length, [places]);
  const restaurantsCount = useMemo(() => places.filter(p => p.category === 'restaurant' || p.category === 'restaurants').length, [places]);

  // Get items to display based on active filter (memoized)
  const displayItems = useMemo(() => {
    let filtered = { places: [], restaurants: [], events: [] };

    if (activeFilter === 'all') {
      // All: show places, restaurants, and events
      filtered = {
        places: places.filter(p => (p.category === 'places' || p.category === 'attraction') && p.name.toLowerCase().includes(searchQuery.toLowerCase())),
        restaurants: places.filter(p => (p.category === 'restaurant' || p.category === 'restaurants') && p.name.toLowerCase().includes(searchQuery.toLowerCase())),
        events: events.filter(e => e.name.toLowerCase().includes(searchQuery.toLowerCase()) || (e.venue || '').toLowerCase().includes(searchQuery.toLowerCase()))
      };
    } else if (activeFilter === 'places') {
      // Places only
      filtered = {
        places: places.filter(p => (p.category === 'places' || p.category === 'attraction') && p.name.toLowerCase().includes(searchQuery.toLowerCase())),
        restaurants: [],
        events: []
      };
    } else if (activeFilter === 'restaurants') {
      // Restaurants only
      filtered = {
        places: [],
        restaurants: places.filter(p => (p.category === 'restaurant' || p.category === 'restaurants') && p.name.toLowerCase().includes(searchQuery.toLowerCase())),
        events: []
      };
    } else if (activeFilter === 'events') {
      // Events only
      filtered = {
        places: [],
        restaurants: [],
        events: events.filter(e => e.name.toLowerCase().includes(searchQuery.toLowerCase()) || (e.venue || '').toLowerCase().includes(searchQuery.toLowerCase()))
      };
    }

    return filtered;
  }, [places, events, searchQuery, activeFilter]);

  return (
    <aside className="ps-sidebar">
      <div className="ps-header">
        <div className="ps-search-wrapper">
          <Search className="ps-search-icon" />
          <input
            type="text"
            placeholder="Search places & events..."
            className="ps-search-input"
            value={searchQuery}
            onChange={handleSearch}
          />
        </div>

        <div className="ps-filters">
          {filters.map((filter) => (
            <button
              type="button"
              key={filter.id}
              className={`ps-filter-btn ${activeFilter === filter.id ? 'ps-filter-active' : ''}`}
              onClick={() => handleFilterChange(filter.id)}
            >
              {filter.label}
              {filter.id === 'places' && placesCount > 0 && (
                <span className="ps-filter-count">{placesCount}</span>
              )}
              {filter.id === 'restaurants' && restaurantsCount > 0 && (
                <span className="ps-filter-count">{restaurantsCount}</span>
              )}
              {filter.id === 'events' && events.length > 0 && (
                <span className="ps-filter-count">{events.length}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="ps-content">
        {/* Render based on active filter */}
        {displayItems.places.length > 0 && (
          <>
            <h3 className="ps-section-title">Places</h3>
            <div className="ps-places-list">
              {displayItems.places.map((place) => {
                const imageUrl = imageErrors[place.id] || getPlaceImage(place);
                return (
                  <div key={place.id} className="ps-place-card">
                    <div
                      className="ps-place-image"
                      style={{ backgroundImage: `url('${imageUrl}')` }}
                    >
                      <img 
                        src={imageUrl} 
                        alt="" 
                        style={{ display: 'none' }}
                        onError={() => handleImageError(place.id, place.category)}
                      />
                      <div className="ps-place-category-badge">
                        <MapPin size={10} />
                      </div>
                    </div>
                    <div className="ps-place-info">
                      <div className="ps-place-header">
                        <h4 className="ps-place-name">{place.name}</h4>
                        {place.rating && (
                          <span className="ps-place-rating">★ {Number(place.rating).toFixed(1)}</span>
                        )}
                      </div>
                      <p className="ps-place-description">
                        {place.description || 'Attraction'}
                      </p>
                      <button
                        className="ps-add-btn"
                        onClick={() => onAddPlace && onAddPlace(place)}
                      >
                        <PlusCircle className="ps-add-icon" />
                        Add to Itinerary
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {displayItems.restaurants.length > 0 && (
          <>
            <h3 className="ps-section-title">Restaurants</h3>
            <div className="ps-places-list">
              {displayItems.restaurants.map((place) => {
                const imageUrl = imageErrors[place.id] || getPlaceImage(place);
                return (
                  <div key={place.id} className="ps-place-card">
                    <div
                      className="ps-place-image"
                      style={{ backgroundImage: `url('${imageUrl}')` }}
                    >
                      <img 
                        src={imageUrl} 
                        alt="" 
                        style={{ display: 'none' }}
                        onError={() => handleImageError(place.id, place.category)}
                      />
                      <div className="ps-place-category-badge">
                        <Utensils size={10} />
                      </div>
                    </div>
                    <div className="ps-place-info">
                      <div className="ps-place-header">
                        <h4 className="ps-place-name">{place.name}</h4>
                        {place.rating && (
                          <span className="ps-place-rating">★ {Number(place.rating).toFixed(1)}</span>
                        )}
                      </div>
                      <p className="ps-place-description">
                        {place.description || 'Restaurant'}
                      </p>
                      <button
                        className="ps-add-btn"
                        onClick={() => onAddPlace && onAddPlace(place)}
                      >
                        <PlusCircle className="ps-add-icon" />
                        Add to Itinerary
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {displayItems.events.length > 0 && (
          <>
            <h3 className="ps-section-title">
              Events
              {isLoadingEvents && <Loader className="ps-loading-icon" size={14} />}
            </h3>
            <div className="ps-places-list">
              {displayItems.events.map((event) => {
                const imageUrl = imageErrors[event.id] || event.image_url || DEFAULT_IMAGES.event;
                return (
                  <div key={event.id} className="ps-place-card ps-event-card">
                    <div
                      className="ps-place-image"
                      style={{ backgroundImage: `url('${imageUrl}')` }}
                    >
                      <img 
                        src={imageUrl} 
                        alt="" 
                        style={{ display: 'none' }}
                        onError={() => handleImageError(event.id, 'event')}
                      />
                      <div className="ps-place-category-badge ps-event-badge">
                        {getEventIcon(event.event_type)}
                      </div>
                    </div>
                    <div className="ps-place-info">
                      <div className="ps-place-header">
                        <h4 className="ps-place-name">{event.name}</h4>
                        {event.event_type && (
                          <span className="ps-event-type">{event.event_type}</span>
                        )}
                      </div>
                      <p className="ps-event-datetime">
                        <Calendar size={12} />
                        {formatEventDateTime(event.date, event.time)}
                      </p>
                      {event.venue && (
                        <p className="ps-event-venue">
                          <MapPin size={12} />
                          {event.venue}
                        </p>
                      )}
                      {event.min_price && (
                        <p className="ps-event-price">
                          ${event.min_price}{event.max_price && ` - $${event.max_price}`}
                        </p>
                      )}
                      <button
                        className="ps-add-btn"
                        onClick={() => onAddPlace && onAddPlace({
                          ...event,
                          lat: event.latitude,
                          lng: event.longitude,
                          category: 'event'
                        })}
                      >
                        <PlusCircle className="ps-add-icon" />
                        Add to Itinerary
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* Empty state */}
        {displayItems.places.length === 0 && displayItems.restaurants.length === 0 && displayItems.events.length === 0 && (
          <div className="ps-empty">
            {places.length === 0 && events.length === 0
              ? 'Select a destination to see places' 
              : 'No items found matching your search'}
          </div>
        )}
      </div>
    </aside>
  );
}
