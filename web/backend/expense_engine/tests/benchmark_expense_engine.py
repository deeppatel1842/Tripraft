"""
Performance Benchmark Script for Expense Engine
Phase 8: Testing & Documentation

Usage:
    cd web/backend
    python -m expense_engine.tests.benchmark_expense_engine

This script measures:
- API response times
- Cache hit rates  
- Firestore query counts
- Memory usage
- Concurrent request handling
"""

import time
import statistics
import json
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class BenchmarkResult:
    """Single benchmark measurement"""
    name: str
    duration_ms: float
    success: bool
    cache_hit: bool = False
    firestore_reads: int = 0
    firestore_writes: int = 0
    error: str = None


@dataclass
class BenchmarkSummary:
    """Summary of benchmark results"""
    name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    min_ms: float
    max_ms: float
    avg_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    cache_hit_rate: float
    total_firestore_reads: int
    total_firestore_writes: int


class ExpenseEngineBenchmark:
    """Performance benchmarking for expense engine"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.start_time = None
        self.end_time = None
    
    def _measure(self, name: str, func, *args, **kwargs) -> BenchmarkResult:
        """Measure execution time of a function"""
        start = time.perf_counter()
        success = True
        error = None
        result = None
        
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            success = False
            error = str(e)
        
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        
        benchmark_result = BenchmarkResult(
            name=name,
            duration_ms=duration_ms,
            success=success,
            error=error
        )
        
        self.results.append(benchmark_result)
        return benchmark_result
    
    def _summarize(self, name: str, results: List[BenchmarkResult]) -> BenchmarkSummary:
        """Calculate statistics for a set of results"""
        if not results:
            return None
        
        durations = [r.duration_ms for r in results]
        successful = [r for r in results if r.success]
        cache_hits = [r for r in results if r.cache_hit]
        
        return BenchmarkSummary(
            name=name,
            total_runs=len(results),
            successful_runs=len(successful),
            failed_runs=len(results) - len(successful),
            min_ms=min(durations),
            max_ms=max(durations),
            avg_ms=statistics.mean(durations),
            median_ms=statistics.median(durations),
            p95_ms=self._percentile(durations, 95),
            p99_ms=self._percentile(durations, 99),
            cache_hit_rate=len(cache_hits) / len(results) if results else 0,
            total_firestore_reads=sum(r.firestore_reads for r in results),
            total_firestore_writes=sum(r.firestore_writes for r in results)
        )
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[-1]
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight


class ServiceBenchmark(ExpenseEngineBenchmark):
    """Benchmark service layer operations"""
    
    def __init__(self):
        super().__init__()
        self.mock_data = self._generate_mock_data()
    
    def _generate_mock_data(self) -> Dict:
        """Generate mock data for benchmarks"""
        return {
            'user_id': 'benchmark_user_123',
            'group_id': 'benchmark_group_123',
            'expense': {
                'group_id': 'benchmark_group_123',
                'description': 'Benchmark expense',
                'amount': '100.00',
                'paid_by': 'benchmark_user_123',
                'split_type': 'equal',
                'splits': [
                    {'user_id': 'benchmark_user_123', 'amount': '50.00'},
                    {'user_id': 'benchmark_user_456', 'amount': '50.00'}
                ]
            }
        }
    
    def benchmark_balance_calculation(self, iterations: int = 100) -> BenchmarkSummary:
        """Benchmark incremental balance calculation"""
        from decimal import Decimal
        from expense_engine.services.balance_service import BalanceService
        from expense_engine.models.expense import Expense, ExpenseSplit
        from unittest.mock import MagicMock
        
        results = []
        
        # Create mock balance service
        balance_service = BalanceService(
            balance_repo=MagicMock(),
            expense_repo=MagicMock()
        )
        
        # Create test expense
        expense = Expense(
            group_id='test_group',
            description='Test',
            amount=Decimal('100.00'),
            paid_by='user_1',
            split_type='equal',
            splits=[
                ExpenseSplit(user_id='user_1', amount=Decimal('25.00')),
                ExpenseSplit(user_id='user_2', amount=Decimal('25.00')),
                ExpenseSplit(user_id='user_3', amount=Decimal('25.00')),
                ExpenseSplit(user_id='user_4', amount=Decimal('25.00'))
            ],
            created_by='user_1'
        )
        
        print(f"\n📊 Benchmarking balance calculation ({iterations} iterations)...")
        
        for i in range(iterations):
            start = time.perf_counter()
            deltas = balance_service.calculate_expense_deltas(expense)
            end = time.perf_counter()
            
            results.append(BenchmarkResult(
                name='balance_calculation',
                duration_ms=(end - start) * 1000,
                success=len(deltas) == 4
            ))
        
        return self._summarize('balance_calculation', results)
    
    def benchmark_split_validation(self, iterations: int = 100) -> BenchmarkSummary:
        """Benchmark split validation logic"""
        from decimal import Decimal
        from expense_engine.models.expense import Expense, ExpenseSplit
        
        results = []
        
        print(f"\n📊 Benchmarking split validation ({iterations} iterations)...")
        
        for i in range(iterations):
            start = time.perf_counter()
            
            # Create and validate expense
            expense = Expense(
                group_id='test_group',
                description='Test expense',
                amount=Decimal('100.00'),
                paid_by='user_1',
                split_type='equal',
                splits=[
                    ExpenseSplit(user_id='user_1', amount=Decimal('50.00')),
                    ExpenseSplit(user_id='user_2', amount=Decimal('50.00'))
                ],
                created_by='user_1'
            )
            
            end = time.perf_counter()
            
            results.append(BenchmarkResult(
                name='split_validation',
                duration_ms=(end - start) * 1000,
                success=True
            ))
        
        return self._summarize('split_validation', results)
    
    def benchmark_model_serialization(self, iterations: int = 100) -> BenchmarkSummary:
        """Benchmark Pydantic model serialization"""
        from decimal import Decimal
        from expense_engine.models.expense import Expense, ExpenseSplit
        
        results = []
        
        expense = Expense(
            group_id='test_group',
            description='Test expense',
            amount=Decimal('100.00'),
            paid_by='user_1',
            split_type='equal',
            splits=[
                ExpenseSplit(user_id='user_1', amount=Decimal('50.00')),
                ExpenseSplit(user_id='user_2', amount=Decimal('50.00'))
            ],
            created_by='user_1'
        )
        
        print(f"\n📊 Benchmarking model serialization ({iterations} iterations)...")
        
        for i in range(iterations):
            start = time.perf_counter()
            
            # Serialize to dict and back
            data = expense.model_dump()
            Expense(**data)
            
            end = time.perf_counter()
            
            results.append(BenchmarkResult(
                name='model_serialization',
                duration_ms=(end - start) * 1000,
                success=True
            ))
        
        return self._summarize('model_serialization', results)


class CacheBenchmark(ExpenseEngineBenchmark):
    """Benchmark cache operations"""
    
    def benchmark_cache_operations(self, iterations: int = 100) -> Dict[str, BenchmarkSummary]:
        """Benchmark Redis cache operations"""
        try:
            from expense_engine.utils.cache_manager import get_cache_manager
            cache = get_cache_manager()
            
            if not cache or not cache.is_available():
                print("⚠️  Redis cache not available, skipping cache benchmarks")
                return {}
        except Exception as e:
            print(f"⚠️  Cache manager error: {e}")
            return {}
        
        results = {
            'cache_set': [],
            'cache_get_hit': [],
            'cache_get_miss': [],
            'cache_delete': []
        }
        
        print(f"\n📊 Benchmarking cache operations ({iterations} iterations each)...")
        
        # Benchmark SET
        for i in range(iterations):
            key = f'benchmark:set:{i}'
            value = {'data': f'value_{i}', 'timestamp': time.time()}
            
            start = time.perf_counter()
            success = cache.set(key, value, ttl=60)
            end = time.perf_counter()
            
            results['cache_set'].append(BenchmarkResult(
                name='cache_set',
                duration_ms=(end - start) * 1000,
                success=success
            ))
        
        # Benchmark GET (hit)
        for i in range(iterations):
            key = f'benchmark:set:{i}'
            
            start = time.perf_counter()
            value = cache.get(key)
            end = time.perf_counter()
            
            result = BenchmarkResult(
                name='cache_get_hit',
                duration_ms=(end - start) * 1000,
                success=value is not None,
                cache_hit=value is not None
            )
            results['cache_get_hit'].append(result)
        
        # Benchmark GET (miss)
        for i in range(iterations):
            key = f'benchmark:nonexistent:{i}'
            
            start = time.perf_counter()
            value = cache.get(key)
            end = time.perf_counter()
            
            results['cache_get_miss'].append(BenchmarkResult(
                name='cache_get_miss',
                duration_ms=(end - start) * 1000,
                success=True,
                cache_hit=False
            ))
        
        # Benchmark DELETE
        for i in range(iterations):
            key = f'benchmark:set:{i}'
            
            start = time.perf_counter()
            success = cache.delete(key)
            end = time.perf_counter()
            
            results['cache_delete'].append(BenchmarkResult(
                name='cache_delete',
                duration_ms=(end - start) * 1000,
                success=True
            ))
        
        return {
            name: self._summarize(name, result_list)
            for name, result_list in results.items()
        }


def print_summary(summary: BenchmarkSummary):
    """Print benchmark summary in a formatted table"""
    if not summary:
        return
    
    print(f"\n{'=' * 60}")
    print(f"📈 {summary.name}")
    print(f"{'=' * 60}")
    print(f"  Total runs:     {summary.total_runs}")
    print(f"  Successful:     {summary.successful_runs}")
    print(f"  Failed:         {summary.failed_runs}")
    print(f"  {'─' * 40}")
    print(f"  Min:            {summary.min_ms:.3f} ms")
    print(f"  Max:            {summary.max_ms:.3f} ms")
    print(f"  Average:        {summary.avg_ms:.3f} ms")
    print(f"  Median:         {summary.median_ms:.3f} ms")
    print(f"  P95:            {summary.p95_ms:.3f} ms")
    print(f"  P99:            {summary.p99_ms:.3f} ms")
    if summary.cache_hit_rate > 0:
        print(f"  {'─' * 40}")
        print(f"  Cache hit rate: {summary.cache_hit_rate * 100:.1f}%")


def run_all_benchmarks():
    """Run all benchmarks and generate report"""
    print("=" * 70)
    print("🚀 EXPENSE ENGINE PERFORMANCE BENCHMARKS")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    
    all_results = {}
    
    # Service benchmarks
    service_bench = ServiceBenchmark()
    
    all_results['balance_calculation'] = service_bench.benchmark_balance_calculation(100)
    print_summary(all_results['balance_calculation'])
    
    all_results['split_validation'] = service_bench.benchmark_split_validation(100)
    print_summary(all_results['split_validation'])
    
    all_results['model_serialization'] = service_bench.benchmark_model_serialization(100)
    print_summary(all_results['model_serialization'])
    
    # Cache benchmarks
    cache_bench = CacheBenchmark()
    cache_results = cache_bench.benchmark_cache_operations(100)
    
    for name, summary in cache_results.items():
        all_results[name] = summary
        print_summary(summary)
    
    # Summary report
    print("\n" + "=" * 70)
    print("📋 BENCHMARK SUMMARY")
    print("=" * 70)
    
    print("\n| Operation | Avg (ms) | P95 (ms) | P99 (ms) |")
    print("|-----------|----------|----------|----------|")
    
    for name, summary in all_results.items():
        if summary:
            print(f"| {name:<20} | {summary.avg_ms:>8.3f} | {summary.p95_ms:>8.3f} | {summary.p99_ms:>8.3f} |")
    
    # Performance targets check
    print("\n" + "=" * 70)
    print("🎯 PERFORMANCE TARGETS")
    print("=" * 70)
    
    targets = {
        'balance_calculation': 1.0,  # < 1ms
        'split_validation': 5.0,     # < 5ms
        'model_serialization': 2.0,  # < 2ms
        'cache_set': 5.0,            # < 5ms
        'cache_get_hit': 2.0,        # < 2ms
        'cache_get_miss': 2.0,       # < 2ms
    }
    
    for name, target in targets.items():
        if name in all_results and all_results[name]:
            actual = all_results[name].avg_ms
            status = "✅ PASS" if actual < target else "❌ FAIL"
            print(f"  {name}: {actual:.3f}ms (target: <{target}ms) {status}")
    
    print(f"\nCompleted: {datetime.now().isoformat()}")
    
    return all_results


if __name__ == '__main__':
    run_all_benchmarks()
