// Purpose: Renders the Itinerary interface within apps\web\src\features\itinerary\jsx.
import React from 'react';
import ItineraryStop from './ItineraryStop';

const Itinerary = ({ itinerary = [] }) => {
  return (
    <div className="itinerary">
      {(Array.isArray(itinerary) ? itinerary : []).map((dayPlan) => (
        <div key={dayPlan.day} className="day-plan">
          <h3 className="day-title">
            Day {dayPlan.day}: {dayPlan.title}
          </h3>
          <ul className="stops-list">
            {dayPlan.stops.map((stop, stopIndex) => (
              <ItineraryStop
                key={stopIndex}
                stop={stop}
                isLast={stopIndex === dayPlan.stops.length - 1}
              />
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

export default Itinerary;
