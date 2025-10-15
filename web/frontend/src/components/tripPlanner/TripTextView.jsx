import React from 'react';

const TripTextView = ({ plan }) => {
  if (!plan) return null;

  const formatRating = (rating) => {
    return rating ? rating.toFixed(1) : '0.0';
  };

  const formatReviewCount = (count) => {
    return count ? count.toLocaleString() : '0';
  };

  const getPlaceType = (types) => {
    if (!types || types.length === 0) return 'Place';
    const type = types[0].replace(/_/g, ' ');
    return type.charAt(0).toUpperCase() + type.slice(1);
  };

  return (
    <div className="trip-text-view">
      {/* Airport Information */}
      {plan.airport && (
        <div className="text-view-section">
          <div className="text-view-line">
            <strong>Nearest Airport:</strong> {plan.airport.name} (~
            {plan.airport.distance_km.toFixed(1)} km from city center)
          </div>
        </div>
      )}

      {/* Main Title */}
      <div className="text-view-section">
        <div className="text-view-divider">======================================================================</div>
        <div className="text-view-title">   {plan.title}</div>
        <div className="text-view-divider">======================================================================</div>
      </div>

      {/* Daily Itinerary */}
      {plan.itinerary && plan.itinerary.map((day, dayIndex) => (
        <div key={dayIndex} className="text-view-day">
          <div className="text-view-day-header">
            --- Day {day.day}: {day.title} ---
          </div>
          
          {day.stops && day.stops.map((stop, stopIndex) => (
            <div key={stopIndex} className="text-view-stop">
              <div className="text-view-stop-arrival">
                [{stop.arrivalTime}] &gt;&gt; Arrive at: {stop.name}
              </div>
              <div className="text-view-stop-details">
                <div className="text-view-detail">  |-- Hours: {stop.hours}</div>
                <div className="text-view-detail">  |-- Visit: {stop.visitDuration}</div>
                {stop.website && (
                  <div className="text-view-detail">  |-- Web: {stop.website}</div>
                )}
                {stop.placeObj && stop.placeObj.rating && (
                  <div className="text-view-detail">
                    |-- Rating: {formatRating(stop.placeObj.rating)}/5.0 ({formatReviewCount(stop.placeObj.userRatingCount)} reviews)
                  </div>
                )}
                <div className="text-view-detail">  |</div>
              </div>
              
              {!stop.endOfDay && stop.travelToNext && (
                <div className="text-view-travel">
                  +-- Travel: ~{stop.travelToNext} minutes to next stop.
                </div>
              )}
              
              {stop.endOfDay && (
                <div className="text-view-end">  +-- End of day.</div>
              )}
            </div>
          ))}
          
          <div className="text-view-day-divider">
            ----------------------------------------------------------------------
          </div>
        </div>
      ))}

      {/* Other Top Places */}
      {plan.highRankedPlaces && plan.highRankedPlaces.length > 0 && (
        <div className="text-view-section">
          <div className="text-view-divider">======================================================================</div>
          <div className="text-view-title">   OTHER TOP PLACES YOU MAY VISIT</div>
          <div className="text-view-divider">======================================================================</div>
          <div className="text-view-list">
            {plan.highRankedPlaces.map((place, index) => (
              <div key={index} className="text-view-list-item">
                {index + 1}. {place.name}
                <span className="text-view-rating">
                  [{formatRating(place.rating)}/5.0] ({formatReviewCount(place.reviewCount)} reviews)
                </span>
              </div>
            ))}
          </div>
          <div style={{ height: '20px' }}></div>
        </div>
      )}

      {/* Special Time Suggestions */}
      {plan.specialPlaces && (
        <>
          {/* Early Morning */}
          {plan.specialPlaces.early_morning && plan.specialPlaces.early_morning.length > 0 && (
            <div className="text-view-section">
              <div className="text-view-divider">======================================================================</div>
              <div className="text-view-title">   EARLY MORNING SUGGESTIONS (Sunrise & More)</div>
              <div className="text-view-divider">======================================================================</div>
              <div className="text-view-list">
                {plan.specialPlaces.early_morning.map((place, index) => (
                  <div key={index} className="text-view-special-place">
                    <div className="text-view-special-name">
                      {index + 1}. {place.name}
                    </div>
                    <div className="text-view-special-details">
                       [{formatRating(place.rating)}/5.0] | {getPlaceType(place.types)}
                    </div>
                    {place.website && (
                      <div className="text-view-special-web">   Web: {place.website}</div>
                    )}
                    {index < plan.specialPlaces.early_morning.length - 1 && (
                      <div style={{ height: '10px' }}></div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Late Night */}
          {plan.specialPlaces.late_night && plan.specialPlaces.late_night.length > 0 && (
            <div className="text-view-section">
              <div className="text-view-divider">======================================================================</div>
              <div className="text-view-title">   LATE NIGHT SUGGESTIONS (Sunset & Night Views)</div>
              <div className="text-view-divider">======================================================================</div>
              <div className="text-view-list">
                {plan.specialPlaces.late_night.map((place, index) => (
                  <div key={index} className="text-view-special-place">
                    <div className="text-view-special-name">
                      {index + 1}. {place.name}
                    </div>
                    <div className="text-view-special-details">
                       [{formatRating(place.rating)}/5.0] | {getPlaceType(place.types)}
                    </div>
                    {place.website && (
                      <div className="text-view-special-web">   Web: {place.website}</div>
                    )}
                    {index < plan.specialPlaces.late_night.length - 1 && (
                      <div style={{ height: '10px' }}></div>
                    )}
                  </div>
                ))}
              </div>
              <div style={{ height: '20px' }}></div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default TripTextView;
