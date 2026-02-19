import React from 'react';
import Itinerary from './Itinerary';
import SuggestedPlaces from './SuggestedPlaces';

const TripPlanCard = ({ plan }) => {
  // Handler for when user wants to add a place (placeholder for future functionality)
  const handleAddPlace = (place) => {
    // Future: Add the place to the itinerary
  };

  return (
    <div className="trip-plan-card-container">
      {/* Main Plan Card */}
      <div className="trip-plan-card">
        <h2 className="trip-plan-title">
          🗺️ {plan.title}
        </h2>
        
        {/* City & Airport Info */}
        <div className="trip-meta-info">
          {plan.city && (
            <div className="city-info">
              <i className="fas fa-map-marker-alt"></i>
              <span>{plan.city.name}, {plan.city.country}</span>
            </div>
          )}
          
          {plan.airport && plan.airport.name && (
            <div className="airport-info">
              <i className="fas fa-plane"></i>
              <div className="airport-details">
                <span className="airport-name">
                  {plan.airport.name}
                  {plan.airport.iata && <span className="airport-code"> ({plan.airport.iata})</span>}
                </span>
              </div>
            </div>
          )}
          
          {plan.pacing && (
            <div className="pacing-info">
              <i className="fas fa-tachometer-alt"></i>
              <span>Pacing: {plan.pacing}</span>
            </div>
          )}
        </div>
        
        <div className="trip-plan-content">
          <Itinerary itinerary={plan.itinerary} />
        </div>
      </div>
      
      {/* Suggested Places Sidebar - Right Side with all suggestions */}
      {(plan.highRankedPlaces?.length > 0 || 
        plan.specialPlaces?.early_morning?.length > 0 || 
        plan.specialPlaces?.late_night?.length > 0) && (
        <SuggestedPlaces 
          places={plan.highRankedPlaces} 
          specialPlaces={plan.specialPlaces}
          onAddPlace={handleAddPlace}
        />
      )}
    </div>
  );
};

export default TripPlanCard;
