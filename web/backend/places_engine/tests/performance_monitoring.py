"""
Phase 6: Performance Monitoring & Benchmarking Tools

Tools for:
- Real-time performance monitoring
- Cache hit rate tracking
- Firebase read count analysis
- Bottleneck identification
- Performance optimization reporting

Date: December 8, 2025
"""

import json
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class QueryMetric:
    """Individual query metric"""
    timestamp: datetime
    query: str
    query_type: str
    response_time_ms: float
    firebase_reads: int
    cache_hit: bool
    status_code: int
    error: str = None


@dataclass
class CacheMetric:
    """Cache performance metric"""
    timestamp: datetime
    query_type: str
    cache_hits: int
    cache_misses: int
    avg_hit_time_ms: float
    avg_miss_time_ms: float


@dataclass
class PerformanceReport:
    """Complete performance report"""
    test_name: str
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    
    # Response times
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    
    # Firebase reads
    total_firebase_reads: int
    avg_firebase_reads_per_request: float
    max_firebase_reads_per_request: int
    
    # Cache metrics
    cache_hit_rate: float
    cache_hits: int
    cache_misses: int
    avg_cached_response_time_ms: float
    avg_uncached_response_time_ms: float
    cache_speedup_factor: float
    
    # Targets met
    targets_met: Dict[str, bool] = field(default_factory=dict)
    
    # Bottlenecks identified
    bottlenecks: List[str] = field(default_factory=list)


