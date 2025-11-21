/**
 * Development-Only Logging Utility
 * All console.log statements wrapped with this will only execute in development
 */

const IS_DEVELOPMENT = process.env.NODE_ENV === 'development';
const IS_DEBUG = localStorage.getItem('DEBUG_MODE') === 'true';

/**
 * Debug configuration
 */
const DEBUG_CONFIG = {
  enableApiLogs: IS_DEVELOPMENT || IS_DEBUG,
  enableStateLogs: IS_DEVELOPMENT,
  enablePerformanceLogs: IS_DEVELOPMENT,
  enableCacheLogs: IS_DEVELOPMENT,
  sampleRate: 0.01, // 1% sampling in production
};

/**
 * Safe console.log that only runs in development
 * @param {...any} args - Arguments to log
 */
export const devLog = (...args) => {
  if (IS_DEVELOPMENT || IS_DEBUG) {
    console.log(...args);
  }
};

/**
 * Safe console.debug
 * @param {...any} args - Arguments to log
 */
export const devDebug = (...args) => {
  if (IS_DEVELOPMENT || IS_DEBUG) {
    console.debug(...args);
  }
};

/**
 * Safe console.info
 * @param {...any} args - Arguments to log
 */
export const devInfo = (...args) => {
  if (IS_DEVELOPMENT || IS_DEBUG) {
    console.info(...args);
  }
};

/**
 * Safe console.warn (always shows, but sanitized in production)
 * @param {...any} args - Arguments to log
 */
export const devWarn = (...args) => {
  if (IS_DEVELOPMENT) {
    console.warn(...args);
  } else {
    // In production, show sanitized warning
    console.warn('Warning occurred. Enable DEBUG_MODE for details.');
  }
};

/**
 * console.error should always show (but sanitized in production)
 * @param {...any} args - Arguments to log
 */
export const devError = (...args) => {
  if (IS_DEVELOPMENT) {
    console.error(...args);
  } else {
    // In production, show generic error
    console.error('An error occurred. Enable DEBUG_MODE for details.');
  }
};

/**
 * Log API calls (with sampling in production)
 * @param {string} method - HTTP method
 * @param {string} url - API URL
 * @param {any} data - Request/response data
 */
export const logApiCall = (method, url, data = null) => {
  if (!DEBUG_CONFIG.enableApiLogs) {
    return;
  }

  if (!IS_DEVELOPMENT && Math.random() > DEBUG_CONFIG.sampleRate) {
    return; // Sample only 1% in production
  }

  const sanitizedData = sanitizeData(data);
  console.log(`%c${method} ${url}`, 'color: #10b981; font-weight: bold;', sanitizedData);
};

/**
 * Log state changes
 * @param {string} component - Component name
 * @param {string} action - Action description
 * @param {any} state - State data
 */
export const logStateChange = (component, action, state = null) => {
  if (!DEBUG_CONFIG.enableStateLogs) {
    return;
  }

  const sanitizedState = sanitizeData(state);
  console.log(`%c[${component}] ${action}`, 'color: #3b82f6; font-weight: bold;', sanitizedState);
};

/**
 * Log performance metrics
 * @param {string} operation - Operation name
 * @param {number} duration - Duration in ms
 * @param {object} metadata - Additional metadata
 */
export const logPerformance = (operation, duration, metadata = {}) => {
  if (!DEBUG_CONFIG.enablePerformanceLogs) {
    return;
  }

  console.log(
    `%c⚡ ${operation}`,
    'color: #f59e0b; font-weight: bold;',
    `${duration.toFixed(2)}ms`,
    metadata
  );
};

/**
 * Log cache operations
 * @param {string} operation - Cache operation (hit/miss/set)
 * @param {string} key - Cache key
 * @param {any} data - Cache data
 */
export const logCache = (operation, key, data = null) => {
  if (!DEBUG_CONFIG.enableCacheLogs) {
    return;
  }

  const icons = {
    hit: '✅',
    miss: '❌',
    set: '💾',
  };

  const icon = icons[operation] || '📦';
  const sanitizedKey = sanitizeKey(key);
  
  console.log(`${icon} Cache ${operation}: ${sanitizedKey}`, data);
};

