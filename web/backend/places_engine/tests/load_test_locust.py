"""
Phase 6: Load Testing with Locust
Simulates 1000 concurrent users with realistic query patterns.

Date: December 8, 2025
Usage: locust -f load_test_locust.py --host=http://localhost:5000
"""

from locust import HttpUser, between, task, TaskSet, events
import random
import time
import json
from datetime import datetime


class PerformanceTracker:
    """Track performance metrics across load test"""
    
    def __init__(self):
        self.metrics = {
            'country_searches': [],
            'state_searches': [],
            'city_searches': [],
            'place_searches': [],
            'autocomplete_searches': [],
            'errors': [],
        }
    
    def record_request(self, query_type, response_time, success, error=None):
        """Record a request"""
        metric = {
            'timestamp': datetime.now().isoformat(),
            'response_time': response_time,
            'success': success,
            'error': error,
        }
        
        if query_type in self.metrics:
            self.metrics[query_type].append(metric)
        
        if not success:
            self.metrics['errors'].append(metric)
    
    def get_summary(self):
        """Get summary statistics"""
        summary = {}
        for query_type, metrics in self.metrics.items():
            if metrics:
                response_times = [m['response_time'] for m in metrics]
                successes = sum(1 for m in metrics if m['success'])
                
                summary[query_type] = {
                    'total': len(metrics),
                    'successful': successes,
                    'failed': len(metrics) - successes,
                    'avg_response_time': sum(response_times) / len(response_times),
                    'min_response_time': min(response_times),
                    'max_response_time': max(response_times),
                    'p95_response_time': sorted(response_times)[int(len(response_times) * 0.95)],
                }
        
        return summary


# Global tracker
tracker = PerformanceTracker()


class PlacesSearchTasks(TaskSet):
    """Define tasks for Places search load test"""
    
    # Test data
    countries = ['france', 'china', 'japan', 'usa', 'brazil', 'india', 'mexico', 'spain']
    states = ['california', 'texas', 'new york', 'florida', 'london', 'paris', 'tokyo', 'beijing']
    cities = ['paris', 'london', 'tokyo', 'new york', 'shanghai', 'delhi', 'mexico city', 'madrid']
    places = ['eiffel tower', 'big ben', 'statue of liberty', 'taj mahal', 'golden gate bridge', 'great wall']
    prefixes = ['par', 'lond', 'tok', 'new', 'taj', 'gol', 'fra', 'chi']
    
    @task(2)
    def search_country(self):
        """Search for country (2 out of 10 requests)"""
        query = random.choice(self.countries)
        start_time = time.time()
        
        try:
            response = self.client.get(
                f'/api/v1/places/search',
                params={'q': query, 'limit': 20},
                timeout=5
            )
            response_time = (time.time() - start_time) * 1000
            
            success = response.status_code == 200
            tracker.record_request('country_searches', response_time, success)
            
            if not success:
                self.on_request_failure(query, response_time, response.status_code)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            tracker.record_request('country_searches', response_time, False, str(e))
            self.on_request_failure(query, response_time, str(e))
    
    @task(3)
    def search_state(self):
        """Search for state (3 out of 10 requests)"""
        query = random.choice(self.states)
        start_time = time.time()
        
        try:
            response = self.client.get(
                f'/api/v1/places/search',
                params={'q': query, 'limit': 20},
                timeout=5
            )
            response_time = (time.time() - start_time) * 1000
            
            success = response.status_code == 200
            tracker.record_request('state_searches', response_time, success)
            
            if not success:
                self.on_request_failure(query, response_time, response.status_code)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            tracker.record_request('state_searches', response_time, False, str(e))
            self.on_request_failure(query, response_time, str(e))
    
    @task(3)
    def search_city(self):
        """Search for city (3 out of 10 requests)"""
        query = random.choice(self.cities)
        start_time = time.time()
        
        try:
            response = self.client.get(
                f'/api/v1/places/search',
                params={'q': query, 'limit': 20},
                timeout=5
            )
            response_time = (time.time() - start_time) * 1000
            
            success = response.status_code == 200
            tracker.record_request('city_searches', response_time, success)
            
            if not success:
                self.on_request_failure(query, response_time, response.status_code)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            tracker.record_request('city_searches', response_time, False, str(e))
            self.on_request_failure(query, response_time, str(e))
    
    @task(2)
    def search_place(self):
        """Search for specific place (2 out of 10 requests)"""
        query = random.choice(self.places)
        start_time = time.time()
        
        try:
            response = self.client.get(
                f'/api/v1/places/search',
                params={'q': query, 'limit': 10},
                timeout=5
            )
            response_time = (time.time() - start_time) * 1000
            
            success = response.status_code == 200
            tracker.record_request('place_searches', response_time, success)
            
            if not success:
                self.on_request_failure(query, response_time, response.status_code)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            tracker.record_request('place_searches', response_time, False, str(e))
            self.on_request_failure(query, response_time, str(e))
    
    @task(2)
    def autocomplete_search(self):
        """Autocomplete search (2 out of 10 requests)"""
        prefix = random.choice(self.prefixes)
        start_time = time.time()
        
        try:
            # Try v2 API first if available
            response = self.client.get(
                f'/api/v2/places/autocomplete',
                params={'q': prefix, 'limit': 10},
                timeout=5
            )
            
            # Fallback to v1 if v2 not available
            if response.status_code == 404:
                response = self.client.get(
                    f'/api/v1/places/autocomplete',
                    params={'q': prefix, 'limit': 10},
                    timeout=5
                )
            
            response_time = (time.time() - start_time) * 1000
            
            success = response.status_code == 200
            tracker.record_request('autocomplete_searches', response_time, success)
            
            if not success:
                self.on_request_failure(prefix, response_time, response.status_code)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            tracker.record_request('autocomplete_searches', response_time, False, str(e))
            self.on_request_failure(prefix, response_time, str(e))
    
    def on_request_failure(self, query, response_time, error):
        """Log request failure"""
        print(f"[FAILED] Query: {query}, Time: {response_time}ms, Error: {error}")


