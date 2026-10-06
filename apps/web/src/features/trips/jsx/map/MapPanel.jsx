// Purpose: Renders the Map Panel interface within apps\web\src\features\trips\jsx\map.
import { validCoordinates } from '../../../../utils/coordinates';
import React, { useEffect, useRef } from 'react';
import useLeaflet from '../../hooks/useMapRenderer';
import { TILE_URL, DEFAULT_CENTER, DEFAULT_ZOOM, DAY_COLORS, MARKER_COLORS, MARKER_ICONS } from '../../constants/mapConfig';
import { getMarkerCategory, sanitizePopup } from '../../utils/groupPlannerUtils';
import { formatDate } from '../../utils/formatters';

/**
 * Leaflet map panel for the Group Planner right pane.
 *
 * Props:
 *   group           - group detail object (destination_lat, destination_lng)
 *   places          - all group places (itinerary + unscheduled)
 *   filteredLibrary - destination discovery items (for library tab)
 *   activeTab       - current tab key
 *   mapDay          - 'all' | day number string
 *   uniqueDates     - sorted array of visit_date strings
 *   dayNumbers      - array of day numbers [1,2,3...]
 *   onMapDayChange  - callback(dayStr)
 */
export default function MapPanel({
  group,
  places,
  filteredLibrary,
  activeTab,
  mapDay,
  uniqueDates,
  dayNumbers,
  onMapDayChange,
}) {
  const leafletReady = useLeaflet();
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  const itineraryPlaces = places.filter((p) => p.visit_date && !p.is_deleted);
  const unscheduledPlaces = places.filter((p) => !p.visit_date && !p.is_deleted);

  function getDayNumber(dateStr) {
    if (!dateStr) return 1;
    const idx = uniqueDates.indexOf(dateStr);
    if (idx >= 0) return idx + 1;
    const sorted = [...uniqueDates, dateStr].sort();
    return sorted.indexOf(dateStr) + 1;
  }

  // Initialize map
  useEffect(() => {
    if (!leafletReady || !mapRef.current) return;

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
      markersLayerRef.current = null;
    }

    if (!group) return;

    const L = window.L;
    const center = validCoordinates(group.destination_lat, group.destination_lng)
      ? [group.destination_lat, group.destination_lng]
      : DEFAULT_CENTER;

    const map = L.map(mapRef.current, {
      center,
      zoom: DEFAULT_ZOOM,
      zoomControl: false,
      attributionControl: false,
    });
    L.tileLayer(TILE_URL).addTo(map);
    const markersLayer = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;
    markersLayerRef.current = markersLayer;

    return () => {
      if (mapInstanceRef.current === map) {
        map.remove();
        mapInstanceRef.current = null;
        markersLayerRef.current = null;
      }
    };
  }, [leafletReady, group?.id]);

  // Re-center on destination change
  useEffect(() => {
    if (!mapInstanceRef.current || !group) return;
    if (validCoordinates(group.destination_lat, group.destination_lng)) {
      mapInstanceRef.current.setView([group.destination_lat, group.destination_lng], DEFAULT_ZOOM);
    }
  }, [group?.destination_lat, group?.destination_lng]);

  // Render markers
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current || !window.L) return;
    const L = window.L;
    markersLayerRef.current.clearLayers();
    const bounds = [];

    if (activeTab === 'library') {
      filteredLibrary.forEach((item) => {
        if (!validCoordinates(item.latitude, item.longitude)) return;
        const cat = item.category || 'PLACE';
        const color = MARKER_COLORS[cat] || MARKER_COLORS.PLACE;
        const iconHtml = MARKER_ICONS[cat] || MARKER_ICONS.PLACE;

        const icon = L.divIcon({
          className: 'custom-marker',
          html: '<div class="marker-pin-wrapper" style="background: ' + color + ';">' + iconHtml + '</div>',
          iconSize: [40, 40],
          iconAnchor: [20, 20],
        });

        const lat = parseFloat(item.latitude);
        const lng = parseFloat(item.longitude);
        L.marker([lat, lng], { icon })
          .addTo(markersLayerRef.current)
          .bindPopup(
            '<div style="padding:4px;font-weight:600;">' + sanitizePopup(item.name) + '</div>' +
            '<div style="font-size:11px;color:#71717a;">' + sanitizePopup(item.address) + '</div>'
          );
        bounds.push([lat, lng]);
      });

      if (bounds.length > 0) {
        mapInstanceRef.current.fitBounds(bounds, { padding: [80, 80], maxZoom: 14 });
      }
      return;
    }

    // Itinerary / other tabs
    let scheduledItems = itineraryPlaces.filter((p) => validCoordinates(p.latitude, p.longitude));
    if (mapDay !== 'all') {
      scheduledItems = scheduledItems.filter((p) => getDayNumber(p.visit_date) === parseInt(mapDay));
    }

    const byDay = {};

    scheduledItems.forEach((p) => {
      const cat = getMarkerCategory(p.category);
      const color = MARKER_COLORS[cat] || MARKER_COLORS.PLACE;
      const iconHtml = MARKER_ICONS[cat] || MARKER_ICONS.PLACE;
      const day = getDayNumber(p.visit_date);

      const icon = L.divIcon({
        className: 'custom-marker',
        html: '<div class="marker-pin-wrapper" style="background: ' + color + ';">' + iconHtml + '<div class="marker-day-badge">D' + day + '</div></div>',
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      });

      const lat = parseFloat(p.latitude);
      const lng = parseFloat(p.longitude);

      let popupHtml = '<div style="padding:4px;"><div style="font-weight:600;margin-bottom:4px;">' + sanitizePopup(p.name) + '</div>';
      popupHtml += '<div style="font-size:11px;color:#52525b;">Day ' + day;
      if (p.visit_date) popupHtml += ' &middot; ' + sanitizePopup(formatDate(p.visit_date));
      if (p.suggested_time) popupHtml += ' &middot; ' + sanitizePopup(p.suggested_time.slice(0, 5));
      popupHtml += '</div>';
      if (p.remarks) popupHtml += '<div style="font-size:11px;color:#71717a;margin-top:4px;font-style:italic;">' + sanitizePopup(p.remarks) + '</div>';
      popupHtml += '</div>';

      L.marker([lat, lng], { icon })
        .addTo(markersLayerRef.current)
        .bindPopup(popupHtml);
      bounds.push([lat, lng]);

      if (!byDay[day]) byDay[day] = [];
      byDay[day].push({ lat, lng, time: p.suggested_time || p.visit_date || '' });
    });

    // Always show unassigned places with icon-only markers (no day badge)
    unscheduledPlaces.forEach((p) => {
        if (!validCoordinates(p.latitude, p.longitude)) return;
        const cat = getMarkerCategory(p.category);
        const iconHtml = MARKER_ICONS[cat] || MARKER_ICONS.PLACE;

        const icon = L.divIcon({
          className: 'custom-marker',
          html: '<div class="marker-pin-wrapper" style="background: #a1a1aa; opacity: 0.75;">' + iconHtml + '</div>',
          iconSize: [34, 34],
          iconAnchor: [17, 17],
        });

        const lat = parseFloat(p.latitude);
        const lng = parseFloat(p.longitude);

        let popupHtml = '<div style="padding:4px;"><div style="font-weight:600;margin-bottom:2px;">' + sanitizePopup(p.name) + '</div>';
        popupHtml += '<div style="font-size:11px;color:#a1a1aa;">Unassigned</div>';
        if (p.remarks) popupHtml += '<div style="font-size:11px;color:#71717a;margin-top:4px;font-style:italic;">' + sanitizePopup(p.remarks) + '</div>';
        popupHtml += '</div>';

        L.marker([lat, lng], { icon })
          .addTo(markersLayerRef.current)
          .bindPopup(popupHtml);
        bounds.push([lat, lng]);
      });

    Object.keys(byDay).forEach((day) => {
      const stops = byDay[day].sort((a, b) => a.time.localeCompare(b.time));
      if (stops.length < 2) return;
      const latlngs = stops.map((s) => [s.lat, s.lng]);
      const lineColor = DAY_COLORS[(parseInt(day) - 1) % DAY_COLORS.length];
      L.polyline(latlngs, {
        color: lineColor,
        weight: 3,
        opacity: 0.7,
        dashArray: '8 6',
      }).addTo(markersLayerRef.current);
    });

    if (bounds.length > 0) {
      mapInstanceRef.current.fitBounds(bounds, { padding: [80, 80], maxZoom: 15 });
    }
  }, [itineraryPlaces, unscheduledPlaces, mapDay, group, activeTab, filteredLibrary]);

  return (
    <div className="gp-map-container">
      <div className="gp-map-day-selector">
        <button
          className={'gp-map-day-btn' + (mapDay === 'all' ? ' active' : '')}
          onClick={() => onMapDayChange('all')}
        >All</button>
        {dayNumbers.map((d) => (
          <button
            key={d}
            className={'gp-map-day-btn' + (mapDay === String(d) ? ' active' : '')}
            onClick={() => onMapDayChange(String(d))}
          >Day {d}</button>
        ))}
      </div>
      <div ref={mapRef} className="gp-leaflet-map" />
    </div>
  );
}
