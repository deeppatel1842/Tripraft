import React, { useState, useEffect, useRef } from 'react';
import PlaceCard from './PlaceCard';
import './PlanTabContent.css';

// Mock suggested places - simplified
const SUGGESTED_PLACES = [
  { id: 'sp1', name: 'Shibuya Crossing', hint: 'Must see!' },
  { id: 'sp2', name: 'Tokyo Skytree', hint: 'Get tickets in advance.' },
  { id: 'sp3', name: 'Ghibli Museum', hint: 'Book ahead' },
  { id: 'sp4', name: 'Senso-ji Temple', hint: 'Historic site' },
  { id: 'sp5', name: 'Tsukiji Market', hint: 'Fresh seafood' },
];

// Demo place to show in Your Places
const DEMO_PLACE = {
  id: 'demo-1',
  name: 'Senso-ji Temple',
  votes: ['user-1'],
  remarks: 'Historic site in Tokyo, must visit at sunrise!',
};

export default function PlanTabContent({
  places = [],
  currentUserId = 'user-1',
  onAddPlace,
  onVotePlace,
  onDeletePlace,
  onUpdatePlaceRemark,
}) {
  const [newPlace, setNewPlace] = useState('');
  const [loading, setLoading] = useState(false);
  const mapRef = useRef(null);
  const mapInstance = useRef(null);

  // Combine demo place with passed places
  const allPlaces = Array.isArray(places) && places.length > 0 ? places : [DEMO_PLACE];

  // Store markers reference
  const markersRef = useRef([]);

  // Initialize Leaflet map
  useEffect(() => {
    // Dynamically load Leaflet
    const loadLeaflet = async () => {
      if (!mapRef.current) return;
      
      // Check if map already initialized
      if (mapInstance.current) {
        try {
          mapInstance.current.remove();
          mapInstance.current = null;
        } catch (e) {
          console.log('Map cleanup:', e);
        }
      }

      // Load Leaflet CSS
      if (!document.querySelector('link[href*="leaflet.min.css"]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
        document.head.appendChild(link);
      }

      // Load Leaflet JS
      if (!window.L) {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
        script.onload = () => {
          const L = window.L;
          if (L && mapRef.current && !mapInstance.current) {
            try {
              // Initialize map - centered on world view with reduced scroll sensitivity
              mapInstance.current = L.map(mapRef.current, {
                scrollWheelZoom: true,
                wheelDebounceTime: 100,
                wheelPxPerZoomLevel: 120
              }).setView([20, 0], 2);
              
              // Add OpenStreetMap DE tiles (better English names)
              L.tileLayer('https://tile.openstreetmap.de/{z}/{x}/{y}.png', {
                maxZoom: 18,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              }).addTo(mapInstance.current);
            } catch (e) {
              console.log('Map init error:', e);
            }
          }
        };
        document.body.appendChild(script);
      } else {
        // Leaflet already loaded, initialize map
        const L = window.L;
        if (L && mapRef.current && !mapInstance.current) {
          try {
            mapInstance.current = L.map(mapRef.current, {
              scrollWheelZoom: true,
              wheelDebounceTime: 100,
              wheelPxPerZoomLevel: 120
            }).setView([20, 0], 2);
            
            L.tileLayer('https://tile.openstreetmap.de/{z}/{x}/{y}.png', {
              maxZoom: 18,
              attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(mapInstance.current);
          } catch (e) {
            console.log('Map init error:', e);
          }
        }
      }
    };

    loadLeaflet();

    return () => {
      if (mapInstance.current) {
        try {
          mapInstance.current.remove();
          mapInstance.current = null;
        } catch (e) {
          console.log('Cleanup error:', e);
        }
      }
    };
  }, []);

  // Update map markers when places change
  useEffect(() => {
    if (!mapInstance.current || !window.L) {
      console.log('🗺️ Map not ready yet:', { map: !!mapInstance.current, leaflet: !!window.L });
      return;
    }

    console.log('🗺️ Adding markers for places:', allPlaces.length);

    // Clear existing markers
    markersRef.current.forEach(marker => {
      mapInstance.current.removeLayer(marker);
    });
    markersRef.current = [];

    // Geocode and add markers for each place
    const addPlaceMarkers = async () => {
      const validCoords = [];
      
      for (let i = 0; i < allPlaces.length; i++) {
        const place = allPlaces[i];
        console.log(`🔍 Geocoding place ${i + 1}/${allPlaces.length}: ${place.name}`);
        
        try {
          // Use Nominatim API to geocode place name (English names from OSM)
          const response = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(place.name)}&limit=1&accept-language=en`,
            {
              headers: {
                'User-Agent': 'TripPlanner/1.0'
              }
            }
          );
          
          const data = await response.json();
          console.log(`📍 Geocode result for "${place.name}":`, data);
          
          if (data && data.length > 0) {
            const lat = parseFloat(data[0].lat);
            const lon = parseFloat(data[0].lon);
            const displayName = data[0].display_name; // English name from OSM
            
            console.log(`✅ Adding marker at [${lat}, ${lon}] for "${place.name}"`);
            validCoords.push([lat, lon]);
            
            // Create custom pin marker icon
            const markerNumber = i + 1;
            const iconHtml = `
              <div style="position: relative; width: 40px; height: 50px;">
                <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
                  <ellipse cx="20" cy="48" rx="6" ry="2" fill="rgba(0,0,0,0.2)"/>
                  <path d="M20 0 C11 0 4 7 4 15 C4 25 20 45 20 45 C20 45 36 25 36 15 C36 7 29 0 20 0 Z" 
                        fill="#4f46e5" stroke="white" stroke-width="2"/>
                  <circle cx="20" cy="15" r="10" fill="white"/>
                  <text x="20" y="20" text-anchor="middle" font-size="12" font-weight="bold" fill="#4f46e5">${markerNumber}</text>
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
            
            const marker = window.L.marker([lat, lon], { icon: customIcon })
              .addTo(mapInstance.current)
              .bindPopup(`
                <div style="min-width:200px;">
                  <b style="font-size: 14px;">${place.name}</b><br/>
                  <span style="font-size: 12px; color: #666;">${displayName}</span><br/>
                  ${place.remarks ? `<p style="margin: 8px 0 0; font-size: 12px;">${place.remarks}</p>` : ''}
                  ${place.votes ? `<span style="font-size: 11px; color: #888;">👍 ${place.votes.length} vote${place.votes.length !== 1 ? 's' : ''}</span>` : ''}
                </div>
              `);
            
            markersRef.current.push(marker);
            console.log(`✅ Marker added successfully`);
          } else {
            console.log(`❌ No geocode results for "${place.name}"`);
          }
        } catch (error) {
          console.error(`❌ Error geocoding ${place.name}:`, error);
        }
        
        // Add delay between requests to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      
      console.log(`🗺️ Total markers added: ${markersRef.current.length}`);
      
      // Auto-focus map to show all markers with proper zoom
      if (validCoords.length > 0) {
        const bounds = window.L.latLngBounds(validCoords);
        
        // If single place, zoom to it directly
        if (validCoords.length === 1) {
          console.log(`🎯 Focusing on single place:`, validCoords[0]);
          mapInstance.current.setView(validCoords[0], 13);
        } else {
          // Multiple places - fit bounds with padding
          console.log(`🎯 Fitting bounds for ${validCoords.length} places`);
          mapInstance.current.fitBounds(bounds, { 
            padding: [80, 80],
            maxZoom: 15
          });
        }
      } else {
        console.log(`⚠️ No valid coordinates found for places`);
      }
    };

    addPlaceMarkers();
  }, [allPlaces]);

  const handleAddPlace = async () => {
    if (!newPlace.trim()) return;
    setLoading(true);
    try {
      await onAddPlace(newPlace);
      setNewPlace('');
      console.log('✅ [PLAN] Place added successfully:', newPlace);
    } catch (error) {
      if (error.message === 'DUPLICATE_PLACE') {
        alert('⚠️ This place is already in your list!');
        console.log('⚠️ [PLAN] Duplicate place:', newPlace);
      } else {
        console.error('❌ [PLAN] Error adding place:', error);
        alert('Failed to add place. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAddSuggestedPlace = (place) => {
    handleAddPlaceFromName(place.name);
  };

  const handleAddPlaceFromName = async (placeName) => {
    setLoading(true);
    try {
      await onAddPlace(placeName);
      console.log('✅ [PLAN] Suggested place added:', placeName);
    } catch (error) {
      if (error.message === 'DUPLICATE_PLACE') {
        alert(`⚠️ "${placeName}" is already in your list!`);
        console.log('⚠️ [PLAN] Duplicate suggested place:', placeName);
      } else {
        console.error('❌ [PLAN] Error adding suggested place:', error);
        alert('Failed to add place. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Generate OSM map URL for given location
  const getMapUrl = (lat = 35.6762, lng = 139.6503) => {
    // Using OpenStreetMap tiles
    return `https://tile.openstreetmap.org/{z}/{x}/{y}.png`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* FULL WIDTH LEAFLET MAP */}
      <div className="demo-card">
        <h3 style={{ margin: '0 0 12px' }}>Trip Map</h3>
        <div
          ref={mapRef}
          style={{
            height: '400px',
            borderRadius: '12px',
            border: '1px solid var(--gray-200)',
            overflow: 'hidden',
          }}
        />
      </div>

      {/* TWO COLUMN SECTION - Search + Suggestions */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* LEFT COLUMN - Add Places + Your Places */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Add Places Search */}
          <div className="demo-card">
            <h3 style={{ margin: '0 0 12px' }}>Add Places</h3>
            <div className="ptc-add-field">
              <input
                type="text"
                className="ptc-add-input"
                placeholder="Search for a city, landmark, or restaurant..."
                value={newPlace}
                onChange={(e) => setNewPlace(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddPlace()}
              />
              <button className="ptc-add-btn" onClick={handleAddPlace} disabled={loading}>
                {loading ? '⟳' : '✚'} Add
              </button>
            </div>
          </div>

          {/* Your Places List */}
          <div className="demo-card">
            <h3 style={{ margin: '0 0 12px' }}>Your Places</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {Array.isArray(allPlaces) && allPlaces.length > 0 ? (
                allPlaces.map((place) => (
                  <PlaceCard
                    key={place.id}
                    place={place}
                    currentUserId={currentUserId}
                    onVote={() => onVotePlace && onVotePlace(place.id)}
                    onDelete={() => onDeletePlace && onDeletePlace(place.id)}
                    onUpdateRemark={(remark) => onUpdatePlaceRemark && onUpdatePlaceRemark(place.id, remark)}
                  />
                ))
              ) : (
                <div style={{ textAlign: 'center', color: '#9ca3af', padding: '20px' }}>
                  No places added yet. Use search above or suggested places →
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN - Suggested Places */}
        <div className="demo-card">
          <h3 style={{ margin: '0 0 12px' }}>Suggested Places</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {SUGGESTED_PLACES.map((place) => (
              <div
                key={place.id}
                className="ptc-suggested-card"
              >
                <div className="ptc-suggested-info">
                  <div className="ptc-suggested-name">{place.name}</div>
                  <div className="ptc-suggested-hint">{place.hint}</div>
                </div>
                <button
                  className="ptc-suggested-btn"
                  onClick={() => handleAddSuggestedPlace(place)}
                >
                  ✚ Add
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