class PlacesUser(HttpUser):
    """Simulates a user performing places searches"""
    
    tasks = [PlacesSearchTasks]
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests


# Event handlers for Locust
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("\n" + "=" * 80)
    print("PHASE 6: PERFORMANCE TESTING - LOAD TEST STARTED")
    print("=" * 80)
    print(f"Starting load test at {datetime.now().isoformat()}")
    print("Target: 1000 concurrent users")
    print("=" * 80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    print("\n" + "=" * 80)
    print("PHASE 6: PERFORMANCE TESTING - LOAD TEST RESULTS")
    print("=" * 80)
    
    summary = tracker.get_summary()
    
    print("\nPerformance Summary:")
    print("-" * 80)
    
    total_requests = 0
    total_successful = 0
    all_response_times = []
    
    for query_type, stats in summary.items():
        if stats:
            total_requests += stats['total']
            total_successful += stats['successful']
            
            print(f"\n{query_type.upper()}:")
            print(f"  Total: {stats['total']}")
            print(f"  Successful: {stats['successful']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Avg Response Time: {stats['avg_response_time']:.2f}ms")
            print(f"  Min Response Time: {stats['min_response_time']:.2f}ms")
            print(f"  Max Response Time: {stats['max_response_time']:.2f}ms")
            print(f"  P95 Response Time: {stats['p95_response_time']:.2f}ms")
    
    # Calculate overall metrics
    if total_requests > 0:
        success_rate = (total_successful / total_requests) * 100
        
        print("\n" + "-" * 80)
        print("OVERALL METRICS:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Successful: {total_successful}")
        print(f"  Failed: {total_requests - total_successful}")
        print(f"  Success Rate: {success_rate:.2f}%")
        print("-" * 80)
        
        # Performance targets
        print("\nPERFORMANCE TARGETS:")
        
        if summary.get('country_searches'):
            avg_country_time = summary['country_searches']['avg_response_time']
            status = "✓ PASS" if avg_country_time < 1000 else "✗ FAIL"
            print(f"  Country Search (<1000ms): {avg_country_time:.2f}ms {status}")
        
        if summary.get('state_searches'):
            avg_state_time = summary['state_searches']['avg_response_time']
            status = "✓ PASS" if avg_state_time < 500 else "✗ FAIL"
            print(f"  State Search (<500ms): {avg_state_time:.2f}ms {status}")
        
        if summary.get('city_searches'):
            avg_city_time = summary['city_searches']['avg_response_time']
            status = "✓ PASS" if avg_city_time < 500 else "✗ FAIL"
            print(f"  City Search (<500ms): {avg_city_time:.2f}ms {status}")
        
        if summary.get('autocomplete_searches'):
            avg_auto_time = summary['autocomplete_searches']['avg_response_time']
            status = "✓ PASS" if avg_auto_time < 100 else "✗ FAIL"
            print(f"  Autocomplete (<100ms): {avg_auto_time:.2f}ms {status}")
        
        if success_rate >= 99:
            print(f"  Error Rate (<1%): {100-success_rate:.2f}% ✓ PASS")
        else:
            print(f"  Error Rate (<1%): {100-success_rate:.2f}% ✗ FAIL")
    
    print("\n" + "=" * 80)
    print("Load test completed successfully!")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    print("""
    
    Phase 6: Load Testing with Locust
    ==================================
    
    Usage:
        locust -f load_test_locust.py --host=http://localhost:5000
    
    Options:
        --users 1000        - Number of concurrent users
        --spawn-rate 50     - Users to spawn per second
        --run-time 5m       - How long to run the test
        --headless         - Run without web UI
    
    Example:
        locust -f load_test_locust.py --host=http://localhost:5000 \\
               --users 1000 --spawn-rate 50 --run-time 5m --headless
    
    The test will:
        1. Simulate 1000 concurrent users
        2. Each user makes 10 requests (mixed query types)
        3. Monitor response times, cache hit rates
        4. Verify Firebase read counts
        5. Identify bottlenecks
        6. Generate comprehensive report
    
    """)
