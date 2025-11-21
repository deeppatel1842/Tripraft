/**
 * Frontend Constants
 * All hardcoded values centralized following professional practices
 */

// ============================================================================
// API CONFIGURATION
// ============================================================================

export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second
};

// ============================================================================
// ROUTE PATHS
// ============================================================================

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  SIGNUP: '/signup',
  EXPENSES: '/expenses',
  ANALYTICS: '/analytics',
  TRIP_PLANNER: '/trip-planner',
  PLACES_EXPLORER: '/places',
  INVITATION_ACCEPT: '/accept-invitation/:invitationId',
};

// ============================================================================
// LOCAL STORAGE KEYS
// ============================================================================

export const STORAGE_KEYS = {
  AUTH_TOKEN: 'authToken',
  USER_DATA: 'userData',
  THEME_PREFERENCE: 'themePreference',
  LAST_VIEWED_GROUP: 'lastViewedGroup',
  EXPENSE_FILTERS: 'expenseFilters',
};

// ============================================================================
// EXPENSE CATEGORIES
// ============================================================================

export const EXPENSE_CATEGORIES = [
  { value: 'food', label: 'Food & Dining', icon: 'utensils' },
  { value: 'transport', label: 'Transportation', icon: 'car' },
  { value: 'accommodation', label: 'Accommodation', icon: 'home' },
  { value: 'entertainment', label: 'Entertainment', icon: 'music' },
  { value: 'shopping', label: 'Shopping', icon: 'shopping-bag' },
  { value: 'groceries', label: 'Groceries', icon: 'shopping-cart' },
  { value: 'health', label: 'Health & Medical', icon: 'heart' },
  { value: 'utilities', label: 'Utilities', icon: 'zap' },
  { value: 'bills', label: 'Bills', icon: 'file-text' },
  { value: 'salary', label: 'Salary & Income', icon: 'dollar-sign' },
  { value: 'other', label: 'Other', icon: 'more-horizontal' },
];

// ============================================================================
// SPLIT TYPES
// ============================================================================

export const SPLIT_TYPES = {
  EQUAL: 'equal',
  EXACT: 'exact',
  PERCENTAGE: 'percentage',
  SHARES: 'shares',
};

export const SPLIT_TYPE_OPTIONS = [
  { value: 'equal', label: 'Equal Split' },
  { value: 'exact', label: 'Exact Amounts' },
  { value: 'percentage', label: 'Percentage' },
  { value: 'shares', label: 'By Shares' },
];

// ============================================================================
// CURRENCIES
// ============================================================================

export const CURRENCIES = [
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'EUR', symbol: '€', name: 'Euro' },
  { code: 'GBP', symbol: '£', name: 'British Pound' },
  { code: 'INR', symbol: '₹', name: 'Indian Rupee' },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen' },
  { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar' },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar' },
  { code: 'CHF', symbol: 'Fr', name: 'Swiss Franc' },
  { code: 'CNY', symbol: '¥', name: 'Chinese Yuan' },
];

export const DEFAULT_CURRENCY = 'USD';

// ============================================================================
// PAGINATION
// ============================================================================

export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
};

// ============================================================================
// VALIDATION RULES
// ============================================================================

export const VALIDATION = {
  USERNAME: {
    MIN_LENGTH: 3,
    MAX_LENGTH: 30,
    PATTERN: /^[a-zA-Z0-9_-]+$/,
    ERROR_MESSAGE: 'Username must be 3-30 characters and contain only letters, numbers, underscores, and hyphens',
  },
  
  EMAIL: {
    PATTERN: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
    ERROR_MESSAGE: 'Please enter a valid email address',
  },
  
  PASSWORD: {
    MIN_LENGTH: 8,
    MAX_LENGTH: 128,
    PATTERN: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
    ERROR_MESSAGE: 'Password must be at least 8 characters and contain uppercase, lowercase, and numbers',
  },
  
  EXPENSE: {
    MIN_AMOUNT: 0.01,
    MAX_AMOUNT: 1000000,
    MIN_DESCRIPTION_LENGTH: 1,
    MAX_DESCRIPTION_LENGTH: 500,
  },
  
  GROUP: {
    MIN_NAME_LENGTH: 1,
    MAX_NAME_LENGTH: 100,
    MAX_DESCRIPTION_LENGTH: 500,
    MIN_MEMBERS: 2,
    MAX_MEMBERS: 100,
  },
};

// ============================================================================
// UI CONSTANTS
// ============================================================================

export const UI = {
  // Toast notifications
  TOAST: {
    DURATION: 4000, // 4 seconds
    MAX_VISIBLE: 3,
    POSITION: 'top-right',
  },
  
  // Modal
  MODAL: {
    ANIMATION_DURATION: 200, // ms
    BACKDROP_OPACITY: 0.5,
  },
  
  // Loading states
  LOADING: {
    MIN_DISPLAY_TIME: 300, // ms - prevent flash
    SKELETON_COUNT: 5,
  },
  
  // Debounce delays
  DEBOUNCE: {
    SEARCH: 500, // ms
    AUTOSAVE: 1000, // ms
    RESIZE: 200, // ms
  },
  
  // Animation durations
  ANIMATION: {
    FAST: 150,
    DEFAULT: 200,
    SLOW: 300,
  },
};

// ============================================================================
// ERROR MESSAGES
// ============================================================================