/**
 * Sanitize data for logging (remove sensitive information)
 * @param {any} data - Data to sanitize
 * @returns {any} - Sanitized data
 */
const sanitizeData = (data) => {
  if (!data) return data;

  // In production, never log full objects
  if (!IS_DEVELOPMENT) {
    if (typeof data === 'object') {
      return '[OBJECT]';
    }
    return '[DATA]';
  }

  // In development, still remove sensitive fields
  if (typeof data === 'object' && data !== null) {
    const sanitized = { ...data };
    const sensitiveFields = ['password', 'token', 'api_key', 'secret', 'credential', 'authorization'];
    
    Object.keys(sanitized).forEach(key => {
      const keyLower = key.toLowerCase();
      if (sensitiveFields.some(field => keyLower.includes(field))) {
        sanitized[key] = '[REDACTED]';
      } else if (keyLower === 'email') {
        sanitized[key] = maskEmail(sanitized[key]);
      }
    });
    
    return sanitized;
  }

  return data;
};

/**
 * Sanitize cache key for logging
 * @param {string} key - Cache key
 * @returns {string} - Sanitized key
 */
const sanitizeKey = (key) => {
  if (!key) return key;

  // In production, hash user IDs
  if (!IS_DEVELOPMENT && key.includes('user:')) {
    return key.replace(/user:[^:]+/, 'user:***');
  }

  return key;
};

/**
 * Mask email address
 * @param {string} email - Email address
 * @returns {string} - Masked email
 */
const maskEmail = (email) => {
  if (!email || !email.includes('@')) return email;

  const [local, domain] = email.split('@');
  if (local.length <= 2) return email;

  const masked = local[0] + '*'.repeat(local.length - 2) + local[local.length - 1];
  return `${masked}@${domain}`;
};

/**
 * Performance timing wrapper
 * @param {Function} fn - Function to measure
 * @param {string} label - Label for logging
 * @returns {any} - Function result
 */
export const measurePerformance = async (fn, label) => {
  if (!DEBUG_CONFIG.enablePerformanceLogs) {
    return await fn();
  }

  const start = performance.now();
  const result = await fn();
  const duration = performance.now() - start;

  logPerformance(label, duration);

  return result;
};

/**
 * Enable debug mode dynamically
 */
export const enableDebugMode = () => {
  localStorage.setItem('DEBUG_MODE', 'true');
  console.log('✅ Debug mode enabled. Reload the page for full effect.');
};

/**
 * Disable debug mode
 */
export const disableDebugMode = () => {
  localStorage.removeItem('DEBUG_MODE');
  console.log('✅ Debug mode disabled.');
};

/**
 * Group logs for better organization
 * @param {string} label - Group label
 * @param {Function} fn - Function containing logs
 */
export const devGroup = (label, fn) => {
  if (!IS_DEVELOPMENT && !IS_DEBUG) {
    fn();
    return;
  }

  console.group(label);
  try {
    fn();
  } finally {
    console.groupEnd();
  }
};

/**
 * Collapsed group (good for less important logs)
 * @param {string} label - Group label
 * @param {Function} fn - Function containing logs
 */
export const devGroupCollapsed = (label, fn) => {
  if (!IS_DEVELOPMENT && !IS_DEBUG) {
    fn();
    return;
  }

  console.groupCollapsed(label);
  try {
    fn();
  } finally {
    console.groupEnd();
  }
};

/**
 * Table logging (for arrays/objects)
 * @param {Array|Object} data - Data to display
 * @param {Array<string>} columns - Columns to show
 */
export const devTable = (data, columns = null) => {
  if (!IS_DEVELOPMENT && !IS_DEBUG) {
    return;
  }

  if (columns) {
    console.table(data, columns);
  } else {
    console.table(data);
  }
};

// Export all utilities
export default {
  devLog,
  devDebug,
  devInfo,
  devWarn,
  devError,
  logApiCall,
  logStateChange,
  logPerformance,
  logCache,
  measurePerformance,
  enableDebugMode,
  disableDebugMode,
  devGroup,
  devGroupCollapsed,
  devTable,
};