class PerformanceMonitor:
    """Real-time performance monitoring"""
    
    def __init__(self, test_name: str = "Performance Test"):
        self.test_name = test_name
        self.start_time = datetime.now()
        self.metrics: List[QueryMetric] = []
        self.cache_metrics: List[CacheMetric] = []
    
    def record_query(self, query: str, query_type: str, response_time_ms: float,
                    firebase_reads: int, cache_hit: bool, status_code: int = 200,
                    error: str = None) -> None:
        """Record a query metric"""
        metric = QueryMetric(
            timestamp=datetime.now(),
            query=query,
            query_type=query_type,
            response_time_ms=response_time_ms,
            firebase_reads=firebase_reads,
            cache_hit=cache_hit,
            status_code=status_code,
            error=error
        )
        self.metrics.append(metric)
    
    def record_cache_metric(self, query_type: str, cache_hits: int, cache_misses: int,
                           avg_hit_time_ms: float, avg_miss_time_ms: float) -> None:
        """Record cache performance"""
        metric = CacheMetric(
            timestamp=datetime.now(),
            query_type=query_type,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            avg_hit_time_ms=avg_hit_time_ms,
            avg_miss_time_ms=avg_miss_time_ms
        )
        self.cache_metrics.append(metric)
    
    def get_response_times(self) -> List[float]:
        """Get all response times"""
        return [m.response_time_ms for m in self.metrics]
    
    def get_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not values:
            return 0
        sorted_vals = sorted(values)
        index = int((percentile / 100) * len(sorted_vals))
        return sorted_vals[min(index, len(sorted_vals) - 1)]
    
    def generate_report(self, targets: Dict[str, float] = None) -> PerformanceReport:
        """Generate comprehensive performance report"""
        if not self.metrics:
            return None
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Response times
        response_times = self.get_response_times()
        avg_time = sum(response_times) / len(response_times)
        
        # Successful/failed
        successful = [m for m in self.metrics if m.status_code == 200]
        failed = [m for m in self.metrics if m.status_code != 200]
        error_rate = len(failed) / len(self.metrics) if self.metrics else 0
        
        # Firebase reads
        total_reads = sum(m.firebase_reads for m in self.metrics)
        avg_reads = total_reads / len(self.metrics) if self.metrics else 0
        max_reads = max((m.firebase_reads for m in self.metrics), default=0)
        
        # Cache metrics
        cached_metrics = [m for m in self.metrics if m.cache_hit]
        uncached_metrics = [m for m in self.metrics if not m.cache_hit]
        cache_hit_rate = len(cached_metrics) / len(self.metrics) if self.metrics else 0
        
        cached_times = [m.response_time_ms for m in cached_metrics]
        uncached_times = [m.response_time_ms for m in uncached_metrics]
        
        avg_cached = sum(cached_times) / len(cached_times) if cached_times else 0
        avg_uncached = sum(uncached_times) / len(uncached_times) if uncached_times else 0
        speedup = avg_uncached / avg_cached if avg_cached > 0 else 0
        
        # Targets met
        targets_met = {}
        if targets:
            for target_name, target_value in targets.items():
                if 'response_time' in target_name:
                    if 'p95' in target_name:
                        metric_value = self.get_percentile(response_times, 95)
                    elif 'p99' in target_name:
                        metric_value = self.get_percentile(response_times, 99)
                    elif 'avg' in target_name:
                        metric_value = avg_time
                    elif 'max' in target_name:
                        metric_value = max(response_times)
                    else:
                        metric_value = avg_time
                    targets_met[target_name] = metric_value <= target_value
                elif 'cache_hit' in target_name:
                    targets_met[target_name] = cache_hit_rate >= target_value
                elif 'error_rate' in target_name:
                    targets_met[target_name] = error_rate <= target_value
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks()
        
        return PerformanceReport(
            test_name=self.test_name,
            start_time=self.start_time,
            end_time=end_time,
            total_duration_seconds=duration,
            total_requests=len(self.metrics),
            successful_requests=len(successful),
            failed_requests=len(failed),
            error_rate=error_rate,
            avg_response_time_ms=avg_time,
            p50_response_time_ms=self.get_percentile(response_times, 50),
            p95_response_time_ms=self.get_percentile(response_times, 95),
            p99_response_time_ms=self.get_percentile(response_times, 99),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            total_firebase_reads=total_reads,
            avg_firebase_reads_per_request=avg_reads,
            max_firebase_reads_per_request=max_reads,
            cache_hit_rate=cache_hit_rate,
            cache_hits=len(cached_metrics),
            cache_misses=len(uncached_metrics),
            avg_cached_response_time_ms=avg_cached,
            avg_uncached_response_time_ms=avg_uncached,
            cache_speedup_factor=speedup,
            targets_met=targets_met,
            bottlenecks=bottlenecks
        )
    
    def _identify_bottlenecks(self) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        if not self.metrics:
            return bottlenecks
        
        # High response time bottleneck
        response_times = self.get_response_times()
        avg_time = sum(response_times) / len(response_times)
        high_time_queries = [m for m in self.metrics if m.response_time_ms > avg_time * 2]
        if len(high_time_queries) > len(self.metrics) * 0.1:  # > 10%
            bottlenecks.append(f"High response times: {len(high_time_queries)} queries > {avg_time*2:.0f}ms")
        
        # High read count bottleneck
        read_counts = [m.firebase_reads for m in self.metrics]
        avg_reads = sum(read_counts) / len(read_counts)
        high_read_queries = [m for m in self.metrics if m.firebase_reads > avg_reads * 2]
        if high_read_queries:
            bottlenecks.append(f"High Firebase reads: {len(high_read_queries)} queries > {avg_reads*2:.0f} reads")
        
        # Low cache hit rate
        cache_hit_rate = sum(1 for m in self.metrics if m.cache_hit) / len(self.metrics)
        if cache_hit_rate < 0.5:
            bottlenecks.append(f"Low cache hit rate: {cache_hit_rate*100:.0f}% (target 60%+)")
        
        # Query-type specific issues
        query_type_times = defaultdict(list)
        for m in self.metrics:
            query_type_times[m.query_type].append(m.response_time_ms)
        
        for query_type, times in query_type_times.items():
            if times:
                avg = sum(times) / len(times)
                if query_type == 'country' and avg > 1000:
                    bottlenecks.append(f"Country search slow: {avg:.0f}ms (target <1000ms)")
                elif query_type == 'autocomplete' and avg > 100:
                    bottlenecks.append(f"Autocomplete slow: {avg:.0f}ms (target <100ms)")
        
        return bottlenecks
    
    def print_report(self, report: PerformanceReport) -> None:
        """Print formatted performance report"""
        print("\n" + "=" * 100)
        print(f"PERFORMANCE REPORT: {report.test_name}")
        print("=" * 100)
        
        print(f"\nTest Duration: {report.start_time.isoformat()} to {report.end_time.isoformat()}")
        print(f"Total Time: {report.total_duration_seconds:.2f} seconds")
        
        # Request metrics
        print("\n" + "-" * 100)
        print("REQUEST METRICS")
        print("-" * 100)
        print(f"  Total Requests:     {report.total_requests}")
        print(f"  Successful:         {report.successful_requests} ({(report.successful_requests/report.total_requests*100):.1f}%)")
        print(f"  Failed:             {report.failed_requests} ({report.error_rate*100:.1f}%)")
        
        # Response time metrics
        print("\n" + "-" * 100)
        print("RESPONSE TIME METRICS (milliseconds)")
        print("-" * 100)
        print(f"  Average:            {report.avg_response_time_ms:.2f}ms")
        print(f"  Median (P50):       {report.p50_response_time_ms:.2f}ms")
        print(f"  P95:                {report.p95_response_time_ms:.2f}ms")
        print(f"  P99:                {report.p99_response_time_ms:.2f}ms")
        print(f"  Min:                {report.min_response_time_ms:.2f}ms")
        print(f"  Max:                {report.max_response_time_ms:.2f}ms")
        
        # Firebase metrics
        print("\n" + "-" * 100)
        print("FIREBASE READ METRICS")
        print("-" * 100)
        print(f"  Total Reads:        {report.total_firebase_reads}")
        print(f"  Avg Per Request:    {report.avg_firebase_reads_per_request:.2f}")
        print(f"  Max Per Request:    {report.max_firebase_reads_per_request}")
        
        # Cache metrics
        print("\n" + "-" * 100)
        print("CACHE METRICS")
        print("-" * 100)
        print(f"  Cache Hit Rate:     {report.cache_hit_rate*100:.1f}%")
        print(f"  Cache Hits:         {report.cache_hits}")
        print(f"  Cache Misses:       {report.cache_misses}")
        print(f"  Avg Hit Time:       {report.avg_cached_response_time_ms:.2f}ms")
        print(f"  Avg Miss Time:      {report.avg_uncached_response_time_ms:.2f}ms")
        print(f"  Speedup Factor:     {report.cache_speedup_factor:.1f}x")
        
        # Targets
        if report.targets_met:
            print("\n" + "-" * 100)
            print("TARGETS")
            print("-" * 100)
            for target, met in report.targets_met.items():
                status = "✓ PASS" if met else "✗ FAIL"
                print(f"  {target}: {status}")
        
        # Bottlenecks
        if report.bottlenecks:
            print("\n" + "-" * 100)
            print("IDENTIFIED BOTTLENECKS")
            print("-" * 100)
            for i, bottleneck in enumerate(report.bottlenecks, 1):
                print(f"  {i}. {bottleneck}")
        
        print("\n" + "=" * 100 + "\n")
    
    def export_json(self, report: PerformanceReport, filename: str) -> None:
        """Export report as JSON"""
        data = {
            'test_name': report.test_name,
            'start_time': report.start_time.isoformat(),
            'end_time': report.end_time.isoformat(),
            'duration_seconds': report.total_duration_seconds,
            'requests': {
                'total': report.total_requests,
                'successful': report.successful_requests,
                'failed': report.failed_requests,
                'error_rate': report.error_rate,
            },
            'response_times': {
                'average_ms': report.avg_response_time_ms,
                'median_ms': report.p50_response_time_ms,
                'p95_ms': report.p95_response_time_ms,
                'p99_ms': report.p99_response_time_ms,
                'min_ms': report.min_response_time_ms,
                'max_ms': report.max_response_time_ms,
            },
            'firebase': {
                'total_reads': report.total_firebase_reads,
                'avg_reads_per_request': report.avg_firebase_reads_per_request,
                'max_reads_per_request': report.max_firebase_reads_per_request,
            },
            'cache': {
                'hit_rate': report.cache_hit_rate,
                'hits': report.cache_hits,
                'misses': report.cache_misses,
                'avg_hit_time_ms': report.avg_cached_response_time_ms,
                'avg_miss_time_ms': report.avg_uncached_response_time_ms,
                'speedup_factor': report.cache_speedup_factor,
            },
            'targets_met': report.targets_met,
            'bottlenecks': report.bottlenecks,
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Report exported to {filename}")


class BenchmarkComparator:
    """Compare performance across phases"""
    
    def __init__(self):
        self.phase_results: Dict[str, PerformanceReport] = {}
    
    def add_phase_result(self, phase_name: str, report: PerformanceReport) -> None:
        """Add phase result"""
        self.phase_results[phase_name] = report
    
    def compare_phases(self) -> Dict[str, any]:
        """Compare all phases"""
        if len(self.phase_results) < 2:
            return {}
        
        phases = sorted(self.phase_results.keys())
        baseline = self.phase_results[phases[0]]
        
        comparison = {
            'baseline': phases[0],
            'comparisons': {}
        }
        
        for phase in phases[1:]:
            current = self.phase_results[phase]
            
            time_improvement = ((baseline.avg_response_time_ms - current.avg_response_time_ms) / 
                               baseline.avg_response_time_ms * 100)
            read_improvement = ((baseline.avg_firebase_reads_per_request - 
                               current.avg_firebase_reads_per_request) / 
                              baseline.avg_firebase_reads_per_request * 100)
            cache_improvement = current.cache_hit_rate - baseline.cache_hit_rate
            
            comparison['comparisons'][phase] = {
                'response_time_improvement_percent': time_improvement,
                'firebase_reads_improvement_percent': read_improvement,
                'cache_hit_rate_improvement_percent': cache_improvement * 100,
            }
        
        return comparison
    
    def print_comparison(self) -> None:
        """Print phase comparison"""
        comparison = self.compare_phases()
        
        if not comparison.get('comparisons'):
            print("Need at least 2 phase results to compare")
            return
        
        print("\n" + "=" * 100)
        print("PHASE COMPARISON")
        print("=" * 100)
        print(f"\nBaseline Phase: {comparison['baseline']}")
        
        for phase, metrics in comparison['comparisons'].items():
            print(f"\n{phase}:")
            print(f"  Response Time Improvement: {metrics['response_time_improvement_percent']:+.1f}%")
            print(f"  Firebase Reads Improvement: {metrics['firebase_reads_improvement_percent']:+.1f}%")
            print(f"  Cache Hit Rate Improvement: {metrics['cache_hit_rate_improvement_percent']:+.1f}%")
        
        print("\n" + "=" * 100 + "\n")


if __name__ == '__main__':
    # Example usage
    monitor = PerformanceMonitor("Example Performance Test")
    
    # Simulate some metrics
    for i in range(100):
        cache_hit = i % 3 == 0  # ~33% cache hit rate
        response_time = 50 if cache_hit else 350
        
        monitor.record_query(
            query=f'test_{i}',
            query_type='city',
            response_time_ms=response_time,
            firebase_reads=0 if cache_hit else 1,
            cache_hit=cache_hit,
            status_code=200
        )
    
    # Define targets
    targets = {
        'avg_response_time': 300,
        'p95_response_time': 400,
        'cache_hit_rate': 0.5,
        'error_rate': 0.01,
    }
    
    # Generate and print report
    report = monitor.generate_report(targets)
    monitor.print_report(report)
    
    # Export to JSON
    monitor.export_json(report, 'performance_report.json')
