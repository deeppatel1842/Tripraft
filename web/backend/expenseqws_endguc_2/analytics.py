"""
Comprehensive Analytics Tracker for Expense Engine
==================================================

Tracks:
- API call counts and timing per endpoint
- Firestore operations (read/write/delete/search)
- Cache hit/miss rates
- Response times (min/avg/max)
- Errors and exceptions

Provides professional analytics dashboard data.

Author: AI Assistant
Date: 2025-11-21
"""

import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class AnalyticsTracker:
    """
    Thread-safe analytics tracker for API performance monitoring
    """
    
    def __init__(self):
        """Initialize analytics tracker"""
        self.lock = Lock()
        self.start_time = datetime.utcnow()
        
        # Endpoint metrics
        self.endpoint_calls = defaultdict(int)  # endpoint -> count
        self.endpoint_times = defaultdict(list)  # endpoint -> [times]
        self.endpoint_errors = defaultdict(int)  # endpoint -> error_count
        
        # Firestore operations
        self.firestore_ops = {
            'read': 0,
            'write': 0,
            'delete': 0,
            'search': 0
        }
        
        # Cache metrics
        self.cache_hits = defaultdict(int)  # cache_type -> hits
        self.cache_misses = defaultdict(int)  # cache_type -> misses
        
        # Request tracking
        self.total_requests = 0
        self.active_requests = 0
        
        logger.info("✅ AnalyticsTracker initialized")
    
    def track_request_start(self, endpoint: str) -> float:
        """
        Track the start of an API request
        
        Args:
            endpoint: API endpoint name (e.g., 'get_user_groups')
        
        Returns:
            Start timestamp for calculating duration
        """
        with self.lock:
            self.total_requests += 1
            self.active_requests += 1
            self.endpoint_calls[endpoint] += 1
        
        return time.time()
    
    def track_request_end(self, endpoint: str, start_time: float, error: bool = False):
        """
        Track the end of an API request
        
        Args:
            endpoint: API endpoint name
            start_time: Start timestamp from track_request_start()
            error: Whether the request resulted in an error
        """
        duration_ms = (time.time() - start_time) * 1000
        
        with self.lock:
            self.active_requests = max(0, self.active_requests - 1)
            self.endpoint_times[endpoint].append(duration_ms)
            
            if error:
                self.endpoint_errors[endpoint] += 1
    
    def track_firestore_op(self, operation: str, count: int = 1):
        """
        Track Firestore operations
        
        Args:
            operation: Operation type ('read', 'write', 'delete', 'search')
            count: Number of operations (default 1)
        """
        with self.lock:
            if operation in self.firestore_ops:
                self.firestore_ops[operation] += count
    
    def track_cache_hit(self, cache_type: str):
        """
        Track cache hit
        
        Args:
            cache_type: Type of cache (e.g., 'user_groups', 'group_details')
        """
        with self.lock:
            self.cache_hits[cache_type] += 1
    
    def track_cache_miss(self, cache_type: str):
        """
        Track cache miss
        
        Args:
            cache_type: Type of cache
        """
        with self.lock:
            self.cache_misses[cache_type] += 1
    
    def get_comprehensive_stats(self) -> Dict:
        """
        Get comprehensive analytics statistics
        
        Returns:
            Dictionary with all metrics
        """
        with self.lock:
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Calculate total cache operations
            total_cache_hits = sum(self.cache_hits.values())
            total_cache_misses = sum(self.cache_misses.values())
            total_cache_ops = total_cache_hits + total_cache_misses
            cache_hit_rate = (total_cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
            
            # Calculate average response time
            all_times = []
            for times in self.endpoint_times.values():
                all_times.extend(times)
            
            avg_response_time = sum(all_times) / len(all_times) if all_times else 0
            min_response_time = min(all_times) if all_times else 0
            max_response_time = max(all_times) if all_times else 0
            
            # Build endpoint breakdown
            endpoint_breakdown = {}
            for endpoint in self.endpoint_calls.keys():
                times = self.endpoint_times.get(endpoint, [])
                
                endpoint_breakdown[endpoint] = {
                    'count': self.endpoint_calls[endpoint],
                    'errors': self.endpoint_errors.get(endpoint, 0),
                    'avg_time': sum(times) / len(times) if times else 0,
                    'min_time': min(times) if times else 0,
                    'max_time': max(times) if times else 0,
                    'total_time': sum(times)
                }
            
            return {
                'uptime_seconds': uptime_seconds,
                'uptime_formatted': self._format_uptime(uptime_seconds),
                'total_api_calls': self.total_requests,
                'active_requests': self.active_requests,
                'firestore_operations': self.firestore_ops.copy(),
                'cache_stats': {
                    'hits': total_cache_hits,
                    'misses': total_cache_misses,
                    'hit_rate_percent': round(cache_hit_rate, 2),
                    'by_type': {
                        cache_type: {
                            'hits': self.cache_hits[cache_type],
                            'misses': self.cache_misses[cache_type],
                            'total': self.cache_hits[cache_type] + self.cache_misses[cache_type],
                            'hit_rate': round(
                                (self.cache_hits[cache_type] / (self.cache_hits[cache_type] + self.cache_misses[cache_type]) * 100)
                                if (self.cache_hits[cache_type] + self.cache_misses[cache_type]) > 0 else 0,
                                2
                            )
                        }
                        for cache_type in set(list(self.cache_hits.keys()) + list(self.cache_misses.keys()))
                    }
                },
                'response_times': {
                    'avg_ms': round(avg_response_time, 2),
                    'min_ms': round(min_response_time, 2),
                    'max_ms': round(max_response_time, 2)
                },
                'endpoint_breakdown': endpoint_breakdown,
                'total_errors': sum(self.endpoint_errors.values())
            }
    
    def get_endpoint_breakdown(self) -> Dict:
        """
        Get detailed per-endpoint metrics
        
        Returns:
            Dictionary with per-endpoint statistics
        """
        with self.lock:
            breakdown = {}
            
            for endpoint in self.endpoint_calls.keys():
                times = self.endpoint_times.get(endpoint, [])
                errors = self.endpoint_errors.get(endpoint, 0)
                count = self.endpoint_calls[endpoint]
                
                breakdown[endpoint] = {
                    'total_calls': count,
                    'success_calls': count - errors,
                    'error_calls': errors,
                    'error_rate_percent': round((errors / count * 100) if count > 0 else 0, 2),
                    'avg_response_time_ms': round(sum(times) / len(times), 2) if times else 0,
                    'min_response_time_ms': round(min(times), 2) if times else 0,
                    'max_response_time_ms': round(max(times), 2) if times else 0,
                    'total_execution_time_ms': round(sum(times), 2),
                    'p50_response_time_ms': round(self._percentile(times, 50), 2) if times else 0,
                    'p95_response_time_ms': round(self._percentile(times, 95), 2) if times else 0,
                    'p99_response_time_ms': round(self._percentile(times, 99), 2) if times else 0
                }
            
            return breakdown
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile from list of values"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _format_uptime(self, seconds: float) -> str:
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
        if secs > 0 or not parts:
            parts.append(f"{secs}s")
        
        return " ".join(parts)
    
    def reset_stats(self):
        """Reset all statistics (useful for testing)"""
        with self.lock:
            self.start_time = datetime.utcnow()
            self.endpoint_calls.clear()
            self.endpoint_times.clear()
            self.endpoint_errors.clear()
            self.firestore_ops = {'read': 0, 'write': 0, 'delete': 0, 'search': 0}
            self.cache_hits.clear()
            self.cache_misses.clear()
            self.total_requests = 0
            self.active_requests = 0
        
        logger.info("Analytics statistics reset")


# Global singleton instance
analytics_tracker = AnalyticsTracker()


# Export for use in other modules
__all__ = ['analytics_tracker', 'AnalyticsTracker']
