/**
 * React Hook for TOS-Compliant Session Cache
 * 
 * Provides easy-to-use session caching for Google Places data.
 * Automatically clears on logout and tab close.
 */

import { useEffect, useRef, useCallback } from 'react';
import TripRaftSessionCache from '../utils/sessionCache';

/**
 * Custom hook for session-based place caching
 * 
 * @param {number} ttlMinutes - Time to live in minutes (default: 15)
 * @returns {object} Cache methods
 */
export function useSessionCache(ttlMinutes = 15) {
    const cacheRef = useRef(null);
    
    // Initialize cache on mount
    useEffect(() => {
        if (!cacheRef.current) {
            cacheRef.current = new TripRaftSessionCache(ttlMinutes);
        }
        
        // Cleanup expired entries periodically
        const interval = setInterval(() => {
            if (cacheRef.current) {
                cacheRef.current.cleanupExpired();
            }
        }, 60000); // Every minute
        
        return () => clearInterval(interval);
    }, [ttlMinutes]);
    
    // Get places from cache
    const getCachedPlaces = useCallback((city, radiusKm, travelMode = 'DRIVE') => {
        if (!cacheRef.current) return null;
        return cacheRef.current.get(city, radiusKm, travelMode);
    }, []);
    
    // Store places in cache
    const cachePlaces = useCallback((city, radiusKm, places, travelMode = 'DRIVE') => {
        if (!cacheRef.current) return false;
        return cacheRef.current.set(city, radiusKm, places, travelMode);
    }, []);
    
    // Clear cache (e.g., on logout)
    const clearCache = useCallback(() => {
        if (!cacheRef.current) return 0;
        return cacheRef.current.clearOnLogout();
    }, []);
    
    // Get cache statistics
    const getCacheStats = useCallback(() => {
        if (!cacheRef.current) return null;
        return cacheRef.current.getStats();
    }, []);
    
    // Check if cached
    const hasCache = useCallback((city, radiusKm, travelMode = 'DRIVE') => {
        if (!cacheRef.current) return false;
        return cacheRef.current.has(city, radiusKm, travelMode);
    }, []);
    
    return {
        getCachedPlaces,
        cachePlaces,
        clearCache,
        getCacheStats,
        hasCache
    };
}

/**
 * Example Usage in React Component:
 * 
 * function PlaceSearch() {
 *     const { getCachedPlaces, cachePlaces, clearCache } = useSessionCache(15);
 *     const [places, setPlaces] = useState([]);
 *     const [loading, setLoading] = useState(false);
 *     
 *     const searchPlaces = async (city, radius) => {
 *         // Check cache first
 *         const cached = getCachedPlaces(city, radius);
 *         if (cached) {
 *             console.log('Using cached places');
 *             setPlaces(cached);
 *             return;
 *         }
 *         
 *         // Fetch from API
 *         setLoading(true);
 *         try {
 *             const response = await fetch(`/api/search?city=${city}&radius=${radius}`);
 *             const data = await response.json();
 *             
 *             // Cache the results
 *             cachePlaces(city, radius, data.places);
 *             setPlaces(data.places);
 *         } catch (error) {
 *             console.error('Search failed:', error);
 *         } finally {
 *             setLoading(false);
 *         }
 *     };
 *     
 *     const handleLogout = () => {
 *         clearCache();
 *         // ... rest of logout logic
 *     };
 *     
 *     return (
 *         // ... component JSX
 *     );
 * }
 */

export default useSessionCache;
