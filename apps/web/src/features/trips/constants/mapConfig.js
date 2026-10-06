// Purpose: Provides map Config logic and exports for apps\web\src\features\trips\constants.
/**
 * Map configuration constants for the Group Planner.
 * Leaflet CDN, marker icons, day colors, tile layer URL.
 */

export const LEAFLET_CSS_URL = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
export const LEAFLET_JS_URL = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';

export const TILE_URL = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

export const DEFAULT_CENTER = [20, 0];
export const DEFAULT_ZOOM = 2;

export const DAY_COLORS = [
  '#4f46e5', '#ea580c', '#0891b2', '#16a34a',
  '#9333ea', '#dc2626', '#ca8a04', '#0d9488',
];

export const MARKER_COLORS = {
  PLACE: '#4f46e5',
  RES: '#ea580c',
  EVENT: '#0891b2',
  attraction: '#4f46e5',
  restaurant: '#ea580c',
  event: '#0891b2',
};

export const MARKER_ICONS = {
  PLACE: '<svg class="marker-icon-svg" viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"/></svg>',
  RES: '<svg class="marker-icon-svg" viewBox="0 0 24 24"><path d="M11 9H9V2H7v7H5V2H3v7c0 2.12 1.66 3.84 3.75 3.97V22h2.5v-9.03C11.34 12.84 13 11.12 13 9V2h-2v7zm5-3v8h2.5v8H21V2c-2.76 0-5 2.24-5 4z"/></svg>',
  EVENT: '<svg class="marker-icon-svg" viewBox="0 0 24 24"><path d="M22 10V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v4c1.1 0 2 .9 2 2s-.9 2-2 2v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4c-1.1 0-2-.9-2-2s.9-2 2-2z"/></svg>',
};
