"""
Phase 5 Tests - Performance Monitoring
Tests for performance monitor, timing stats, and Flask integration

Run with: pytest tests/test_performance.py -v

Note: Tests access protected members for testing internal state,
which is normal practice in unit tests.
"""
# pylint: disable=protected-access,unused-argument
# pyright: reportUnusedVariable=false

import pytest
import time


# =========================================================================
# Test TimingStats
# =========================================================================

class TestTimingStats:
    """Tests for TimingStats dataclass"""
    
    def test_timing_stats_initial(self):
        """Test initial stats are zero/empty"""
        from expense_engine.monitoring.performance import TimingStats
        
        stats = TimingStats()
        assert stats.count == 0
        assert stats.total_ms == 0.0
        assert stats.min_ms == float('inf')
        assert stats.max_ms == 0.0
    
    def test_timing_stats_record(self):
        """Test recording timing"""
        from expense_engine.monitoring.performance import TimingStats
        
        stats = TimingStats()
        stats.record(100.0)
        
        assert stats.count == 1
        assert stats.total_ms == 100.0
        assert stats.min_ms == 100.0
        assert stats.max_ms == 100.0
    
    def test_timing_stats_avg_ms(self):
        """Test average calculation via avg_ms property"""
        from expense_engine.monitoring.performance import TimingStats
        
        stats = TimingStats()
        stats.record(100.0)
        stats.record(200.0)
        stats.record(300.0)
        
        assert stats.avg_ms == 200.0  # (100 + 200 + 300) / 3
    
    def test_timing_stats_avg_zero_when_empty(self):
        """Test avg_ms is zero when no recordings"""
        from expense_engine.monitoring.performance import TimingStats
        
        stats = TimingStats()
        assert stats.avg_ms == 0.0
    
    def test_timing_stats_min_max(self):
        """Test min/max tracking"""
        from expense_engine.monitoring.performance import TimingStats
        
        stats = TimingStats()
        stats.record(50.0)
        stats.record(200.0)
        stats.record(100.0)
        
        assert stats.min_ms == 50.0
        assert stats.max_ms == 200.0
    
    def test_timing_stats_percentile(self):
        """Test percentile calculations"""
        from expense_engine.monitoring.performance import TimingStats
        
        stats = TimingStats()
        # Add enough samples for meaningful percentiles
        for i in range(100):
            stats.record(float(i + 1))  # 1 to 100
        
        # P50 should be around 50
        assert 45 <= stats.percentile(50) <= 55
        # P95 should be around 95
        assert 90 <= stats.percentile(95) <= 100
        # P99 should be around 99
        assert 95 <= stats.percentile(99) <= 100
    
    def test_timing_stats_to_dict(self):
        """Test to_dict returns all fields"""
        from expense_engine.monitoring.performance import TimingStats
        
        stats = TimingStats()
        stats.record(100.0)
        
        result = stats.to_dict()
        
        assert 'count' in result
        assert 'total_ms' in result
        assert 'avg_ms' in result
        assert 'min_ms' in result
        assert 'max_ms' in result
        assert 'p50_ms' in result
        assert 'p95_ms' in result
        assert 'p99_ms' in result


# =========================================================================
# Test Counter
# =========================================================================

class TestCounter:
    """Tests for Counter class"""
    
    def test_counter_initial(self):
        """Test counter starts at zero"""
        from expense_engine.monitoring.performance import Counter
        
        counter = Counter()
        assert counter.value == 0
    
    def test_counter_inc(self):
        """Test counter inc method"""
        from expense_engine.monitoring.performance import Counter
        
        counter = Counter()
        counter.inc()
        counter.inc()
        
        assert counter.value == 2
    
    def test_counter_inc_by_value(self):
        """Test counter inc with specific amount"""
        from expense_engine.monitoring.performance import Counter
        
        counter = Counter()
        counter.inc(5)
        counter.inc(3)
        
        assert counter.value == 8
    
    def test_counter_reset(self):
        """Test counter reset"""
        from expense_engine.monitoring.performance import Counter
        
        counter = Counter()
        counter.inc(10)
        counter.reset()
        
        assert counter.value == 0
    
    def test_counter_with_labels(self):
        """Test counter with labels"""
        from expense_engine.monitoring.performance import Counter
        
        counter = Counter()
        counter.inc(1, endpoint="/api/test")
        counter.inc(2, endpoint="/api/test")
        counter.inc(1, endpoint="/api/other")
        
        assert counter.value == 4
        assert counter.get_by_label(endpoint="/api/test") == 3
        assert counter.get_by_label(endpoint="/api/other") == 1
    
    def test_counter_to_dict(self):
        """Test counter to_dict"""
        from expense_engine.monitoring.performance import Counter
        
        counter = Counter()
        counter.inc(5, operation="read")
        
        result = counter.to_dict()
        assert result['total'] == 5
        assert result['by_label'] is not None


# =========================================================================
# Test Gauge
# =========================================================================

class TestGauge:
    """Tests for Gauge class"""
    
    def test_gauge_initial(self):
        """Test gauge starts at zero by default"""
        from expense_engine.monitoring.performance import Gauge
        
        gauge = Gauge()
        assert gauge.value == 0.0
    
    def test_gauge_initial_value(self):
        """Test gauge with initial value"""
        from expense_engine.monitoring.performance import Gauge
        
        gauge = Gauge(initial=10.0)
        assert gauge.value == 10.0
    
    def test_gauge_set(self):
        """Test setting gauge value"""
        from expense_engine.monitoring.performance import Gauge
        
        gauge = Gauge()
        gauge.set(42.5)
        
        assert gauge.value == 42.5
    
    def test_gauge_inc(self):
        """Test gauge inc method"""
        from expense_engine.monitoring.performance import Gauge
        
        gauge = Gauge()
        gauge.set(10.0)
        gauge.inc(5.0)
        
        assert gauge.value == 15.0
    
    def test_gauge_dec(self):
        """Test gauge dec method"""
        from expense_engine.monitoring.performance import Gauge
        
        gauge = Gauge()
        gauge.set(10.0)
        gauge.dec(3.0)
        
        assert gauge.value == 7.0


