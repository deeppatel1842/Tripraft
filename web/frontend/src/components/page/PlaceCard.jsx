import React, { useState, memo } from 'react';
import '../css/PlaceCard.css';

const PlaceCard = memo(({ place, animationDelay, onClick, isExpertChoice, rank }) => {
  const [imageError, setImageError] = useState(false);

  const handleImageError = () => {
    setImageError(true);
  };

  const getPlaceholderImage = () => {
    return 'https://placehold.co/600x400/e2e8f0/4a5568?text=Image+Not+Available';
  };

  const getDescription = () => {
    return place.summary || 
           place.generativeSummary?.text || 
           place.reviewSummary?.text?.text || 
           'No description available.';
  };

  const truncateText = (text, wordLimit) => {
    const words = text.split(' ');
    if (words.length > wordLimit) {
      return words.slice(0, wordLimit).join(' ') + '...';
    }
    return text;
  };

  const description = getDescription();
  const displayDescription = truncateText(description, 20);

  return (
    <div 
      className="place-card" 
      style={{ animationDelay }}
      onClick={onClick}
      role="region"
      aria-labelledby={`place-title-${place.id}`}
    >
      <div className="card-image-wrapper">
        <img
          className="card-image"
          src={imageError ? getPlaceholderImage() : (place.thumbnailUrl || getPlaceholderImage())}
          alt={place.displayName?.text || 'Place'}
          onError={handleImageError}
          loading="lazy"
          decoding="async"
        />
        {isExpertChoice && (
          <div className="card-badge crown" aria-label="Expert's top pick">
            <i className="fas fa-crown" aria-hidden="true"></i>
          </div>
        )}
      </div>

      <div className="card-content">
        <h3 id={`place-title-${place.id}`} className="card-title">
          {place.displayName?.text || place.name || 'Unknown Place'}
        </h3>
        
        {(place.city_name || place.state_name) && (
          <p className="card-location">
            <i className="fas fa-map-marker-alt" aria-hidden="true"></i>
            {place.city_name && place.state_name 
              ? `${place.city_name}, ${place.state_name}` 
              : place.city_name || place.state_name}
          </p>
        )}
        
        <p className="card-description">
          {displayDescription}
        </p>

        <div className="card-tags" aria-label="Tags">
          {(place.tags || place.types || []).slice(0, 3).map((tag, index) => (
            <span key={index} className="card-tag">
              {typeof tag === 'string' ? tag.replace(/_/g, ' ') : tag}
            </span>
          ))}
        </div>
      </div>

      <div className="card-footer">
        <button className="card-button" aria-haspopup="dialog">
          <i className="fas fa-info-circle" aria-hidden="true"></i>
          View Details
        </button>
      </div>
    </div>
  );
});

export default PlaceCard;
