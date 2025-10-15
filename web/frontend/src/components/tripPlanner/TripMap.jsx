import React, { useEffect, useRef, useState } from 'react';

const TripMap = ({ plans }) => {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const [selectedPlanIndex, setSelectedPlanIndex] = useState(0);

  useEffect(() => {
    if (window.L && mapRef.current && !mapInstance.current) {
      mapInstance.current = window.L.map(mapRef.current).setView([32.8, -117.2], 10);
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(mapInstance.current);
    }

    if (mapInstance.current && plans.length > 0) {
      // Clear existing markers and lines
      mapInstance.current.eachLayer(layer => {
        if (layer instanceof window.L.Marker || layer instanceof window.L.Polyline || layer instanceof window.L.Circle) {
          mapInstance.current.removeLayer(layer);
        }
      });

      const dayColors = ['#4A90E2', '#50E3C2', '#F5A623'];
      const allCoords = [];
      
      // Only show the selected plan
      const plan = plans[selectedPlanIndex];
      
      // Add itinerary stops with numbered markers
      plan.itinerary.forEach(dayPlan => {
        const dayCoords = dayPlan.stops.filter(stop => stop.coords).map(stop => stop.coords);
        allCoords.push(...dayCoords);
        const color = dayColors[dayPlan.day - 1] || dayColors[0];

        dayPlan.stops.forEach((stop, stopIndex) => {
          if (!stop.coords) return;
          
          // Create pin-point marker icon (teardrop/pin style)
          const markerNumber = stopIndex + 1;
          const iconHtml = `
            <div style="position: relative; width: 40px; height: 50px;">
              <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
                <!-- Pin shadow -->
                <ellipse cx="20" cy="48" rx="6" ry="2" fill="rgba(0,0,0,0.2)"/>
                <!-- Pin shape -->
                <path d="M20 0 C11 0 4 7 4 15 C4 25 20 45 20 45 C20 45 36 25 36 15 C36 7 29 0 20 0 Z" 
                      fill="${color}" stroke="white" stroke-width="2"/>
                <!-- Number circle -->
                <circle cx="20" cy="15" r="10" fill="white"/>
                <text x="20" y="20" text-anchor="middle" font-size="12" font-weight="bold" fill="${color}">${markerNumber}</text>
              </svg>
            </div>
          `;
          const customIcon = window.L.divIcon({
            html: iconHtml,
            className: '',
            iconSize: [40, 50],
            iconAnchor: [20, 45],
            popupAnchor: [0, -45]
          });
          
          window.L.marker(stop.coords, { icon: customIcon })
            .addTo(mapInstance.current)
            .bindPopup(`<div style="min-width:150px;"><b>Day ${dayPlan.day} - Stop ${markerNumber}</b><br/><b>${stop.name}</b><br/>${stop.arrivalTime} | ${stop.hours}</div>`);
        });

        // Draw route lines for each day
        if (dayCoords.length > 1) {
          window.L.polyline(dayCoords, {
            color,
            weight: 4,
            opacity: 0.7,
            dashArray: '',
            lineJoin: 'round'
          }).addTo(mapInstance.current);
        }
      });

      // Add highRankedPlaces (Other Places) with different marker style
      if (plan.highRankedPlaces && plan.highRankedPlaces.length > 0) {
        plan.highRankedPlaces.forEach((place) => {
          // Only show places with coords
          if (place.coords && place.coords[0] && place.coords[1]) {
            allCoords.push(place.coords);
            
            const iconHtml = `
              <div style="position: relative; width: 32px; height: 40px;">
                <svg width="32" height="40" viewBox="0 0 32 40" xmlns="http://www.w3.org/2000/svg">
                  <!-- Pin shadow -->
                  <ellipse cx="16" cy="38" rx="5" ry="1.5" fill="rgba(0,0,0,0.2)"/>
                  <!-- Pin shape -->
                  <path d="M16 0 C9 0 3 6 3 13 C3 20 16 36 16 36 C16 36 29 20 29 13 C29 6 23 0 16 0 Z" 
                        fill="#9333ea" stroke="white" stroke-width="2"/>
                  <!-- Star icon -->
                  <text x="16" y="17" text-anchor="middle" font-size="14" fill="white">★</text>
                </svg>
              </div>
            `;
            const customIcon = window.L.divIcon({
              html: iconHtml,
              className: '',
              iconSize: [32, 40],
              iconAnchor: [16, 36],
              popupAnchor: [0, -36]
            });
            
            window.L.marker(place.coords, { icon: customIcon })
              .addTo(mapInstance.current)
              .bindPopup(`<div style="min-width:150px;"><b>★ Other Place</b><br/><b>${place.name}</b><br/>Rating: ${place.rating}/5.0</div>`);
          }
        });
      }

      // Fit map to show all markers
      if (allCoords.length > 0) {
        const bounds = window.L.latLngBounds(allCoords);
        mapInstance.current.fitBounds(bounds, { padding: [50, 50] });
      }
    }
  }, [plans, selectedPlanIndex]);

  return (
    <div style={{ position: 'relative' }}>
      {plans.length > 1 && (
        <div className="map-plan-toggle">
          {plans.map((plan, index) => (
            <button
              key={index}
              className={`map-toggle-btn ${selectedPlanIndex === index ? 'active' : ''}`}
              onClick={() => setSelectedPlanIndex(index)}
            >
              {index === 0 ? 'Plan 1' : 'Plan 2'}
            </button>
          ))}
        </div>
      )}
      <div ref={mapRef} className="trip-map"></div>
    </div>
  );
};

export default TripMap;
