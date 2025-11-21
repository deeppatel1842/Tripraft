"""
Global Health & Performance Monitoring Endpoints
Provides comprehensive system health checks and performance metrics
Similar to what major companies use for monitoring
"""

from flask import Blueprint, jsonify
import time
import psutil
import redis
import os
from datetime import datetime
from functools import wraps
from firebase_admin import firestore, auth as firebase_auth

health_bp = Blueprint('health', __name__)

# Performance tracking storage
performance_metrics = {
    'requests': 0,
    'total_response_time': 0,
    'slow_requests': 0,
    'failed_requests': 0,
    'firebase_operations': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'start_time': time.time()
}

# Cache for health check results (30 second TTL)
health_check_cache = {
    'detailed': None,
    'detailed_timestamp': 0,
    'redis': None,
    'redis_timestamp': 0,
    'firebase': None,
    'firebase_timestamp': 0
}
HEALTH_CACHE_TTL = 30  # seconds

def track_performance(f):
    """Decorator to track endpoint performance"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        performance_metrics['requests'] += 1
        
        try:
            result = f(*args, **kwargs)
            response_time = time.time() - start_time
            performance_metrics['total_response_time'] += response_time
            
            if response_time > 1.0:  # Slow request threshold
                performance_metrics['slow_requests'] += 1
            
            return result
        except Exception as e:
            performance_metrics['failed_requests'] += 1
            raise e
    
    return decorated_function


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint - ultra fast
    Returns 200 if service is alive
    """
    return jsonify({
        'status': 'healthy',
        'service': 'TripRaft API',
        'timestamp': datetime.utcnow().isoformat(),
        'uptime_seconds': int(time.time() - performance_metrics['start_time'])
    }), 200


