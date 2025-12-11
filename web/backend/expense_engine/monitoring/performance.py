"""
Performance Monitor - API Latency and Metrics Tracking
Enterprise-grade performance monitoring for expense_engine

Phase 5: Performance Optimization
"""

import time
import logging
import threading
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from functools import wraps
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics tracked"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    TIMER = "timer"


@dataclass
class TimingStats:
    """Statistics for timing data"""
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0
    _values: List[float] = field(default_factory=list)
    
    def record(self, value_ms: float):
        """Record a timing value"""
        self.count += 1
        self.total_ms += value_ms
        self.min_ms = min(self.min_ms, value_ms)
        self.max_ms = max(self.max_ms, value_ms)
        self._values.append(value_ms)
        
        # Keep only last 1000 values for percentile calculation
        if len(self._values) > 1000:
            self._values = self._values[-1000:]
    
    @property
    def avg_ms(self) -> float:
        """Calculate average"""
        return self.total_ms / self.count if self.count > 0 else 0.0
    
    def percentile(self, p: int) -> float:
        """Calculate percentile (e.g., 95 for P95)"""
        if not self._values:
            return 0.0
        sorted_values = sorted(self._values)
        idx = int(len(sorted_values) * p / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "count": self.count,
            "total_ms": round(self.total_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.min_ms != float('inf') else 0,
            "max_ms": round(self.max_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "p50_ms": round(self.percentile(50), 2),
            "p95_ms": round(self.percentile(95), 2),
            "p99_ms": round(self.percentile(99), 2),
        }


class Counter:
    """Thread-safe counter"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._value = 0
        self._labels: Dict[str, int] = defaultdict(int)
    
    def inc(self, value: int = 1, **labels):
        """Increment counter"""
        with self._lock:
            self._value += value
            if labels:
                label_key = json.dumps(labels, sort_keys=True)
                self._labels[label_key] += value
    
    @property
    def value(self) -> int:
        return self._value
    
    def get_by_label(self, **labels) -> int:
        """Get count for specific labels"""
        label_key = json.dumps(labels, sort_keys=True)
        return self._labels.get(label_key, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total": self._value,
            "by_label": dict(self._labels) if self._labels else None
        }
    
    def reset(self):
        """Reset counter"""
        with self._lock:
            self._value = 0
            self._labels.clear()


class Gauge:
    """Thread-safe gauge (can go up or down)"""
    
    def __init__(self, initial: float = 0.0):
        self._lock = threading.Lock()
        self._value = initial
    
    def set(self, value: float):
        """Set gauge value"""
        with self._lock:
            self._value = value
    
    def inc(self, value: float = 1.0):
        """Increment gauge"""
        with self._lock:
            self._value += value
    
    def dec(self, value: float = 1.0):
        """Decrement gauge"""
        with self._lock:
            self._value -= value
    
    @property
    def value(self) -> float:
        return self._value


class PerformanceMonitor:
    """
    Centralized performance monitoring for expense_engine
    
    Features:
    - API latency tracking with percentiles
    - Firestore operation counting
    - Cache hit rate monitoring
    - Error rate tracking
    - Slow operation alerting
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        slow_threshold_ms: int = 1000,
        enable_detailed_logging: bool = True,
        alert_callback: Optional[Callable[[str, Dict], None]] = None
    ):
        """
        Initialize performance monitor
        
        Args:
            slow_threshold_ms: Threshold for slow operation alerts
            enable_detailed_logging: Enable detailed performance logging
            alert_callback: Callback for slow operation alerts
        """
        if self._initialized:  # pylint: disable=access-member-before-definition
            return
        
        self.slow_threshold_ms = slow_threshold_ms
        self.enable_detailed_logging = enable_detailed_logging
        self.alert_callback = alert_callback
        
        # Metrics storage
        self._api_timings: Dict[str, TimingStats] = defaultdict(TimingStats)
        self._firestore_ops = Counter()
        self._cache_hits = Counter()
        self._cache_misses = Counter()
        self._errors = Counter()
        self._active_requests = Gauge()
        
        # Lock for thread safety
        self._metrics_lock = threading.Lock()
        
        # Start time for uptime tracking
        self._start_time = datetime.utcnow()
        
        self._initialized = True
        logger.info("Performance monitor initialized")
    
    # =========================================================================
    # API Timing Methods
    # =========================================================================
    
    def record_api_call(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        **metadata
    ):
        """
        Record API call timing
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
            **metadata: Additional metadata (user_id, group_id, etc.)
        """
        key = f"{method}:{endpoint}"
        
        with self._metrics_lock:
            self._api_timings[key].record(duration_ms)
        
        # Track errors
        if status_code >= 400:
            self._errors.inc(endpoint=endpoint, status=status_code)
        
        # Log slow operations
        if duration_ms > self.slow_threshold_ms:
            self._log_slow_operation(endpoint, method, duration_ms, metadata)
        
        # Detailed logging
        if self.enable_detailed_logging:
            logger.debug(
                "API: %s %s - %.0fms - %d",
                method, endpoint, duration_ms, status_code
            )
    
    def _log_slow_operation(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        metadata: Dict  # noqa: ARG002 pylint: disable=unused-argument
    ):
        """Log and alert on slow operations"""
        logger.warning(
            "SLOW: %s %s took %.0fms (threshold: %dms)",
            method, endpoint, duration_ms, self.slow_threshold_ms
        )
        
        if self.alert_callback:
            try:
                self.alert_callback("slow_operation", {
                    "endpoint": endpoint,
                    "method": method,
                    "duration_ms": duration_ms,
                    "threshold_ms": self.slow_threshold_ms,
                    "metadata": metadata
                })
            except (TypeError, ValueError) as e:
                logger.error("Alert callback failed: %s", str(e))
    
    # =========================================================================
    # Firestore Operation Tracking
    # =========================================================================
    
    def record_firestore_read(self, count: int = 1, collection: str = "unknown"):
        """Record Firestore read operation"""
        self._firestore_ops.inc(count, operation="read", collection=collection)
    
    def record_firestore_write(self, count: int = 1, collection: str = "unknown"):
        """Record Firestore write operation"""
        self._firestore_ops.inc(count, operation="write", collection=collection)
    
    def record_firestore_delete(self, count: int = 1, collection: str = "unknown"):
        """Record Firestore delete operation"""
        self._firestore_ops.inc(count, operation="delete", collection=collection)
    
    # =========================================================================
    # Cache Metrics
    # =========================================================================
    
    def record_cache_hit(self, cache_type: str = "default"):
        """Record cache hit"""
        self._cache_hits.inc(cache_type=cache_type)
    
    def record_cache_miss(self, cache_type: str = "default"):
        """Record cache miss"""
        self._cache_misses.inc(cache_type=cache_type)
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate overall cache hit rate"""
        total = self._cache_hits.value + self._cache_misses.value
        if total == 0:
            return 0.0
        return self._cache_hits.value / total
    
    # =========================================================================
    # Active Request Tracking
    # =========================================================================
    
    def request_started(self):
        """Mark request started"""
        self._active_requests.inc()
    
    def request_ended(self):
        """Mark request ended"""
        self._active_requests.dec()
    
    @property
    def active_requests(self) -> int:
        """Get current active request count"""
        return int(self._active_requests.value)
    
    # =========================================================================
    # Error Tracking
    # =========================================================================
    
    def record_error(
        self,
        error_type: str,
        endpoint: Optional[str] = None,
        **metadata  # noqa: ARG002 - Reserved for future use
    ):
        """Record error"""
        # Note: metadata captured for future extension (e.g., error details)
        _ = metadata  # Acknowledge captured kwargs
        self._errors.inc(error_type=error_type, endpoint=endpoint or "unknown")
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate (errors / total requests)"""
        total_requests = sum(t.count for t in self._api_timings.values())
        if total_requests == 0:
            return 0.0
        return self._errors.value / total_requests
    
    # =========================================================================
    # Statistics and Reporting
    # =========================================================================
    
    def get_api_stats(self) -> Dict[str, Dict]:
        """Get API timing statistics"""
        with self._metrics_lock:
            return {
                endpoint: stats.to_dict()
                for endpoint, stats in self._api_timings.items()
            }
    
    def get_endpoint_stats(self, endpoint: str, method: str = "GET") -> Dict:
        """Get stats for specific endpoint"""
        key = f"{method}:{endpoint}"
        with self._metrics_lock:
            if key in self._api_timings:
                return self._api_timings[key].to_dict()
        return {}
    
    def get_firestore_stats(self) -> Dict[str, Any]:
        """Get Firestore operation statistics"""
        return {
            "total_operations": self._firestore_ops.value,
            "by_type": self._firestore_ops.to_dict()
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "hits": self._cache_hits.value,
            "misses": self._cache_misses.value,
            "hit_rate": round(self.cache_hit_rate, 4),
            "hit_rate_percent": f"{self.cache_hit_rate * 100:.1f}%"
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        total_requests = sum(t.count for t in self._api_timings.values())
        total_latency = sum(t.total_ms for t in self._api_timings.values())
        
        return {
            "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds(),
            "total_requests": total_requests,
            "active_requests": self.active_requests,
            "avg_latency_ms": round(total_latency / total_requests, 2) if total_requests > 0 else 0,
            "error_count": self._errors.value,
            "error_rate": round(self.error_rate, 4),
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "firestore_operations": self._firestore_ops.value,
        }
    
    def get_full_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": self.get_summary(),
            "api_endpoints": self.get_api_stats(),
            "firestore": self.get_firestore_stats(),
            "cache": self.get_cache_stats(),
            "errors": self._errors.to_dict()
        }
    
    def reset(self):
        """Reset all metrics"""
        with self._metrics_lock:
            self._api_timings.clear()
        self._firestore_ops.reset()
        self._cache_hits.reset()
        self._cache_misses.reset()
        self._errors.reset()
        self._active_requests.set(0)
        self._start_time = datetime.utcnow()
        logger.info("Performance metrics reset")


# =========================================================================
# Decorators
# =========================================================================

def track_performance(endpoint: Optional[str] = None, method: str = "GET"):
    """
    Decorator to track function/endpoint performance
    
    Args:
        endpoint: Endpoint name (defaults to function name)
        method: HTTP method
        
    Returns:
        Decorated function
        
    Example:
        @track_performance(endpoint="/groups/{group_id}", method="GET")
        def get_group(group_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            endpoint_name = endpoint or f"/{func.__name__}"
            
            monitor.request_started()
            start_time = time.perf_counter()
            status_code = 200
            
            try:
                result = func(*args, **kwargs)
                
                # Try to extract status code from Flask response
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                elif isinstance(result, tuple) and len(result) > 1:
                    status_code = result[1]
                
                return result
                
            except Exception as e:
                status_code = 500
                monitor.record_error(
                    error_type=type(e).__name__,
                    endpoint=endpoint_name
                )
                raise
                
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                monitor.request_ended()
                monitor.record_api_call(
                    endpoint=endpoint_name,
                    method=method,
                    duration_ms=duration_ms,
                    status_code=status_code
                )
        
        return wrapper
    
    return decorator


def track_firestore(operation: str = "read", collection: str = "unknown"):
    """
    Decorator to track Firestore operations
    
    Args:
        operation: Type of operation (read, write, delete)
        collection: Collection name
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            
            result = func(*args, **kwargs)
            
            # Record operation
            if operation == "read":
                monitor.record_firestore_read(collection=collection)
            elif operation == "write":
                monitor.record_firestore_write(collection=collection)
            elif operation == "delete":
                monitor.record_firestore_delete(collection=collection)
            
            return result
        
        return wrapper
    
    return decorator


def track_cache(cache_type: str = "default"):
    """
    Decorator to track cache operations
    
    The decorated function should return a tuple: (value, was_cached)
    
    Args:
        cache_type: Type of cache being used
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            
            result = func(*args, **kwargs)
            
            # Check if result indicates cache status
            if isinstance(result, tuple) and len(result) == 2:
                value, was_cached = result
                if was_cached:
                    monitor.record_cache_hit(cache_type=cache_type)
                else:
                    monitor.record_cache_miss(cache_type=cache_type)
                return value
            
            return result
        
        return wrapper
    
    return decorator


class Timer:
    """Context manager for timing code blocks"""
    
    def __init__(self, name: str, monitor: Optional[PerformanceMonitor] = None):
        self.name = name
        self.monitor = monitor or get_performance_monitor()
        self.start_time = None
        self.duration_ms = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000
        
        # Record as API call with custom endpoint
        self.monitor.record_api_call(
            endpoint=f"timer:{self.name}",
            method="TIMER",
            duration_ms=self.duration_ms,
            status_code=500 if exc_type else 200
        )
        
        return False  # Don't suppress exceptions


# =========================================================================
# Global Monitor Instance
# =========================================================================

_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor  # pylint: disable=global-statement
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def configure_performance_monitor(
    slow_threshold_ms: int = 1000,
    enable_detailed_logging: bool = True,
    alert_callback: Optional[Callable[[str, Dict], None]] = None
):
    """Configure the global performance monitor"""
    global _performance_monitor  # pylint: disable=global-statement
    _performance_monitor = PerformanceMonitor(
        slow_threshold_ms=slow_threshold_ms,
        enable_detailed_logging=enable_detailed_logging,
        alert_callback=alert_callback
    )
    return _performance_monitor


# =========================================================================
# Flask Integration
# =========================================================================

def init_flask_performance(app):
    """
    Initialize performance monitoring for Flask app
    
    Args:
        app: Flask application instance
    """
    monitor = get_performance_monitor()
    
    @app.before_request
    def before_request():
        from flask import g
        g.start_time = time.perf_counter()
        monitor.request_started()
    
    @app.after_request
    def after_request(response):
        from flask import g, request
        
        if hasattr(g, 'start_time'):
            duration_ms = (time.perf_counter() - g.start_time) * 1000
            monitor.request_ended()
            monitor.record_api_call(
                endpoint=request.endpoint or request.path,
                method=request.method,
                duration_ms=duration_ms,
                status_code=response.status_code
            )
        
        return response
    
    @app.teardown_request
    def teardown_request(exception):
        if exception:
            from flask import request
            monitor.record_error(
                error_type=type(exception).__name__,
                endpoint=request.endpoint or request.path
            )
    
    logger.info("Flask performance monitoring initialized")


# =========================================================================
# Cost Estimation
# =========================================================================

class FirestoreCostTracker:
    """Track and estimate Firestore costs"""
    
    # Firestore pricing (as of 2024)
    PRICES = {
        'read': 0.06 / 100_000,      # $0.06 per 100K reads
        'write': 0.18 / 100_000,     # $0.18 per 100K writes
        'delete': 0.02 / 100_000,    # $0.02 per 100K deletes
        'storage_gb': 0.18           # $0.18 per GB per month
    }
    
    def __init__(self):
        self.reads = 0
        self.writes = 0
        self.deletes = 0
        self._lock = threading.Lock()
    
    def record_read(self, count: int = 1):
        with self._lock:
            self.reads += count
    
    def record_write(self, count: int = 1):
        with self._lock:
            self.writes += count
    
    def record_delete(self, count: int = 1):
        with self._lock:
            self.deletes += count
    
    def estimate_cost(self) -> Dict[str, float]:
        """Estimate current costs"""
        return {
            'reads_cost': self.reads * self.PRICES['read'],
            'writes_cost': self.writes * self.PRICES['write'],
            'deletes_cost': self.deletes * self.PRICES['delete'],
            'total_cost': (
                self.reads * self.PRICES['read'] +
                self.writes * self.PRICES['write'] +
                self.deletes * self.PRICES['delete']
            ),
            'operations': {
                'reads': self.reads,
                'writes': self.writes,
                'deletes': self.deletes
            }
        }
    
    def reset(self):
        with self._lock:
            self.reads = 0
            self.writes = 0
            self.deletes = 0
