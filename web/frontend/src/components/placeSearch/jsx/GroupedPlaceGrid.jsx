/**
 * GroupedPlaceGrid Component
 * 
 * For state search: shows all cities with top 5 places each (5 in a row).
 * For country search: shows all states with top 5 places each (5 in a row).
 */

import React, { useMemo } from 'react';
import PlaceCard from './PlaceCard';
import '../css/GroupedPlaceGrid.css';

const GroupedPlaceGrid = ({
  places,
  groupBy, // 'city' or 'state'
  onPlaceClick,
}) => {
  // Group places by the specified field
  const groupedPlaces = useMemo(() => {
    if (!places || places.length === 0) return {};

    const groups = {};
    places.forEach(place => {
      const groupKey = groupBy === 'city' ? place.city_name : place.state_name;
      const key = groupKey || 'Other';
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(place);
    });

    // Sort group keys alphabetically
    const sortedGroups = {};
    Object.keys(groups).sort().forEach(key => {
      sortedGroups[key] = groups[key];
    });

    return sortedGroups;
  }, [places, groupBy]);

  const groupNames = Object.keys(groupedPlaces);

  if (groupNames.length === 0) {
    return null;
  }

  return (
    <div className="ps-grouped-grid">
      {groupNames.map((groupName, groupIndex) => (
        <div key={groupName} className="ps-place-group">
          <div className="ps-group-header">
            <h2 className="ps-group-title">
              <i className={`fas ${groupBy === 'city' ? 'fa-city' : 'fa-map-marked-alt'}`}></i>
              {groupName}
            </h2>
            <span className="ps-group-count">
              {groupedPlaces[groupName].length} places
            </span>
          </div>
          <div className="ps-group-row">
            {groupedPlaces[groupName].slice(0, 5).map((place, index) => (
              <PlaceCard
                key={place.id}
                place={place}
                onClick={() => onPlaceClick(place)}
                animationDelay={`${(groupIndex * 5 + index) * 30}ms`}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default GroupedPlaceGrid;