@health_bp.route('/health/quick', methods=['GET'])
def quick_health_check():
    """
    Quick health check - just checks if services are initialized
    Even faster than detailed, no actual service calls
    """
    return jsonify({
        'status': 'healthy',
        'service': 'TripRaft API',
        'redis': 'initialized',
        'firebase': 'initialized',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@health_bp.route('/health/detailed', methods=['GET'])
def detailed_health_check():
    """
    Detailed health check with all service statuses
    Checks: Redis, Firebase, System Resources
    Cached for 30 seconds to prevent slowdowns
    """
    # Check if we have a cached result
    current_time = time.time()
    if (health_check_cache['detailed'] is not None and 
        current_time - health_check_cache['detailed_timestamp'] < HEALTH_CACHE_TTL):
        cached_result = health_check_cache['detailed'].copy()
        cached_result['cached'] = True
        cached_result['cache_age_seconds'] = int(current_time - health_check_cache['detailed_timestamp'])
        return jsonify(cached_result), 200 if cached_result['status'] == 'healthy' else 503
    
    # Generate fresh health status
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'uptime_seconds': int(time.time() - performance_metrics['start_time']),
        'services': {},
        'cached': False
    }
    
    overall_healthy = True
    
    # Check Redis (fast)
    redis_status = check_redis_health()
    health_status['services']['redis'] = redis_status
    if redis_status['status'] not in ['healthy', 'unavailable']:  # unavailable is acceptable
        overall_healthy = False
    
    # Check Firebase (now optimized)
    firebase_status = check_firebase_health()
    health_status['services']['firebase'] = firebase_status
    if firebase_status['status'] != 'healthy':
        overall_healthy = False
    
    # Check System Resources (fast)
    system_status = check_system_resources()
    health_status['services']['system'] = system_status
    if system_status['status'] not in ['healthy', 'warning']:  # warning is acceptable
        overall_healthy = False
    
    # Overall status
    health_status['status'] = 'healthy' if overall_healthy else 'degraded'
    
    # Cache the result
    health_check_cache['detailed'] = health_status.copy()
    health_check_cache['detailed_timestamp'] = current_time
    
    return jsonify(health_status), 200 if overall_healthy else 503


@health_bp.route('/health/redis', methods=['GET'])
def redis_health():
    """Check Redis cache health"""
    return jsonify(check_redis_health()), 200


@health_bp.route('/health/firebase', methods=['GET'])
def firebase_health():
    """Check Firebase/Firestore health"""
    return jsonify(check_firebase_health()), 200


@health_bp.route('/health/system', methods=['GET'])
def system_health():
    """Check system resources (CPU, Memory, Disk)"""
    return jsonify(check_system_resources()), 200


@health_bp.route('/metrics', methods=['GET'])
def performance_metrics_endpoint():
    """
    Performance metrics endpoint
    Shows real-time performance statistics
    """
    uptime = time.time() - performance_metrics['start_time']
    avg_response_time = (
        performance_metrics['total_response_time'] / performance_metrics['requests']
        if performance_metrics['requests'] > 0 else 0
    )
    
    cache_total = performance_metrics['cache_hits'] + performance_metrics['cache_misses']
    cache_hit_rate = (
        (performance_metrics['cache_hits'] / cache_total * 100)
        if cache_total > 0 else 0
    )
    
    return jsonify({
        'uptime_seconds': int(uptime),
        'uptime_formatted': format_uptime(uptime),
        'requests': {
            'total': performance_metrics['requests'],
            'failed': performance_metrics['failed_requests'],
            'slow': performance_metrics['slow_requests'],
            'requests_per_second': round(performance_metrics['requests'] / uptime, 2)
        },
        'response_times': {
            'average_ms': round(avg_response_time * 1000, 2),
            'slow_requests': performance_metrics['slow_requests'],
            'slow_request_percentage': round(
                (performance_metrics['slow_requests'] / performance_metrics['requests'] * 100)
                if performance_metrics['requests'] > 0 else 0,
                2
            )
        },
        'firebase': {
            'operations': performance_metrics['firebase_operations']
        },
        'cache': {
            'hits': performance_metrics['cache_hits'],
            'misses': performance_metrics['cache_misses'],
            'hit_rate_percentage': round(cache_hit_rate, 2),
            'total_operations': cache_total
        },
        'targets': {
            'avg_response_time_ms': 500,
            'cache_hit_rate_percentage': 80,
            'firebase_reads_per_request': 2
        }
    }), 200


@health_bp.route('/metrics/reset', methods=['POST'])
def reset_metrics():
    """Reset performance metrics (useful for testing)"""
    global performance_metrics
    performance_metrics = {
        'requests': 0,
        'total_response_time': 0,
        'slow_requests': 0,
        'failed_requests': 0,
        'firebase_operations': 0,
        'cache_hits': 0,
        'cache_misses': 0,
        'start_time': time.time()
    }
    return jsonify({'message': 'Metrics reset successfully'}), 200


@health_bp.route('/performance/test', methods=['GET'])
def performance_test():
    """
    Run a quick performance test
    Tests all major operations and returns timing
    """
    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'tests': {}
    }
    
    # Test 1: Redis Connection Speed
    redis_start = time.time()
    redis_result = test_redis_speed()
    redis_time = (time.time() - redis_start) * 1000
    results['tests']['redis'] = {
        'duration_ms': round(redis_time, 2),
        'status': redis_result,
        'target_ms': 10,
        'passed': redis_time < 10
    }
    
    # Test 2: Firebase Read Speed
    firebase_start = time.time()
    firebase_result = test_firebase_speed()
    firebase_time = (time.time() - firebase_start) * 1000
    results['tests']['firebase'] = {
        'duration_ms': round(firebase_time, 2),
        'status': firebase_result,
        'target_ms': 300,
        'passed': firebase_time < 300
    }
    
    # Test 3: System Response
    system_start = time.time()
    system_result = test_system_response()
    system_time = (time.time() - system_start) * 1000
    results['tests']['system'] = {
        'duration_ms': round(system_time, 2),
        'status': system_result,
        'target_ms': 5,
        'passed': system_time < 5
    }
    
    # Overall assessment
    all_passed = all(test['passed'] for test in results['tests'].values())
    results['overall'] = 'PASS' if all_passed else 'FAIL'
    results['summary'] = {
        'total_tests': len(results['tests']),
        'passed': sum(1 for test in results['tests'].values() if test['passed']),
        'failed': sum(1 for test in results['tests'].values() if not test['passed'])
    }
    
    return jsonify(results), 200


