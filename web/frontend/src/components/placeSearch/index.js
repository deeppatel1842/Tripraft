/**
 * Place Search Components Index
 * 
 * Export all place search related components for easy import.
 * Connected to backend API for real data.
 */

// Main page component
export { default as PlaceSearchPage } from './jsx/PlaceSearchPage';

// Individual components
export { default as SearchBar } from './jsx/SearchBar';
export { default as PlaceGrid } from './jsx/PlaceGrid';
export { default as GroupedPlaceGrid } from './jsx/GroupedPlaceGrid';
export { default as PlaceCard } from './jsx/PlaceCard';
export { default as PlaceDetailModal } from './jsx/PlaceDetailModal';
export { default as SearchSuggestions } from './jsx/SearchSuggestions';

// API Service
export * from './placeSearchService';
