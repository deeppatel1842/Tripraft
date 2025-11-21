"""
Administrative and Utility Routes
Handles system health monitoring, cache management, performance metrics, and reference data
"""

from flask import Blueprint, request, jsonify, g
import logging
import time
from datetime import datetime

from ..service import expense_service
from ..models import ExpenseCategory, SplitType
from .route_helpers import require_auth

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin', __name__)


# =============================================================================
# HEALTH CHECK ROUTES
# =============================================================================

@admin_bp.route('/health', methods=['GET'])
def health_check():
    """
    System health check (PUBLIC - no auth required)
    
    Returns basic health status with worker and performance metrics.
    Designed for load balancers and monitoring systems.
    
    Returns:
        200: System healthy
        503: System unhealthy
        
    Response includes:
        - status: Overall health status
        - email_worker: Worker queue status and success rate
        - performance: Cache hit rate and request count
        - resources: CPU/memory/disk usage (if psutil available)
    """
    try:
        health = expense_service.health_check()
        
        # Add email worker stats
        try:
            from ..workers import get_email_worker
            email_worker = get_email_worker()
            worker_stats = email_worker.get_stats()
            health['email_worker'] = {
                'status': 'healthy' if worker_stats['running'] and worker_stats['worker_alive'] else 'unhealthy',
                'queue_size': worker_stats['queue_size'],
                'processed': worker_stats['processed_count'],
                'failed': worker_stats['failed_count'],
                'success_rate': round((worker_stats['processed_count'] - worker_stats['failed_count']) / max(worker_stats['processed_count'], 1) * 100, 2) if worker_stats['processed_count'] > 0 else 100.0
            }
        except Exception as worker_error:
            health['email_worker'] = {
                'status': 'error',
                'error': str(worker_error)
            }
        
        # Add performance metrics
        try:
            cache_analytics = expense_service.get_cache_analytics()
            health['performance'] = {
                'cache_hit_rate': cache_analytics.get('overall_hit_rate', 0),
                'total_requests': cache_analytics.get('total_requests', 0),
                'uptime_seconds': cache_analytics.get('uptime_seconds', 0)
            }
        except:
            pass  # Non-critical, continue without metrics
        
        # Add system resources (if available)
        try:
            import psutil
            health['resources'] = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except:
            pass  # psutil not installed, skip resource monitoring
        
        status_code = 200 if health['status'] == 'healthy' else 503
        return jsonify(health), status_code
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503


