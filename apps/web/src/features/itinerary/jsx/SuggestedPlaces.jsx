// Purpose: Renders the Suggested Places interface within apps\web\src\features\itinerary\jsx.
import React from 'react';
import Icon from './Icon';
import { placeRating } from '../../../utils/placeRating';

const SuggestedPlaces = ({ places, onAddPlace, specialPlaces }) => {
  const hasPlaces = places && places.length > 0;
  const hasSunrise = specialPlaces?.early_morning && specialPlaces.early_morning.length > 0;
  const hasSunset = specialPlaces?.late_night && specialPlaces.late_night.length > 0;
  
  if (!hasPlaces && !hasSunrise && !hasSunset) {
    return null;
  }

  return (
    <div className="suggested-places-sidebar no-scroll">
      {/* Other Places to Consider - FIRST */}
      {hasPlaces && (
        <div className="suggested-places-section">
          <h3 className="sidebar-title">
            <Icon name="sparkles" />
            <span>More Places to Explore</span>
          </h3>
          <p className="sidebar-hint">More places to consider for your trip</p>
          
          <div className="suggested-places-grid">
            {places.map((place, index) => (
              <div
                key={place.id || index}
                className="suggested-place-card"
              >
                {place.photo && (
                  <div className="place-photo-thumb">
                    <img src={place.photo} alt={place.name} loading="lazy" />
                  </div>
                )}
                <div className="place-info">
                  <h4 className="place-name">{place.name}</h4>
                  {place.rank_score && (
                    <div className="place-rating">
                      <span className="rating-stars">
                        {'★'.repeat(Math.round(placeRating(place)))}
                        {'☆'.repeat(5 - Math.round(place.rank_score * 5))}
                      </span>
                    </div>
                  )}
                  {place.tags && place.tags.length > 0 && (
                    <div className="place-tags-mini">
                      {place.tags.slice(0, 2).map((tag, i) => (
                        <span key={i} className="tag-mini">{tag}</span>
                      ))}
                    </div>
                  )}
                  {place.suggested_duration && (
                    <span className="place-duration">
                      <Icon name="clock" size="sm" />
                      {place.suggested_duration}
                    </span>
                  )}
                </div>
                {onAddPlace && <button
                  className="add-place-btn"
                  onClick={() => onAddPlace(place)}
                  title="Add to itinerary"
                >
                  <Icon name="plus" />
                </button>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Best for Sunset - SECOND */}
      {hasSunset && (
        <div className="special-places-section sunset-section">
          <h3 className="section-title sunset">
            <span className="title-icon">🌇</span>
            <span>Best for Sunset</span>
          </h3>
          <div className="special-places-row">
            {specialPlaces.late_night.slice(0, 3).map((place, index) => (
              <div key={index} className="special-place-card sunset">
                {place.photo && (
                  <div className="special-place-photo">
                    <img src={place.photo} alt={place.name} loading="lazy" />
                    <span className="time-badge sunset">{place.time || 'Evening'}</span>
                  </div>
                )}
                <div className="special-place-content">
                  <span className="special-place-name">{place.name}</span>
                  {place.tags && place.tags.length > 0 && (
                    <div className="special-place-tags">
                      {place.tags.slice(0, 2).map((tag, i) => (
                        <span key={i} className="tag-mini">{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  className="add-place-btn"
                  onClick={() => onAddPlace(place)}
                  title="Add to itinerary"
                >
                  <Icon name="plus" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Best for Sunrise - THIRD */}
      {hasSunrise && (
        <div className="special-places-section sunrise-section">
          <h3 className="section-title sunrise">
            <span className="title-icon">🌅</span>
            <span>Best for Sunrise</span>
          </h3>
          <div className="special-places-row">
            {specialPlaces.early_morning.slice(0, 3).map((place, index) => (
              <div key={index} className="special-place-card sunrise">
                {place.photo && (
                  <div className="special-place-photo">
                    <img src={place.photo} alt={place.name} loading="lazy" />
                    <span className="time-badge sunrise">{place.time || 'Early AM'}</span>
                  </div>
                )}
                <div className="special-place-content">
                  <span className="special-place-name">{place.name}</span>
                  {place.tags && place.tags.length > 0 && (
                    <div className="special-place-tags">
                      {place.tags.slice(0, 2).map((tag, i) => (
                        <span key={i} className="tag-mini">{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  className="add-place-btn"
                  onClick={() => onAddPlace(place)}
                  title="Add to itinerary"
                >
                  <Icon name="plus" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SuggestedPlaces;
