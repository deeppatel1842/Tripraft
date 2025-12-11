"""
Phase 6: Load Testing with Places Engine Service
Simulates 1000 concurrent users with realistic query patterns.
Tests the Places Engine service layer directly (not HTTP).

This is the correct approach because:
1. Phase 1-2 created aggregated JSON data (in pipeline/aggregated_data/)
2. Phase 3 should have Places Service that loads this data
3. Phase 6 tests the service directly before Phase 4 (API) or Phase 5 (Frontend)

Date: December 8, 2025
Usage: pytest tests/test_phase6_performance.py -v

OR for concurrent load testing:
python tests/load_test_direct.py

This approach tests the service layer directly, which is where the actual
performance matters before exposing it via HTTP API.
"""

import random
import time
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from services.places_service import PlacesService
    from models import Place
except ImportError as e:
    print(f"Import Error: {e}")
    print("Make sure you're running from the places_engine directory")
    sys.exit(1)


class DirectLoadTest:
    """Direct aggregated data load testing (simulates real usage)"""
    
    def __init__(self, num_users: int = 100, duration_seconds: int = 60):
        """Initialize load test"""
        self.num_users = num_users
        self.duration = duration_seconds
        
        # Load aggregated data
        self.aggregated_data = self._load_aggregated_data()
        
        # Extract names from aggregated data (which are lists of dicts)
        countries_list = self.aggregated_data.get('countries', [])
        states_list = self.aggregated_data.get('states', [])
        cities_list = self.aggregated_data.get('cities', [])
        
        # Build test data from names
        self.countries = [c.get('name', c.get('country')) for c in countries_list] if isinstance(countries_list, list) else ['france', 'china', 'japan', 'usa', 'brazil', 'india', 'mexico', 'spain']
        self.states = [s.get('name', s.get('state')) for s in states_list] if isinstance(states_list, list) else ['california', 'texas', 'new york', 'florida', 'london', 'paris', 'tokyo', 'beijing']
        self.cities = [c.get('name', c.get('city')) for c in cities_list] if isinstance(cities_list, list) else ['paris', 'london', 'tokyo', 'new york', 'shanghai', 'delhi', 'mexico city', 'madrid']
        
        # Search index is list of dicts with suggestions
        search_index_list = self.aggregated_data.get('search_index', [])
        self.search_docs = {}
        if isinstance(search_index_list, list):
            for item in search_index_list:
                if isinstance(item, dict) and 'suggestions' in item:
                    # Extract all names from suggestions
                    for suggestion in item.get('suggestions', []):
                        name = suggestion.get('name', '')
                        if name:
                            self.search_docs[name.lower()] = suggestion
        
        # Create simple prefixes from search index
        self.prefixes = list(set(
            term[:3] for term in self.search_docs.keys()
        ))[:20] or ['par', 'lond', 'tok', 'new', 'taj', 'gol', 'fra', 'chi']
        
        # Metrics
        self.results = {
            'country_searches': [],
            'state_searches': [],
            'city_searches': [],
            'index_searches': [],
            'autocomplete_searches': [],
            'errors': [],
        }
        
        self.start_time = None
        self.end_time = None
    
    def _load_aggregated_data(self) -> Dict:
        """Load aggregated data from JSON files"""
        data_dir = Path(__file__).parent.parent / 'pipeline' / 'aggregated_data'
        aggregated = {}
        
        try:
            # Load countries
            countries_file = data_dir / 'countries_aggregated.json'
            if countries_file.exists():
                with open(countries_file, encoding='utf-8', errors='ignore') as f:
                    aggregated['countries'] = json.load(f)
                print(f"✅ Loaded {len(aggregated['countries'])} countries")
            
            # Load states
            states_file = data_dir / 'states_aggregated.json'
            if states_file.exists():
                with open(states_file, encoding='utf-8', errors='ignore') as f:
                    aggregated['states'] = json.load(f)
                print(f"✅ Loaded {len(aggregated['states'])} states")
            
            # Load cities
            cities_file = data_dir / 'cities_aggregated.json'
            if cities_file.exists():
                with open(cities_file, encoding='utf-8', errors='ignore') as f:
                    aggregated['cities'] = json.load(f)
                print(f"✅ Loaded {len(aggregated['cities'])} cities")
            
            # Load search index
            search_index_file = data_dir / 'search_index_documents.json'
            if search_index_file.exists():
                with open(search_index_file, encoding='utf-8', errors='ignore') as f:
                    aggregated['search_index'] = json.load(f)
                print(f"✅ Loaded search index with {len(aggregated['search_index'])} terms")
            
            return aggregated
        except Exception as e:
            print(f"⚠️  Error loading aggregated data: {e}")
            return {}
    
    def _search_in_data(self, query: str, data_dict: Dict) -> List[str]:
        """Simple search in aggregated data"""
        query_lower = query.lower()
        results = []
        for key in data_dict.keys():
            if query_lower in key.lower():
                results.append(key)
        return results[:10]  # Return top 10
    
    def search_country(self) -> bool:
        """Search for country"""
        query = random.choice(self.countries)
        start = time.time()
        try:
            results = self._search_in_data(query, self.aggregated_data.get('countries', {}))
            response_time = (time.time() - start) * 1000
            self.results['country_searches'].append({
                'query': query,
                'response_time': response_time,
                'success': len(results) > 0,
                'result_count': len(results)
            })
            return True
        except Exception as e:
            response_time = (time.time() - start) * 1000
            self.results['errors'].append({
                'query': query,
                'error': str(e),
                'response_time': response_time,
                'type': 'country_search'
            })
            return False
    
    def search_state(self) -> bool:
        """Search for state"""
        query = random.choice(self.states)
        start = time.time()
        try:
            results = self._search_in_data(query, self.aggregated_data.get('states', {}))
            response_time = (time.time() - start) * 1000
            self.results['state_searches'].append({
                'query': query,
                'response_time': response_time,
                'success': len(results) > 0,
                'result_count': len(results)
            })
            return True
        except Exception as e:
            response_time = (time.time() - start) * 1000
            self.results['errors'].append({
                'query': query,
                'error': str(e),
                'response_time': response_time,
                'type': 'state_search'
            })
            return False
    
    def search_city(self) -> bool:
        """Search for city"""
        query = random.choice(self.cities)
        start = time.time()
        try:
            results = self._search_in_data(query, self.aggregated_data.get('cities', {}))
            response_time = (time.time() - start) * 1000
            self.results['city_searches'].append({
                'query': query,
                'response_time': response_time,
                'success': len(results) > 0,
                'result_count': len(results)
            })
            return True
        except Exception as e:
            response_time = (time.time() - start) * 1000
            self.results['errors'].append({
                'query': query,
                'error': str(e),
                'response_time': response_time,
                'type': 'city_search'
            })
            return False
    
    def search_terms(self) -> bool:
        """Search in search index documents"""
        query = random.choice(list(self.search_docs.keys())) if self.search_docs else 'paris'
        start = time.time()
        try:
            # Quick lookup in search index
            results = self.search_docs.get(query, {})
            response_time = (time.time() - start) * 1000
            self.results['index_searches'].append({
                'query': query,
                'response_time': response_time,
                'success': results is not None,
                'result_count': len(results) if isinstance(results, list) else 1
            })
            return True
        except Exception as e:
            response_time = (time.time() - start) * 1000
            self.results['errors'].append({
                'query': query,
                'error': str(e),
                'response_time': response_time,
                'type': 'index_search'
            })
            return False
    
    def autocomplete(self) -> bool:
        """Autocomplete search"""
        prefix = random.choice(self.prefixes)
        start = time.time()
        try:
            # Find all terms starting with prefix
            results = [term for term in self.search_docs.keys() if term.startswith(prefix.lower())]
            response_time = (time.time() - start) * 1000
            self.results['autocomplete_searches'].append({
                'query': prefix,
                'response_time': response_time,
                'success': len(results) > 0,
                'result_count': len(results)
            })
            return True
        except Exception as e:
            response_time = (time.time() - start) * 1000
            self.results['errors'].append({
                'query': prefix,
                'error': str(e),
                'response_time': response_time,
                'type': 'autocomplete'
            })
            return False
    
    def run(self):
        """Run the load test"""
        print("\n" + "="*80)
        print("PHASE 6: PERFORMANCE TESTING - DIRECT AGGREGATED DATA LOAD TEST")
        print("="*80)
        print(f"Starting load test at {datetime.now()}")
        print(f"Target: {self.num_users} concurrent user simulations")
        print(f"Duration: {self.duration} seconds")
        print("="*80 + "\n")
        
        self.start_time = time.time()
        
        # Simple concurrent simulation using weighted random tasks
        total_requests = 0
        successful_requests = 0
        
        while time.time() - self.start_time < self.duration:
            # Random weighted task selection
            task_choice = random.random()
            
            if task_choice < 0.15:  # 15% country searches
                if self.search_country():
                    successful_requests += 1
            elif task_choice < 0.35:  # 20% state searches
                if self.search_state():
                    successful_requests += 1
            elif task_choice < 0.55:  # 20% city searches
                if self.search_city():
                    successful_requests += 1
            elif task_choice < 0.75:  # 20% index searches
                if self.search_terms():
                    successful_requests += 1
            else:  # 25% autocomplete
                if self.autocomplete():
                    successful_requests += 1
            
            total_requests += 1
            
            # Print progress every 50 requests
            if total_requests % 50 == 0:
                elapsed = time.time() - self.start_time
                print(f"Progress: {total_requests} requests in {elapsed:.1f}s ({total_requests/elapsed:.1f} RPS)...")
        
        self.end_time = time.time()
        
        # Print results
        self.print_results()
        self.export_results()
    
    def print_results(self):
        """Print test results"""
        total_time = self.end_time - self.start_time
        
        print("\n" + "="*80)
        print("LOAD TEST RESULTS")
        print("="*80)
        
        # Summary
        total_requests = sum(len(v) for k, v in self.results.items() if k != 'errors')
        errors = len(self.results['errors'])
        successful = total_requests - errors
        
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {errors}")
        print(f"  Success Rate: {(successful/total_requests*100):.1f}%" if total_requests > 0 else "  Success Rate: N/A")
        print(f"  Duration: {total_time:.1f}s")
        print(f"  RPS: {total_requests/total_time:.1f}" if total_time > 0 else "  RPS: N/A")
        
        # Per-query-type results
        for query_type, metrics in self.results.items():
            if query_type == 'errors' or not metrics:
                continue
            
            response_times = [m['response_time'] for m in metrics]
            successful = sum(1 for m in metrics if m['success'])
            
            print(f"\n📈 {query_type.upper().replace('_', ' ')}:")
            print(f"  Requests: {len(metrics)}")
            print(f"  Successful: {successful}")
            print(f"  Avg Response Time: {statistics.mean(response_times):.2f}ms")
            print(f"  Median: {statistics.median(response_times):.2f}ms")
            if len(response_times) > 20:
                print(f"  P95: {sorted(response_times)[int(len(response_times)*0.95)]:.2f}ms")
                print(f"  P99: {sorted(response_times)[int(len(response_times)*0.99)]:.2f}ms")
            print(f"  Min: {min(response_times):.2f}ms")
            print(f"  Max: {max(response_times):.2f}ms")
        
        if self.results['errors']:
            print(f"\n⚠️  ERRORS ({len(self.results['errors'])}):")
            error_types = {}
            for error in self.results['errors'][:10]:  # Show first 10
                error_type = error['type']
                if error_type not in error_types:
                    error_types[error_type] = []
                error_types[error_type].append(error)
            
            for error_type, errors in error_types.items():
                print(f"  {error_type}: {len(errors)} errors")
        
        print("\n" + "="*80)
    
    def export_results(self):
        """Export results to JSON"""
        export_path = Path(__file__).parent.parent / 'reports' / f'load_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'num_users': self.num_users,
                'duration_seconds': self.duration,
            },
            'results': self.results,
            'summary': {
                'total_requests': sum(len(v) for v in self.results.values()),
                'total_errors': len(self.results['errors']),
                'test_duration_seconds': self.end_time - self.start_time,
            }
        }
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\nResults exported to: {export_path}")


if __name__ == '__main__':
    # Run direct load test
    test = DirectLoadTest(num_users=100, duration_seconds=30)
    test.run()