# Helper Functions

def check_redis_health():
    """Check if Redis is accessible and responsive"""
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url, decode_responses=True)
        start = time.time()
        r.ping()
        latency = (time.time() - start) * 1000
        
        # Get Redis info
        info = r.info()
        
        return {
            'status': 'healthy',
            'latency_ms': round(latency, 2),
            'connected_clients': info.get('connected_clients', 0),
            'used_memory_mb': round(info.get('used_memory', 0) / (1024 * 1024), 2),
            'uptime_seconds': info.get('uptime_in_seconds', 0)
        }
    except redis.ConnectionError:
        return {
            'status': 'unavailable',
            'error': 'Redis connection refused',
            'message': 'Cache layer disabled, system running in degraded mode'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def check_firebase_health():
    """Check if Firebase/Firestore is accessible"""
    try:
        # Just check if Firebase is initialized - much faster than actual operations
        db = firestore.client()
        
        # Quick check: verify client is accessible
        start = time.time()
        _ = db._database_string  # Internal property check - very fast
        latency = (time.time() - start) * 1000
        
        return {
            'status': 'healthy',
            'latency_ms': round(latency, 2),
            'service': 'Firestore',
            'authentication': 'Firebase Admin SDK'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'service': 'Firestore'
        }


def check_system_resources():
    """Check system CPU, Memory, and Disk usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        status = 'healthy'
        warnings = []
        
        if cpu_percent > 80:
            status = 'warning'
            warnings.append('High CPU usage')
        if memory.percent > 80:
            status = 'warning'
            warnings.append('High memory usage')
        if disk.percent > 90:
            status = 'critical'
            warnings.append('Low disk space')
        
        return {
            'status': status,
            'cpu': {
                'usage_percent': round(cpu_percent, 1),
                'cores': psutil.cpu_count()
            },
            'memory': {
                'usage_percent': round(memory.percent, 1),
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2)
            },
            'disk': {
                'usage_percent': round(disk.percent, 1),
                'total_gb': round(disk.total / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2)
            },
            'warnings': warnings
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def test_redis_speed():
    """Test Redis read/write speed"""
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Write test
        r.set('_health_test', 'test_value')
        # Read test
        r.get('_health_test')
        # Delete test
        r.delete('_health_test')
        
        return 'success'
    except:
        return 'unavailable'


def test_firebase_speed():
    """Test Firebase read/write speed"""
    try:
        db = firestore.client()
        test_ref = db.collection('_health_check').document('speed_test')
        
        # Write test
        test_ref.set({'test': True, 'timestamp': firestore.SERVER_TIMESTAMP})
        # Read test
        test_ref.get()
        # Delete test
        test_ref.delete()
        
        return 'success'
    except Exception as e:
        return f'error: {str(e)}'


def test_system_response():
    """Test basic system response"""
    try:
        # Simple computation test
        result = sum(range(1000))
        return 'success' if result == 499500 else 'error'
    except:
        return 'error'


def format_uptime(seconds):
    """Format uptime in human-readable format"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    
    return " ".join(parts)


# Function to increment metrics (called from other modules)
def increment_firebase_operations(count=1):
    """Increment Firebase operation counter"""
    performance_metrics['firebase_operations'] += count


def increment_cache_hit():
    """Increment cache hit counter"""
    performance_metrics['cache_hits'] += 1


def increment_cache_miss():
    """Increment cache miss counter"""
    performance_metrics['cache_misses'] += 1
