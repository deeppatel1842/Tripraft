// Purpose: Renders the Grouped Place Grid interface within apps\web\src\features\discover\jsx.
/**
 * GroupedPlaceGrid Component
 * 
 * For state search: shows all cities with top 4 places each (4 in a row).
 * For country search: shows all states with top 4 places each (4 in a row).
 * Groups are virtualized for country-level searches with many states.
 */

import React, { useMemo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import PlaceCard from './PlaceCard';
import '../css/GroupedPlaceGrid.css';

const GROUP_HEIGHT = 540; // Estimated height per group (header + card row)

const GroupedPlaceGrid = ({
  places,
  groupBy, // 'city' or 'state'
  onPlaceClick,
}) => {
  const parentRef = useRef(null);

  // Group places by the specified field
  const groupEntries = useMemo(() => {
    if (!places || places.length === 0) return [];

    const groups = {};
    places.forEach(place => {
      const groupKey = groupBy === 'city' ? place.city_name : place.state_name;
      const key = groupKey || 'Other';
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(place);
    });

    // Sort group keys alphabetically; return as [name, places] entries
    return Object.keys(groups).sort().map(key => [key, groups[key]]);
  }, [places, groupBy]);

  const virtualizer = useVirtualizer({
    count: groupEntries.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => GROUP_HEIGHT,
    overscan: 2,
  });

  if (groupEntries.length === 0) {
    return null;
  }

  // For small group counts (<=8), render directly without virtualization
  if (groupEntries.length <= 8) {
    return (
      <div className="ps-grouped-grid">
        {groupEntries.map(([groupName, groupPlaces], groupIndex) => (
          <div key={groupName} className="ps-place-group">
            <div className="ps-group-header">
              <h2 className="ps-group-title">
                <i className={`fas ${groupBy === 'city' ? 'fa-city' : 'fa-map-marked-alt'}`}></i>
                {groupName}
              </h2>
            </div>
            <div className="ps-group-row">
              {groupPlaces.slice(0, 4).map((place, index) => (
                <PlaceCard
                  key={place.id}
                  place={place}
                  onClick={() => onPlaceClick(place)}
                  animationDelay={`${(groupIndex * 4 + index) * 30}ms`}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className="ps-grouped-grid-virtual"
      style={{ maxHeight: '80vh', overflow: 'auto' }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const [groupName, groupPlaces] = groupEntries[virtualItem.index];
          return (
            <div
              key={virtualItem.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              <div className="ps-place-group">
                <div className="ps-group-header">
                  <h2 className="ps-group-title">
                    <i className={`fas ${groupBy === 'city' ? 'fa-city' : 'fa-map-marked-alt'}`}></i>
                    {groupName}
                  </h2>
                </div>
                <div className="ps-group-row">
                  {groupPlaces.slice(0, 4).map((place, index) => (
                    <PlaceCard
                      key={place.id}
                      place={place}
                      onClick={() => onPlaceClick(place)}
                      animationDelay={`${(virtualItem.index * 4 + index) * 30}ms`}
                    />
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default GroupedPlaceGrid;
