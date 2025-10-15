import React from 'react';
import Itinerary from './Itinerary';
import HighRankedPlaces from './HighRankedPlaces';

const TripPlanCard = ({ plan }) => {
  return (
    <div className="trip-plan-card">
      <h2 className="trip-plan-title">
        🗺️ {plan.title}
      </h2>
      
      {plan.airport && (
        <div className="airport-info">
          <i className="fas fa-plane-arrival"></i>
          <div className="airport-details">
            <strong>Nearest Airport:</strong> {plan.airport.name}
            <span className="airport-distance">
              (~{plan.airport.distance_km?.toFixed(1)} km from city center)
            </span>
          </div>
        </div>
      )}
      
      <div className="trip-plan-content">
        <Itinerary itinerary={plan.itinerary} />
      </div>
      <div className="trip-plan-footer">
        <HighRankedPlaces places={plan.highRankedPlaces} />
        
        {/* Early Morning Suggestions */}
        {plan.specialPlaces?.early_morning && plan.specialPlaces.early_morning.length > 0 && (
          <div className="special-places-section">
            <h4 className="special-places-title">🌅 Early Morning Suggestions</h4>
            <div className="special-places-list">
              {plan.specialPlaces.early_morning.slice(0, 3).map((place, index) => (
                <div key={index} className="special-place-item">
                  <span className="special-place-name">{place.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Late Night Suggestions */}
        {plan.specialPlaces?.late_night && plan.specialPlaces.late_night.length > 0 && (
          <div className="special-places-section">
            <h4 className="special-places-title">🌙 Late Night Suggestions</h4>
            <div className="special-places-list">
              {plan.specialPlaces.late_night.slice(0, 3).map((place, index) => (
                <div key={index} className="special-place-item">
                  <span className="special-place-name">{place.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <button className="choose-plan-btn">
        Choose This Plan
      </button>
    </div>
  );
};

export default TripPlanCard;
