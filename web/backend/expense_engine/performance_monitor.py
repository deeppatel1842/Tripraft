"""
Performance Monitoring System
Tracks API response times, slow operations, and Firebase costs
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Real-time performance monitoring system
    
    Features:
    - Track all API response times
    - Alert on slow operations (>1s)
    - Daily performance reports
    - Firebase cost tracking
    """
    
    def __init__(self, redis_client=None):
        """Initialize performance monitor"""
        self.redis_client = redis_client
        self.slow_threshold_ms = 1000  # Alert if operation > 1s
        
        # In-memory stats (fallback if Redis unavailable)
        self.api_calls = defaultdict(list)
        self.slow_operations = []
        
        logger.info("📊 Performance monitor initialized")
    
    def track_api_call(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        user_id: Optional[str] = None,
        firestore_reads: int = 0,
        firestore_writes: int = 0
    ):
        """
        Track API call performance
        
        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
            user_id: Optional user ID
            firestore_reads: Number of Firestore read operations
            firestore_writes: Number of Firestore write operations
        """
        try:
            timestamp = datetime.utcnow()
            
            metric = {
                'endpoint': endpoint,
                'method': method,
                'duration_ms': duration_ms,
                'status_code': status_code,
                'user_id': user_id,
                'firestore_reads': firestore_reads,
                'firestore_writes': firestore_writes,
                'timestamp': timestamp.isoformat()
            }
            
            # Store in Redis if available
            if self.redis_client:
                try:
                    key = f"perf:api_calls:{timestamp.strftime('%Y-%m-%d')}"
                    self.redis_client.lpush(key, json.dumps(metric))
                    self.redis_client.expire(key, 86400 * 7)  # Keep 7 days
                    
                    # Track Firestore operations
                    if firestore_reads > 0:
                        self._track_firestore_operation('reads', firestore_reads)
                    if firestore_writes > 0:
                        self._track_firestore_operation('writes', firestore_writes)
                    
                except Exception as redis_error:
                    logger.warning(f"Redis error (tracking in memory): {redis_error}")
                    self.api_calls[endpoint].append(metric)
            else:
                # Fallback to in-memory storage
                self.api_calls[endpoint].append(metric)
            
            # Alert on slow operations
            if duration_ms > self.slow_threshold_ms:
                self._alert_slow_operation(metric)
            
            # Log performance
            emoji = '🟢' if duration_ms < 500 else '🟡' if duration_ms < 1000 else '🔴'
            logger.info(
                f"{emoji} {method} {endpoint}: {duration_ms:.0f}ms "
                f"(reads: {firestore_reads}, writes: {firestore_writes})"
            )
            
        except Exception as e:
            logger.error(f"Error tracking API call: {e}")
    
    def _track_firestore_operation(self, operation_type: str, count: int):
        """Track Firestore operations for cost monitoring"""
        try:
            today = datetime.utcnow().strftime('%Y-%m-%d')
            key = f"perf:firestore:{today}:{operation_type}"
            self.redis_client.incrby(key, count)
            self.redis_client.expire(key, 86400 * 30)  # Keep 30 days
        except Exception as e:
            logger.warning(f"Error tracking Firestore operation: {e}")
    
    def _alert_slow_operation(self, metric: Dict):
        """Alert on slow operations"""
        try:
            # Store slow operation
            if self.redis_client:
                key = "perf:slow_operations"
                self.redis_client.lpush(key, json.dumps(metric))
                self.redis_client.ltrim(key, 0, 99)  # Keep last 100
            else:
                self.slow_operations.append(metric)
                if len(self.slow_operations) > 100:
                    self.slow_operations.pop(0)
            
            # Log alert
            logger.warning(
                f"⚠️ SLOW OPERATION: {metric['method']} {metric['endpoint']} "
                f"took {metric['duration_ms']:.0f}ms (threshold: {self.slow_threshold_ms}ms)"
            )
            
        except Exception as e:
            logger.error(f"Error alerting slow operation: {e}")
    
    def get_performance_report(self, date: Optional[str] = None) -> Dict:
        """
        Generate performance report for specific date
        
        Args:
            date: Date string (YYYY-MM-DD) or None for today
        
        Returns:
            Performance report dictionary
        """
        try:
            if date is None:
                date = datetime.utcnow().strftime('%Y-%m-%d')
            
            report = {
                'date': date,
                'api_performance': self._get_api_performance(date),
                'slow_operations': self._get_slow_operations(),
                'firestore_costs': self._get_firestore_costs(date),
                'summary': {}
            }
            
            # Calculate summary
            api_perf = report['api_performance']
            if api_perf['total_calls'] > 0:
                report['summary'] = {
                    'total_calls': api_perf['total_calls'],
                    'avg_response_time': api_perf['avg_response_time'],
                    'slow_calls': len(report['slow_operations']),
                    'slow_call_percentage': (len(report['slow_operations']) / api_perf['total_calls']) * 100,
                    'total_firestore_reads': report['firestore_costs']['reads'],
                    'total_firestore_writes': report['firestore_costs']['writes'],
                    'estimated_cost_usd': report['firestore_costs']['estimated_cost']
                }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {'error': str(e)}
    
    def _get_api_performance(self, date: str) -> Dict:
        """Get API performance metrics for date"""
        try:
            if self.redis_client:
                key = f"perf:api_calls:{date}"
                calls_json = self.redis_client.lrange(key, 0, -1)
                
                if not calls_json:
                    return {'total_calls': 0}
                
                calls = [json.loads(c) for c in calls_json]
                
                total_calls = len(calls)
                total_duration = sum(c['duration_ms'] for c in calls)
                avg_duration = total_duration / total_calls if total_calls > 0 else 0
                
                # Group by endpoint
                endpoint_stats = defaultdict(lambda: {'count': 0, 'total_ms': 0})
                for call in calls:
                    endpoint = call['endpoint']
                    endpoint_stats[endpoint]['count'] += 1
                    endpoint_stats[endpoint]['total_ms'] += call['duration_ms']
                
                # Calculate averages
                endpoint_averages = {}
                for endpoint, stats in endpoint_stats.items():
                    endpoint_averages[endpoint] = {
                        'count': stats['count'],
                        'avg_ms': stats['total_ms'] / stats['count']
                    }
                
                return {
                    'total_calls': total_calls,
                    'avg_response_time': avg_duration,
                    'by_endpoint': endpoint_averages
                }
            else:
                # Use in-memory data
                total_calls = sum(len(calls) for calls in self.api_calls.values())
                return {'total_calls': total_calls}
                
        except Exception as e:
            logger.error(f"Error getting API performance: {e}")
            return {'error': str(e)}
    
    def _get_slow_operations(self) -> List[Dict]:
        """Get recent slow operations"""
        try:
            if self.redis_client:
                key = "perf:slow_operations"
                slow_ops_json = self.redis_client.lrange(key, 0, 9)  # Last 10
                return [json.loads(op) for op in slow_ops_json]
            else:
                return self.slow_operations[-10:]  # Last 10
                
        except Exception as e:
            logger.error(f"Error getting slow operations: {e}")
            return []
    
    def _get_firestore_costs(self, date: str) -> Dict:
        """Calculate Firestore costs for date"""
        try:
            if self.redis_client:
                reads_key = f"perf:firestore:{date}:reads"
                writes_key = f"perf:firestore:{date}:writes"
                
                reads = int(self.redis_client.get(reads_key) or 0)
                writes = int(self.redis_client.get(writes_key) or 0)
                
                # Firebase pricing (as of 2025)
                # Reads: $0.06 per 100,000 reads
                # Writes: $0.18 per 100,000 writes
                read_cost = (reads / 100000) * 0.06
                write_cost = (writes / 100000) * 0.18
                
                return {
                    'reads': reads,
                    'writes': writes,
                    'read_cost_usd': round(read_cost, 4),
                    'write_cost_usd': round(write_cost, 4),
                    'estimated_cost': round(read_cost + write_cost, 4)
                }
            else:
                return {'reads': 0, 'writes': 0, 'estimated_cost': 0}
                
        except Exception as e:
            logger.error(f"Error calculating Firestore costs: {e}")
            return {'error': str(e)}


# Singleton instance
_performance_monitor = None


def get_performance_monitor(redis_client=None) -> PerformanceMonitor:
    """Get or create performance monitor singleton"""
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(redis_client)
    
    return _performance_monitor
