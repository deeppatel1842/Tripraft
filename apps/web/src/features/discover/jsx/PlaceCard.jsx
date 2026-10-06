// Purpose: Renders the Place Card interface within apps\web\src\features\discover\jsx.
/**
 * PlaceCard Component
 * 
 * Individual place card for display in grid.
 * Shows place image, name, location, rating, and tags.
 */

import React, { useState, memo, useRef, useEffect } from 'react';
import placeholderSvg from '../../../assets/placeholder-place.svg';
import '../css/PlaceCard.css';

const PlaceCard = memo(({ 
  place, 
  onClick, 
  animationDelay = '0ms' 
}) => {
  const [imageError, setImageError] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const cardRef = useRef(null);

  // Intersection Observer for true lazy loading
  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(el);
        }
      },
      { rootMargin: '200px' }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  /**
   * Handle image load error
   */
  const handleImageError = () => {
    setImageError(true);
    setImageLoaded(true);
  };

  /**
   * Handle image load success
   */
  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  const getPlaceholderImage = () => placeholderSvg;

  /**
   * Get display image URL
   */
  const getImageUrl = () => {
    if (place.photo_url) return place.photo_url;
    if (place.thumbnail_url) return place.thumbnail_url;
    return null;
  };

  /**
   * Truncate text to word limit
   */
  const truncateText = (text, wordLimit) => {
    if (!text) return '';
    const words = text.split(' ');
    if (words.length > wordLimit) {
      return words.slice(0, wordLimit).join(' ') + '...';
    }
    return text;
  };

  /**
   * Get rating display
   */
  const getRatingStars = (rating) => {
    if (!rating) return null;
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalf = rating % 1 >= 0.5;

    for (let i = 0; i < fullStars && i < 5; i++) {
      stars.push(<i key={i} className="fas fa-star"></i>);
    }
    if (hasHalf && stars.length < 5) {
      stars.push(<i key="half" className="fas fa-star-half-alt"></i>);
    }
    while (stars.length < 5) {
      stars.push(<i key={`empty-${stars.length}`} className="far fa-star"></i>);
    }

    return stars;
  };

  /**
   * Get cost indicator
   */
  const getCostIndicator = (cost) => {
    if (!cost) {
      return { text: 'Paid', class: 'cost-paid' };
    }
    const costLower = cost.toLowerCase();
    if (costLower === 'free') {
      return { text: 'Free', class: 'cost-free' };
    }
    // Any other value means paid
    return { text: 'Paid', class: 'cost-paid' };
  };

  /**
   * Get Google Maps URL
   */
  const getGoogleMapsUrl = () => {
    // Always use place name for better Google Maps search
    const placeName = place.name || place.place_name || '';
    const cityName = place.city_name || '';
    const stateName = place.state_name || '';
    const searchQuery = encodeURIComponent(`${placeName}, ${cityName}, ${stateName}`.trim());
    return `https://www.google.com/maps/search/?api=1&query=${searchQuery}`;
  };

  const imageUrl = getImageUrl();
  const description = truncateText(place.ai_summary || place.description || 'Discover this amazing destination.', 20);
  const costInfo = getCostIndicator(place.cost);
  const displayTags = (place.tags || []).slice(0, 3);

  return (
    <article
      ref={cardRef}
      className="place-card"
      style={{ animationDelay }}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
      {/* Image Section */}
      <div className="place-card-image">
        {!imageLoaded && (
          <div className="place-card-image-skeleton">
            <div className="skeleton-shimmer"></div>
          </div>
        )}
        <img
          src={!isVisible ? placeholderSvg : (imageError ? getPlaceholderImage() : (imageUrl || getPlaceholderImage()))}
          alt={place.name}
          onError={handleImageError}
          onLoad={handleImageLoad}
          className={imageLoaded ? 'loaded' : ''}
        />
        
        {/* Badges */}
        <div className="place-card-badges">
          {costInfo && (
            <span className={`badge ${costInfo.class}`}>
              {costInfo.text}
            </span>
          )}
          {place.sunrise_view && (
            <span className="badge badge-sunrise">
              <i className="fas fa-sun"></i>
            </span>
          )}
          {place.sunset_view && (
            <span className="badge badge-sunset">
              <i className="fas fa-moon"></i>
            </span>
          )}
        </div>

        {/* Hover preview overlay */}
        <div className="place-card-hover-overlay">
          {place.rating_tourist_priority && (
            <span><i className="fas fa-star"></i> {place.rating_tourist_priority.toFixed(1)}</span>
          )}
          {place.suggested_duration && (
            <span><i className="fas fa-clock"></i> {place.suggested_duration}</span>
          )}
          {costInfo && (
            <span><i className="fas fa-tag"></i> {costInfo.text}</span>
          )}
        </div>
      </div>

      {/* Content Section */}
      <div className="place-card-content">
        <h3 className="place-card-title">{place.name}</h3>

        {/* Location */}
        <div className="place-card-location">
          <i className="fas fa-map-marker-alt"></i>
          <span>
            {place.city_name}
            {place.state_name && `, ${place.state_name}`}
          </span>
        </div>

        {/* Rating */}
        {place.rating_tourist_priority && (
          <div className="place-card-rating">
            <div className="stars">
              {getRatingStars(place.rating_tourist_priority)}
            </div>
            <span className="rating-value">
              {place.rating_tourist_priority.toFixed(1)}
            </span>
          </div>
        )}

        {/* Description */}
        <p className="place-card-description">{description}</p>

        {/* Tags */}
        {displayTags.length > 0 && (
          <div className="place-card-tags">
            {displayTags.map((tag, index) => (
              <span key={index} className="tag">
                {tag.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="place-card-footer">
        <a 
          href={getGoogleMapsUrl()}
          target="_blank"
          rel="noopener noreferrer"
          className="maps-link"
          onClick={(e) => e.stopPropagation()}
        >
          <i className="fas fa-map-marked-alt"></i>
          <span>View on Maps</span>
        </a>
        <button className="explore-btn">
          <span>Explore</span>
          <i className="fas fa-arrow-right"></i>
        </button>
      </div>
    </article>
  );
});

PlaceCard.displayName = 'PlaceCard';

export default PlaceCard;
