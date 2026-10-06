// Purpose: Renders the Place Grid interface within apps\web\src\features\discover\jsx.
/**
 * PlaceGrid Component
 * 
 * Virtualized grid layout for city search - shows 4 cards per row.
 * Uses @tanstack/react-virtual for efficient rendering of large result sets.
 */

import React, { useRef, useMemo, useState, useEffect } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import PlaceCard from './PlaceCard';
import '../css/PlaceGrid.css';

// Breakpoint -> columns mapping
const getColumns = (width) => {
  if (width <= 640) return 1;
  if (width <= 900) return 2;
  if (width <= 1200) return 3;
  return 4;
};

const ROW_HEIGHT = 480; // Estimated card height + gap
const GAP = 40;

const PlaceGrid = ({
  places,
  onPlaceClick,
}) => {
  const parentRef = useRef(null);
  const [columns, setColumns] = useState(4);

  // Track container width for responsive columns
  useEffect(() => {
    if (!parentRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const width = entries[0].contentRect.width;
      setColumns(getColumns(width));
    });
    observer.observe(parentRef.current);
    return () => observer.disconnect();
  }, []);

  // Chunk places into rows
  const rows = useMemo(() => {
    if (!places || places.length === 0) return [];
    const result = [];
    for (let i = 0; i < places.length; i += columns) {
      result.push(places.slice(i, i + columns));
    }
    return result;
  }, [places, columns]);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 3,
  });

  if (!places || places.length === 0) {
    return null;
  }

  // For small lists (<=20 items), skip virtualization overhead
  if (places.length <= 20) {
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
  }

  return (
    <div
      ref={parentRef}
      className="ps-place-grid-virtual"
      style={{ maxHeight: '80vh', overflow: 'auto' }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            <div className="ps-place-grid">
              {rows[virtualRow.index].map((place, colIndex) => (
                <PlaceCard
                  key={place.id}
                  place={place}
                  onClick={() => onPlaceClick(place)}
                  animationDelay={`${(virtualRow.index * columns + colIndex) * 30}ms`}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PlaceGrid;
