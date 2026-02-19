
/**
 * Timezone & Location Utility Functions
 * Handles consistent date/time display and user location detection.
 */

// ==========================================
// SECTION 1: Timezone & Date Formatting
// ==========================================

/**
 * Format date/time in user's local timezone
 * FIX APPLIED: Automatically detects if "Z" is missing from backend strings
 * to prevent the "8-hour offset" error.
 * * @param {string|Date} dateString - ISO date string or Date object
 * @param {Object} options - Formatting options
 * @returns {string} Formatted date string in user's local timezone
 */
export const formatDateLocal = (dateString, options = {}) => {
  if (!dateString) return 'Unknown date';
  
  try {
    let cleanDateString = dateString;

    // === THE FIX FOR INCORRECT TIMES ===
    // If the string looks like an ISO string (has 'T') but is missing timezone info
    // (no 'Z' and no '+' or '-'), we assume it is UTC and append 'Z'.
    if (typeof dateString === 'string' && 
        dateString.includes('T') && 
        !dateString.endsWith('Z') && 
        !dateString.includes('+') && 
        !dateString.match(/-\d\d:?\d\d/)) { // Checks for offsets like -08:00
        
        cleanDateString = dateString + 'Z';
    }
    // ===================================

    const date = new Date(cleanDateString);
    if (isNaN(date.getTime())) return 'Invalid date';
    
    // Default formatting options
    const defaultOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short',
      ...options
    };
    
    // Uses the browser's system clock for the timezone
    return date.toLocaleString('en-US', defaultOptions);
  } catch (error) {
    return 'Invalid date';
  }
};

/**
 * Format date only (no time) in user's local timezone
 */
export const formatDateOnlyLocal = (dateString) => {
  return formatDateLocal(dateString, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: undefined,
    minute: undefined,
    second: undefined,
    timeZoneName: undefined
  });
};

/**
 * Format time only in user's local timezone
 */
export const formatTimeOnlyLocal = (dateString) => {
  return formatDateLocal(dateString, {
    year: undefined,
    month: undefined,
    day: undefined,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZoneName: 'short'
  });
};

/**
 * Get user's timezone offset (e.g., "-08:00" for PST)
 */
export const getTimezoneOffset = () => {
  const now = new Date();
  const offset = -now.getTimezoneOffset();
  const hours = Math.floor(Math.abs(offset) / 60);
  const minutes = Math.abs(offset) % 60;
  const sign = offset >= 0 ? '+' : '-';
  return `${sign}${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
};

/**
 * Get user's timezone name (e.g., "PST", "EST", "CET")
 */
export const getTimezoneName = () => {
  const now = new Date();
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZoneName: 'short'
  }).formatToParts(now);
  
  const timezonePart = parts.find(p => p.type === 'timeZoneName');
  return timezonePart ? timezonePart.value : 'Local';
};

/**
 * Convert ISO string to user's local date for input fields (YYYY-MM-DD)
 */
export const isoToLocalDateInput = (isoString) => {
  if (!isoString) return '';
  try {
    // Apply the same Z fix here just in case
    let cleanString = isoString;
    if (typeof isoString === 'string' && isoString.includes('T') && !isoString.endsWith('Z')) {
        cleanString = isoString + 'Z';
    }
    
    const date = new Date(cleanString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  } catch (error) {
    return '';
  }
};

/**
 * Convert local date from input to ISO string (Midnight UTC)
 */
export const localDateInputToISO = (localDate) => {
  if (!localDate) return '';
  try {
    const parts = localDate.split('-');
    const date = new Date(
      parseInt(parts[0]),
      parseInt(parts[1]) - 1,
      parseInt(parts[2]),
      0, 0, 0, 0
    );
    return date.toISOString();
  } catch (error) {
    return '';
  }
};

export const isToday = (dateString) => {
  const dateStr = formatDateLocal(dateString); 
  const todayStr = formatDateLocal(new Date().toISOString());
  return dateStr.split(',')[0] === todayStr.split(',')[0]; // Compare date parts
};

export const isPast = (dateString) => {
  let cleanDateString = dateString;
  if (typeof dateString === 'string' && dateString.includes('T') && !dateString.endsWith('Z')) {
      cleanDateString = dateString + 'Z';
  }
  return new Date(cleanDateString) < new Date();
};

export const getRelativeTime = (dateString) => {
  let cleanDateString = dateString;
  if (typeof dateString === 'string' && dateString.includes('T') && !dateString.endsWith('Z')) {
      cleanDateString = dateString + 'Z';
  }
  
  const date = new Date(cleanDateString);
  const now = new Date();
  const diffMs = now - date;
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 30) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  
  return formatDateLocal(cleanDateString, {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
};

// ==========================================
// SECTION 2: Location Detection
// ==========================================

/**
 * Get user's current coordinates (Latitude & Longitude)
 * Uses the browser's Geolocation API.
 * @returns {Promise<{lat: number, lng: number, accuracy: number}>}
 */
export const getUserCoordinates = () => {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation is not supported by this browser."));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy
        });
      },
      (error) => {
        let errorMessage = "Unknown error fetching location.";
        switch(error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = "User denied the request for Geolocation.";
            break;
          case error.POSITION_UNAVAILABLE:
            errorMessage = "Location information is unavailable.";
            break;
          case error.TIMEOUT:
            errorMessage = "The request to get user location timed out.";
            break;
        }
        reject(new Error(errorMessage));
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    );
  });
};

/**
 * Get City Name from Coordinates using OpenStreetMap (Free)
 * @param {number} lat 
 * @param {number} lng 
 * @returns {Promise<string>} City name or "Unknown Location"
 */
export const getCityFromCoordinates = async (lat, lng) => {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=10`
    );
    
    if (!response.ok) throw new Error("Failed to fetch address");
    
    const data = await response.json();
    
    return (
      data.address.city || 
      data.address.town || 
      data.address.village || 
      data.address.county || 
      "Unknown Location"
    );
  } catch (error) {
    return "Unknown Location";
  }
};

export default {
  formatDateLocal,
  formatDateOnlyLocal,
  formatTimeOnlyLocal,
  getTimezoneOffset,
  getTimezoneName,
  isoToLocalDateInput,
  localDateInputToISO,
  isToday,
  isPast,
  getRelativeTime,
  getUserCoordinates,
  getCityFromCoordinates
};