import React, { useEffect, useRef, memo } from 'react';
import { MapPin, Coffee, Utensils, Camera } from 'lucide-react';
import '../css/MapSection.css';

export default memo(function MapSection({
  location = 'Select a destination',
  markers = [],
  center = [20.5937, 78.9629], // Default to center of India
  zoom = 5,
  onMarkerClick,
  fitBounds = false, // When true, fit map to show all markers
}) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);

  useEffect(() => {
    // Check if Leaflet is loaded
    if (typeof window.L === 'undefined') {
      // Load Leaflet CSS
      const cssLink = document.createElement('link');
      cssLink.rel = 'stylesheet';
      cssLink.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(cssLink);
      
      // Load Leaflet JS
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload = () => initMap();
      document.head.appendChild(script);
    } else {
      initMap();
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update map center when center prop changes
  useEffect(() => {
    if (mapInstanceRef.current && center && center[0] && center[1] && !fitBounds) {
      // Use flyTo for smooth animated transition
      mapInstanceRef.current.flyTo(center, zoom, {
        duration: 1.5, // 1.5 seconds animation
        easeLinearity: 0.25,
      });
    }
  }, [center, zoom, fitBounds]);

  useEffect(() => {
    if (mapInstanceRef.current) {
      updateMarkers();
    }
  }, [markers, fitBounds]);

  const initMap = () => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const L = window.L;
    
    // Initialize map with smooth zoom options
    const map = L.map(mapRef.current, {
      center: center,
      zoom: zoom,
      zoomControl: false,
      zoomAnimation: true,
      zoomAnimationThreshold: 4,
      wheelPxPerZoomLevel: 360, // Much slower mouse wheel zoom (3x slower)
      wheelDebounceTime: 100,
      zoomDelta: 0.5, // Smaller zoom steps
      zoomSnap: 0.25, // Smoother zoom levels
    });

    // Add tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    // Add custom zoom control on bottom right
    L.control.zoom({
      position: 'bottomright',
    }).addTo(map);

    mapInstanceRef.current = map;
    updateMarkers();
  };

  const getMarkerColor = (type) => {
    switch (type) {
      case 'attraction':
        return '#4f46e5'; // indigo
      case 'restaurant':
        return '#f97316'; // orange
      case 'cafe':
        return '#8b5cf6'; // purple
      default:
        return '#4f46e5';
    }
  };

  const createCustomIcon = (type, name, order = null) => {
    const L = window.L;
    const color = getMarkerColor(type);
    
    // If order is provided, show a numbered marker for itinerary
    const pinContent = order !== null && order !== undefined
      ? `<span class="ms-marker-number">${order}</span>`
      : `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path>
          <circle cx="12" cy="10" r="3"></circle>
        </svg>`;
    
    return L.divIcon({
      className: 'ms-custom-marker',
      html: `
        <div class="ms-marker-wrapper">
          <div class="ms-marker-label">${name}</div>
          <div class="ms-marker-pin" style="background-color: ${color};">
            ${pinContent}
          </div>
        </div>
      `,
      iconSize: [100, 50],
      iconAnchor: [50, 50],
    });
  };

  const updateMarkers = () => {
    if (!mapInstanceRef.current || !window.L) return;

    const L = window.L;

    // Clear existing markers
    markersRef.current.forEach((marker) => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current = [];

    // Add new markers
    const bounds = [];
    markers.forEach((markerData) => {
      // Only add marker if it has valid coordinates
      if (markerData.lat && markerData.lng) {
        const icon = createCustomIcon(markerData.type, markerData.name, markerData.order);
        
        const marker = L.marker([markerData.lat, markerData.lng], { icon })
          .addTo(mapInstanceRef.current);
        
        bounds.push([markerData.lat, markerData.lng]);
        
        if (onMarkerClick) {
          marker.on('click', () => onMarkerClick(markerData));
        }

        markersRef.current.push(marker);
      }
    });
    
    // Fit bounds if requested and we have valid markers with coordinates
    if (fitBounds && bounds.length > 0) {
      try {
        const latLngBounds = L.latLngBounds(bounds);
        // Validate bounds before fitting
        if (latLngBounds.isValid && latLngBounds.isValid()) {
          mapInstanceRef.current.fitBounds(latLngBounds, {
            padding: [50, 50],
            maxZoom: 14,
            animate: true,
            duration: 0.5
          });
        }
      } catch (error) {
      }
    }
  };

  return (
    <div className="ms-container">
      <div className="ms-location-badge">
        <span className="ms-location-dot"></span>
        {location}
      </div>
      
      <div ref={mapRef} className="ms-map"></div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison to prevent unnecessary map re-renders
  const centerEqual = prevProps.center?.[0] === nextProps.center?.[0] &&
                      prevProps.center?.[1] === nextProps.center?.[1];
  return (
    prevProps.location === nextProps.location &&
    prevProps.markers === nextProps.markers &&
    centerEqual &&
    prevProps.zoom === nextProps.zoom &&
    prevProps.fitBounds === nextProps.fitBounds
  );
});
