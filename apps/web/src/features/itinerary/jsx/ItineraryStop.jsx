// Purpose: Renders the Itinerary Stop interface within apps\web\src\features\itinerary\jsx.
import React, { useState } from 'react';
import Icon from './Icon';

const ItineraryStop = ({ stop, isLast }) => {
  const [expanded, setExpanded] = useState(false);
  const placeData = stop.place_data || {};
  
  // Check if we have meaningful expanded content (handle empty strings)
  const hasExpandedContent = (placeData.description && placeData.description.trim()) || 
    (placeData.place_tip && placeData.place_tip.trim()) || 
    (placeData.best_time_to_visit && placeData.best_time_to_visit.trim()) || 
    placeData.photo || 
    (placeData.tags && placeData.tags.length > 0) ||
    placeData.sunrise_view || placeData.sunset_view ||
    (placeData.address && placeData.address.trim()) ||
    (placeData.website && placeData.website.trim());

  return (
    <li className="stop-item">
      <div className="stop-container">
        {!isLast && <span className="stop-connector" />}
        <div className="stop-content">
          <div className="stop-icon-wrapper">
            <span className="stop-icon">
              <Icon name={stop.icon || 'mapPin'} className={stop.color || 'text-purple-600'} />
            </span>
          </div>
          <div className="stop-details">
            <div className="stop-header">
              <div className="stop-title-row">
                <p className="stop-name">{stop.name}</p>
                {placeData.rating_tourist_priority && (
                  <span className="stop-priority-badge">
                    ★ {placeData.rating_tourist_priority}/5
                  </span>
                )}
              </div>
              <p className="stop-time">{stop.arrivalTime}</p>
            </div>
            
            <div className="stop-info">
              <div className="info-item">
                <Icon name="clock" />
                <span>Hours: {stop.hours}</span>
              </div>
              <div className="info-item">
                <Icon name="hourglass" />
                <span>Visit: {stop.visitDuration}</span>
                {stop.suggestedDuration && (
                  <span className="suggested-hint"> ({stop.suggestedDuration})</span>
                )}
              </div>
              
              {/* Cost info */}
              {placeData.cost && (
                <div className="info-item cost-info">
                  <Icon name="ticket" />
                  <span>{placeData.cost}</span>
                </div>
              )}
              
              {/* Booking requirement */}
              {placeData.advanced_booking && String(placeData.advanced_booking).toLowerCase().includes('recommend') && (
                <div className="info-item booking-alert">
                  <Icon name="calendar" />
                  <span>Booking: {placeData.advanced_booking}</span>
                </div>
              )}
              
              {stop.lunch && (
                <div className="info-item lunch-break">
                  <Icon name="utensils" />
                  <span>Lunch Break (~60 minutes)</span>
                </div>
              )}
              
              {stop.endOfDay && (
                <div className="info-item end-of-day">
                  <Icon name="moon" />
                  <span>End of day</span>
                </div>
              )}
            </div>
            
            {/* Expandable details - only show toggle if we have content */}
            {hasExpandedContent && (
              <>
                {expanded && (
                  <div className="stop-expanded-details">
                    {/* Photo */}
                    {placeData.photo && (
                      <div className="stop-photo">
                        <img src={placeData.photo} alt={stop.name} loading="lazy" />
                      </div>
                    )}
                    
                    {/* Description */}
                    {placeData.description && (
                      <p className="stop-description">{placeData.description}</p>
                    )}
                    
                    {/* Tip */}
                    {placeData.place_tip && (
                      <div className="stop-tip">
                        <strong>💡 Tip:</strong> {placeData.place_tip}
                      </div>
                    )}
                    
                    {/* Best time */}
                    {placeData.best_time_to_visit && (
                      <div className="stop-best-time">
                        <strong>🕐 Best time:</strong> {placeData.best_time_to_visit}
                      </div>
                    )}
                    
                    {/* Sunrise/Sunset */}
                    {(placeData.sunrise_view || placeData.sunset_view) && (
                      <div className="stop-views">
                        {placeData.sunrise_view && (
                          <span className="view-badge sunrise">🌅 {placeData.sunrise_time || 'Sunrise spot'}</span>
                        )}
                        {placeData.sunset_view && (
                          <span className="view-badge sunset">🌇 {placeData.sunset_time || 'Sunset spot'}</span>
                        )}
                      </div>
                    )}
                    
                    {/* Address */}
                    {placeData.address && (
                      <div className="stop-address">
                        <strong>📍</strong> {placeData.address}
                      </div>
                    )}
                    
                    {/* Tags */}
                    {placeData.tags && placeData.tags.length > 0 && (
                      <div className="stop-tags">
                        {placeData.tags.slice(0, 5).map((tag, i) => (
                          <span key={i} className="tag">{tag}</span>
                        ))}
                      </div>
                    )}
                    
                    {/* Website */}
                    {placeData.website && (
                      <a href={placeData.website} target="_blank" rel="noopener noreferrer" className="stop-website">
                        🔗 Official Website
                      </a>
                    )}
                  </div>
                )}
                
                {/* Expand toggle */}
                <button 
                  className="expand-toggle"
                  onClick={() => setExpanded(!expanded)}
                >
                  {expanded ? '▲ Less info' : '▼ More info'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </li>
  );
};

export default ItineraryStop;
