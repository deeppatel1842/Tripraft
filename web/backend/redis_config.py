# Redis Configuration for Production
# Optimized for high-traffic scenarios

import os

# =============================================================================
# CONNECTION SETTINGS
# =============================================================================
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Connection pool settings
MAX_CONNECTIONS = int(os.getenv('REDIS_MAX_CONNECTIONS', 50))
SOCKET_TIMEOUT = int(os.getenv('REDIS_SOCKET_TIMEOUT', 5))
SOCKET_CONNECT_TIMEOUT = int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', 5))
SOCKET_KEEPALIVE = True
SOCKET_KEEPALIVE_OPTIONS = {
    1: 1,   # TCP_KEEPIDLE
    2: 1,   # TCP_KEEPINTVL
    3: 3,   # TCP_KEEPCNT
}

# Retry settings
RETRY_ON_TIMEOUT = True
RETRY_ON_ERROR = [ConnectionError, TimeoutError]
MAX_RETRIES = 3

# Health check interval (seconds)
HEALTH_CHECK_INTERVAL = int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', 30))

# =============================================================================
# CACHING STRATEGY
# =============================================================================
# Default TTL for cached data (7 days)
DEFAULT_CACHE_TTL = int(os.getenv('CACHE_TTL', 604800))

# Cache key prefixes for organization
CACHE_PREFIX = {
    'places': 'places:',
    'geocode': 'geocode:',
    'routes': 'routes:',
    'user': 'user:',
    'session': 'session:',
}

# Enable aggressive caching in production
ENABLE_AGGRESSIVE_CACHING = os.getenv('ENABLE_AGGRESSIVE_CACHING', 'True').lower() == 'true'

# =============================================================================
# EVICTION POLICY
# =============================================================================
# Redis eviction policy (set in redis.conf or via CONFIG SET)
# Recommended: allkeys-lru (evict any key using LRU when memory limit is reached)
EVICTION_POLICY = 'allkeys-lru'

# =============================================================================
# PERSISTENCE (if using Redis persistence)
# =============================================================================
# RDB settings (snapshot)
SAVE_SECONDS = 900  # Save after 900 seconds if at least 1 key changed
SAVE_CHANGES = 1

# AOF settings (append-only file)
APPENDONLY = os.getenv('REDIS_APPENDONLY', 'no')
APPENDFSYNC = 'everysec'  # fsync every second (balanced)

# =============================================================================
# SENTINEL (for high availability)
# =============================================================================
USE_SENTINEL = os.getenv('REDIS_USE_SENTINEL', 'False').lower() == 'true'
SENTINEL_HOSTS = os.getenv('REDIS_SENTINEL_HOSTS', '').split(',') if USE_SENTINEL else []
SENTINEL_MASTER = os.getenv('REDIS_SENTINEL_MASTER', 'mymaster')
SENTINEL_PASSWORD = os.getenv('REDIS_SENTINEL_PASSWORD', None)

# =============================================================================
# CLUSTER (for horizontal scaling)
# =============================================================================
USE_CLUSTER = os.getenv('REDIS_USE_CLUSTER', 'False').lower() == 'true'
CLUSTER_NODES = os.getenv('REDIS_CLUSTER_NODES', '').split(',') if USE_CLUSTER else []
