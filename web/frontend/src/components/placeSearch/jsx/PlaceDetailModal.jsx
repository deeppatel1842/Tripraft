/**
 * PlaceDetailModal Component
 * 
 * Full detail view for a selected place.
 * Shows all place information including photos, hours, tips, etc.
 */

import React, { useEffect, useCallback } from 'react';
import '../css/PlaceDetailModal.css';

const PlaceDetailModal = ({ place, onClose }) => {
  /**
   * Handle escape key to close modal
   */
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  /**
   * Prevent body scroll when modal is open
   */
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  /**
   * Handle backdrop click
   */
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  /**
   * Get rating stars
   */
  const getRatingStars = (rating) => {
    if (!rating) return null;
    const stars = [];
    for (let i = 1; i <= 5; i++) {
      stars.push(
        <i
          key={i}
          className={i <= rating ? 'fas fa-star' : 'far fa-star'}
        ></i>
      );
    }
    return stars;
  };

  /**
   * Format cost display
   */
  const formatCost = (cost) => {
    if (!cost) {
      return { text: 'Paid', class: 'paid' };
    }
    if (cost.toLowerCase() === 'free') {
      return { text: 'Free Entry', class: 'free' };
    }
    return { text: 'Paid', class: 'paid' };
  };

  /**
   * Get Google Maps URL
   */
  const getGoogleMapsUrl = () => {
    if (place.latitude && place.longitude) {
      return `https://www.google.com/maps/search/?api=1&query=${place.latitude},${place.longitude}`;
    }
    const searchQuery = encodeURIComponent(`${place.name || place.place_name}, ${place.city_name || ''}`);
    return `https://www.google.com/maps/search/?api=1&query=${searchQuery}`;
  };

  const costInfo = formatCost(place.cost);

  return (
    <div className="place-modal-overlay" onClick={handleBackdropClick}>
      <div className="place-modal" role="dialog" aria-modal="true">
        {/* Close Button */}
        <button
          className="modal-close-btn"
          onClick={onClose}
          aria-label="Close modal"
        >
          <i className="fas fa-times"></i>
        </button>

        {/* Hero Image */}
        <div className="modal-hero">
          <img
            src={place.photo_url || place.thumbnail_url || 'https://placehold.co/1200x600/94a3b8/ffffff?text=No+Image'}
            alt={place.name}
          />
          <div className="modal-hero-overlay">
            <h1 className="modal-title">{place.name}</h1>
            <div className="modal-location">
              <i className="fas fa-map-marker-alt"></i>
              <span>
                {place.city_name}
                {place.state_name && `, ${place.state_name}`}
                {place.country_name && `, ${place.country_name}`}
              </span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="modal-content">
          {/* Quick Info Row */}
          <div className="modal-quick-info">
            {place.rating_tourist_priority && (
              <div className="info-item">
                <div className="stars">
                  {getRatingStars(place.rating_tourist_priority)}
                </div>
                <span className="label">Tourist Rating</span>
              </div>
            )}
            
            {place.cost && (
              <div className="info-item">
                <span className={`cost-badge ${costInfo.class}`}>
                  {costInfo.text}
                </span>
              </div>
            )}

            {place.suggested_duration && (
              <div className="info-item">
                <i className="fas fa-clock"></i>
                <span>{place.suggested_duration}</span>
              </div>
            )}

            {place.best_time_to_visit && (
              <div className="info-item">
                <i className="fas fa-calendar-alt"></i>
                <span>{place.best_time_to_visit}</span>
              </div>
            )}
          </div>

          {/* Description */}
          {place.ai_summary && (
            <section className="modal-section">
              <h2>About</h2>
              <p className="description">{place.ai_summary}</p>
            </section>
          )}

          {/* Features */}
          <section className="modal-section">
            <h2>Features</h2>
            <div className="features-grid">
              <div className={`feature ${place.sunrise_view ? 'active' : 'inactive'}`}>
                <i className="fas fa-sun"></i>
                <span>Sunrise View</span>
              </div>
              <div className={`feature ${place.sunset_view ? 'active' : 'inactive'}`}>
                <i className="fas fa-moon"></i>
                <span>Sunset View</span>
              </div>
              <div className={`feature ${place.advanced_booking === 'recommended' ? 'active' : 'inactive'}`}>
                <i className="fas fa-ticket-alt"></i>
                <span>Advance Booking</span>
              </div>
            </div>
          </section>

          {/* Tip */}
          {place.place_tip && (
            <section className="modal-section">
              <h2>Traveler Tip</h2>
              <div className="tip-box">
                <i className="fas fa-lightbulb"></i>
                <p>{place.place_tip}</p>
              </div>
            </section>
          )}

          {/* Opening Hours */}
          {place.opening_hours && (
            <section className="modal-section">
              <h2>Opening Hours</h2>
              <div className="hours-grid">
                {['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].map(day => (
                  place.opening_hours[day] && (
                    <div key={day} className="hour-item">
                      <span className="day">{day.charAt(0).toUpperCase() + day.slice(1)}</span>
                      <span className="time">{place.opening_hours[day]}</span>
                    </div>
                  )
                ))}
              </div>
            </section>
          )}

          {/* Tags */}
          {place.tags && place.tags.length > 0 && (
            <section className="modal-section">
              <h2>Tags</h2>
              <div className="tags-list">
                {place.tags.map((tag, index) => (
                  <span key={index} className="tag">
                    {tag.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Contact & Links */}
          <section className="modal-section">
            <h2>Information</h2>
            <div className="info-grid">
              {place.address && (
                <div className="info-row">
                  <i className="fas fa-map-marker-alt"></i>
                  <span>{place.address}</span>
                </div>
              )}
              {place.official_website && (
                <div className="info-row">
                  <i className="fas fa-globe"></i>
                  <a href={place.official_website} target="_blank" rel="noopener noreferrer">
                    Visit Website
                  </a>
                </div>
              )}
              {place.latitude && place.longitude && (
                <div className="info-row">
                  <i className="fas fa-location-arrow"></i>
                  <a 
                    href={getGoogleMapsUrl()}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View on Google Maps
                  </a>
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Footer Actions */}
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
          <button className="btn-primary">
            <i className="fas fa-plus"></i>
            Add to Trip
          </button>
        </div>
      </div>
    </div>
  );
};

export default PlaceDetailModal;