export const ERROR_MESSAGES = {
  NETWORK: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'Please login to continue.',
  FORBIDDEN: 'You don\'t have permission to perform this action.',
  NOT_FOUND: 'Resource not found.',
  SERVER_ERROR: 'Server error. Please try again later.',
  VALIDATION: 'Please check your input and try again.',
  
  // Specific errors
  EXPENSE: {
    CREATE_FAILED: 'Failed to create expense.',
    UPDATE_FAILED: 'Failed to update expense.',
    DELETE_FAILED: 'Failed to delete expense.',
    LOAD_FAILED: 'Failed to load expenses.',
  },
  
  GROUP: {
    CREATE_FAILED: 'Failed to create group.',
    JOIN_FAILED: 'Failed to join group.',
    LEAVE_FAILED: 'Failed to leave group.',
    DELETE_FAILED: 'Failed to delete group.',
    LOAD_FAILED: 'Failed to load groups.',
  },
  
  AUTH: {
    LOGIN_FAILED: 'Invalid email or password.',
    SIGNUP_FAILED: 'Failed to create account.',
    LOGOUT_FAILED: 'Failed to logout.',
  },
};

// ============================================================================
// SUCCESS MESSAGES
// ============================================================================

export const SUCCESS_MESSAGES = {
  EXPENSE: {
    CREATED: 'Expense added successfully!',
    UPDATED: 'Expense updated successfully!',
    DELETED: 'Expense deleted successfully!',
  },
  
  GROUP: {
    CREATED: 'Group created successfully!',
    JOINED: 'Joined group successfully!',
    LEFT: 'Left group successfully!',
    DELETED: 'Group deleted successfully!',
    MEMBER_ADDED: 'Member added successfully!',
  },
  
  AUTH: {
    LOGIN: 'Welcome back!',
    SIGNUP: 'Account created successfully!',
    LOGOUT: 'Logged out successfully!',
  },
  
  SETTLEMENT: {
    RECORDED: 'Settlement recorded successfully!',
    COMPLETED: 'Payment marked as completed!',
  },
};

// ============================================================================
// DATE & TIME FORMATS
// ============================================================================

export const DATE_FORMATS = {
  SHORT: 'MMM d, yyyy',            // Jan 1, 2025
  LONG: 'MMMM d, yyyy',            // January 1, 2025
  WITH_TIME: 'MMM d, yyyy h:mm a', // Jan 1, 2025 2:30 PM
  TIME_ONLY: 'h:mm a',             // 2:30 PM
  ISO: 'yyyy-MM-dd',               // 2025-01-01
};

// ============================================================================
// FEATURE FLAGS
// ============================================================================

export const FEATURES = {
  ENABLE_ANALYTICS: true,
  ENABLE_TRIP_PLANNER: true,
  ENABLE_PLACES_EXPLORER: true,
  ENABLE_EMAIL_NOTIFICATIONS: true,
  ENABLE_PUSH_NOTIFICATIONS: false,
  ENABLE_DARK_MODE: false,
  ENABLE_EXPORT_CSV: true,
  ENABLE_EXPORT_PDF: false,
};

// ============================================================================
// EXPENSE MODES
// ============================================================================

export const EXPENSE_MODES = {
  PERSONAL: 'personal',
  GROUP: 'group',
};

// ============================================================================
// FILTER OPTIONS
// ============================================================================

export const FILTER_OPTIONS = {
  SORT_BY: [
    { value: 'date-desc', label: 'Newest First' },
    { value: 'date-asc', label: 'Oldest First' },
    { value: 'amount-desc', label: 'Highest Amount' },
    { value: 'amount-asc', label: 'Lowest Amount' },
  ],
  
  TYPE: [
    { value: 'all', label: 'All Expenses' },
    { value: 'paid', label: 'I Paid' },
    { value: 'owe', label: 'I Owe' },
  ],
};

// ============================================================================
// MAP CONFIGURATION
// ============================================================================

export const MAP_CONFIG = {
  DEFAULT_CENTER: [20, 0], // [lat, lng]
  DEFAULT_ZOOM: 2,
  MARKER_ZOOM: 13,
  MIN_ZOOM: 2,
  MAX_ZOOM: 18,
};

// ============================================================================
// FILE UPLOAD
// ============================================================================

export const FILE_UPLOAD = {
  MAX_SIZE: 5 * 1024 * 1024, // 5 MB
  ALLOWED_TYPES: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  ALLOWED_EXTENSIONS: ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
};

// ============================================================================
// REGEX PATTERNS
// ============================================================================

export const REGEX = {
  EMAIL: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
  USERNAME: /^[a-zA-Z0-9_-]+$/,
  PHONE: /^\+?[1-9]\d{1,14}$/,
  URL: /^https?:\/\/.+/,
  CURRENCY_AMOUNT: /^\d+(\.\d{1,2})?$/,
};

// ============================================================================
// HTTP STATUS CODES
// ============================================================================

export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get category by value
 */
export const getCategoryByValue = (value) => {
  return EXPENSE_CATEGORIES.find(cat => cat.value === value);
};

/**
 * Get currency symbol
 */
export const getCurrencySymbol = (code) => {
  const currency = CURRENCIES.find(c => c.code === code);
  return currency ? currency.symbol : '$';
};

/**
 * Format currency
 */
export const formatCurrency = (amount, currencyCode = DEFAULT_CURRENCY) => {
  const symbol = getCurrencySymbol(currencyCode);
  return `${symbol}${parseFloat(amount).toFixed(2)}`;
};

// Export all constants
export default {
  API_CONFIG,
  ROUTES,
  STORAGE_KEYS,
  EXPENSE_CATEGORIES,
  SPLIT_TYPES,
  SPLIT_TYPE_OPTIONS,
  CURRENCIES,
  DEFAULT_CURRENCY,
  PAGINATION,
  VALIDATION,
  UI,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
  DATE_FORMATS,
  FEATURES,
  EXPENSE_MODES,
  FILTER_OPTIONS,
  MAP_CONFIG,
  FILE_UPLOAD,
  REGEX,
  HTTP_STATUS,
};
