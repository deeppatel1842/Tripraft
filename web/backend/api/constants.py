"""
Places API Constants
All hardcoded values centralized for the Places API module.
"""

# =============================================================================
# HTTP STATUS CODES
# =============================================================================

class HTTPStatus:
    """Standard HTTP status codes"""
    
    # Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # Client errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # Server errors
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


# =============================================================================
# PAGINATION CONFIGURATION
# =============================================================================

class PaginationConfig:
    """Pagination settings"""
    
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1
    DEFAULT_OFFSET = 0


# =============================================================================
# SEARCH CONFIGURATION
# =============================================================================

class SearchConfig:
    """Search and query configuration"""
    
    MIN_SEARCH_QUERY_LENGTH = 2
    MAX_SEARCH_QUERY_LENGTH = 100
    DEFAULT_SEARCH_LIMIT = 20
    MAX_SEARCH_RESULTS = 100
    SEARCH_TIMEOUT_SECONDS = 5


# =============================================================================
# API CONFIGURATION
# =============================================================================

class APIConfig:
    """API settings"""
    
    API_VERSION = '1.0.0'
    API_PREFIX = '/api/v1'
    SERVICE_NAME = 'Places API'
    
    # Request limits
    MAX_REQUEST_SIZE_MB = 10
    REQUEST_TIMEOUT_SECONDS = 30
    
    # Compression
    COMPRESS_MIN_SIZE = 500  # bytes
    COMPRESS_LEVEL = 6  # 1-9, balanced
    COMPRESS_MIMETYPES = [
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript',
        'text/javascript'
    ]


# =============================================================================
# CORS CONFIGURATION
# =============================================================================

class CORSConfig:
    """CORS settings"""
    
    DEFAULT_ORIGINS = ['http://localhost:5173', 'http://localhost:3000']
    ALLOWED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    ALLOWED_HEADERS = ['Content-Type', 'Authorization']
    SUPPORTS_CREDENTIALS = True


# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

class CacheConfig:
    """Cache TTL settings (seconds)"""
    
    TTL_COUNTRY = 86400       # 24 hours - rarely changes
    TTL_STATE = 86400         # 24 hours - rarely changes
    TTL_CITY = 43200          # 12 hours - occasionally changes
    TTL_PLACE = 3600          # 1 hour - changes more frequently
    TTL_SEARCH_RESULTS = 1800 # 30 minutes - search results
    
    # Cache key prefixes
    PREFIX_COUNTRY = "places:country:"
    PREFIX_STATE = "places:state:"
    PREFIX_CITY = "places:city:"
    PREFIX_PLACE = "places:place:"
    PREFIX_SEARCH = "places:search:"


# =============================================================================
# VALIDATION RULES
# =============================================================================

class ValidationRules:
    """Input validation rules"""
    
    # ID validation
    MIN_ID_LENGTH = 1
    MAX_ID_LENGTH = 100
    
    # Name validation
    MIN_NAME_LENGTH = 1
    MAX_NAME_LENGTH = 200
    
    # Description validation
    MAX_DESCRIPTION_LENGTH = 1000
    
    # Coordinates validation
    MIN_LATITUDE = -90.0
    MAX_LATITUDE = 90.0
    MIN_LONGITUDE = -180.0
    MAX_LONGITUDE = 180.0


# =============================================================================
# ERROR CODES
# =============================================================================

class ErrorCodes:
    """Application-specific error codes"""
    
    # Resource errors
    COUNTRY_NOT_FOUND = 'COUNTRY_NOT_FOUND'
    STATE_NOT_FOUND = 'STATE_NOT_FOUND'
    CITY_NOT_FOUND = 'CITY_NOT_FOUND'
    PLACE_NOT_FOUND = 'PLACE_NOT_FOUND'
    
    # Validation errors
    INVALID_PAGINATION = 'INVALID_PAGINATION'
    INVALID_SEARCH_QUERY = 'INVALID_SEARCH_QUERY'
    INVALID_COORDINATES = 'INVALID_COORDINATES'
    INVALID_ID_FORMAT = 'INVALID_ID_FORMAT'
    
    # System errors
    DATABASE_ERROR = 'DATABASE_ERROR'
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'


# =============================================================================
# ERROR MESSAGES
# =============================================================================

class ErrorMessages:
    """User-facing error messages"""
    
    # Resource not found
    COUNTRY_NOT_FOUND = "Country not found"
    STATE_NOT_FOUND = "State not found"
    CITY_NOT_FOUND = "City not found"
    PLACE_NOT_FOUND = "Place not found"
    
    # Validation errors
    INVALID_LIMIT = "Limit must be between {min} and {max}"
    INVALID_OFFSET = "Offset must be non-negative"
    INVALID_SEARCH_QUERY = "Search query must be between {min} and {max} characters"
    INVALID_COORDINATES = "Invalid coordinates provided"
    
    # System errors
    DATABASE_ERROR = "Database operation failed"
    INTERNAL_ERROR = "An internal error occurred"
    SERVICE_UNAVAILABLE = "Service temporarily unavailable"
    
    # Request errors
    INVALID_REQUEST = "Invalid request data"
    MISSING_PARAMETER = "Missing required parameter: {param}"


# =============================================================================
# SUCCESS MESSAGES
# =============================================================================

class SuccessMessages:
    """Success response messages"""
    
    COUNTRY_RETRIEVED = "Country retrieved successfully"
    COUNTRIES_RETRIEVED = "Countries retrieved successfully"
    STATE_RETRIEVED = "State retrieved successfully"
    STATES_RETRIEVED = "States retrieved successfully"
    CITY_RETRIEVED = "City retrieved successfully"
    CITIES_RETRIEVED = "Cities retrieved successfully"
    PLACE_RETRIEVED = "Place retrieved successfully"
    PLACES_RETRIEVED = "Places retrieved successfully"
    SEARCH_COMPLETED = "Search completed successfully"


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

class LoggingConfig:
    """Logging settings"""
    
    DEFAULT_LEVEL = 'INFO'
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Log file settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5
    
    # Request logging
    LOG_REQUESTS = True
    LOG_RESPONSES = True
    LOG_ERRORS = True


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

class DatabaseConfig:
    """Database settings"""
    
    # Connection settings
    CONNECTION_TIMEOUT = 30
    BUSY_TIMEOUT = 5000  # milliseconds
    
    # Query settings
    MAX_QUERY_TIME = 10  # seconds
    MAX_RESULTS_PER_QUERY = 1000
    
    # Table names
    TABLE_COUNTRIES = 'countries'
    TABLE_STATES = 'states'
    TABLE_CITIES = 'cities'
    TABLE_PLACES = 'places'


# =============================================================================
# RATE LIMITING (if enabled in future)
# =============================================================================

class RateLimitConfig:
    """Rate limiting configuration"""
    
    ENABLED = False
    DEFAULT_LIMIT = 100  # requests
    DEFAULT_WINDOW = 3600  # per hour
    
    # Per-endpoint limits
    SEARCH_LIMIT = 50  # per hour
    LIST_LIMIT = 200   # per hour


# Export all configs
__all__ = [
    'HTTPStatus',
    'PaginationConfig',
    'SearchConfig',
    'APIConfig',
    'CORSConfig',
    'CacheConfig',
    'ValidationRules',
    'ErrorCodes',
    'ErrorMessages',
    'SuccessMessages',
    'LoggingConfig',
    'DatabaseConfig',
    'RateLimitConfig',
]
