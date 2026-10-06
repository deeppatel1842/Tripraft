// Purpose: Renders the Place Detail Modal interface within apps\web\src\features\discover\jsx.
/**
 * PlaceDetailModal Component
 * 
 * Full detail view for a selected place.
 * Shows all place information including photos, hours, tips, etc.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { getPlaceDetails } from '../../../services/placeSearchService';
import placeholderSvg from '../../../assets/placeholder-place.svg';
import '../css/PlaceDetailModal.css';

const PlaceDetailModal = ({ place, onClose }) => {
  const [fullPlace, setFullPlace] = useState(place);
  const [shareError, setShareError] = useState('');
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
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

  // Fetch full place details (with all photos) when modal opens
  useEffect(() => {
    if (!place?.id) return;
    let cancelled = false;
    getPlaceDetails(place.id).then(data => {
      if (!cancelled && data) setFullPlace(data);
    }).catch(() => {}); // keep showing search-result data on failure
    return () => { cancelled = true; };
  }, [place?.id]);

  const photos = fullPlace.photos && fullPlace.photos.length > 0 ? fullPlace.photos : [];
  const hasGallery = photos.length > 1;

  const nextPhoto = () => setCurrentPhotoIndex(i => (i + 1) % photos.length);
  const prevPhoto = () => setCurrentPhotoIndex(i => (i - 1 + photos.length) % photos.length);

  const handleShare = async () => {
    const url = window.location.origin + '/places?q=' + encodeURIComponent(fullPlace.name || fullPlace.place_name || '');
    if (navigator.share) {
      try {
        await navigator.share({ title: fullPlace.name, url });
      } catch {}
    } else {
      try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(url);
        setShareError('');
      } catch { setShareError('The link could not be copied. Copy the page address to share it.'); }
    }
  };

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
    if (fullPlace.latitude && fullPlace.longitude) {
      return `https://www.google.com/maps/search/?api=1&query=${fullPlace.latitude},${fullPlace.longitude}`;
    }
    const searchQuery = encodeURIComponent(`${fullPlace.name || fullPlace.place_name}, ${fullPlace.city_name || ''}`);
    return `https://www.google.com/maps/search/?api=1&query=${searchQuery}`;
  };

  const costInfo = formatCost(fullPlace.cost);

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

        {/* Hero Image / Gallery */}
        <div className="modal-hero">
          <img
            src={
              hasGallery
                ? (photos[currentPhotoIndex]?.url || placeholderSvg)
                : (fullPlace.photo_url || fullPlace.thumbnail_url || placeholderSvg)
            }
            alt={hasGallery ? (photos[currentPhotoIndex]?.title || fullPlace.name) : fullPlace.name}
          />
          {hasGallery && (
            <>
              <button className="gallery-nav gallery-prev" onClick={prevPhoto} aria-label="Previous photo">
                <i className="fas fa-chevron-left"></i>
              </button>
              <button className="gallery-nav gallery-next" onClick={nextPhoto} aria-label="Next photo">
                <i className="fas fa-chevron-right"></i>
              </button>
              <div className="gallery-counter">
                {currentPhotoIndex + 1} / {photos.length}
              </div>
            </>
          )}
          <div className="modal-hero-overlay">
            <h1 className="modal-title">{fullPlace.name}</h1>
            <div className="modal-location">
              <i className="fas fa-map-marker-alt"></i>
              <span>
                {fullPlace.city_name}
                {fullPlace.state_name && `, ${fullPlace.state_name}`}
                {fullPlace.country_name && `, ${fullPlace.country_name}`}
              </span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="modal-content">
          {/* Quick Info Row */}
          <div className="modal-quick-info">
            {fullPlace.rating_tourist_priority && (
              <div className="info-item">
                <div className="stars">
                  {getRatingStars(fullPlace.rating_tourist_priority)}
                </div>
                <span className="label">Tourist Rating</span>
              </div>
            )}
            
            {fullPlace.cost && (
              <div className="info-item">
                <span className={`cost-badge ${costInfo.class}`}>
                  {costInfo.text}
                </span>
              </div>
            )}

            {fullPlace.suggested_duration && (
              <div className="info-item">
                <i className="fas fa-clock"></i>
                <span>{fullPlace.suggested_duration}</span>
              </div>
            )}

            {fullPlace.best_time_to_visit && (
              <div className="info-item">
                <i className="fas fa-calendar-alt"></i>
                <span>{fullPlace.best_time_to_visit}</span>
              </div>
            )}
          </div>

          {/* Description */}
          {fullPlace.ai_summary && (
            <section className="modal-section">
              <h2>About</h2>
              <p className="description">{fullPlace.ai_summary}</p>
            </section>
          )}

          {/* Features */}
          <section className="modal-section">
            <h2>Features</h2>
            <div className="features-grid">
              <div className={`feature ${fullPlace.sunrise_view ? 'active' : 'inactive'}`}>
                <i className="fas fa-sun"></i>
                <span>Sunrise View</span>
              </div>
              <div className={`feature ${fullPlace.sunset_view ? 'active' : 'inactive'}`}>
                <i className="fas fa-moon"></i>
                <span>Sunset View</span>
              </div>
              <div className={`feature ${fullPlace.advanced_booking === 'recommended' ? 'active' : 'inactive'}`}>
                <i className="fas fa-ticket-alt"></i>
                <span>Advance Booking</span>
              </div>
            </div>
          </section>

          {/* Tip */}
          {fullPlace.place_tip && (
            <section className="modal-section">
              <h2>Traveler Tip</h2>
              <div className="tip-box">
                <i className="fas fa-lightbulb"></i>
                <p>{fullPlace.place_tip}</p>
              </div>
            </section>
          )}

          {/* Opening Hours */}
          {fullPlace.opening_hours && (
            <section className="modal-section">
              <h2>Opening Hours</h2>
              <div className="hours-grid">
                {['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].map(day => (
                  fullPlace.opening_hours[day] && (
                    <div key={day} className="hour-item">
                      <span className="day">{day.charAt(0).toUpperCase() + day.slice(1)}</span>
                      <span className="time">{fullPlace.opening_hours[day]}</span>
                    </div>
                  )
                ))}
              </div>
            </section>
          )}

          {/* Tags */}
          {fullPlace.tags && fullPlace.tags.length > 0 && (
            <section className="modal-section">
              <h2>Tags</h2>
              <div className="tags-list">
                {fullPlace.tags.map((tag, index) => (
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
              {fullPlace.address && (
                <div className="info-row">
                  <i className="fas fa-map-marker-alt"></i>
                  <span>{fullPlace.address}</span>
                </div>
              )}
              {fullPlace.official_website && (
                <div className="info-row">
                  <i className="fas fa-globe"></i>
                  <a href={fullPlace.official_website} target="_blank" rel="noopener noreferrer">
                    Visit Website
                  </a>
                </div>
              )}
              {fullPlace.latitude && fullPlace.longitude && (
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
          <button className="btn-secondary" onClick={handleShare}>
            <i className="fas fa-share-alt"></i>
            Share
          </button>
          {shareError && <p role="alert">{shareError}</p>}
        </div>
      </div>
    </div>
  );
};

export default PlaceDetailModal;
