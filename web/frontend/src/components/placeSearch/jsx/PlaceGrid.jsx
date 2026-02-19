/**
 * PlaceGrid Component
 * 
 * Grid layout for city search - shows 4 cards per row.
 */

import React from 'react';
import PlaceCard from './PlaceCard';
import '../css/PlaceGrid.css';

const PlaceGrid = ({
  places,
  onPlaceClick,
}) => {
  if (!places || places.length === 0) {
    return null;
  }

  return (
    <div className="ps-place-grid">
      {places.map((place, index) => (
        <PlaceCard
          key={place.id}
          place={place}
          onClick={() => onPlaceClick(place)}
          animationDelay={`${index * 50}ms`}
        />
      ))}
    </div>
  );
};

export default PlaceGrid;