@admin_bp.route('/health/detailed', methods=['GET'])
@require_auth
def detailed_health_check():
    """
    Detailed health check with comprehensive metrics (AUTHENTICATED)
    
    Returns comprehensive system health information:
    - Service health (Firestore, Redis, Email Worker)
    - Service latency measurements
    - Performance metrics
    - System resources
    - Overall health status
    
    Designed for admin dashboards and debugging.
    
    Returns:
        200: System healthy or degraded
        503: System unhealthy
        
    Status Levels:
        - healthy: All services operational
        - degraded: Some services slow or non-critical failures
        - unhealthy: Critical service failures
    """
    try:
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0',
            'environment': 'production'
        }
        
        # Service health checks
        health['services'] = {}
        
        # Firebase health
        try:
            test_start = time.time()
            _ = expense_service.firebase.db.collection('health_check').limit(1).get()
            firebase_latency = (time.time() - test_start) * 1000
            health['services']['firestore'] = {
                'status': 'healthy',
                'latency_ms': round(firebase_latency, 2),
                'healthy': firebase_latency < 500
            }
        except Exception as e:
            health['services']['firestore'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['status'] = 'degraded'
        
        # Redis health
        try:
            test_start = time.time()
            expense_service.cache.redis_client.ping()
            redis_latency = (time.time() - test_start) * 1000
            health['services']['redis'] = {
                'status': 'healthy',
                'latency_ms': round(redis_latency, 2),
                'healthy': redis_latency < 50
            }
        except Exception as e:
            health['services']['redis'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['status'] = 'degraded'
        
        # Email worker health
        try:
            from ..workers import get_email_worker
            email_worker = get_email_worker()
            worker_stats = email_worker.get_stats()
            health['services']['email_worker'] = {
                'status': 'healthy' if worker_stats['running'] and worker_stats['worker_alive'] else 'unhealthy',
                'queue_size': worker_stats['queue_size'],
                'processed': worker_stats['processed_count'],
                'failed': worker_stats['failed_count'],
                'success_rate': round((worker_stats['processed_count'] - worker_stats['failed_count']) / max(worker_stats['processed_count'], 1) * 100, 2) if worker_stats['processed_count'] > 0 else 100.0,
                'healthy': worker_stats['running'] and worker_stats['worker_alive'] and worker_stats['queue_size'] < 50
            }
            if not health['services']['email_worker']['healthy']:
                health['status'] = 'degraded'
        except Exception as e:
            health['services']['email_worker'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Performance metrics
        try:
            cache_analytics = expense_service.get_cache_analytics()
            health['performance'] = {
                'cache_hit_rate': cache_analytics.get('overall_hit_rate', 0),
                'total_requests': cache_analytics.get('total_requests', 0),
                'uptime_seconds': cache_analytics.get('uptime_seconds', 0),
                'cache_healthy': cache_analytics.get('overall_hit_rate', 0) > 50
            }
        except:
            health['performance'] = {'error': 'Analytics unavailable'}
        
        # System resources
        try:
            import psutil
            health['resources'] = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'healthy': psutil.cpu_percent(interval=0.1) < 80 and psutil.virtual_memory().percent < 80
            }
            if not health['resources']['healthy']:
                health['status'] = 'degraded'
        except:
            health['resources'] = {'error': 'psutil not installed'}
        
        # Determine overall status
        all_services_healthy = all(
            service.get('status') == 'healthy' or service.get('healthy') == True 
            for service in health['services'].values()
        )
        if not all_services_healthy and health['status'] == 'healthy':
            health['status'] = 'degraded'
        
        status_code = 200 if health['status'] in ['healthy', 'degraded'] else 503
        return jsonify(health), status_code
    
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503


# =============================================================================
# CACHE MANAGEMENT ROUTES
# =============================================================================

@admin_bp.route('/cache/stats', methods=['GET'])
@require_auth
def get_cache_stats():
    """
    Get cache statistics (AUTHENTICATED)
    
    Returns basic Redis cache statistics:
    - Hit rate
    - Miss rate
    - Total keys
    - Memory usage
    
    Returns:
        200: Stats retrieved successfully
        500: Server error
    """
    try:
        stats = expense_service.get_cache_stats()
        return jsonify({'success': True, 'stats': stats}), 200
    
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/cache/stats/detailed', methods=['GET'])
@require_auth
def get_detailed_cache_stats():
    """
    Get detailed cache statistics (AUTHENTICATED)
    
    Returns comprehensive cache statistics:
    - Per-key hit/miss counts
    - Memory usage breakdown
    - TTL information
    - Eviction statistics
    
    Returns:
        200: Stats retrieved successfully
        500: Server error
    """
    try:
        stats = expense_service.get_detailed_cache_stats()
        return jsonify({'success': True, 'stats': stats}), 200
    
    except Exception as e:
        logger.error(f"Error getting detailed cache stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/cache/warm', methods=['POST'])
@require_auth
def warm_cache():
    """
    Warm up cache for current user (AUTHENTICATED)
    
    Pre-loads frequently accessed data for authenticated user:
    - User profile
    - User groups
    - Recent expenses
    - Balance calculations
    
    Improves subsequent request performance by 80-90%.
    
    Returns:
        200: Cache warmed successfully
        500: Server error
    """
    try:
        result = expense_service.warm_user_cache(g.user_id)
        return jsonify({
            'success': result.get('success', False),
            'stats': result
        }), 200
    
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# PERFORMANCE METRICS ROUTES
# =============================================================================

@admin_bp.route('/metrics', methods=['GET'])
@require_auth
def get_performance_metrics():
    """
    Get comprehensive performance metrics (AUTHENTICATED)
    
    Returns detailed performance information:
    - Cache statistics (hit rates, key counts)
    - Redis memory usage
    - System health indicators
    - Performance benchmarks
    
    Useful for performance monitoring dashboards.
    
    Returns:
        200: Metrics retrieved successfully
        500: Server error
    """
    try:
        metrics = expense_service.get_performance_metrics()
        return jsonify({
            'success': True,
            'metrics': metrics
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/rate-limits', methods=['GET'])
@require_auth
def get_rate_limits():
    """
    Get rate limit configuration and current usage (AUTHENTICATED)
    
    Returns rate limiting information:
    - Rate limit configurations for each operation type
    - Current usage stats (if available)
    - Limit reset times
    
    Useful for monitoring API usage and preventing abuse.
    
    Returns:
        200: Rate limits retrieved successfully
        500: Server error
    """
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from middleware import rate_limit_config
        
        # Build response with rate limit info
        response_data = {
            'success': True,
            'rate_limits': {
                'global': '200 per hour',
                'operations': rate_limit_config
            },
            'description': {
                'read_light': 'Simple GET requests (list operations)',
                'read_heavy': 'Complex queries with joins (full group data)',
                'create': 'Create expense or group',
                'update': 'Update expense',
                'delete': 'Delete operations',
                'settle': 'Settlement creation',
                'invitation': 'Send/accept invitations',
                'auth': 'Login/signup attempts'
            },
            'current_user': g.user_data.get('uid') if hasattr(g, 'user_data') else None
        }
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f"Error getting rate limits: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# REFERENCE DATA ROUTES
# =============================================================================

@admin_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Get list of expense categories (PUBLIC - no auth required)
    
    Returns all available expense categories for frontend dropdown menus.
    
    Returns:
        200: Categories retrieved
        
    Example Response:
        {
            'success': True,
            'categories': ['food', 'transport', 'entertainment', ...]
        }
    """
    categories = [cat.value for cat in ExpenseCategory]
    return jsonify({'success': True, 'categories': categories}), 200


@admin_bp.route('/split-types', methods=['GET'])
def get_split_types():
    """
    Get list of split types (PUBLIC - no auth required)
    
    Returns all available split types for frontend expense forms.
    
    Returns:
        200: Split types retrieved
        
    Example Response:
        {
            'success': True,
            'split_types': ['equal', 'exact', 'percentage', 'shares']
        }
    """
    split_types = [st.value for st in SplitType]
    return jsonify({'success': True, 'split_types': split_types}), 200


# =============================================================================
# PERFORMANCE MONITORING ROUTES (Week 3)
# =============================================================================

@admin_bp.route('/performance/report', methods=['GET'])
@require_auth
def get_performance_report():
    """
    Get performance report for specific date (AUTHENTICATED)
    
    Returns comprehensive performance metrics including:
    - API response times by endpoint
    - Slow operations (>1s)
    - Firestore operation costs
    - Performance summary
    
    Query Parameters:
        date (str): Date in YYYY-MM-DD format (default: today)
    
    Returns:
        200: Performance report
        500: Server error
    """
    try:
        from ..performance_monitor import get_performance_monitor
        
        date = request.args.get('date', None)
        performance_monitor = get_performance_monitor(expense_service.cache.redis_client)
        report = performance_monitor.get_performance_report(date)
        
        return jsonify({
            'success': True,
            'report': report
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/performance/slow-operations', methods=['GET'])
@require_auth
def get_slow_operations():
    """
    Get recent slow operations (AUTHENTICATED)
    
    Returns list of recent API calls that exceeded 1s threshold.
    Useful for identifying performance bottlenecks.
    
    Returns:
        200: Slow operations list
        500: Server error
    """
    try:
        from ..performance_monitor import get_performance_monitor
        
        performance_monitor = get_performance_monitor(expense_service.cache.redis_client)
        slow_ops = performance_monitor._get_slow_operations()
        
        return jsonify({
            'success': True,
            'slow_operations': slow_ops,
            'count': len(slow_ops)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting slow operations: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/performance/costs', methods=['GET'])
@require_auth
def get_firestore_costs():
    """
    Get Firebase/Firestore costs for date range (AUTHENTICATED)
    
    Returns detailed breakdown of Firestore operations and estimated costs.
    
    Query Parameters:
        date (str): Date in YYYY-MM-DD format (default: today)
    
    Returns:
        200: Cost breakdown
        500: Server error
    """
    try:
        from ..performance_monitor import get_performance_monitor
        from datetime import datetime, timedelta
        
        date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        performance_monitor = get_performance_monitor(expense_service.cache.redis_client)
        costs = performance_monitor._get_firestore_costs(date_str)
        
        return jsonify({
            'success': True,
            'date': date_str,
            'costs': costs
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting Firestore costs: {e}")
        return jsonify({'error': 'Internal server error'}), 500
