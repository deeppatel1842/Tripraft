/**
 * TripRaft Session Cache - Client-Side
 * 
 * TOS-compliant session storage for Google Places data.
 * Data is stored in browser sessionStorage and cleared when:
 * - User closes the browser tab
 * - User logs out
 * - Session expires (15-30 minutes)
 * 
 * This ensures full TOS compliance with Google Maps Platform Terms.
 */

class TripRaftSessionCache {
    constructor(ttlMinutes = 15) {
        this.storage = window.sessionStorage;
        this.ttlMs = ttlMinutes * 60 * 1000;
        this.prefix = 'tripraft_places_';
        
        console.log('✅ TripRaft Session Cache initialized (TTL: ' + ttlMinutes + ' min)');
        
        // Cleanup expired entries on initialization
        this.cleanupExpired();
    }
    
    /**
     * Generate cache key from search parameters
     */
    generateKey(city, radiusKm, travelMode = 'DRIVE') {
        const normalized = `${city}_${radiusKm}_${travelMode}`.toLowerCase();
        return this.prefix + normalized;
    }
    
    /**
     * Store place data in session
     */
    set(city, radiusKm, places, travelMode = 'DRIVE') {
        const cacheKey = this.generateKey(city, radiusKm, travelMode);
        const expiresAt = Date.now() + this.ttlMs;
        
        const entry = {
            data: places,
            storedAt: Date.now(),
            expiresAt: expiresAt,
            city: city,
            radiusKm: radiusKm,
            travelMode: travelMode,
            count: places.length
        };
        
        try {
            this.storage.setItem(cacheKey, JSON.stringify(entry));
            console.log(`💾 Session cached: ${city} (${places.length} places)`);
            return true;
        } catch (error) {
            console.error('❌ Session cache storage failed:', error);
            return false;
        }
    }
    
    /**
     * Get place data from session if not expired
     */
    get(city, radiusKm, travelMode = 'DRIVE') {
        const cacheKey = this.generateKey(city, radiusKm, travelMode);
        
        try {
            const item = this.storage.getItem(cacheKey);
            if (!item) {
                console.log(`❌ Session cache MISS: ${city}`);
                return null;
            }
            
            const entry = JSON.parse(item);
            
            // Check expiration
            if (Date.now() > entry.expiresAt) {
                this.storage.removeItem(cacheKey);
                console.log(`⏰ Session cache EXPIRED: ${city}`);
                return null;
            }
            
            const ageSeconds = Math.floor((Date.now() - entry.storedAt) / 1000);
            const remainingSeconds = Math.floor((entry.expiresAt - Date.now()) / 1000);
            
            console.log(`✅ Session cache HIT: ${city} (${entry.count} places, age: ${ageSeconds}s, remaining: ${remainingSeconds}s)`);
            
            return entry.data;
            
        } catch (error) {
            console.error('❌ Session cache read failed:', error);
            return null;
        }
    }
    
    /**
     * Clear all TripRaft cache entries
     */
    clear() {
        try {
            const keys = Object.keys(this.storage);
            const tripraftKeys = keys.filter(key => key.startsWith(this.prefix));
            
            tripraftKeys.forEach(key => {
                this.storage.removeItem(key);
            });
            
            console.log(`🗑️ Cleared ${tripraftKeys.length} session cache entries`);
            return tripraftKeys.length;
        } catch (error) {
            console.error('❌ Session cache clear failed:', error);
            return 0;
        }
    }
    
    /**
     * Clear cache on logout (call this when user logs out)
     */
    clearOnLogout() {
        const cleared = this.clear();
        console.log('🔒 Session cache cleared on logout');
        return cleared;
    }
    
    /**
     * Remove expired entries
     */
    cleanupExpired() {
        try {
            const keys = Object.keys(this.storage);
            const tripraftKeys = keys.filter(key => key.startsWith(this.prefix));
            let cleaned = 0;
            
            tripraftKeys.forEach(key => {
                const item = this.storage.getItem(key);
                if (item) {
                    const entry = JSON.parse(item);
                    if (Date.now() > entry.expiresAt) {
                        this.storage.removeItem(key);
                        cleaned++;
                    }
                }
            });
            
            if (cleaned > 0) {
                console.log(`🧹 Cleaned ${cleaned} expired session entries`);
            }
            
            return cleaned;
        } catch (error) {
            console.error('❌ Session cache cleanup failed:', error);
            return 0;
        }
    }
    
    /**
     * Get cache statistics
     */
    getStats() {
        try {
            const keys = Object.keys(this.storage);
            const tripraftKeys = keys.filter(key => key.startsWith(this.prefix));
            
            let totalEntries = 0;
            let validEntries = 0;
            let expiredEntries = 0;
            let totalPlaces = 0;
            
            tripraftKeys.forEach(key => {
                const item = this.storage.getItem(key);
                if (item) {
                    totalEntries++;
                    const entry = JSON.parse(item);
                    
                    if (Date.now() > entry.expiresAt) {
                        expiredEntries++;
                    } else {
                        validEntries++;
                        totalPlaces += entry.count || 0;
                    }
                }
            });
            
            return {
                totalEntries,
                validEntries,
                expiredEntries,
                totalPlaces,
                ttlMinutes: this.ttlMs / 60000
            };
        } catch (error) {
            console.error('❌ Session cache stats failed:', error);
            return null;
        }
    }
    
    /**
     * Check if data exists in cache
     */
    has(city, radiusKm, travelMode = 'DRIVE') {
        return this.get(city, radiusKm, travelMode) !== null;
    }
}

// Export for use in React/other frameworks
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TripRaftSessionCache;
}

// Also make available globally
if (typeof window !== 'undefined') {
    window.TripRaftSessionCache = TripRaftSessionCache;
}

/**
 * Usage Example:
 * 
 * // Initialize cache
 * const placeCache = new TripRaftSessionCache(15); // 15 minutes TTL
 * 
 * // Before making API call, check cache
 * async function searchPlaces(city, radiusKm) {
 *     // Try cache first
 *     const cached = placeCache.get(city, radiusKm, 'DRIVE');
 *     if (cached) {
 *         return cached;
 *     }
 *     
 *     // Cache miss - fetch from API
 *     const response = await fetch(`/api/search?city=${city}&radius=${radiusKm}`);
 *     const data = await response.json();
 *     
 *     // Store in cache
 *     placeCache.set(city, radiusKm, data.places, 'DRIVE');
 *     
 *     return data.places;
 * }
 * 
 * // On logout
 * function handleLogout() {
 *     placeCache.clearOnLogout();
 *     // ... rest of logout logic
 * }
 * 
 * // Check cache stats
 * const stats = placeCache.getStats();
 * console.log('Cache stats:', stats);
 */
