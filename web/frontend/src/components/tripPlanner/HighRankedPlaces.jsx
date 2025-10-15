import React from 'react';

const HighRankedPlaces = ({ places }) => {
  return (
    <div className="high-ranked-places">
      <h4 className="places-title">
        🤔 Other Places to Consider
      </h4>
      <div className="places-list">
        {places.map((place, index) => (
          <div key={index} className="place-item">
            <p className="place-name">{place.name}</p>
            <div className="place-rating">
              <div className="rating-stars">
                <i className="fas fa-star"></i>
                <span className="rating-value">{place.rating}</span>
              </div>
              <span className="review-count">
                ({place.reviewCount.toLocaleString()})
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HighRankedPlaces;
