"""
Performance Routes
API endpoints for performance monitoring

Phase 5: Performance Optimization
"""

from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

performance_bp = Blueprint('performance', __name__, url_prefix='/api/expense/performance')


@performance_bp.route('', methods=['GET'])
def get_performance_stats():
    """
    Get performance statistics
    
    Returns:
        Performance metrics including API latency, Firestore operations, cache stats
    """
    try:
        from expense_engine.monitoring import get_performance_monitor
        
        monitor = get_performance_monitor()
        
        return jsonify({
            'success': True,
            'data': monitor.get_full_report()
        }), 200
        
    except Exception as e:
        logger.error("Error getting performance stats: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/summary', methods=['GET'])
def get_performance_summary():
    """
    Get performance summary (quick overview)
    
    Returns:
        Summary of uptime, requests, errors, latency
    """
    try:
        from expense_engine.monitoring import get_performance_monitor
        
        monitor = get_performance_monitor()
        
        return jsonify({
            'success': True,
            'data': monitor.get_summary()
        }), 200
        
    except Exception as e:
        logger.error("Error getting performance summary: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/firestore', methods=['GET'])
def get_firestore_stats():
    """
    Get Firestore operation statistics
    
    Returns:
        Reads, writes, deletes by collection
    """
    try:
        from expense_engine.monitoring import get_performance_monitor
        
        monitor = get_performance_monitor()
        
        return jsonify({
            'success': True,
            'data': monitor.get_firestore_stats()
        }), 200
        
    except Exception as e:
        logger.error("Error getting Firestore stats: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/cache', methods=['GET'])
def get_cache_stats():
    """
    Get cache statistics
    
    Returns:
        Cache hits, misses, hit rate
    """
    try:
        from expense_engine.monitoring import get_performance_monitor
        
        monitor = get_performance_monitor()
        
        return jsonify({
            'success': True,
            'data': monitor.get_cache_stats()
        }), 200
        
    except Exception as e:
        logger.error("Error getting cache stats: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/endpoints', methods=['GET'])
def get_endpoint_stats():
    """
    Get per-endpoint performance statistics
    
    Returns:
        Timing stats for each API endpoint
    """
    try:
        from expense_engine.monitoring import get_performance_monitor
        
        monitor = get_performance_monitor()
        
        return jsonify({
            'success': True,
            'data': monitor.get_api_stats()
        }), 200
        
    except Exception as e:
        logger.error("Error getting endpoint stats: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/reset', methods=['POST'])
def reset_stats():
    """
    Reset all performance statistics
    
    Returns:
        Success message
    """
    try:
        from expense_engine.monitoring import get_performance_monitor
        
        monitor = get_performance_monitor()
        monitor.reset()
        
        return jsonify({
            'success': True,
            'message': 'Performance statistics reset'
        }), 200
        
    except Exception as e:
        logger.error("Error resetting performance stats: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