# =========================================================================
# Test PerformanceMonitor
# =========================================================================

class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class"""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        PerformanceMonitor._instance = None
        yield
        PerformanceMonitor._instance = None
    
    def test_performance_monitor_singleton(self):
        """Test PerformanceMonitor is singleton"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor1 = PerformanceMonitor()
        monitor2 = PerformanceMonitor()
        
        assert monitor1 is monitor2
    
    def test_record_api_call(self):
        """Test recording API call"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        monitor.record_api_call("/api/test", "GET", 150.0, 200)
        monitor.record_api_call("/api/test", "GET", 200.0, 200)
        
        stats = monitor.get_endpoint_stats("/api/test", "GET")
        assert stats['count'] == 2
        assert stats['avg_ms'] == 175.0  # (150 + 200) / 2
    
    def test_record_firestore_read(self):
        """Test recording Firestore read operation"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        monitor.record_firestore_read(count=1, collection="users")
        monitor.record_firestore_read(count=2, collection="groups")
        
        stats = monitor.get_firestore_stats()
        assert stats['total_operations'] == 3
    
    def test_record_firestore_write(self):
        """Test recording Firestore write operation"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        monitor.record_firestore_write(count=1, collection="expenses")
        
        stats = monitor.get_firestore_stats()
        assert stats['total_operations'] == 1
    
    def test_cache_hit_miss(self):
        """Test recording cache hit/miss"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        monitor.record_cache_hit("default")
        monitor.record_cache_hit("default")
        monitor.record_cache_miss("default")
        
        stats = monitor.get_cache_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_rate'] == pytest.approx(2/3, rel=0.01)
    
    def test_active_requests(self):
        """Test active request tracking"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        assert monitor.active_requests == 0
        monitor.request_started()
        monitor.request_started()
        assert monitor.active_requests == 2
        monitor.request_ended()
        assert monitor.active_requests == 1
    
    def test_record_error(self):
        """Test recording error"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        monitor.record_error("api_error", endpoint="/api/test")
        monitor.record_error("api_error", endpoint="/api/other")
        
        summary = monitor.get_summary()
        assert summary['error_count'] == 2
    
    def test_get_summary(self):
        """Test getting comprehensive summary"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # Add some data
        monitor.record_api_call("/api/test", "GET", 100.0, 200)
        monitor.record_firestore_read(count=1, collection="test")
        monitor.record_cache_hit("default")
        
        summary = monitor.get_summary()
        
        assert 'uptime_seconds' in summary
        assert 'total_requests' in summary
        assert 'active_requests' in summary
        assert 'avg_latency_ms' in summary
        assert 'error_count' in summary
        assert 'error_rate' in summary
        assert 'cache_hit_rate' in summary
        assert 'firestore_operations' in summary
    
    def test_get_full_report(self):
        """Test getting full performance report"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        monitor.record_api_call("/api/test", "GET", 100.0, 200)
        
        report = monitor.get_full_report()
        
        assert 'generated_at' in report
        assert 'summary' in report
        assert 'api_endpoints' in report
        assert 'firestore' in report
        assert 'cache' in report
        assert 'errors' in report
    
    def test_reset(self):
        """Test resetting all stats"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        monitor.record_api_call("/api/test", "GET", 100.0, 200)
        monitor.record_cache_hit("default")
        
        monitor.reset()
        
        summary = monitor.get_summary()
        assert summary['total_requests'] == 0
        assert summary['cache_hit_rate'] == 0.0


# =========================================================================
# Test Performance Decorators
# =========================================================================

class TestPerformanceDecorators:
    """Tests for performance tracking decorators"""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        PerformanceMonitor._instance = None
        yield
        PerformanceMonitor._instance = None
    
    def test_track_performance_decorator(self):
        """Test @track_performance decorator"""
        from expense_engine.monitoring.performance import (
            track_performance,
            get_performance_monitor
        )
        
        @track_performance(endpoint="/api/test", method="GET")
        def api_handler():
            time.sleep(0.01)
            return {"success": True}
        
        result = api_handler()
        
        assert result == {"success": True}
        
        monitor = get_performance_monitor()
        stats = monitor.get_endpoint_stats("/api/test", "GET")
        assert stats['count'] == 1
        assert stats['avg_ms'] >= 10.0


# =========================================================================
# Test get_performance_monitor function
# =========================================================================

class TestGetPerformanceMonitor:
    """Tests for get_performance_monitor helper"""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test"""
        from expense_engine.monitoring.performance import PerformanceMonitor
        PerformanceMonitor._instance = None
        yield
        PerformanceMonitor._instance = None
    
    def test_returns_singleton(self):
        """Test returns singleton instance"""
        from expense_engine.monitoring.performance import (
            get_performance_monitor,
            PerformanceMonitor
        )
        
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2
        assert isinstance(monitor1, PerformanceMonitor)


# =========================================================================
# Test MetricType Enum
# =========================================================================

class TestMetricType:
    """Tests for MetricType enum"""
    
    def test_metric_types(self):
        """Test all metric types exist"""
        from expense_engine.monitoring.performance import MetricType
        
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.TIMER.value == "timer"
