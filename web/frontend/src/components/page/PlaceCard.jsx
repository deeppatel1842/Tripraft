import React, { useState } from 'react';
import '../css/PlaceCard.css';

const PlaceCard = ({ place, animationDelay, onClick, isExpertChoice, rank }) => {
  const [imageError, setImageError] = useState(false);

  const generateStars = (rating) => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

    for (let i = 0; i < fullStars; i++) {
      stars.push(
        <svg key={`full-${i}`} className="star star-filled" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
        </svg>
      );
    }

    if (hasHalfStar) {
      stars.push(
        <svg key="half" className="star star-filled" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
        </svg>
      );
    }

    for (let i = 0; i < emptyStars; i++) {
      stars.push(
        <svg key={`empty-${i}`} className="star star-empty" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
        </svg>
      );
    }

    return stars;
  };

  const handleImageError = () => {
    setImageError(true);
  };

  const getPlaceholderImage = () => {
    return 'https://placehold.co/600x400/e2e8f0/4a5568?text=Image+Not+Available';
  };

  const getDescription = () => {
    return place.generativeSummary?.overview?.text || 
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
  const displayDescription = truncateText(description, 15);

  return (
    <div 
      className="place-card" 
      style={{ animationDelay }}
      onClick={onClick}
    >
      {isExpertChoice && (
        <div className="expert-badge">
          <i className="fas fa-crown"></i>
        </div>
      )}

      <div className="place-image-container">
        <img
          className="place-image"
          src={imageError ? getPlaceholderImage() : (place.thumbnailUrl || getPlaceholderImage())}
          alt={place.displayName?.text || 'Place'}
          onError={handleImageError}
        />
        <div className="place-rating-badge">
          <span className="rating-value">
            <i className="fas fa-star"></i> {place.rating ? place.rating.toFixed(1) : 'N/A'}
          </span>
        </div>
      </div>

      <div className="place-content">
        <h3 className="place-name">{place.displayName?.text || 'Unknown Place'}</h3>
        
        {place.userRatingCount && (
          <p className="place-review-count">
            <i className="fas fa-users"></i> {place.userRatingCount.toLocaleString()} reviews
          </p>
        )}
        
        <p className="place-description">
          {displayDescription}
        </p>
        
        <div className="place-stars">
          {generateStars(place.rating || 0)}
        </div>

        <div className="place-types">
          {(place.types || []).slice(0, 2).map((type, index) => (
            <span key={index} className="type-tag">
              {type.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </div>

      <div className="place-footer">
        <button className="view-details-button">
          <i className="fas fa-info-circle"></i> View Details
        </button>
      </div>
    </div>
  );
};

export default PlaceCard;
